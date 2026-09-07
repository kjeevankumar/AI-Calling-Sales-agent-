import sqlite3
import os

db_path = os.path.join(os.path.dirname(__file__), "calls.db")
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Get all table columns and rows for debugging
cursor.execute("SELECT id, phone_number, lead_name, status FROM calls")
rows = cursor.fetchall()
print("Current DB state:")
for r in rows:
    print(f"ID: {r[0]}, Phone: {r[1]}, Name: {r[2]}, Status: {r[3]}")

# Update all leads to pending
cursor.execute("UPDATE calls SET status = 'pending'")
conn.commit()

print("\nSuccessfully updated all leads to pending!")
conn.close()
