import sqlite3
from datetime import datetime

DB_FILE = "message_history.db"

conn = sqlite3.connect(DB_FILE, check_same_thread=False)
cursor = conn.cursor()

# Create table if it doesn't exist
cursor.execute('''
CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    role TEXT NOT NULL,
    content TEXT NOT NULL,
    timestamp TEXT NOT NULL
)
''')
conn.commit()

def save_message(role, content):
    timestamp = datetime.utcnow().isoformat()
    cursor.execute('INSERT INTO messages (role, content, timestamp) VALUES (?, ?, ?)',
                   (role, content, timestamp))
    conn.commit()

def get_all_messages():
    cursor.execute('SELECT role, content, timestamp FROM messages ORDER BY id')
    return cursor.fetchall()
