import sqlite3
import os
import time
from urllib import request

db_path = 'm6_events.db'
conn = sqlite3.connect(db_path)
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

# Get one event that has evidence
cursor.execute("SELECT * FROM evidence_packages WHERE crop_path IS NOT NULL LIMIT 1")
ev = cursor.fetchone()

print("==============================")
print("1. EXACT EVENT-FRAME TEST")
print("==============================")
if ev:
    ev_dict = dict(ev)
    cursor.execute("SELECT * FROM security_events WHERE event_id = ?", (ev_dict['security_event_id'],))
    event = cursor.fetchone()
    
    if event:
        e_dict = dict(event)
        print(f"event_id: {e_dict['event_id']}")
        print(f"evidence frame_id: {ev_dict['frame_id']}")
        print(f"track_id: {e_dict['track_id']}")
        print(f"bbox: {ev_dict['bbox']}")
        # Wait, security_events doesn't have frame_id directly, it has timestamp. Let's compare timestamps.
        event_timestamp = e_dict['timestamp']
        evidence_timestamp = ev_dict['timestamp']
        print(f"event timestamp: {event_timestamp}")
        print(f"evidence timestamp: {evidence_timestamp}")
        
        if event_timestamp == evidence_timestamp:
            print("PASS")
        else:
            print("FAIL")
else:
    print("No evidence found")

print("\n==============================")
print("3. DELETE TEST")
print("==============================")
cursor.execute("SELECT * FROM evidence_packages WHERE crop_path IS NOT NULL LIMIT 1 OFFSET 1")
ev_del = cursor.fetchone()
if ev_del:
    ev_del_dict = dict(ev_del)
    event_id_to_del = ev_del_dict['security_event_id']
    crop_path = ev_del_dict['crop_path']
    full_path = ev_del_dict['full_frame_path']
    
    req = request.Request(f'http://localhost:8000/api/v1/validation/evidence/{event_id_to_del}/delete', method='POST')
    try:
        resp = request.urlopen(req)
        resp_data = resp.read()
    except Exception as e:
        print(f"Delete API error: {e}")
        
    time.sleep(1)
    if os.path.exists(crop_path):
        print(f"Crop file still exists: {crop_path}")
        del_pass = False
    elif os.path.exists(full_path):
        print(f"Full file still exists: {full_path}")
        del_pass = False
    else:
        cursor.execute("SELECT * FROM evidence_packages WHERE security_event_id = ?", (event_id_to_del,))
        if cursor.fetchone() is not None:
            print("DB record still exists")
            del_pass = False
        else:
            del_pass = True
            
    print("PASS" if del_pass else "FAIL")

print("\n==============================")
print("4. TWO-HOUR EXPIRATION TEST")
print("==============================")
cursor.execute("SELECT * FROM evidence_packages WHERE crop_path IS NOT NULL LIMIT 1 OFFSET 2")
ev_exp = cursor.fetchone()
if ev_exp:
    ev_exp_dict = dict(ev_exp)
    event_id_exp = ev_exp_dict['security_event_id']
    crop_path_exp = ev_exp_dict['crop_path']
    
    import datetime
    past = (datetime.datetime.utcnow() - datetime.timedelta(minutes=5)).isoformat()
    cursor.execute("UPDATE evidence_packages SET expires_at = ?, is_saved = 0 WHERE security_event_id = ?", (past, event_id_exp))
    conn.commit()
    
    print(f"Set {event_id_exp} to expire at {past}. Wait manually for cleanup worker...")
    
print("\n==============================")
print("5. SAVE PERSISTENCE TEST")
print("==============================")
cursor.execute("SELECT * FROM evidence_packages WHERE crop_path IS NOT NULL LIMIT 1 OFFSET 3")
ev_save = cursor.fetchone()
if ev_save:
    ev_save_dict = dict(ev_save)
    event_id_save = ev_save_dict['security_event_id']
    
    req = request.Request(f'http://localhost:8000/api/v1/validation/evidence/{event_id_save}/save', method='POST')
    try:
        resp = request.urlopen(req)
        resp_data = resp.read()
    except Exception as e:
        print(f"Save API error: {e}")
        
    cursor.execute("SELECT * FROM evidence_packages WHERE security_event_id = ?", (event_id_save,))
    after_save = dict(cursor.fetchone())
    print(f"is_saved: {after_save['is_saved']}, expires_at: {after_save['expires_at']}, saved_at: {after_save['saved_at']}")
    save_pass = after_save['is_saved'] == 1 and after_save['expires_at'] is None and after_save['saved_at'] is not None
    print("PASS" if save_pass else "FAIL")

print("\n==============================")
print("CHECK EXPIRATION RECORD")
cursor.execute("SELECT * FROM evidence_packages WHERE security_event_id = '08850026-fbe7-4796-9de5-e9518eeea37a'")
row = cursor.fetchone()
print("PASS" if row is None else "FAIL")

conn.close()
