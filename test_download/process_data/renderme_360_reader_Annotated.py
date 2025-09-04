# Import statements for various functionalities
from calendar import c  # Unused import, possibly leftover
from functools import partial  # For creating partial functions (unused in this code)
import json  # For JSON data handling (unused in this code)
from unittest.mock import NonCallableMagicMock  # For testing/mocking (unused)
from pydub import AudioSegment  # Audio processing library for MP3 export

import time  # For timing operations
import cv2  # OpenCV for image processing (decoding compressed images)
import h5py  # For reading HDF5 files (the .smc format is HDF5-based)
import numpy as np  # Numerical operations on arrays
import torch  # PyTorch for deep learning (unused in this code)
import tqdm  # Progress bars for loops
import sys  # System-specific parameters and functions


class SMCReader:
    """
    Main class for reading SenseMocapFile (.smc) files.
    These files contain synchronized multi-modal capture data including:
    - Multi-view RGB images and masks
    - 3D facial/body keypoints
    - Audio recordings
    - FLAME model parameters
    - Camera calibration data
    """

    def __init__(self, file_path):
        """
        Initialize the SMC reader by opening the HDF5 file and extracting metadata.
        
        Args:
            file_path (str): Path to an SMC file (HDF5 format)
        """
        # Open the HDF5 file in read-only mode
        self.smc = h5py.File(file_path, 'r')
        
        # Initialize calibration cache (will be populated on first access)
        self.__calibration_dict__ = None
        
        # Extract top-level metadata attributes
        self.actor_id = self.smc.attrs['actor_id']  # Unique identifier for the person captured
        self.performance_part = self.smc.attrs['performance_part']  # Type of performance (e.g., 'e' for expression, 's' for speech)
        self.capture_date = self.smc.attrs['capture_date']  # When the data was captured
        
        # Create dictionary of actor information
        self.actor_info = dict(
            age=self.smc.attrs['age'],  # Actor's age
            color=self.smc.attrs['color'],  # TODO: Unclear what this represents (skin color? clothing?)
            gender=self.smc.attrs['gender'],  # Actor's gender
            height=self.smc.attrs['height'],  # Height in cm (TODO: verify units)
            weight=self.smc.attrs['weight']  # Weight in kg (TODO: verify units)
        )
        
        # Extract camera setup information
        self.Camera_info = dict(
            num_device=self.smc['Camera'].attrs['num_device'],  # Total number of cameras (typically 60)
            num_frame=self.smc['Camera'].attrs['num_frame'],  # Total frames in the sequence
            resolution=self.smc['Camera'].attrs['resolution'],  # Image resolution [height, width]
        )

    ###info section - Simple getter methods
    def get_actor_info(self):
        """Return the actor information dictionary"""
        return self.actor_info
    
    def get_Camera_info(self):
        """Return the camera setup information dictionary"""
        return self.Camera_info

    
    ### Calibration section - Camera calibration parameters
    def get_Calibration_all(self):  # Method to load and cache ALL cameras' calibration at once
        """
        Get calibration matrices for all cameras and cache them.
        Uses lazy loading - only loads when first requested.
        
        Why calibration is needed for EVERY image:
        - D matrix: Corrects lens distortion (real lenses aren't perfect)
        - K matrix: Projects 3D points to 2D pixels (defines camera's "vision")
        - RT matrix: Positions camera in world space (where it is and where it's looking)
        
        Returns:
            Dictionary with structure:
            {
                'camera_id': {
                    'D': distortion_coefficients,  # [k1, k2, p1, p2, k3] lens distortion
                    'K': intrinsic_matrix,  # 3x3 focal length & principal point
                    'RT': extrinsic_matrix  # 4x4 camera pose in world
                }
            }
        """  
        if self.__calibration_dict__ is not None:  # Check if we've already loaded and cached the calibration
            return self.__calibration_dict__  # Return cached data to avoid expensive disk I/O
        
        self.__calibration_dict__ = dict()  # Initialize empty cache dictionary
        
        for ci in self.smc['Calibration'].keys():  # Loop through all camera IDs: ['00', '01', ..., '59']
            self.__calibration_dict__.setdefault(ci, dict())  # Create nested dict for this camera (same as self.__calibration_dict__[ci] = dict() but safer)
            
            for mt in ['D', 'K', 'RT']:  # Loop through three calibration matrix types
                self.__calibration_dict__[ci][mt] = \
                    self.smc['Calibration'][ci][mt][()]  # Access HDF5 dataset and convert to numpy array with [()] syntax
        
        return self.__calibration_dict__  # Return complete calibration dictionary for all 60 cameras

    def get_Calibration(self, Camera_id):  # Method to get calibration for just ONE specific camera
        """
        Get calibration matrices for a specific camera.
        Each camera has its own calibration because each physical camera is unique.
        
        Args:
            Camera_id (int/str): Camera identifier (0-59)
            
        Returns:
            Dictionary containing 'D', 'K', and 'RT' matrices for the camera
            
        Example usage:
            calib = rd.get_Calibration('25')
            K = calib['K']  # Get intrinsic matrix for camera 25
            # Now can project 3D point to 2D: pixel = K @ point_3d
        """            
        Camera_id = str(Camera_id)  # Convert to string because HDF5 stores keys as '00', '01', not 0, 1
        
        assert Camera_id in self.smc['Calibration'].keys(), f'Invalid Camera_id {Camera_id}'  # Verify this camera exists in calibration data
        
        rs = dict()  # Initialize result dictionary to store the three matrices
        for k in ['D', 'K', 'RT']:  # Loop through each matrix type
            rs[k] = self.smc['Calibration'][Camera_id][k][()]  # Get matrix from HDF5 and convert to numpy with [()]
        return rs  # Return dict with this camera's D, K, and RT matrices

    ### RGB image section - Image data retrieval
    def __read_color_from_bytes__(self, color_array):
        """
        Decode a compressed image from byte array.
        Images are stored compressed (JPEG/PNG) to save space.
        
        Args:
            color_array: Byte array containing compressed image data
            
        Returns:
            Decoded image as numpy array
        """
        # cv2.imdecode decodes the compressed image
        # cv2.IMREAD_COLOR ensures we get a color image (BGR format)
        return cv2.imdecode(color_array, cv2.IMREAD_COLOR)

    def get_img(self, Camera_id, Image_type, Frame_id=None, disable_tqdm=True):  # Main function to retrieve images from any camera/frame
        """
        Retrieve image(s) from the dataset.
        
        Note: Camera_id in this function corresponds directly to calibration ID.
        Each physical camera has unique calibration (Camera 25 → Calibration 25).
        This 1:1 mapping exists because each camera has different:
        - Lens distortion (manufacturing variations)
        - Focal length (slight differences even in "identical" cameras)  
        - Position and orientation in the capture room
        
        Args:
            Camera_id (int/str): Camera ID from '00' to '59'
            Image_type (str): Either 'color' (RGB image) or 'mask' (segmentation mask)
            Frame_id: Can be:
                - int/str: Single frame number
                - list: Multiple frame numbers
                - None: Get all frames (returns as batch)
            disable_tqdm (bool): Whether to show progress bar
            
        Returns:
            Single image: HWC array (2048, 2448, 3) for color, HW for mask
            Multiple images: NHWC array for color, NHW for mask
        """ 
        Camera_id = str(Camera_id)  # Convert to string since HDF5 stores camera IDs as strings like '00', '01', etc.
        
        assert Camera_id in self.smc["Camera"].keys(), f'Invalid Camera_id {Camera_id}'  # Check if camera exists in dataset (must be '00'-'59')
        assert Image_type in self.smc["Camera"][Camera_id].keys(), f'Invalid Image_type {Image_type}'  # Check if this camera has the requested image type ('color' or 'mask')
        assert isinstance(Frame_id, (list, int, str, type(None))), f'Invalid Frame_id datatype {type(Frame_id)}'  # Frame_id must be one of these types
        
        if isinstance(Frame_id, (str, int)):  # Check if requesting a single frame (not a list)
            Frame_id = str(Frame_id)  # Convert to string since frames are stored as strings in HDF5
            assert Frame_id in self.smc["Camera"][Camera_id][Image_type].keys(), f'Invalid Frame_id {Frame_id}'  # Verify this frame exists for this camera/type
            
            if Image_type in ['color', 'mask']:  # Check if it's an image type we need to decode
                img_byte = self.smc["Camera"][Camera_id][Image_type][Frame_id][()]  # Access HDF5 dataset and get compressed bytes with [()] syntax
                img_color = self.__read_color_from_bytes__(img_byte)  # Decompress JPEG/PNG bytes into numpy array using OpenCV
            
            if Image_type == 'mask':  # Masks need special processing
                img_color = np.max(img_color, 2).astype(np.uint8)  # Convert 3-channel mask to 1-channel by taking max across RGB (axis=2)
            
            return img_color  # Return the single processed image
        
        else:  # Handle request for multiple frames (Frame_id is list or None)
            if Frame_id is None:  # User wants all frames from this camera
                Frame_id_list = sorted([int(l) for l in self.smc["Camera"][Camera_id][Image_type].keys()])  # Get all frame numbers, convert to int for sorting, then sort numerically
            elif isinstance(Frame_id, list):  # User provided specific list of frames
                Frame_id_list = Frame_id  # Use the provided list directly
            
            rs = []  # Initialize list to collect all images
            for fi in tqdm.tqdm(Frame_id_list, disable=disable_tqdm):  # Loop through frames with optional progress bar
                rs.append(self.get_img(Camera_id, Image_type, fi))  # Recursively call get_img for each frame
            
            return np.stack(rs, axis=0)  # Stack all images into batch dimension N x H x W x C
    
    def get_audio(self):  # Method to extract synchronized audio data
        """
        Retrieve audio data from the capture session.
        Audio is only available for speech performances (performance_part contains 's').
        
        Returns:
            Dictionary with:
                - 'audio': numpy array of audio samples
                - 'sample_rate': sampling rate in Hz
            Or None if no audio available
        """
        if "s" not in self.performance_part.split('_')[0]:  # Split performance_part by '_' and check if first part contains 's' for speech
            print(f"no audio data in the performance part: {self.performance_part}")  # Inform user why no audio available
            return None  # Return None since this isn't a speech capture
        
        data = self.smc["Camera"]['00']['audio']  # Audio is always stored with camera 00 in the HDF5 structure
        return data  # Return the audio dictionary containing waveform and sample rate
    
    def writemp3(self, f, sr, x, normalized=False):  # Utility function to export audio as MP3
        """
        Export audio data to MP3 file.
        
        Args:
            f: Output file path
            sr: Sample rate in Hz
            x: Audio data as numpy array
            normalized: If True, input is normalized to [-1, 1], else raw int16
            
        Audio channel formats:
            - Mono: Single channel, same sound in both ears
              Shape: (n_samples,) or (n_samples, 1)
            - Stereo: Two channels, different sounds in left/right ears  
              Shape: (n_samples, 2) where column 0=left ear, column 1=right ear
        """
        channels = 2 if (x.ndim == 2 and x.shape[1] == 2) else 1  # Check if stereo (2D array with 2 columns) or mono (1D array or single column)
        
        if normalized:  # Check if audio values are in normalized range [-1, 1]
            y = np.int16(x * 2 ** 15)  # Scale from [-1, 1] to [-32768, 32767] for 16-bit audio
        else:  # Audio is already in int16 format
            y = np.int16(x)  # Ensure it's int16 type
        
        song = AudioSegment(y.tobytes(), frame_rate=sr, sample_width=2, channels=channels)  # Create AudioSegment: tobytes() converts numpy to bytes, sample_width=2 means 16-bit
        song.export(f, format="mp3", bitrate="320k")  # Export to MP3 with high quality 320kbps bitrate

    ### Keypoints2d section - 2D facial landmarks
    def get_Keypoints2d(self, Camera_id, Frame_id=None):  # Method to get 2D facial landmarks from specific camera views
        """
        Get 2D facial keypoints detected in camera images.
        Note: Only cameras 18-32 have keypoint detection results.
        
        Args:
            Camera_id (int/str): Camera ID (must be between 18-32)
            Frame_id: Single frame, list of frames, or None for all frames
            
        Returns:
            Single frame: (106, 2) array of 2D points
            Multiple frames: (N, 106, 2) array
            None if no detection available
            
        Example usage:
            # Get single frame
            kpt = rd.get_Keypoints2d('25', 100)  # Get frame 100 from camera 25
            if kpt is not None:
                nose_tip = kpt[30]  # Get nose tip coordinates (x, y)
            
            # Get multiple frames
            kpts = rd.get_Keypoints2d('25', [100, 101, 102])  # Get 3 frames
            # Returns (3, 106, 2) array
            
            # Get all frames from camera 25
            all_kpts = rd.get_Keypoints2d('25', None)
            
        Why multiple validation stages:
            1. Camera 18-32: Hardware limitation - only these cameras run face detection
            2. Camera has data?: Maybe camera 20 exists but detector failed completely
            3. Frame in range?: Check frame number is valid for entire sequence
            4. Frame has detection?: Maybe person turned away in frame 100
        """ 
        Camera_id = str(Camera_id)  # Convert to string format as HDF5 uses string keys
        
        # VALIDATION STAGE 1: Check if camera is in the valid hardware range (only cameras 18-32 have face detectors)
        assert Camera_id in [f'%02d' % i for i in range(18, 33)], f'Invalid Camera_id {Camera_id}'  # Only cameras 18-32 have 2D keypoints
        assert isinstance(Frame_id, (list, int, str, type(None))), f'Invalid Frame_id datatype: {type(Frame_id)}'  # Validate Frame_id type
        
        # VALIDATION STAGE 2: Check if this specific camera actually has ANY keypoint data (detector might have failed for this camera)
        if Camera_id not in self.smc['Keypoints2d'].keys():  # Check if this camera has any keypoint data at all
            print(f"not lmk2d result in camera id {Camera_id}")  # Inform user no landmarks for this camera
            return None  # Return None since no data exists
        
        if isinstance(Frame_id, (str, int)):  # Handle single frame request
            Frame_id = int(Frame_id)  # Convert to int for validation
            
            # VALIDATION STAGE 3: Check if frame number is within the valid range of the entire sequence
            assert Frame_id >= 0 and Frame_id < self.smc['Keypoints2d'].attrs['num_frame'], f'Invalid frame_index {Frame_id}'  # Check frame is in valid range
            Frame_id = str(Frame_id)  # Convert back to string for HDF5 access
            
            # VALIDATION STAGE 4: Check if THIS SPECIFIC frame has detection results (face might be occluded/turned away)
            if Frame_id not in self.smc['Keypoints2d'][Camera_id].keys() or \
                self.smc['Keypoints2d'][Camera_id][Frame_id] is None or \
                len(self.smc['Keypoints2d'][Camera_id][Frame_id]) == 0:  # Triple check: key exists, not None, not empty
                print(f"not lmk2d result in Camera_id/Frame_id {Camera_id}/{Frame_id}")  # Specific frame has no detection
                return None  # Return None for this frame
            
            return self.smc['Keypoints2d'][Camera_id][Frame_id]  # Return the (106, 2) keypoint array
        
        else:  # Handle multiple frames request
            if Frame_id is None:  # User wants all frames
                return self.smc['Keypoints2d'][Camera_id]  # Return entire dataset for this camera
            elif isinstance(Frame_id, list):  # User provided list of specific frames
                Frame_id_list = Frame_id  # Use provided list
            
            rs = []  # Initialize list to collect keypoints
            for fi in tqdm.tqdm(Frame_id_list):  # Iterate through frames with progress bar
                kpt2d = self.get_Keypoints2d(Camera_id, fi)  # Recursively get each frame's keypoints
                if kpt2d is not None:  # Only add if detection exists
                    rs.append(kpt2d)  # Add to results list
            
            return np.stack(rs, axis=0)  # Stack into (N, 106, 2) array

    ### Keypoints3d section - 3D facial landmarks
    def get_Keypoints3d(self, Frame_id=None):  # Method to get 3D keypoints triangulated from multiple views
        """
        Get 3D facial keypoints in world coordinates.
        These are triangulated from multiple 2D views.
        
        Args:
            Frame_id: Single frame, list of frames, or None for all
            
        Returns:
            Single frame: (106, 3) array of 3D points
            Multiple frames: (N, 106, 3) array
            None if no data available
        """ 
        if isinstance(Frame_id, (str, int)):  # Check if requesting single frame
            Frame_id = int(Frame_id)  # Convert to int for validation
            assert Frame_id >= 0 and Frame_id < self.smc['Keypoints3d'].attrs['num_frame'], \
                f'Invalid frame_index {Frame_id}'  # Validate frame is within sequence bounds
            
            if str(Frame_id) not in self.smc['Keypoints3d'].keys() or \
                len(self.smc['Keypoints3d'][str(Frame_id)]) == 0:  # Check if frame exists and has data
                print(f"get_Keypoints3d: data of frame {Frame_id} do not exist.")  # Inform user of missing data
                return None  # Return None for missing frame
            
            return self.smc['Keypoints3d'][str(Frame_id)]  # Return (106, 3) array of 3D points
        
        else:  # Handle multiple frames
            if Frame_id is None:  # User wants all 3D keypoints
                return self.smc['Keypoints3d']  # Return entire 3D keypoints dataset
            elif isinstance(Frame_id, list):  # User provided specific frames
                Frame_id_list = Frame_id  # Use provided list
            
            rs = []  # Initialize results list
            for fi in tqdm.tqdm(Frame_id_list):  # Iterate with progress bar
                kpt3d = self.get_Keypoints3d(fi)  # Recursively get each frame
                if kpt3d is not None:  # Only add existing data
                    rs.append(kpt3d)  # Add to results
            
            return np.stack(rs, axis=0)  # Stack into (N, 106, 3) array

    ### FLAME section - Parametric face model
    def get_FLAME(self, Frame_id=None):  # Method to get FLAME parametric model data
        """
        Get FLAME parametric face model data.
        FLAME is a statistical 3D face model that represents faces using:
        - Shape parameters (face structure)
        - Expression parameters (facial expressions)
        - Pose parameters (head/jaw/eye rotations)
        
        Only available for expression performances ('e' in performance_part).
        
        Args:
            Frame_id: Single frame, list, or None for all
            
        Returns:
            Dictionary containing:
                - global_pose: (3,) head rotation
                - neck_pose: (3,) neck rotation
                - jaw_pose: (3,) jaw articulation
                - left_eye_pose: (3,) left eye rotation
                - right_eye_pose: (3,) right eye rotation
                - trans: (3,) global translation
                - shape: (100,) identity/shape parameters
                - exp: (50,) expression parameters
                - verts: (5023, 3) 3D mesh vertices
                - albedos: (3, 256, 256) texture maps
        """
        if "e" not in self.performance_part.split('_')[0]:  # Check if this is expression performance
            print(f"no flame data in the performance part: {self.performance_part}")  # Inform user why no FLAME
            return None  # Return None for non-expression captures
        
        if "FLAME" not in self.smc.keys():  # Check if FLAME group exists in HDF5
            print("not flame parameters, please check the performance part.")  # Data might be corrupted
            return None  # Return None if FLAME data missing
        
        flame = self.smc['FLAME']  # Get reference to FLAME group in HDF5
        
        if Frame_id is None:  # User wants all FLAME data
            return flame  # Return entire FLAME dataset
        
        elif isinstance(Frame_id, list):  # User wants specific frames
            frame_list = [str(fi) for fi in Frame_id]  # Convert all frame IDs to strings
            rs = []  # Initialize results list
            for fi in tqdm.tqdm(frame_list):  # Iterate with progress bar
                rs.append(self.get_FLAME(fi))  # Recursively get each frame's FLAME
            return np.stack(rs, axis=0)  # Stack all FLAME dictionaries
        
        elif isinstance(Frame_id, (int, str)):  # Single frame request
            Frame_id = int(Frame_id)  # Convert to int for validation
            assert Frame_id >= 0 and Frame_id < self.smc['FLAME'].attrs['num_frame'], f'Invalid frame_index {Frame_id}'  # Check bounds
            return flame[str(Frame_id)]  # Return FLAME dictionary for this frame
        else:  # Invalid Frame_id type
            raise TypeError('frame_id should be int, list or None.')  # Raise error for invalid type
    
    ### UV texture map section
    def get_uv(self, Frame_id=None, disable_tqdm=True):  # Method to get UV texture maps
        """
        Get UV texture map - a 2D "unwrapped" representation of facial texture.
        Think of it like unwrapping a 3D face onto a flat image.
        Only available for expression performances.
        
        Args:
            Frame_id: Single frame, list, or None for all
            disable_tqdm: Whether to show progress bar
            
        Returns:
            Single frame: HWC image in BGR format
            Multiple frames: NHWC batch of images
        """
        if "e" not in self.performance_part.split('_')[0]:  # Check if expression performance
            print(f"no uv data in the performance part: {self.performance_part}")  # Inform user why no UV
            return None  # Return None for non-expression captures
        
        if "UV_texture" not in self.smc.keys():  # Check if UV_texture group exists
            print("not uv texture, please check the performance part.")  # Data might be missing
            return None  # Return None if UV data missing
        
        assert isinstance(Frame_id, (list, int, str, type(None))), f'Invalid Frame_id datatype {type(Frame_id)}'  # Validate Frame_id type
        
        if isinstance(Frame_id, (str, int)):  # Handle single frame request
            Frame_id = str(Frame_id)  # Convert to string for HDF5 access
            assert Frame_id in self.smc['UV_texture'].keys(), f'Invalid Frame_id {Frame_id}'  # Check frame exists
            
            img_byte = self.smc['UV_texture'][Frame_id][()]  # Get compressed UV texture bytes
            img_color = self.__read_color_from_bytes__(img_byte)  # Decode JPEG/PNG to numpy array
            return img_color  # Return decoded UV map
        
        else:  # Handle multiple frames
            if Frame_id is None:  # User wants all UV textures
                Frame_id_list = sorted([int(l) for l in self.smc['UV_texture'].keys()])  # Get all frames sorted numerically
            elif isinstance(Frame_id, list):  # User provided specific frames
                Frame_id_list = Frame_id  # Use provided list
            
            rs = []  # Initialize results list
            for fi in tqdm.tqdm(Frame_id_list, disable=disable_tqdm):  # Iterate with optional progress bar
                rs.append(self.get_uv(fi))  # Recursively get each UV map
            
            return np.stack(rs, axis=0)  # Stack into (N, H, W, 3) batch
    
    ### Scan mesh section - High-resolution 3D reconstruction
    def get_scanmesh(self):  # Method to get high-res 3D scan
        """
        Get high-resolution 3D scan mesh from dense reconstruction pipeline.
        This is a detailed 3D surface reconstruction of the face/head.
        Only available for expression performances.
        
        Returns:
            Dictionary with:
                - 'vertex': (n, 3) array of 3D vertex positions
                - 'vertex_indices': (m, 3) array of triangle indices
        """
        if "e" not in self.performance_part.split('_')[0]:  # Check if expression performance
            print(f"no scan mesh data in the performance part: {self.performance_part}")  # Inform user why no scan
            return None  # Return None for non-expression captures
        
        data = self.smc["Scan"]  # Get reference to Scan group in HDF5
        return data  # Return scan dictionary with vertices and indices
    
    def write_ply(self, scan, outpath):  # Utility to export 3D mesh
        """
        Export 3D scan mesh to PLY format for visualization.
        PLY is a standard 3D mesh format readable by MeshLab, Blender, etc.
        
        Args:
            scan: Dictionary with 'vertex' and 'vertex_indices'
            outpath: Output file path for .ply file
        """
        from plyfile import PlyData, PlyElement  # Import PLY library for mesh export
        
        vertex = np.empty(len(scan['vertex']), dtype=[('x', 'f4'), ('y', 'f4'), ('z', 'f4')])  # Create structured array for vertices
        for i in range(len(scan['vertex'])):  # Iterate through all vertices
            vertex[i] = np.array([(scan['vertex'][i, 0], scan['vertex'][i, 1], scan['vertex'][i, 2])], \
                        dtype=[('x', 'f4'), ('y', 'f4'), ('z', 'f4')])  # Pack x,y,z into structured format
        
        triangles = scan['vertex_indices']  # Get triangle definitions (face connectivity)
        
        face = np.empty(len(triangles), dtype=[('vertex_indices', 'i4', (3,)),
                           ('red', 'u1'), ('green', 'u1'),
                           ('blue', 'u1')])  # Create structured array for faces with color
        
        for i in range(len(triangles)):  # Iterate through all triangles
            face[i] = np.array([
                ([triangles[i, 0], triangles[i, 1], triangles[i, 2]], 255, 255, 255)  # Triangle vertices + white color (255,255,255)
            ],
            dtype=[('vertex_indices', 'i4', (3,)),
                ('red', 'u1'), ('green', 'u1'),
                ('blue', 'u1')])  # Pack triangle and color data
        
        PlyData([
                PlyElement.describe(vertex, 'vertex'),  # Create vertex element
                PlyElement.describe(face, 'face')  # Create face element
                ], text=True).write(outpath)  # Write as text PLY (human-readable)

    def get_scanmask(self, Camera_id=None):  # Method to get scan segmentation masks
        """
        Get segmentation mask for the 3D scan from each camera view.
        These masks indicate which pixels belong to the scanned object.
        
        Args:
            Camera_id: Specific camera ID or None for all cameras
            
        Returns:
            Single camera: HW (2048, 2448) binary mask
            All cameras: NHW (60, 2048, 2448) batch of masks
        """ 
        if Camera_id is None:  # User wants masks from all cameras
            rs = []  # Initialize results list
            for i in range(60):  # Iterate through all 60 cameras
                rs.append(self.get_scanmask(f'{i:02d}'))  # Recursively get each camera's mask
            return np.stack(rs, axis=0)  # Stack into (60, H, W) batch
        
        assert isinstance(Camera_id, (str, int)), f'Invalid Camera_id type {Camera_id}'  # Validate Camera_id type
        Camera_id = str(Camera_id)  # Convert to string for HDF5 access
        assert Camera_id in self.smc["Camera"].keys(), f'Invalid Camera_id {Camera_id}'  # Check camera exists
        
        img_byte = self.smc["ScanMask"][Camera_id][()]  # Get compressed mask bytes
        img_color = self.__read_color_from_bytes__(img_byte)  # Decode to numpy array
        
        img_color = np.max(img_color, 2).astype(np.uint8)  # Convert RGB to single channel by taking max
        return img_color  # Return binary mask           

