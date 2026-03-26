import sqlite3
import bcrypt
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
SECURITY_DB = BASE_DIR / "security" / "security.db"

def show_all_users():
    """Display all users in the system"""
    conn = sqlite3.connect(SECURITY_DB)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("""
        SELECT u.user_id, u.username, u.first_name, u.last_name, s.level_name, u.role
        FROM Users u
        JOIN SecurityLevels s ON u.security_level = s.level
        ORDER BY u.security_level DESC
    """)
    
    users = cursor.fetchall()
    conn.close()
    
    print("\n" + "="*80)
    print("VICINITY SAFETY FINANCIAL SYSTEM - ALL USERS")
    print("="*80 + "\n")
    
    for user in users:
        print(f"ID: {user['user_id']}")
        print(f"  Username: {user['username']}")
        print(f"  Name: {user['first_name']} {user['last_name']}")
        print(f"  Level: {user['level_name']}")
        print(f"  Role: {user['role']}")
        print()

def reset_password(username, new_password):
    """Reset a user's password"""
    conn = sqlite3.connect(SECURITY_DB)
    cursor = conn.cursor()
    
    # Check if user exists
    cursor.execute("SELECT user_id FROM Users WHERE username = ?", (username,))
    user = cursor.fetchone()
    
    if not user:
        print(f"❌ User '{username}' not found")
        conn.close()
        return False
    
    # Hash new password
    password_hash = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    
    # Update password
    cursor.execute("UPDATE Users SET password_hash = ? WHERE username = ?", (password_hash, username))
    conn.commit()
    conn.close()
    
    print(f"✅ Password for '{username}' reset to: {new_password}")
    return True

if __name__ == '__main__':
    print("\n🔐 TEST CREDENTIALS FOR DUAL-CONTROL TESTING\n")
    
    print("LOGIN CREDENTIALS:")
    print("-" * 80)
    print("\n📌 Owner (Level 4):")
    print("   Username: admin")
    print("   Password: admin123")
    print("   Purpose: Request Level 5 user removal")
    
    print("\n🚔 Police/Government Officers (Level 5):")
    print("   Username: officer1")
    print("   Password: officer123")
    print("   Purpose: Approve/Reject removal requests")
    
    print("\n   Username: officer2")
    print("   Password: officer456")
    print("   Purpose: Approve/Reject removal requests")
    
    print("\n" + "-" * 80)
    
    show_all_users()
    
    print("HOW TO TEST DUAL-CONTROL:")
    print("-" * 80)
    print("1. Login as 'admin' with password 'admin123'")
    print("2. Go to 'Governance' menu")
    print("3. Click 'Request Level 5 Removal'")
    print("4. Select officer2 and submit")
    print("5. Logout")
    print("6. Login as 'officer1' with password 'officer123'")
    print("7. Go to 'Governance' menu")
    print("8. Approve the removal request")
    print("9. Watch the dual-control system in action! 🎯")
    print("\n" + "="*80 + "\n")
