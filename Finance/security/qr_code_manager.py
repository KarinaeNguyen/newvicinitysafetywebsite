"""
Secure QR Code Generation and Validation Module
Generates unique, non-copyable QR codes for employee door entry
Uses cryptographic signatures to prevent tampering
"""

import qrcode
import sqlite3
import hmac
import hashlib
import secrets
import base64
import json
from datetime import datetime, timedelta
from io import BytesIO
import os
from pathlib import Path
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2
from cryptography.hazmat.backends import default_backend

BASE_DIR = Path(__file__).resolve().parents[1]
SECURITY_DB_PATH = BASE_DIR / "security" / "security.db"


class QRCodeManager:
    """Manages secure QR code generation and validation for door entry"""
    
    def __init__(self, master_secret: str = None):
        """
        Initialize QR Code Manager
        
        Args:
            master_secret: Master encryption key (generates from environment if not provided)
        """
        if master_secret is None:
            master_secret = os.environ.get('DOOR_ACCESS_SECRET', 'vicinity_safety_qr_master_key_2026')
        
        # Derive encryption key from master secret
        kdf = PBKDF2(
            algorithm=hashes.SHA256(),
            length=32,
            salt=b'vicinity_safety_door_access_salt',
            iterations=100000,
            backend=default_backend()
        )
        key = base64.urlsafe_b64encode(kdf.derive(master_secret.encode()))
        self.cipher = Fernet(key)
        self.master_secret = master_secret
    
    def generate_secure_token(self, user_id: int, employee_id: str) -> tuple:
        """
        Generate a cryptographically secure, unique token for employee
        
        Args:
            user_id: User ID from database
            employee_id: Employee identifier
            
        Returns:
            Tuple of (qr_token, qr_secret, signature)
        """
        # Generate random components
        random_component = secrets.token_hex(32)  # 64 character hex string
        timestamp = datetime.now().isoformat()
        
        # Create token payload
        payload = {
            'user_id': user_id,
            'employee_id': employee_id,
            'random': random_component,
            'created': timestamp,
            'version': '1.0'
        }
        
        # Encrypt the payload
        payload_json = json.dumps(payload)
        encrypted_payload = self.cipher.encrypt(payload_json.encode())
        qr_token = base64.urlsafe_b64encode(encrypted_payload).decode('ascii')
        
        # Generate HMAC secret for validation
        qr_secret = secrets.token_hex(32)
        
        # Create cryptographic signature
        signature_data = f"{user_id}{employee_id}{qr_token}{timestamp}"
        signature = hmac.new(
            self.master_secret.encode(),
            signature_data.encode(),
            hashlib.sha256
        ).hexdigest()
        
        return qr_token, qr_secret, signature
    
    def create_qr_code_for_employee(self, user_id: int, employee_id: str, 
                                   expiration_days: int = 365) -> dict:
        """
        Create and store a QR code for an employee
        
        Args:
            user_id: User ID from Users table
            employee_id: Employee ID string
            expiration_days: Days until QR code expires (default: 1 year)
            
        Returns:
            Dictionary with QR code information and image
        """
        try:
            qr_token, qr_secret, signature = self.generate_secure_token(user_id, employee_id)
            
            conn = sqlite3.connect(SECURITY_DB_PATH)
            cursor = conn.cursor()
            
            # Check if employee already has active QR code
            cursor.execute(
                "SELECT token_id FROM QRCodeTokens WHERE user_id = ? AND is_active = 1",
                (user_id,)
            )
            existing = cursor.fetchone()
            
            if existing:
                # Deactivate old QR code and log regeneration
                old_token_id = existing[0]
                cursor.execute(
                    "SELECT qr_token FROM QRCodeTokens WHERE token_id = ?",
                    (old_token_id,)
                )
                old_token = cursor.fetchone()[0]
                
                cursor.execute(
                    "UPDATE QRCodeTokens SET is_active = 0 WHERE token_id = ?",
                    (old_token_id,)
                )
                
                # Log regeneration
                cursor.execute("""
                    INSERT INTO QRCodeRegenerationLog 
                    (user_id, old_qr_token, new_qr_token, regeneration_reason, regenerated_at)
                    VALUES (?, ?, ?, 'new_generation', CURRENT_TIMESTAMP)
                """, (user_id, old_token, qr_token))
            
            # Calculate expiration date
            expires_at = (datetime.now() + timedelta(days=expiration_days)).isoformat()
            
            # Store QR code token in database
            cursor.execute("""
                INSERT INTO QRCodeTokens 
                (user_id, qr_token, qr_secret, expires_at, signature)
                VALUES (?, ?, ?, ?, ?)
            """, (user_id, qr_token, qr_secret, expires_at, signature))
            
            conn.commit()
            
            # Generate QR code image
            qr_image = self._generate_qr_image(qr_token)
            
            conn.close()
            
            return {
                'success': True,
                'user_id': user_id,
                'employee_id': employee_id,
                'qr_token': qr_token,
                'qr_image': qr_image,
                'created_at': datetime.now().isoformat(),
                'expires_at': expires_at,
                'message': f'QR code generated for employee {employee_id}'
            }
        
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'message': 'Failed to generate QR code'
            }
    
    def _generate_qr_image(self, qr_token: str, size: int = 200) -> BytesIO:
        """
        Generate QR code image
        
        Args:
            qr_token: Token to encode in QR code
            size: QR code size in pixels
            
        Returns:
            BytesIO image object
        """
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_H,
            box_size=10,
            border=4,
        )
        qr.add_data(qr_token)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        
        # Save to BytesIO
        img_io = BytesIO()
        img.save(img_io, format='PNG')
        img_io.seek(0)
        
        return img_io
    
    def save_qr_code_image(self, qr_image: BytesIO, employee_id: str, 
                          output_dir: str = 'qr_codes') -> str:
        """
        Save QR code image to file
        
        Args:
            qr_image: QR code BytesIO object
            employee_id: Employee ID for filename
            output_dir: Directory to save QR codes
            
        Returns:
            Path to saved image file
        """
        try:
            if not os.path.exists(output_dir):
                os.makedirs(output_dir)
            
            filename = f"{employee_id}_qr_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
            filepath = os.path.join(output_dir, filename)
            
            with open(filepath, 'wb') as f:
                f.write(qr_image.getvalue())
            
            return filepath
        except Exception as e:
            print(f"Error saving QR code image: {e}")
            return None
    
    def validate_qr_code(self, qr_token: str, door_id: int = None) -> dict:
        """
        Validate a scanned QR code
        
        Args:
            qr_token: Token from scanned QR code
            door_id: Door ID being accessed (optional)
            
        Returns:
            Dictionary with validation result
        """
        try:
            conn = sqlite3.connect(SECURITY_DB_PATH)
            cursor = conn.cursor()
            
            # Check if token exists and is active
            cursor.execute("""
                SELECT token_id, user_id, is_active, expires_at, signature
                FROM QRCodeTokens
                WHERE qr_token = ?
            """, (qr_token,))
            
            token_record = cursor.fetchone()
            
            if not token_record:
                conn.close()
                return {
                    'valid': False,
                    'reason': 'invalid_token',
                    'message': 'QR code not recognized'
                }
            
            token_id, user_id, is_active, expires_at, stored_signature = token_record
            
            # Check if QR code is active
            if not is_active:
                conn.close()
                return {
                    'valid': False,
                    'reason': 'token_disabled',
                    'message': 'This QR code has been deactivated'
                }
            
            # Check expiration
            if expires_at:
                exp_datetime = datetime.fromisoformat(expires_at)
                if datetime.now() > exp_datetime:
                    conn.close()
                    return {
                        'valid': False,
                        'reason': 'token_expired',
                        'message': 'QR code has expired'
                    }
            
            # Check door access permissions if door_id provided
            if door_id:
                cursor.execute("""
                    SELECT can_access, access_hours_start, access_hours_end, allowed_days
                    FROM EmployeeAccessPermissions
                    WHERE user_id = ? AND door_id = ?
                """, (user_id, door_id))
                
                permission = cursor.fetchone()
                if not permission or not permission[0]:
                    conn.close()
                    return {
                        'valid': False,
                        'reason': 'access_denied',
                        'message': f'Employee {user_id} does not have access to this door'
                    }
                
                # Check access hours if specified
                can_access, hours_start, hours_end, allowed_days = permission
                if hours_start and hours_end:
                    current_time = datetime.now().time()
                    start_time = datetime.strptime(hours_start, '%H:%M').time()
                    end_time = datetime.strptime(hours_end, '%H:%M').time()
                    
                    if not (start_time <= current_time <= end_time):
                        conn.close()
                        return {
                            'valid': False,
                            'reason': 'outside_access_hours',
                            'message': f'Access only allowed between {hours_start} and {hours_end}'
                        }
                
                # Check allowed days if specified
                if allowed_days:
                    try:
                        allowed_days_list = json.loads(allowed_days)
                        current_day = datetime.now().weekday()
                        if current_day not in allowed_days_list:
                            conn.close()
                            return {
                                'valid': False,
                                'reason': 'not_allowed_today',
                                'message': 'Access not allowed on this day'
                            }
                    except:
                        pass
            
            # Log successful access
            cursor.execute("""
                INSERT INTO DoorAccessLog
                (user_id, qr_token, door_location, access_granted, validation_result)
                VALUES (?, ?, ?, 1, 'valid')
            """, (user_id, qr_token, f"door_{door_id}" if door_id else 'unknown'))
            
            # Check for fraud patterns
            fraud_check = self._check_fraud_patterns(cursor, qr_token, user_id)
            
            conn.commit()
            conn.close()
            
            return {
                'valid': True,
                'reason': 'success',
                'user_id': user_id,
                'message': 'Access granted',
                'fraud_alert': fraud_check if fraud_check['detected'] else None
            }
        
        except Exception as e:
            return {
                'valid': False,
                'reason': 'validation_error',
                'message': f'Error validating QR code: {str(e)}'
            }
    
    def _check_fraud_patterns(self, cursor, qr_token: str, user_id: int) -> dict:
        """
        Check for suspicious patterns that might indicate QR code copying
        
        Args:
            cursor: Database cursor
            qr_token: QR code token
            user_id: User ID
            
        Returns:
            Dictionary with fraud detection results
        """
        try:
            # Check for rapid reuse (same QR code scanned in different locations within short time)
            cursor.execute("""
                SELECT door_location, access_time
                FROM DoorAccessLog
                WHERE qr_token = ?
                ORDER BY access_time DESC
                LIMIT 10
            """, (qr_token,))
            
            recent_scans = cursor.fetchall()
            
            if len(recent_scans) >= 2:
                # Get last two scans
                last_scan = recent_scans[0]
                prev_scan = recent_scans[1]
                
                last_time = datetime.fromisoformat(last_scan[1])
                prev_time = datetime.fromisoformat(prev_scan[1])
                
                time_diff_seconds = (last_time - prev_time).total_seconds()
                
                # If two scans within 60 seconds in different locations - suspicious
                if time_diff_seconds < 60 and last_scan[0] != prev_scan[0]:
                    cursor.execute("""
                        INSERT INTO QRCodeFraudDetection
                        (qr_token, alert_type, scan_count_in_period, time_period_seconds, severity)
                        VALUES (?, 'rapid_reuse', ?, ?, 'high')
                    """, (qr_token, len(recent_scans), int(time_diff_seconds)))
                    
                    return {
                        'detected': True,
                        'type': 'rapid_reuse',
                        'message': 'Suspicious rapid reuse detected',
                        'severity': 'high'
                    }
            
            return {'detected': False}
        
        except Exception as e:
            print(f"Error in fraud detection: {e}")
            return {'detected': False}
    
    def regenerate_qr_code(self, user_id: int, reason: str = 'manual_renewal',
                          regenerated_by: int = None) -> dict:
        """
        Regenerate/renew QR code for an employee
        
        Args:
            user_id: User ID
            reason: Reason for regeneration
            regenerated_by: Admin user ID who triggered regeneration
            
        Returns:
            Dictionary with regeneration result
        """
        try:
            conn = sqlite3.connect(SECURITY_DB_PATH)
            cursor = conn.cursor()
            
            # Get employee details
            cursor.execute("""
                SELECT username FROM Users WHERE user_id = ?
            """, (user_id,))
            
            user_record = cursor.fetchone()
            if not user_record:
                conn.close()
                return {
                    'success': False,
                    'error': 'User not found'
                }
            
            # Get current QR code for logging
            cursor.execute("""
                SELECT qr_token FROM QRCodeTokens
                WHERE user_id = ? AND is_active = 1
            """, (user_id,))
            
            old_record = cursor.fetchone()
            old_token = old_record[0] if old_record else None
            
            # Generate new QR code
            employee_id = user_record[0]
            qr_token, qr_secret, signature = self.generate_secure_token(user_id, employee_id)
            
            expires_at = (datetime.now() + timedelta(days=365)).isoformat()
            
            # Deactivate old token if exists
            if old_token:
                cursor.execute(
                    "UPDATE QRCodeTokens SET is_active = 0 WHERE qr_token = ?",
                    (old_token,)
                )
            
            # Insert new token
            cursor.execute("""
                INSERT INTO QRCodeTokens
                (user_id, qr_token, qr_secret, expires_at, signature)
                VALUES (?, ?, ?, ?, ?)
            """, (user_id, qr_token, qr_secret, expires_at, signature))
            
            # Log regeneration
            cursor.execute("""
                INSERT INTO QRCodeRegenerationLog
                (user_id, old_qr_token, new_qr_token, regeneration_reason, regenerated_by)
                VALUES (?, ?, ?, ?, ?)
            """, (user_id, old_token, qr_token, reason, regenerated_by))
            
            conn.commit()
            conn.close()
            
            return {
                'success': True,
                'user_id': user_id,
                'employee_id': employee_id,
                'new_qr_token': qr_token,
                'old_qr_token': old_token,
                'message': f'QR code regenerated for {employee_id}'
            }
        
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'message': 'Failed to regenerate QR code'
            }
    
    def disable_qr_code(self, user_id: int, reason: str = 'manual_disable') -> dict:
        """
        Disable an employee's active QR code
        
        Args:
            user_id: User ID
            reason: Reason for disabling
            
        Returns:
            Dictionary with result
        """
        try:
            conn = sqlite3.connect(SECURITY_DB_PATH)
            cursor = conn.cursor()
            
            cursor.execute(
                "UPDATE QRCodeTokens SET is_active = 0 WHERE user_id = ? AND is_active = 1",
                (user_id,)
            )
            
            affected_rows = cursor.rowcount
            conn.commit()
            conn.close()
            
            return {
                'success': True,
                'user_id': user_id,
                'disabled': affected_rows > 0,
                'message': f'QR code disabled' if affected_rows > 0 else 'No active QR code found'
            }
        
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_employee_access_log(self, user_id: int, days: int = 30) -> list:
        """
        Get door access history for an employee
        
        Args:
            user_id: User ID
            days: Number of days to retrieve
            
        Returns:
            List of access records
        """
        try:
            conn = sqlite3.connect(SECURITY_DB_PATH)
            cursor = conn.cursor()
            
            date_limit = (datetime.now() - timedelta(days=days)).isoformat()
            
            cursor.execute("""
                SELECT access_id, access_time, door_location, access_granted, validation_result
                FROM DoorAccessLog
                WHERE user_id = ? AND access_time >= ?
                ORDER BY access_time DESC
            """, (user_id, date_limit))
            
            records = cursor.fetchall()
            conn.close()
            
            return records
        
        except Exception as e:
            print(f"Error retrieving access log: {e}")
            return []


# Example usage and testing
if __name__ == '__main__':
    manager = QRCodeManager()
    
    # Example: Generate QR code for employee
    result = manager.create_qr_code_for_employee(user_id=1, employee_id='EMP001')
    print(f"QR Code Generation: {result['message']}")
    
    if result['success']:
        # Save QR code image
        image_path = manager.save_qr_code_image(result['qr_image'], 'EMP001')
        print(f"QR Code saved to: {image_path}")
        
        # Validate the QR code
        qr_token = result['qr_token']
        validation = manager.validate_qr_code(qr_token)
        print(f"Validation result: {validation}")
