import sqlite3
from pathlib import Path

# Paths to SQL schema files and database files
BASE_DIR = Path(__file__).resolve().parents[1]
security_db_path = BASE_DIR / "security" / "security.db"
security_sql_path = BASE_DIR / "security" / "security.db.sql"
logs_db_path = BASE_DIR / "security" / "logs.db"
logs_sql_path = BASE_DIR / "security" / "logs.db.sql"

def initialize_db(db_path, sql_path):
    with open(sql_path, 'r', encoding='utf-8') as f:
        sql_script = f.read()
    conn = sqlite3.connect(db_path)
    try:
        conn.executescript(sql_script)
        print(f"Initialized {db_path} successfully.")
    except Exception as e:
        print(f"Error initializing {db_path}: {e}")
    finally:
        conn.close()

if __name__ == '__main__':
    initialize_db(security_db_path, security_sql_path)
    initialize_db(logs_db_path, logs_sql_path)
