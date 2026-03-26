"""
Initialize FinancialDatabase.db using FinancialDatabase.sql schema.
"""

import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
DB_PATH = BASE_DIR / "db" / "FinancialDatabase.db"
SCHEMA_PATH = BASE_DIR / "db" / "FinancialDatabase.sql"


def initialize_db():
    if not os.path.exists(SCHEMA_PATH):
        raise FileNotFoundError(f"Schema not found: {SCHEMA_PATH}")

    with open(SCHEMA_PATH, "r", encoding="utf-8") as handle:
        schema_sql = handle.read()

    # Remove line comments to avoid semicolons inside comments breaking splitting
    cleaned_lines = []
    for line in schema_sql.splitlines():
        if "--" in line:
            line = line.split("--", 1)[0]
        cleaned_lines.append(line)
    cleaned_sql = "\n".join(cleaned_lines)

    conn = sqlite3.connect(DB_PATH)
    try:
        cursor = conn.cursor()
        for statement in cleaned_sql.split(";"):
            stmt = statement.strip()
            if not stmt:
                continue
            try:
                cursor.execute(stmt)
            except sqlite3.OperationalError as exc:
                if "already exists" in str(exc):
                    continue
                raise
        conn.commit()
        print("FinancialDatabase.db initialized successfully.")
    finally:
        conn.close()


if __name__ == "__main__":
    initialize_db()
