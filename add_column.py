import sqlite3

conn = sqlite3.connect('videos.db')
cursor = conn.cursor()
# Add thumbnail_url if not exists
try:
    cursor.execute("ALTER TABLE video ADD COLUMN thumbnail_url TEXT;")
    print("✅ Column 'thumbnail_url' added successfully!")
except sqlite3.OperationalError:
    print("Column 'thumbnail_url' already exists.")

# Add user_id column
try:
    cursor.execute("ALTER TABLE video ADD COLUMN user_id INTEGER NOT NULL DEFAULT 1;")
    print("✅ Column 'user_id' added successfully!")
except sqlite3.OperationalError:
    print("Column 'user_id' already exists.")

conn.commit()
conn.close()
