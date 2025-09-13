## Task: Create Data Extraction Script for RenderMe360 21ID Dataset with Google Drive Streaming and Selective Extraction

### Background and Current Situation

The RenderMe360 dataset exists in two versions: a 500ID version and a 21ID version. For the 500ID version, we already have a fully functional data extraction script located at `/ssd2/zhuoyuan/renderme360_temp/download_all/process_data_scripts/extract_streaming_gdrive.py`, with its documentation available at `/ssd2/zhuoyuan/renderme360_temp/download_all/process_data_scripts/README_EXTRACTION_SCRIPTS.md`. This existing script has several powerful features that make it particularly valuable for our workflow. It can accept a Google Drive link directly as input and then uses rclone to stream download the data while simultaneously extracting the desired components. Most importantly, during the extraction process, it cleans up the original downloaded data to save memory and storage space, which is a critical feature when dealing with large datasets. This streaming download, extraction, and cleanup logic is essential and must be preserved when we create the extraction script for the 21ID version.

Additionally, the `extract_streaming_gdrive.py` script has an excellent selective extraction functionality that I particularly appreciate. Through a configuration file located at `/ssd2/zhuoyuan/renderme360_temp/download_all/process_data_scripts/config.yaml`, users can specify exactly what they want to extract by selecting specific performances (such as `s1_all` or `e1`), choosing particular subjects, selecting which cameras to include, and determining which modalities to extract. This granular control over the extraction process is extremely useful and should be incorporated into our new script if possible.

### Current 21ID Extraction Script and Its Limitations

