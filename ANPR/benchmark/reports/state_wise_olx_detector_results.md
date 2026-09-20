# State-wise_OLX Detector Evaluation

This evaluation uses exact bounding box matching against Pascal VOC XML ground truth.

| Detector | IoU | TP | FP | FN | Precision | Recall | F1 | mIoU | GT Plates | Pred Instances |
|---|---|---|---|---|---|---|---|---|---|---|
| best | >= 0.50 | 602 | 1 | 0 | 0.9983 | 1.0000 | 0.9992 | 0.9175 | 602 | 603 |
| best | >= 0.75 | 599 | 4 | 3 | 0.9934 | 0.9950 | 0.9942 | 0.9186 | 602 | 603 |
| license | >= 0.50 | 601 | 7 | 1 | 0.9885 | 0.9983 | 0.9934 | 0.8226 | 602 | 608 |
| license | >= 0.75 | 501 | 107 | 101 | 0.8240 | 0.8322 | 0.8281 | 0.8469 | 602 | 608 |
| ANPR2 | >= 0.50 | 0 | 24 | 602 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 602 | 24 |
| ANPR2 | >= 0.75 | 0 | 24 | 602 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 602 | 24 |
