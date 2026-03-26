"""
Door Scanner Integration Module
Simple interface for physical door scanners to validate QR codes in real-time
"""

import sqlite3
import json
from datetime import datetime
from pathlib import Path
from qr_code_manager import QRCodeManager

BASE_DIR = Path(__file__).resolve().parents[1]
SECURITY_DB_PATH = BASE_DIR / "security" / "security.db"


class DoorScanner:
    """Door scanner for validating QR codes at physical access points"""
    
    def __init__(self, scanner_device_id: str, door_id: int):
        """
        Initialize door scanner
        
        Args:
            scanner_device_id: Unique identifier for this scanner device
            door_id: Database door ID this scanner controls
        """
        self.scanner_device_id = scanner_device_id
        self.door_id = door_id
        self.qr_manager = QRCodeManager()
    
    def scan_qr_code(self, qr_token: str) -> Dict:
        """
        Scan and validate a QR code
        
        Args:
            qr_token: QR code token (usually from camera/scanner reading)
            
        Returns:
            Dictionary with access decision and details
        """
        try:
            # Validate QR code
            validation_result = self.qr_manager.validate_qr_code(qr_token, self.door_id)
            
            # Log this scan attempt
            self._log_scan_attempt(qr_token, validation_result)
            
            # Return access decision
            if validation_result['valid']:
                return {
                    'access': 'GRANTED',
                    'status_code': 200,
                    'user_id': validation_result['user_id'],
                    'message': 'Welcome! Access granted.',
                    'fraud_alert': validation_result.get('fraud_alert'),
                    'timestamp': datetime.now().isoformat()
                }
            else:
                reason = validation_result['reason']
                reason_messages = {
                    'invalid_token': 'Invalid QR code - please contact security',
                    'token_disabled': 'This QR code has been disabled',
                    'token_expired': 'QR code has expired - please get a new one',
                    'access_denied': 'You do not have access to this door',
                    'outside_access_hours': validation_result['message'],
                    'not_allowed_today': 'Access not allowed today',
                    'validation_error': 'System error - please contact security'
                }
                
                message = reason_messages.get(reason, validation_result['message'])
                
                return {
                    'access': 'DENIED',
                    'status_code': 403,
                    'reason': reason,
                    'message': message,
                    'timestamp': datetime.now().isoformat()
                }
        
        except Exception as e:
            error_result = {
                'access': 'ERROR',
                'status_code': 500,
                'error': str(e),
                'message': 'System error processing QR code',
                'timestamp': datetime.now().isoformat()
            }
            self._log_scan_attempt(qr_token, error_result)
            return error_result
    
    def _log_scan_attempt(self, qr_token: str, result: Dict):
        """Log scanner attempt to database"""
        try:
            conn = sqlite3.connect(SECURITY_DB_PATH)
            cursor = conn.cursor()
            
            # Only log if we have user_id
            user_id = result.get('user_id')
            validation_result = result.get('reason', result.get('error', 'unknown'))
            
            if user_id:
                cursor.execute("""
                    INSERT INTO DoorAccessLog
                    (user_id, qr_token, door_location, access_granted, validation_result, device_info)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (user_id, qr_token, f"door_{self.door_id}", 
                      result['access'] == 'GRANTED', validation_result, self.scanner_device_id))
            
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"Error logging scan attempt: {e}")
    
    def get_door_status(self) -> Dict:
        """Get current door status and recent activity"""
        try:
            conn = sqlite3.connect(SECURITY_DB_PATH)
            cursor = conn.cursor()
            
            # Get door info
            cursor.execute("""
                SELECT door_name, location, is_active
                FROM DoorConfiguration
                WHERE door_id = ?
            """, (self.door_id,))
            
            door_info = cursor.fetchone()
            
            if not door_info:
                conn.close()
                return {'error': 'Door not found'}
            
            # Get recent successful accesses
            cursor.execute("""
                SELECT user_id, access_time
                FROM DoorAccessLog
                WHERE door_location = ? AND access_granted = 1
                ORDER BY access_time DESC
                LIMIT 5
            """, (f"door_{self.door_id}",))
            
            recent_accesses = cursor.fetchall()
            
            # Get access count today
            cursor.execute("""
                SELECT COUNT(*) FROM DoorAccessLog
                WHERE door_location = ? AND DATE(access_time) = DATE('now')
                  AND access_granted = 1
            """, (f"door_{self.door_id}",))
            
            today_count = cursor.fetchone()[0]
            
            conn.close()
            
            return {
                'door_id': self.door_id,
                'door_name': door_info[0],
                'location': door_info[1],
                'is_active': bool(door_info[2]),
                'scanner_device_id': self.scanner_device_id,
                'status': 'ACTIVE' if door_info[2] else 'INACTIVE',
                'accesses_today': today_count,
                'recent_accesses': [
                    {'user_id': a[0], 'time': a[1]}
                    for a in recent_accesses
                ]
            }
        except Exception as e:
            return {'error': str(e)}


class ScannerSimulator:
    """Simulator for testing QR code scanning without physical hardware"""
    
    def __init__(self):
        self.qr_manager = QRCodeManager()
    
    def simulate_employee_entry(self, user_id: int, door_id: int) -> Dict:
        """
        Simulate an employee entering through a door with their QR code
        
        Args:
            user_id: Employee user ID
            door_id: Door ID
            
        Returns:
            Access result from scanner
        """
        try:
            conn = sqlite3.connect(SECURITY_DB_PATH)
            cursor = conn.cursor()
            
            # Get employee's active QR token
            cursor.execute("""
                SELECT qr_token FROM QRCodeTokens
                WHERE user_id = ? AND is_active = 1
            """, (user_id,))
            
            token_record = cursor.fetchone()
            conn.close()
            
            if not token_record:
                return {
                    'success': False,
                    'message': f'No active QR code for user {user_id}'
                }
            
            qr_token = token_record[0]
            
            # Get scanner for door
            door_config = self._get_door_config(door_id)
            if not door_config:
                return {
                    'success': False,
                    'message': f'Door {door_id} not found'
                }
            
            scanner = DoorScanner(door_config['scanner_device_id'], door_id)
            result = scanner.scan_qr_code(qr_token)
            
            return {
                'success': result['access'] == 'GRANTED',
                'access': result['access'],
                'message': result['message'],
                'user_id': user_id,
                'door_id': door_id,
                'door_name': door_config['door_name']
            }
        
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'message': f'Error simulating entry: {str(e)}'
            }
    
    def _get_door_config(self, door_id: int) -> Dict:
        """Get door configuration"""
        try:
            conn = sqlite3.connect(SECURITY_DB_PATH)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT door_id, door_name, scanner_device_id
                FROM DoorConfiguration
                WHERE door_id = ?
            """, (door_id,))
            
            result = cursor.fetchone()
            conn.close()
            
            if result:
                return {
                    'door_id': result[0],
                    'door_name': result[1],
                    'scanner_device_id': result[2]
                }
            return None
        except Exception as e:
            print(f"Error getting door config: {e}")
            return None


if __name__ == '__main__':
    print("Door Scanner Module Loaded")
    print("\nExample usage:")
    print("1. Initialize scanner: scanner = DoorScanner('SCANNER_001', door_id=1)")
    print("2. Scan QR code: result = scanner.scan_qr_code(qr_token)")
    print("3. Simulate entry: simulator = ScannerSimulator()")
    print("                   result = simulator.simulate_employee_entry(user_id=1, door_id=1)")
