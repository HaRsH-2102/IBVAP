# State-wise_OLX OCR-Only Evaluation

Evaluated on perfectly cropped ground-truth plates.

| OCR Engine | Total Plates | Empty Reads | Exact Match (Raw) | Exact Match (Norm) | Char Acc | CER | Avg Latency (ms) | P50 (ms) | P95 (ms) |
|---|---|---|---|---|---|---|---|---|---|
| easyocr | 602 | 73 | 0.0050 | 0.0631 | 0.5879 | 0.4213 | 22.23 | 18.67 | 34.00 |
| awiros | 602 | 0 | 0.8322 | 0.8322 | 0.9680 | 0.0330 | 2420.89 | 2240.41 | 2379.38 |
