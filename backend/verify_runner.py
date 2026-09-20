import sqlite3
import time
import asyncio
from app.services.validation_runner import runner

async def main():
    vid_id = '09d9f423-93b5-4880-aff1-a779ee7eac8a'
    print('Starting runner...')
    loop = asyncio.get_event_loop()
    runner.start_session(vid_id, loop)
    
    # Wait for processing
    await asyncio.sleep(25)
    
    stats = runner.stats
    print('Frames Processed:', stats.get('frames_processed', 0))
    print('Events Generated:', stats.get('events_generated', 0))
    print('Persons:', stats.get('persons', 0))
    
    runner.stop_session()
    print('Runner stopped.')
    
    # Wait a bit for db writes to complete
    await asyncio.sleep(2)
    
    db_path = r'e:\SIH 2026\IBVAP\backend\m6_events.db'
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    
    cur.execute('SELECT event_id, event_type, track_id, timestamp, metadata FROM security_events')
    rows = cur.fetchall()
    print('ALL EVENTS:')
    for r in rows:
        print(f"ID: {r[0]}, TYPE: {r[1]}, TRACK: {r[2]}, TIME: {r[3]}, META: {r[4]}")
        
    cur.execute('SELECT COUNT(*) FROM evidence_packages')
    print('EVIDENCE:', cur.fetchone()[0])
    
asyncio.run(main())
