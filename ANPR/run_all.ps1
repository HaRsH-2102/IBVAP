$detectors = @(
    "e:\ANPR\ANPR-Indian-License-Plate-Detection\license.pt",
    "e:\ANPR\ANPR-Indian-License-Plate-Detection\ANPR2.pt",
    "e:\ANPR\Auto-Num-Plate-Recognition\best.pt"
)

$ocrs = @("easyocr", "awiros")
$datasets = @("e:\ANPR\State-wise_OLX", "e:\ANPR\video_images")

foreach ($ds in $datasets) {
    $ds_name = Split-Path $ds -Leaf
    foreach ($det in $detectors) {
        $det_name = [System.IO.Path]::GetFileNameWithoutExtension($det)
        foreach ($ocr in $ocrs) {
            $output_file = "e:\ANPR\benchmark\results\${ds_name}_${det_name}_${ocr}.json"
            Write-Host "Running Benchmark: Det=${det_name}, OCR=${ocr}, Dataset=${ds_name}"
            conda run -p e:\ANPR\environments\benchmark python e:\ANPR\benchmark\runner.py --detector $det --ocr $ocr --dataset $ds --output $output_file
        }
    }
}
Write-Host "All benchmarks completed!"
