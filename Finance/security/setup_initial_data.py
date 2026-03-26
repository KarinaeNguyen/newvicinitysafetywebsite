import sqlite3
import bcrypt
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
SECURITY_DB = BASE_DIR / "security" / "security.db"

def setup_security_levels():
    """Initialize security levels"""
    conn = sqlite3.connect(SECURITY_DB)
    cursor = conn.cursor()
    
    levels = [
        (1, "Employee", "Basic access level"),
        (2, "Manager", "Can add users"),
        (3, "Admin", "Can add and remove users"),
        (4, "Owner", "Full access except Level 5"),
        (5, "Police/Government", "Highest level, immutable by owner")
    ]
    
    for level, name, desc in levels:
        try:
            cursor.execute("INSERT INTO SecurityLevels (level, level_name, description) VALUES (?, ?, ?)", 
                          (level, name, desc))
        except sqlite3.IntegrityError:
            print(f"Level {level} already exists")
    
    conn.commit()
    conn.close()
    print("Security levels initialized")

def create_default_admin():
    """Create default admin user"""
    conn = sqlite3.connect(SECURITY_DB)
    cursor = conn.cursor()
    
    # Check if admin exists
    cursor.execute("SELECT * FROM Users WHERE username = 'admin'")
    if cursor.fetchone():
        print("Admin user already exists")
        conn.close()
        return
    
    # Create admin
    password_hash = bcrypt.hashpw("admin123".encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    cursor.execute(
        "INSERT INTO Users (username, password_hash, security_level, first_name, last_name, dob, role, access_type) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        ("admin", password_hash, 4, "System", "Administrator", "1990-01-01", "Owner", "Full")
    )
    
    conn.commit()
    conn.close()
    print("Default admin user created: username='admin', password='admin123'")

if __name__ == '__main__':
    setup_security_levels()
    create_default_admin()
    print("\nSetup complete! You can now run app\\finance_ui.py")
    print("Login with: username='admin', password='admin123'")
