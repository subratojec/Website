import sqlite3
import re

conn = sqlite3.connect('cms.db')
cursor = conn.cursor()

cursor.execute("SELECT id, content FROM journal_entries ORDER BY id DESC LIMIT 1;")
row = cursor.fetchone()
if row:
    entry_id, content = row
    
    # Use regex to find and replace the broken image tag at the end
    # We will replace everything after "architectures." with a proper image
    parts = content.split("architectures.")
    if len(parts) > 1:
        new_content = parts[0] + "architectures.\n\n![kubernetes image](https://upload.wikimedia.org/wikipedia/commons/3/39/Kubernetes_logo_without_workmark.svg)"
        cursor.execute("UPDATE journal_entries SET content = ? WHERE id = ?", (new_content, entry_id))
        conn.commit()
        print("Fixed database!")
    else:
        print("Could not find split point")
conn.close()
