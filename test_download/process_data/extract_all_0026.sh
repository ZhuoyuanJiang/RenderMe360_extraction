#!/bin/bash
# Complete extraction script for all RenderMe360 subject 0026 performances
# This script extracts all 19 performances with resume capability

# Activate conda environment
source ~/miniconda3/etc/profile.d/conda.sh
conda activate RenderMe360_Data_Processing

# All performances for subject 0026
performances=(
    "e0" "e1" "e2" "e3" "e4" "e5" "e6" "e7" "e8" "e9" "e10" "e11"  # Expressions
    "s1_all" "s2_all" "s3_all" "s4_all" "s5_all" "s6_all"         # Speech  
    "h0"                                                            # Head movement
)

echo "============================================================"
echo "EXTRACTING ALL PERFORMANCES FOR SUBJECT 0026"
echo "Total performances: ${#performances[@]}"
echo "Output: /ssd4/zhuoyuan/renderme360_temp/FULL_EXTRACTION/"
echo "============================================================"
echo ""
echo "Features:"
echo "  ✓ Resume capability - skips already extracted data"
echo "  ✓ Separated output - anno and raw in different folders"
echo "  ✓ Progress tracking - shows extraction progress"
echo ""

# Count already completed extractions
completed=0
for perf in "${performances[@]}"; do
    if [ -f "/ssd4/zhuoyuan/renderme360_temp/FULL_EXTRACTION/0026_${perf}/.extraction_complete" ]; then
        ((completed++))
    fi
done

echo "Progress: $completed/${#performances[@]} performances already extracted"
echo ""

# Extract each performance
success_count=0
failed_list=()

for i in "${!performances[@]}"; do
    perf="${performances[$i]}"
    output_dir="/ssd4/zhuoyuan/renderme360_temp/FULL_EXTRACTION/0026_${perf}"
    
    # Check if already extracted
    if [ -f "${output_dir}/.extraction_complete" ]; then
        echo "[$((i+1))/${#performances[@]}] Skipping $perf - already extracted"
        ((success_count++))
        continue
    fi
    
    echo ""
    echo "============================================================"
    echo "[$((i+1))/${#performances[@]}] Extracting: $perf"
    echo "============================================================"
    
    # Run extraction with auto-confirm
    echo "yes" | python extract_0026_FULL.py --performance "$perf" --separate
    
    if [ $? -eq 0 ]; then
        if [ -f "${output_dir}/.extraction_complete" ]; then
            echo "✓ Successfully extracted $perf"
            ((success_count++))
        else
            echo "⚠ Extraction may be incomplete for $perf"
            failed_list+=("$perf")
        fi
    else
        echo "✗ Failed to extract $perf"
        failed_list+=("$perf")
    fi
done

# Final summary
echo ""
echo "============================================================"
echo "EXTRACTION SUMMARY"
echo "============================================================"
echo "Successfully extracted: $success_count/${#performances[@]}"

if [ ${#failed_list[@]} -gt 0 ]; then
    echo ""
    echo "Failed or incomplete:"
    for perf in "${failed_list[@]}"; do
        echo "  - $perf"
    done
    echo ""
    echo "To retry failed extractions, simply run this script again."
    echo "It will skip already completed extractions."
else
    echo ""
    echo "All performances extracted successfully!"
fi

# Show total size
echo ""
echo "Calculating total extracted size..."
total_size=$(du -sh /ssd4/zhuoyuan/renderme360_temp/FULL_EXTRACTION/ 2>/dev/null | cut -f1)
echo "Total size: $total_size"
echo ""
echo "Output location: /ssd4/zhuoyuan/renderme360_temp/FULL_EXTRACTION/"