We currently have another script at `/ssd2/zhuoyuan/renderme360_temp/test_download/process_data/extract_0026_FULL_both.py`, with related documentation at `/ssd2/zhuoyuan/renderme360_temp/test_download/process_data/README_EXTRACTION_SCRIPTS.md`. This script has the significant advantage of being able to extract everything completely without missing any data components. However, it has a major limitation in that it requires all data to be pre-downloaded to local folders before extraction can begin. The current workflow involves first downloading all data from Google Drive to local directories at `/ssd2/zhuoyuan/renderme360_temp/test_download/anno` and `/ssd2/zhuoyuan/renderme360_temp/test_download/raw`, and only then running the extraction script on these locally stored files. (This subject 0026's data was obtained in the early 2024 release format, where the dataset was split into two separate file types: annotation files (stored in /ssd2/zhuoyuan/renderme360_temp/test_download/anno/) containing metadata, calibration, keypoints, and other processed data, and raw files (stored in /ssd2/zhuoyuan/renderme360_temp/test_download/raw/0026/) containing high-resolution images, and other types of data if there is any. Each performance type (expressions like e0-e11, speech performances like s1_all-s6_all, and head rotation h0) had its own pair of anno and raw SMC files.)

This approach presents several problems for extracting the 21ID dataset. All 21 IDs' data currently reside on Google Drive, and pre-downloading everything to local storage before extraction is inefficient in terms of both time and storage space. Furthermore, it's unclear whether the `extract_0026_FULL_both.py` script is hardcoded specifically for subject 0026 or if it can actually handle any subject ID – this needs to be investigated as part of the development process.

### Required Pipeline Changes and New Script Requirements

The pipeline needs to be fundamentally changed from the current two-step process of downloading then extracting, to a streamlined single-step process that downloads and extracts simultaneously directly from Google Drive. The new script, which should be named `extract_subject_FULL_both.py`, needs to combine the best features of both existing scripts. It should take the complete extraction capability from `extract_0026_FULL_both.py` ensuring that absolutely nothing is missed during extraction, while incorporating the Google Drive streaming functionality from `extract_streaming_gdrive.py` that allows direct downloading from Drive links without intermediate local storage.

The new script must be able to accept a Google Drive link as input and then download data directly from that link for any specified subject ID, not just subject 0026. It should implement the streaming download approach where data is extracted while being downloaded, with immediate cleanup of original files to conserve storage space. Most importantly, it should maintain the complete extraction logic from `extract_0026_FULL_both.py` to ensure that all data components are successfully extracted without any omissions.

### Desired Selective Extraction Capabilities

Beyond the basic requirements, I want the new `extract_subject_FULL_both.py` script to incorporate the selective extraction functionality from `extract_streaming_gdrive.py`. The ultimate goal is to have a script where I can provide a subject ID, specify exactly what needs to be extracted, and indicate which cameras to include, and the script will extract only those specified components. This means implementing support for performance selection where users can choose specific performances like `s1_all` or `e1`, subject filtering to process only selected subjects, camera selection to extract data from specific cameras only, and modality filtering to include only desired modalities in the extraction.

This selective extraction capability should ideally be controlled through a configuration file similar to the `config.yaml` used by `extract_streaming_gdrive.py`, providing a clean and organized way to specify extraction parameters without modifying the script itself. This would give users maximum flexibility in controlling what gets extracted while maintaining the efficiency of the streaming download and extraction process.

### Development Action Items and Validation

The first step is to investigate whether `/ssd2/zhuoyuan/renderme360_temp/test_download/process_data/extract_0026_FULL_both.py` is indeed hardcoded for subject 0026 or if it already has the capability to handle any subject ID. Based on this investigation, the script should be modified to create `extract_subject_FULL_both.py` that integrates the Google Drive streaming functionality from `extract_streaming_gdrive.py` while maintaining all the extraction logic from `extract_0026_FULL_both.py`. The new script should accept subject IDs as parameters rather than having them hardcoded, implement the selective extraction features through configuration files, and ensure that the streaming download, extraction, and cleanup process works seamlessly together.

Once developed, the script must be thoroughly validated to ensure it successfully extracts all selected data components without any omissions, maintains the same level of completeness as `extract_0026_FULL_both.py`, operates efficiently with proper memory management through cleanup during extraction, and correctly implements all selective extraction features. The end goal is a single, powerful script that combines complete extraction capability with Google Drive streaming, memory-efficient operation, and granular control over what gets extracted, all while working flexibly with any specified subject ID from the 21ID dataset.

I will provide Google Drive link for you to test soon.

### Google Drive Structure Differences

当500ID的extraction script的expect的google drive link里面的structure长这样：

Instead of separate anno and raw files, the Google Drive version contains only raw SMC files for each performance. These files follow a consistent naming pattern of [Subject Number]_[Performance]_raw.smc under each subject folder (each subject folder is named in their subject ID, for example "0018", "0026" and etc…), where subject numbers are four-digit codes (like 0018, 0019, etc.), and each subject folder contains 19 files: twelve expression performances (e0 through e11), one head rotation performance (h0), and six speech performances (s1_all through s6_all). The file sizes vary dramatically.

但是我们的21ID的google drive link里面的structure长这样：

#### Top level (Drive folder root)

```
RenderMe-360_release/
├── anno/                         # all annotations, split by subject → performance bundles
├── raw/                          # all raw data, split by subject → performance bundles
├── sample/                       # small sample subset (not used for extraction)
├── Face Attribute Annotation Statement.pdf
├── RenderMe_360_How2Use.zip
├── renderme_360_reader.py
├── test-20-static-text.csv
└── test-20-text-descriptions.csv
```

*For our extractor we only care about: `raw/` and `anno/`.*

#### Subject level (under `raw/` and `anno/`)

Each of these two folders contains **one subfolder per subject ID** (4-digit string like `0026`, `0041`, …):

```
RenderMe-360_release/
├── raw/
│   ├── 0026/
│   ├── 0041/
│   └── … (other subject IDs)
└── anno/
    ├── 0026/
    ├── 0041/
    └── … (other subject IDs)
```

#### Bundle level (inside each subject)

Inside each subject folder you have **one bundle per performance**, distinguished by a suffix that also encodes the **data source** (`raw` vs `anno`).

Bundles are directories whose names end with `.smc` (they are containers for many files/parts inside).

**Name pattern:**

```
<subject_id>_<performance>_<datasource>.smc/
```

**Examples (from your screenshots, subject 0026):**

```
raw/0026/
├── 0026_e0_raw.smc/
├── 0026_e1_raw.smc/
├── 0026_e2_raw.smc/
…
├── 0026_e11_raw.smc/
├── 0026_h0_raw.smc/
├── 0026_s1_all_raw.smc/
├── 0026_s2_all_raw.smc/
…
└── 0026_s6_all_raw.smc/

anno/0026/
├── 0026_e0_anno.smc/
├── 0026_e1_anno.smc/
…
├── 0026_e11_anno.smc/
├── 0026_h0_anno.smc/
├── 0026_s1_all_anno.smc/
…
└── 0026_s6_all_anno.smc/
```

#### Tokens and what they mean (for filtering)

- `subject_id` → 4-digit ID (e.g., `0026`, `0041`, …).
- `performance` → one of the per-subject sequences. From the listing you have:
    - `e0` … `e11` (twelve "e*" sequences)
    - `h0`
    - `s1_all` … `s6_all`
- `datasource` → either `raw` (original captures) or `anno` (annotations/metadata).

### Output Directory Requirements

Also, this time, don't output extracted data in `/ssd2/zhuoyuan/renderme360_temp/FULL_EXTRACTION_BOTH`, this time put extracted data like what we did in `extract_streaming_gdrive.py` and put data in `/ssd2/zhuoyuan/renderme360_temp/test_download` and organize data in a subject folder similarly (for example, look at the folder structure within  in `/ssd2/zhuoyuan/renderme360_temp/download_all`). Note that this extraction file you create should also keep the either separate or combined ability like `extract_0026_FULL.py`.

I also want MANIFEST.csv like in the `/ssd2/zhuoyuan/renderme360_temp/download_all` to document our 21ID version's extraction.