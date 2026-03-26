import sqlite3
import bcrypt
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
SECURITY_DB = BASE_DIR / "security" / "security.db"

def create_test_level5_user():
    """Create test Level 5 users for demonstration"""
    conn = sqlite3.connect(SECURITY_DB)
    cursor = conn.cursor()
    
    # Create two test Level 5 users
    level5_users = [
        ("officer1", "officer123", "John", "Smith", "1985-05-10", "Police Officer", "Full"),
        ("officer2", "officer456", "Jane", "Johnson", "1987-08-20", "Government Official", "Full")
    ]
    
    for username, password, fname, lname, dob, role, access in level5_users:
        try:
            password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
            cursor.execute(
                "INSERT INTO Users (username, password_hash, security_level, first_name, last_name, dob, role, access_type) VALUES (?, ?, 5, ?, ?, ?, ?, ?)",
                (username, password_hash, fname, lname, dob, role, access)
            )
            print(f"Created Level 5 user: {username}")
        except sqlite3.IntegrityError:
            print(f"Level 5 user {username} already exists")
    
    conn.commit()
    conn.close()

if __name__ == '__main__':
    create_test_level5_user()
    print("\nTest Level 5 users created!")
    print("Login credentials:")
    print("  officer1 / officer123")
    print("  officer2 / officer456")
