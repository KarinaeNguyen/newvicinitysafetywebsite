"""
Reset Users to Default Test Configuration
Creates 2 users: admin (Level 4) and officer (Level 5)
"""

import sqlite3
import bcrypt
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
SECURITY_DB = BASE_DIR / "security" / "security.db"

def reset_users():
    """Clear all users and create 2 test users"""
    conn = sqlite3.connect(SECURITY_DB)
    cursor = conn.cursor()
    
    print("="*60)
    print("Resetting Users Database")
    print("="*60)
    
    # Delete all existing users
    cursor.execute("DELETE FROM Users")
    print("✓ All existing users removed")
    
    # Reset the autoincrement counter for user_id
    cursor.execute("DELETE FROM sqlite_sequence WHERE name='Users'")
    print("✓ Reset user ID counter")
    
    # Create Level 4 admin user (ID will be 1)
    admin_password = bcrypt.hashpw("admin123".encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    cursor.execute("""
        INSERT INTO Users (username, password_hash, security_level, first_name, last_name, dob, role, access_type)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, ("admin", admin_password, 4, "System", "Administrator", "1990-01-01", "Owner", "Full"))
    admin_id = cursor.lastrowid
    print(f"✓ Created user: admin (ID: {admin_id}, Level 4 - Owner)")
    print("  Username: admin")
    print("  Password: admin123")
    
    # Create Level 5 officer user (ID will be 2)
    officer_password = bcrypt.hashpw("officer123".encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    cursor.execute("""
        INSERT INTO Users (username, password_hash, security_level, first_name, last_name, dob, role, access_type)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, ("officer", officer_password, 5, "Police", "Officer", "1985-01-01", "Police/Government", "View Only"))
    officer_id = cursor.lastrowid
    print(f"✓ Created user: officer (ID: {officer_id}, Level 5 - Police/Government)")
    print("  Username: officer")
    print("  Password: officer123")
    
    conn.commit()
    
    # Verify
    cursor.execute("SELECT user_id, username, security_level, first_name, last_name, access_type FROM Users")
    users = cursor.fetchall()
    
    print("\n" + "="*60)
    print("Current Users in Database:")
    print("="*60)
    for user in users:
        level_name = {1: "Employee", 2: "Manager", 3: "Admin", 4: "Owner", 5: "Police/Government"}.get(user[2], "Unknown")
        print(f"  ID:{user[0]} [{user[2]}] {user[1]:15} - {user[3]} {user[4]:15} ({level_name}) - {user[5]}")
    
    conn.close()
    
    print("\n" + "="*60)
    print("Reset Complete!")
    print("="*60)
    print("\nTest Scenario:")
    print("1. Login as 'admin' (Level 4)")
    print("2. Try to remove 'officer' (Level 5)")
    print("3. System should DENY the request")
    print("   → Level 4 cannot remove Level 5")
    print("   → At least 1 Level 5 user must exist")
    print("\n4. Login as 'officer' (Level 5)")
    print("5. Officer CAN manage all users including admin")
    print("\nSecurity Permissions Structure:")
    print("  Level 1 (Employee):")
    print("    • View & Edit financial data")
    print("    • Cannot manage users")
    print("\n  Level 2 (Manager):")
    print("    • View & Edit financial data")
    print("    • Can add/remove Level 1 users only")
    print("\n  Level 3 (Admin):")
    print("    • View & Edit financial data")
    print("    • Can add Level 1-3 users")
    print("    • Can remove Level 1-2 users only")
    print("    • Cannot remove Level 3, 4, or 5 users")
    print("\n  Level 4 (Owner):")
    print("    • Full access to financial data")
    print("    • Can add Level 1-4 users")
    print("    • Can remove Level 1-4 users")
    print("    • Cannot modify Level 5 users (immutable)")
    print("\n  Level 5 (Police/Government):")
    print("    • VIEW ONLY access to financial data (read-only)")
    print("    • Full user management (can manage all levels)")
    print("    • Supreme authority - At least 1 must always exist")

if __name__ == '__main__':
    reset_users()
