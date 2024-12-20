import os
import shutil
import sqlite3
import datetime

# Step 1: Create the backup folder
backup_folder = "backup"
if not os.path.exists(backup_folder):
    os.makedirs(backup_folder)
    print(f"Backup folder created at: {backup_folder}")
else:
    print(f"Backup folder already exists at: {backup_folder}")

# Step 2: Timestamp for backup files
timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")

# Step 3: Copy the SQLite database
db_file = "products.db"
backup_db_file = os.path.join(backup_folder, f"products_backup_{timestamp}.db")
shutil.copy2(db_file, backup_db_file)
print(f"Database backup created: {backup_db_file}")

# Step 4: Create an SQL dump
sql_dump_file = os.path.join(backup_folder, f"products_backup_{timestamp}.sql")
conn = sqlite3.connect(db_file)
with open(sql_dump_file, "w") as f:
    for line in conn.iterdump():
        f.write(f"{line}\n")
conn.close()
print(f"SQL dump created: {sql_dump_file}")