### Test function - Demonstrates usage of all methods
if __name__ == '__main__':  # Only run this code if script is executed directly, not imported
    actor_part = sys.argv[1]  # Get performance identifier from command line (e.g., 'actor01_e_001')
    
    st = time.time()  # Record start time for performance measurement
    print("reading smc: {}".format(actor_part))  # Print which file is being loaded
    
    rd = SMCReader(f'/mnt/lustre/share_data/pandongwei/RenFace_waic/{actor_part}.smc')  # Initialize reader with full path to SMC file
    print("SMCReader done, in %f sec\n" % (time.time() - st), flush=True)  # Print load time, flush ensures immediate output
    
    print(rd.get_actor_info())  # Print actor metadata (age, gender, height, weight)
    print(rd.get_Camera_info())  # Print camera setup (60 devices, resolution, frame count)
    
    Camera_id = "25"  # Select camera 25 for testing
    Frame_id = 0  # Select first frame for testing

    # image = rd.get_img(Camera_id, 'color', Frame_id)  # Example: Load single RGB image from camera 25, frame 0
    # print(f"image.shape: {image.shape}")  # Would print: (2048, 2448, 3) - height, width, BGR channels
    # images = rd.get_img('04','color',disable_tqdm=False)  # Example: Load ALL frames from camera 04 with progress bar
    # print(f'color {images.shape}, {images.dtype}')  # Would print batch shape and uint8 dtype
    
    # mask = rd.get_img(Camera_id, 'mask', Frame_id)  # Example: Load segmentation mask
    # print(f"mask.shape: {mask.shape}")  # Would print: (2048, 2448) - single channel mask
    # l = [10, 13]  # List of specific frame numbers
    # mask = rd.get_img(13,'mask', l, disable_tqdm=False)  # Example: Get masks for frames 10 and 13 from camera 13
    # mask = rd.get_img(13,'mask',disable_tqdm=False)  # Example: Get ALL masks from camera 13
    # print(f' mask {mask.dtype} {mask.shape}')  # Would print dtype and batch dimensions

    # cameras = rd.get_Calibration_all()  # Example: Load all 60 cameras' calibration matrices
    # print(f"all_calib 30 RT: {cameras['30']['RT']}")  # Example: Print camera 30's extrinsic matrix (4x4 pose)
    # camera = rd.get_Calibration(15)  # Example: Get just camera 15's calibration
    # print(' split_calib ',camera)  # Would print dict with 'D', 'K', 'RT' matrices

    if '_s' in actor_part:  # Check if filename contains '_s' indicating speech performance with audio
        audio = rd.get_audio()  # Get audio dictionary
        print('audio', audio['audio'].shape, 'sample_rate', np.array(audio['sample_rate']))  # Print audio array shape and sample rate
        
        sr = int(np.array(audio['sample_rate']))  # Convert sample rate to integer
        arr = np.array(audio['audio'])  # Get audio waveform as numpy array
        rd.writemp3(f='./test.mp3', sr=sr, x=arr, normalized=True)  # Export audio to MP3 file in current directory
    
    lmk2d = rd.get_Keypoints2d('25', 4)  # Get 2D landmarks from camera 25, frame 4
    print('kepoint2d', lmk2d.shape)  # Should print: (106, 2) - 106 facial points with x,y coordinates
    
    lmk2ds = rd.get_Keypoints2d('26', [1, 2, 3, 4, 5])  # Get 2D landmarks for multiple specific frames
    print(f"lmk2ds.shape: {lmk2ds.shape}")  # Should print: (5, 106, 2) - batch of 5 frames
    
    lmk3d = rd.get_Keypoints3d(4)  # Get 3D landmarks for frame 4
    print(f'kepoint3d shape: {lmk3d.shape}')  # Should print: (106, 3) - 106 points with x,y,z coordinates
    
    lmk3d = rd.get_Keypoints3d([1, 2, 3, 4, 5])  # Get 3D landmarks for multiple frames
    print(f'kepoint3d shape: {lmk3d.shape}')  # Should print: (5, 106, 3) - batch of 5 frames
    
    if '_e' in actor_part:  # Check if filename contains '_e' indicating expression performance
        flame = rd.get_FLAME(56)  # Get FLAME parameters for frame 56
        print(f"keys: {flame.keys()}")  # Print all FLAME parameter names
        
        print(f"global_pose: {flame['global_pose'].shape}")  # (3,) - head rotation angles
        print(f"neck_pose: {flame['neck_pose'].shape}")  # (3,) - neck rotation angles  
        print(f"jaw_pose: {flame['jaw_pose'].shape}")  # (3,) - jaw articulation angles
        print(f"left_eye_pose: {flame['left_eye_pose'].shape}")  # (3,) - left eye gaze angles
        print(f"right_eye_pose: {flame['right_eye_pose'].shape}")  # (3,) - right eye gaze angles
        print(f"trans: {flame['trans'].shape}")  # (3,) - global translation in world space
        print(f"shape: {flame['shape'].shape}")  # (100,) - face identity/structure parameters
        print(f"exp: {flame['exp'].shape}")  # (50,) - facial expression parameters
        print(f"verts: {flame['verts'].shape}")  # (5023, 3) - 3D mesh vertex positions
        print(f"albedos: {flame['albedos'].shape}")  # (3, 256, 256) - RGB texture maps
        
        flame = rd.get_FLAME()  # Get ALL frames' FLAME data
        print(f"keys: {flame.keys()}")  # Print frame numbers available
    
    if '_e' in actor_part:  # Check for expression performance
        uv = rd.get_uv(Frame_id)  # Get UV texture map for specific frame
        print(f"uv shape: {uv.shape}")  # Print UV map dimensions (H, W, 3)
        
        uv = rd.get_uv()  # Get ALL UV texture maps
        print(f"uv shape: {uv.shape}")  # Print batch dimensions (N, H, W, 3)
    
    if '_e' in actor_part:  # Check for expression performance
        scan = rd.get_scanmesh()  # Get high-resolution 3D scan mesh
        print(f"keys: {scan.keys()}")  # Should print: ['vertex', 'vertex_indices']
        print(f"vertex: {scan['vertex'].shape}")  # Print number of 3D vertices (n, 3)
        print(f"vertex_indices: {scan['vertex_indices'].shape}")  # Print number of triangles (m, 3)
        
        rd.write_ply(scan, './test_scan.ply')  # Export mesh to PLY file for visualization in MeshLab/Blender
    
    if '_e' in actor_part:  # Check for expression performance
        scanmask = rd.get_scanmask('03')  # Get scan mask from camera 03
        print(f"scanmask.shape: {scanmask.shape}")  # Should print: (2048, 2448) - binary mask
        
        scanmask = rd.get_scanmask()  # Get scan masks from ALL 60 cameras
        print(f"scanmask.shape all: {scanmask.shape}")  # Should print: (60, 2048, 2448) - batch of masks