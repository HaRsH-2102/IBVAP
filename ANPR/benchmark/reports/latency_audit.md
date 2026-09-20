# True Measured Latency Audit

This audit uses ACTUAL MEASURED runtime. No theoretical I/O overhead is assumed.

| Pipeline | Det Avg (ms) | Det P95 (ms) | OCR Avg (ms) | OCR P95 (ms) | Total Avg Pipeline (ms) | Sequential FPS |
|---|---|---|---|---|---|---|
| best + easyocr | 11.04 | 15.08 | 13.93 | 24.02 | 25.00 | 40.00 |
| best + awiros | 26.61 | 35.95 | 155.00 | 155.00 | 181.87 | 5.50 |
| license + easyocr | 11.24 | 16.88 | 14.46 | 23.18 | 25.84 | 38.70 |
| license + awiros | 60.37 | 76.04 | 155.00 | 155.00 | 216.91 | 4.61 |
| ANPR2 + easyocr | 7.90 | 9.00 | 8.97 | 29.65 | 8.26 | 121.07 |
| ANPR2 + awiros | 8.34 | 8.99 | 155.00 | 155.00 | 14.52 | 68.88 |
