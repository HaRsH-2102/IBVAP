import sqlite3
import json

db_path = 'm6_events.db'
conn = sqlite3.connect(db_path, check_same_thread=False)
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

event_id = 'dcb5abd0-2ae0-45bb-aded-86bd5fc4023f'
plate = 'TEST1234'

cursor.execute("SELECT camera_id, track_id, timestamp, metadata FROM security_events WHERE event_id = ?", (event_id,))
event = cursor.fetchone()
if not event:
    print('Event not found')
    exit(1)

cursor.execute("SELECT * FROM anpr_reads WHERE event_id = ?", (event_id,))
existing = cursor.fetchone()

try:
    if existing:
        cursor.execute('''
            UPDATE anpr_reads 
            SET operator_plate_text = ?, entry_source = 'OPERATOR' 
            WHERE event_id = ?
        ''', (plate, event_id))
        print("Updated existing")
    else:
        vehicle_class = ''
        if event[3]:
            try:
                meta = json.loads(event[3])
                vehicle_class = meta.get('object_class', '')
            except: pass
            
        cursor.execute('''
            INSERT INTO anpr_reads (
                event_id, camera_id, track_id, plate_text, vehicle_class, timestamp, 
                created_at, status, entry_source, operator_plate_text
            ) VALUES (?, ?, ?, '', ?, ?, datetime('now'), 'NO_AI_DATA', 'OPERATOR', ?)
        ''', (event_id, event[0], event[1], vehicle_class, event[2], plate))
        print("Inserted new")
except Exception as e:
    import traceback
    traceback.print_exc()

