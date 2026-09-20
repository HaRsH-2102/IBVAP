import time
import asyncio
from app.services.validation_runner import runner
from app.config import settings
import logging
from app.infrastructure.database import SQLiteDatabase
from app.infrastructure.repositories import SecurityEventRepository

logging.basicConfig(level=logging.INFO)

async def test_loitering():
    # Set to run very fast and test a short dwell threshold
    settings.playback_mode = "max_throughput"
    settings.loitering_threshold_seconds = 2
    
    loop = asyncio.get_event_loop()
    print("Starting session with 2s loitering threshold...")
    runner.start_session('C:\\Users\\Harshal\\Downloads\\videoplayback.mp4', loop)
    
    print("Waiting for frames to process (approx 25 seconds)...")
    time.sleep(25) 
    
    runner.stop_session()
    
    print("--- Stats ---")
    print(runner.stats)
    print("Event counts:", runner.stats["event_counts"])
    
    # Check DB using direct sql
    db = SQLiteDatabase()
    import sqlite3
    conn = sqlite3.connect(db.db_path)
    cur = conn.cursor()
    cur.execute("SELECT track_id, timestamp, event_type FROM security_events WHERE event_type='LOITERING'")
    rows = cur.fetchall()
    
    print(f"\nTotal LOITERING events generated in DB: {len(rows)}")
    for r in rows:
        print(f"Track ID: {r[0]}, Timestamp: {r[1]}, Type: {r[2]}")

asyncio.run(test_loitering())
