import sqlite3
db_path = 'm6_events.db'
conn = sqlite3.connect(db_path)
cursor = conn.cursor()
cursor.execute("SELECT name, file_path FROM video_sources")
for row in cursor.fetchall():
    print(row)
