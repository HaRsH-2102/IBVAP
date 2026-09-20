# ANPR Latency Audit

Latency is calculated per frame sequentially. Total Latency = Avg Detection Time + (Avg Plates per Image * Avg OCR Time) + Assumed I/O Overhead (15ms). FPS = 1000 / Total Latency.

| Dataset | Detector | OCR | Avg Det (ms) | Avg OCR (ms) | Plates/Img | Total Latency (ms) | FPS |
|---|---|---|---|---|---|---|---|
| State-wise_OLX | ANPR2 | awiros | 8.34 | 158.83 | 0.04 | 29.67 | 33.70 |
| State-wise_OLX | ANPR2 | easyocr | 7.90 | 8.97 | 0.04 | 23.26 | 42.99 |
| State-wise_OLX | best | awiros | 26.61 | 155.01 | 1.00 | 196.88 | 5.08 |
| State-wise_OLX | best | easyocr | 11.04 | 13.93 | 1.00 | 40.00 | 25.00 |
| State-wise_OLX | license | awiros | 60.37 | 154.57 | 1.01 | 231.47 | 4.32 |
| State-wise_OLX | license | easyocr | 11.24 | 14.46 | 1.01 | 40.84 | 24.48 |
| video_images | ANPR2 | awiros | 8.82 | 156.53 | 0.02 | 27.41 | 36.48 |
| video_images | ANPR2 | easyocr | 9.22 | 20.21 | 0.02 | 24.68 | 40.51 |
| video_images | best | awiros | 24.64 | 154.88 | 1.00 | 194.76 | 5.13 |
| video_images | best | easyocr | 11.42 | 19.94 | 1.00 | 46.39 | 21.56 |
| video_images | license | awiros | 56.22 | 155.59 | 1.04 | 233.23 | 4.29 |
| video_images | license | easyocr | 11.89 | 19.57 | 1.04 | 47.26 | 21.16 |
