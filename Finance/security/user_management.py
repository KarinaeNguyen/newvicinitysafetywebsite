import sqlite3
import bcrypt
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
SECURITY_DB_PATH = BASE_DIR / "security" / "security.db"

# Security level permissions
ADD_USER_LEVELS = {2, 3, 4, 5}  # Manager, Admin, Owner, Police/Gov
REMOVE_USER_LEVELS = {3, 4, 5}   # Admin, Owner, Police/Gov

# User fields
USER_FIELDS = [
    'username', 'password_hash', 'first_name', 'last_name', 'dob', 'role', 'access_type', 'security_level'
]

def hash_password(password):
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def add_user(current_level, user_data):
    if current_level not in ADD_USER_LEVELS:
        raise PermissionError('Insufficient permission to add users.')
    conn = sqlite3.connect(SECURITY_DB_PATH)
    try:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO Users (username, password_hash, security_level, first_name, last_name, dob, role, access_type) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (
                user_data['username'],
                hash_password(user_data['password']),
                user_data['security_level'],
                user_data['first_name'],
                user_data['last_name'],
                user_data['dob'],
                user_data['role'],
                user_data['access_type']
            )
        )
        conn.commit()
        print(f"User {user_data['username']} added successfully.")
    finally:
        conn.close()

def remove_user(current_level, username):
    if current_level not in REMOVE_USER_LEVELS:
        raise PermissionError('Insufficient permission to remove users.')
    
    conn = sqlite3.connect(SECURITY_DB_PATH)
    try:
        cursor = conn.cursor()
        
        # Get target user's security level
        cursor.execute("SELECT security_level FROM Users WHERE username = ?", (username,))
        target_user = cursor.fetchone()
        
        if not target_user:
            raise ValueError(f"User '{username}' not found.")
        
        target_level = target_user[0]
        
        # Permission Rules:
        
        # Level 2 (Manager) can only remove Level 1
        if current_level == 2 and target_level != 1:
            raise PermissionError(
                "DENIED: Level 2 (Manager) can only remove Level 1 (Employee) users."
            )
        
        # Level 3 (Admin) can only remove Level 1-2 users
        if current_level == 3 and target_level >= 3:
            raise PermissionError(
                "DENIED: Level 3 (Admin) can only remove Level 1-2 users. "
                "Cannot remove Level 3, 4, or 5 users."
            )
        
        # Level 4 (Owner) CANNOT remove Level 5 (Police/Government)
        if current_level == 4 and target_level == 5:
            raise PermissionError(
                "DENIED: Level 4 (Owner) cannot remove Level 5 (Police/Government) users. "
                "Level 5 is immutable by owner. Only Level 5 can manage Level 5 users."
            )
        
        # Cannot remove the last Level 5 user (applies to all levels)
        if target_level == 5:
            cursor.execute("SELECT COUNT(*) FROM Users WHERE security_level = 5")
            level5_count = cursor.fetchone()[0]
            
            if level5_count <= 1:
                raise PermissionError(
                    "DENIED: Cannot remove the last Level 5 (Police/Government) user. "
                    "At least one Level 5 user must exist in the system at all times."
                )
        
        # If all checks pass, proceed with removal
        cursor.execute("DELETE FROM Users WHERE username = ?", (username,))
        conn.commit()
        print(f"User '{username}' removed successfully.")
        
    finally:
        conn.close()

# Example usage:
if __name__ == '__main__':
    # Add user example
    user_data = {
        'username': 'jdoe',
        'password': 'securepass123',
        'first_name': 'John',
        'last_name': 'Doe',
        'dob': '1980-01-01',
        'role': 'Admin',
        'access_type': 'Full',
        'security_level': 3
    }
    try:
        add_user(current_level=3, user_data=user_data)
    except Exception as e:
        print(e)

    # Remove user example
    try:
        remove_user(current_level=3, username='jdoe')
    except Exception as e:
        print(e)
