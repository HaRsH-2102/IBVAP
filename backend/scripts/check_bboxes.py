import sqlite3
import json

conn = sqlite3.connect('m6_events.db')
conn.row_factory = sqlite3.Row
cur = conn.cursor()

cur.execute('SELECT track_id, bbox FROM evidence_packages ORDER BY created_at DESC LIMIT 69')
rows = cur.fetchall()
zeros = sum(1 for r in rows if json.loads(r['bbox']) == {'x1': 0, 'y1': 0, 'x2': 0, 'y2': 0})
print(f'Recent evidence with bbox: {len(rows)}, Zeros: {zeros}')

sample_bbox = [json.loads(r['bbox']) for r in rows if json.loads(r['bbox']) != {'x1': 0, 'y1': 0, 'x2': 0, 'y2': 0}][0]
print("Sample Bbox:", sample_bbox)

