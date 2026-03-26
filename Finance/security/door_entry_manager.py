"""
Door Entry Management Module
Provides functions for managing doors, access permissions, and access logs
"""

import sqlite3
import json
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
SECURITY_DB_PATH = BASE_DIR / "security" / "security.db"


class DoorEntryManager:
    """Manages door configurations and access control"""
    
    def __init__(self):
        self.db_path = SECURITY_DB_PATH
    
    def get_all_doors(self) -> List[Dict]:
        """Get all door configurations"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT door_id, door_name, location, door_type, 
                       requires_security_level, is_active, scanner_device_id, created_at
                FROM DoorConfiguration
                ORDER BY door_name
            """)
            
            doors = cursor.fetchall()
            conn.close()
            
            return [
                {
                    'door_id': d[0],
                    'door_name': d[1],
                    'location': d[2],
                    'door_type': d[3],
                    'requires_security_level': d[4],
                    'is_active': d[5],
                    'scanner_device_id': d[6],
                    'created_at': d[7]
                }
                for d in doors
            ]
        except Exception as e:
            print(f"Error fetching doors: {e}")
            return []
    
    def get_door_info(self, door_id: int) -> Optional[Dict]:
        """Get detailed information about a specific door"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT door_id, door_name, location, door_type, 
                       requires_security_level, is_active, scanner_device_id, created_at
                FROM DoorConfiguration
                WHERE door_id = ?
            """, (door_id,))
            
            door = cursor.fetchone()
            
            if not door:
                conn.close()
                return None
            
            # Get access count
            cursor.execute("""
                SELECT COUNT(*) FROM DoorAccessLog WHERE door_location = ?
            """, (f"door_{door_id}",))
            
            access_count = cursor.fetchone()[0]
            
            conn.close()
            
            return {
                'door_id': door[0],
                'door_name': door[1],
                'location': door[2],
                'door_type': door[3],
                'requires_security_level': door[4],
                'is_active': door[5],
                'scanner_device_id': door[6],
                'created_at': door[7],
                'access_count': access_count
            }
        except Exception as e:
            print(f"Error fetching door: {e}")
            return None
    
    def create_door(self, door_name: str, location: str, door_type: str,
                   requires_security_level: int = 1, scanner_device_id: str = None) -> Dict:
        """Create a new door configuration"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO DoorConfiguration
                (door_name, location, door_type, requires_security_level, scanner_device_id)
                VALUES (?, ?, ?, ?, ?)
            """, (door_name, location, door_type, requires_security_level, scanner_device_id))
            
            door_id = cursor.lastrowid
            conn.commit()
            conn.close()
            
            return {
                'success': True,
                'door_id': door_id,
                'door_name': door_name,
                'message': f'Door "{door_name}" created successfully'
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'message': f'Error creating door: {str(e)}'
            }
    
    def update_door(self, door_id: int, **kwargs) -> Dict:
        """Update door configuration"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            allowed_fields = ['door_name', 'location', 'door_type', 'requires_security_level', 
                            'scanner_device_id', 'is_active']
            
            updates = {k: v for k, v in kwargs.items() if k in allowed_fields}
            
            if not updates:
                conn.close()
                return {'success': False, 'message': 'No valid fields to update'}
            
            set_clause = ', '.join(f"{k} = ?" for k in updates.keys())
            values = list(updates.values()) + [door_id]
            
            cursor.execute(f"""
                UPDATE DoorConfiguration
                SET {set_clause}
                WHERE door_id = ?
            """, values)
            
            conn.commit()
            conn.close()
            
            return {
                'success': True,
                'door_id': door_id,
                'updated_fields': list(updates.keys()),
                'message': 'Door updated successfully'
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def set_employee_door_access(self, user_id: int, door_id: int,
                                can_access: bool = True,
                                access_hours_start: str = None,
                                access_hours_end: str = None,
                                allowed_days: List[int] = None) -> Dict:
        """Configure door access for an employee"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Validate user exists
            cursor.execute("SELECT username FROM Users WHERE user_id = ?", (user_id,))
            user = cursor.fetchone()
            
            if not user:
                conn.close()
                return {'success': False, 'error': 'User not found'}
            
            # Convert allowed_days to JSON
            allowed_days_json = json.dumps(allowed_days) if allowed_days else None
            
            cursor.execute("""
                INSERT OR REPLACE INTO EmployeeAccessPermissions
                (user_id, door_id, can_access, access_hours_start, access_hours_end, allowed_days)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (user_id, door_id, can_access, access_hours_start, access_hours_end, allowed_days_json))
            
            conn.commit()
            conn.close()
            
            status = "granted" if can_access else "revoked"
            return {
                'success': True,
                'user_id': user_id,
                'door_id': door_id,
                'status': status,
                'message': f'Access to door {door_id} {status} for employee {user[0]}'
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def get_employee_access_permissions(self, user_id: int) -> Dict:
        """Get all door access permissions for an employee"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT eap.door_id, eap.can_access, eap.access_hours_start, eap.access_hours_end,
                       eap.allowed_days, dc.door_name, dc.location
                FROM EmployeeAccessPermissions eap
                JOIN DoorConfiguration dc ON eap.door_id = dc.door_id
                WHERE eap.user_id = ?
                ORDER BY dc.door_name
            """, (user_id,))
            
            permissions = cursor.fetchall()
            conn.close()
            
            return {
                'user_id': user_id,
                'permissions': [
                    {
                        'door_id': p[0],
                        'can_access': bool(p[1]),
                        'access_hours_start': p[2],
                        'access_hours_end': p[3],
                        'allowed_days': json.loads(p[4]) if p[4] else None,
                        'door_name': p[5],
                        'location': p[6]
                    }
                    for p in permissions
                ]
            }
        except Exception as e:
            print(f"Error fetching employee permissions: {e}")
            return {'user_id': user_id, 'permissions': [], 'error': str(e)}
    
    def get_door_access_summary(self, door_id: int, hours: int = 24) -> Dict:
        """Get recent access summary for a door"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            time_limit = (datetime.now() - timedelta(hours=hours)).isoformat()
            
            # Total accesses
            cursor.execute("""
                SELECT COUNT(*) FROM DoorAccessLog
                WHERE door_location = ? AND access_time >= ?
            """, (f"door_{door_id}", time_limit))
            
            total_accesses = cursor.fetchone()[0]
            
            # Successful accesses
            cursor.execute("""
                SELECT COUNT(*) FROM DoorAccessLog
                WHERE door_location = ? AND access_time >= ? AND access_granted = 1
            """, (f"door_{door_id}", time_limit))
            
            successful = cursor.fetchone()[0]
            
            # Failed accesses
            failed = total_accesses - successful
            
            # Top users this period
            cursor.execute("""
                SELECT user_id, COUNT(*) as access_count
                FROM DoorAccessLog
                WHERE door_location = ? AND access_time >= ?
                GROUP BY user_id
                ORDER BY access_count DESC
                LIMIT 5
            """, (f"door_{door_id}", time_limit))
            
            top_users = cursor.fetchall()
            
            # Get door info
            cursor.execute("""
                SELECT door_name FROM DoorConfiguration WHERE door_id = ?
            """, (door_id,))
            
            door_record = cursor.fetchone()
            door_name = door_record[0] if door_record else "Unknown Door"
            
            conn.close()
            
            return {
                'door_id': door_id,
                'door_name': door_name,
                'period_hours': hours,
                'total_accesses': total_accesses,
                'successful_accesses': successful,
                'failed_accesses': failed,
                'success_rate': f"{(successful/total_accesses*100):.1f}%" if total_accesses > 0 else "N/A",
                'top_users': [{'user_id': u[0], 'access_count': u[1]} for u in top_users]
            }
        except Exception as e:
            print(f"Error generating access summary: {e}")
            return {}
    
    def get_fraudulent_activities(self, days: int = 7) -> List[Dict]:
        """Get detected fraudulent activities"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            time_limit = (datetime.now() - timedelta(days=days)).isoformat()
            
            cursor.execute("""
                SELECT fraud_alert_id, qr_token, alert_time, alert_type, 
                       scan_count_in_period, severity, action_taken
                FROM QRCodeFraudDetection
                WHERE alert_time >= ?
                ORDER BY alert_time DESC
            """, (time_limit,))
            
            alerts = cursor.fetchall()
            conn.close()
            
            return [
                {
                    'alert_id': a[0],
                    'qr_token': a[1][:20] + '...' if len(a[1]) > 20 else a[1],
                    'alert_time': a[2],
                    'alert_type': a[3],
                    'scan_count': a[4],
                    'severity': a[5],
                    'action_taken': a[6]
                }
                for a in alerts
            ]
        except Exception as e:
            print(f"Error fetching fraud alerts: {e}")
            return []
    
    def get_access_log(self, user_id: int = None, door_id: int = None,
                      days: int = 30) -> List[Dict]:
        """Get door access log"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            time_limit = (datetime.now() - timedelta(days=days)).isoformat()
            
            if user_id and door_id:
                cursor.execute("""
                    SELECT access_id, user_id, access_time, door_location, 
                           access_granted, validation_result
                    FROM DoorAccessLog
                    WHERE user_id = ? AND door_location = ? AND access_time >= ?
                    ORDER BY access_time DESC
                """, (user_id, f"door_{door_id}", time_limit))
            
            elif user_id:
                cursor.execute("""
                    SELECT access_id, user_id, access_time, door_location, 
                           access_granted, validation_result
                    FROM DoorAccessLog
                    WHERE user_id = ? AND access_time >= ?
                    ORDER BY access_time DESC
                """, (user_id, time_limit))
            
            elif door_id:
                cursor.execute("""
                    SELECT access_id, user_id, access_time, door_location, 
                           access_granted, validation_result
                    FROM DoorAccessLog
                    WHERE door_location = ? AND access_time >= ?
                    ORDER BY access_time DESC
                """, (f"door_{door_id}", time_limit))
            
            else:
                cursor.execute("""
                    SELECT access_id, user_id, access_time, door_location, 
                           access_granted, validation_result
                    FROM DoorAccessLog
                    WHERE access_time >= ?
                    ORDER BY access_time DESC
                    LIMIT 100
                """, (time_limit,))
            
            logs = cursor.fetchall()
            conn.close()
            
            return [
                {
                    'access_id': log[0],
                    'user_id': log[1],
                    'access_time': log[2],
                    'door': log[3],
                    'access_granted': bool(log[4]),
                    'result': log[5]
                }
                for log in logs
            ]
        except Exception as e:
            print(f"Error fetching access log: {e}")
            return []


if __name__ == '__main__':
    manager = DoorEntryManager()
    
    # Example: Get all doors
    doors = manager.get_all_doors()
    print("Available doors:")
    for door in doors:
        print(f"  - {door['door_name']} ({door['door_type']}) at {door['location']}")
    
    # Example: Set employee access
    result = manager.set_employee_door_access(
        user_id=1,
        door_id=1,
        can_access=True,
        access_hours_start='08:00',
        access_hours_end='17:00',
        allowed_days=[0, 1, 2, 3, 4]  # Monday to Friday
    )
    print(f"\nAccess permission result: {result['message']}")
