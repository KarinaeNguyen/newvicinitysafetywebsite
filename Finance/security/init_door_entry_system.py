"""
Door Entry System Initialization Script
Sets up all door entry tables and creates initial door configurations
"""

import sqlite3
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
SECURITY_DB_PATH = BASE_DIR / "security" / "security.db"
SCHEMA_FILE = BASE_DIR / "security" / "door_entry_schema.sql"


def initialize_door_entry_system():
    """Initialize door entry database schema"""
    try:
        conn = sqlite3.connect(SECURITY_DB_PATH)
        cursor = conn.cursor()
        
        # Read and execute schema
        with open(SCHEMA_FILE, 'r') as f:
            schema_sql = f.read()
        
        # Execute each statement
        for statement in schema_sql.split(';'):
            if statement.strip():
                cursor.execute(statement)
        
        conn.commit()
        
        print("✓ Door entry system schema initialized successfully")
        return True
    
    except Exception as e:
        print(f"✗ Error initializing door entry system: {e}")
        return False
    finally:
        conn.close()


def create_default_doors():
    """Create default door configurations"""
    try:
        conn = sqlite3.connect(SECURITY_DB_PATH)
        cursor = conn.cursor()
        
        default_doors = [
            {
                'door_name': 'Main Entrance',
                'location': 'Building A - Ground Floor',
                'door_type': 'entrance',
                'requires_security_level': 1,
                'scanner_device_id': 'SCANNER_001'
            },
            {
                'door_name': 'Employee Exit',
                'location': 'Building A - Ground Floor',
                'door_type': 'exit',
                'requires_security_level': 1,
                'scanner_device_id': 'SCANNER_002'
            },
            {
                'door_name': 'Finance Office',
                'location': 'Building A - Second Floor',
                'door_type': 'restricted',
                'requires_security_level': 2,
                'scanner_device_id': 'SCANNER_003'
            },
            {
                'door_name': 'Server Room',
                'location': 'Building A - Basement',
                'door_type': 'restricted',
                'requires_security_level': 4,
                'scanner_device_id': 'SCANNER_004'
            },
            {
                'door_name': 'Emergency Exit',
                'location': 'Building A - All Floors',
                'door_type': 'emergency',
                'requires_security_level': 1,
                'scanner_device_id': 'SCANNER_005'
            },
        ]
        
        for door in default_doors:
            cursor.execute("""
                INSERT OR IGNORE INTO DoorConfiguration
                (door_name, location, door_type, requires_security_level, scanner_device_id)
                VALUES (?, ?, ?, ?, ?)
            """, (
                door['door_name'],
                door['location'],
                door['door_type'],
                door['requires_security_level'],
                door['scanner_device_id']
            ))
        
        conn.commit()
        print(f"✓ Created {len(default_doors)} default door configurations")
        
    except Exception as e:
        print(f"✗ Error creating default doors: {e}")
    finally:
        conn.close()


def assign_employee_door_access(user_id: int, door_id: int, can_access: bool = True,
                               access_hours_start: str = None, access_hours_end: str = None,
                               allowed_days: str = None):
    """
    Assign door access permissions to an employee
    
    Args:
        user_id: Employee user ID
        door_id: Door ID
        can_access: Whether employee can access (boolean)
        access_hours_start: Start time in HH:MM format (optional)
        access_hours_end: End time in HH:MM format (optional)
        allowed_days: JSON list of allowed days 0-6 (optional)
    """
    try:
        conn = sqlite3.connect(SECURITY_DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT OR REPLACE INTO EmployeeAccessPermissions
            (user_id, door_id, can_access, access_hours_start, access_hours_end, allowed_days)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (user_id, door_id, can_access, access_hours_start, access_hours_end, allowed_days))
        
        conn.commit()
        conn.close()
        
        return True
    
    except Exception as e:
        print(f"Error assigning door access: {e}")
        return False


def setup_employee_with_qr(user_id: int, door_ids: list = None):
    """
    Complete setup for new employee: create QR code and assign door access
    
    Args:
        user_id: User ID
        door_ids: List of door IDs to grant access (if None, grants main entrance only)
    """
    from qr_code_manager import QRCodeManager
    
    try:
        # Get user details
        conn = sqlite3.connect(SECURITY_DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute("SELECT username FROM Users WHERE user_id = ?", (user_id,))
        user_record = cursor.fetchone()
        
        if not user_record:
            print(f"Error: User {user_id} not found")
            conn.close()
            return False
        
        employee_id = user_record[0]
        
        # Generate QR code
        qr_manager = QRCodeManager()
        qr_result = qr_manager.create_qr_code_for_employee(user_id, employee_id)
        
        if not qr_result['success']:
            print(f"Error generating QR code: {qr_result['error']}")
            conn.close()
            return False
        
        # Assign door access
        if door_ids is None:
            # Get main entrance door ID
            cursor.execute("SELECT door_id FROM DoorConfiguration WHERE door_name = 'Main Entrance'")
            main_entrance = cursor.fetchone()
            door_ids = [main_entrance[0]] if main_entrance else [1]
        
        for door_id in door_ids:
            assign_employee_door_access(user_id, door_id, can_access=True)
        
        conn.close()
        
        print(f"✓ Employee {employee_id} (ID: {user_id}) set up with QR code")
        print(f"  QR Token: {qr_result['qr_token'][:20]}...")
        print(f"  Expires: {qr_result['expires_at']}")
        print(f"  Door access assigned to {len(door_ids)} door(s)")
        
        return True
    
    except Exception as e:
        print(f"Error in employee setup: {e}")
        return False


if __name__ == '__main__':
    print("="*60)
    print("Door Entry System Initialization")
    print("="*60)
    
    # Initialize schema
    if initialize_door_entry_system():
        # Create default doors
        create_default_doors()
        
        print("\n✓ Door entry system ready for use")
        print("\nNext steps:")
        print("1. Use setup_employee_with_qr(user_id) to add QR codes to employees")
        print("2. Use assign_employee_door_access() to configure door permissions")
        print("3. Use QRCodeManager.validate_qr_code() for scanner validation")
    else:
        print("✗ Failed to initialize door entry system")
