import sqlite3
import os
import glob

db_path = 'm6_events.db'
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

tables_to_clear = [
    'security_events',
    'alerts',
    'evidence_packages',
    'incident_clips',
    'anpr_reads'
]

print('--- PRE-RESET SAFETY CHECK ---')
print(f'1. Database file being modified: {os.path.abspath(db_path)}')
print(f'2. Tables that will be cleared: {", ".join(tables_to_clear)}')

evidence_dir = os.path.abspath('results/evidence')
print(f'3. Runtime evidence directories that will be cleaned: {evidence_dir}')

# Let's count existing rows
print('\n--- CURRENT ROW COUNTS ---')
for table in tables_to_clear:
    cursor.execute(f"SELECT COUNT(*) FROM {table}")
    print(f'{table}: {cursor.fetchone()[0]} rows')

print('\n--- DELETING ROWS ---')
for table in tables_to_clear:
    cursor.execute(f"DELETE FROM {table}")
    deleted = cursor.rowcount
    print(f'Cleared {deleted} rows from {table}')
conn.commit()

print('\n--- CLEANING EVIDENCE FILES ---')
evidence_files_removed = 0
for root, dirs, files in os.walk(evidence_dir):
    for f in files:
        if f.endswith(('.jpg', '.png', '.mp4', '.json')):
            file_path = os.path.join(root, f)
            os.remove(file_path)
            evidence_files_removed += 1

print(f'Removed {evidence_files_removed} runtime evidence files from {evidence_dir}')

print('\n--- POST-RESET VERIFICATION ---')
for table in tables_to_clear:
    cursor.execute(f"SELECT COUNT(*) FROM {table}")
    print(f'{table}: {cursor.fetchone()[0]} rows')

conn.close()
