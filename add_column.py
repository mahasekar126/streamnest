import sqlite3

conn = sqlite3.connect('videos.db')
cursor = conn.cursor()
cursor.execute("ALTER TABLE video ADD COLUMN thumbnail_url TEXT;")
conn.commit()
conn.close()

print("✅ Column 'thumbnail_url' added successfully!")
