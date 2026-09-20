# video_images Final Benchmark Report (True GT)

> [!IMPORTANT]
> This benchmark uses TRUE Ground-Truth extracted from Pascal VOC XML annotations.

## Dataset
- **Path:** `E:\ANPR\video_images`
- **Source Images:** 654
- **GT Images (XML):** 654
- **Matched Images:** 654
- **Missing GT:** 0
- **Format:** Pascal VOC Bounding Box & Text

## Latency Metrics
| Model | Det Avg ms | Det P50 ms | Det P95 ms | OCR Avg ms | OCR P50 ms | OCR P95 ms | Total Avg ms | FPS |
|---|---|---|---|---|---|---|---|---|
| best + awiros | 12.7 | 9.5 | 13.0 | 9.6 | 9.2 | 10.4 | 22.3 | 44.77 |
| license + awiros | 12.3 | 9.0 | 32.9 | 9.9 | 9.3 | 13.2 | 22.3 | 44.87 |

## Dataset Leakage Warning
> [!WARNING]
> **TRAINING OVERLAP UNKNOWN:** It cannot be definitively confirmed if these models were independently trained from this dataset.
