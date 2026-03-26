# Door Entry System with Secure QR Codes

## Overview

A comprehensive employee door entry system using secure, non-copyable QR codes. Each employee receives a unique QR code that cannot be duplicated or shared without detection.

## Key Features

### 1. **Unique QR Codes for Each Employee**
- Every employee gets a cryptographically signed, unique QR code
- QR codes contain encrypted employee tokens that are unique to the system
- Tokens are impossible to forge or copy without the master encryption key

### 2. **Anti-Copy Protection**
- **Cryptographic Signatures**: Each QR code is digitally signed using AES-256 encryption
- **Time-based Validation**: Tokens include creation timestamps for freshness verification
- **Server-Side Validation**: QR codes are validated against a database, not decoded locally
- **Fraud Detection**: System automatically detects suspicious patterns:
  - Multiple scans in different locations within seconds (indicates copying)
  - Rapid reuse patterns
  - Multiple devices scanning same QR code
  - Alerts are logged with severity levels

### 3. **Role-Based Access Control**
- Configure which doors each employee can access
- Set access hours (e.g., 8 AM - 5 PM)
- Restrict access to specific days
- Different door types: entrance, exit, restricted, emergency

### 4. **Comprehensive Audit Logging**
- Every access attempt is logged with:
  - Timestamp
  - Employee ID
  - Door location
  - Access granted/denied status
  - Validation result
  - Scanner device ID
- Logs are immutable and append-only for compliance

### 5. **Fraud Detection & Investigation**
- Real-time detection of suspicious access patterns
- Automatic alerts for:
  - Rapid location changes (indicates QR code copying)
  - Multiple device scans of same QR code
  - Unusual access times or locations
- Alert severity levels: low, medium, high
- Investigation logs for security team

## Architecture

### Database Schema

#### QRCodeTokens Table
Stores all active and inactive QR codes:
- `token_id`: Unique identifier
- `user_id`: Employee's user ID
- `qr_token`: Encrypted, cryptographically unique token
- `qr_secret`: HMAC secret for validation
- `signature`: Cryptographic signature to prevent tampering
- `is_active`: Current status
- `expires_at`: Optional expiration date

#### DoorAccessLog Table
Complete audit trail of all access attempts:
- `access_id`: Unique access attempt ID
- `user_id`: Employee ID
- `qr_token`: QR code used
- `access_time`: When scan occurred
- `door_location`: Which door/gate
- `access_granted`: Boolean result
- `validation_result`: Detailed reason (valid, expired, disabled, forged, etc.)

#### QRCodeFraudDetection Table
Tracks detected fraud attempts:
- Alert types: unusual_location, rapid_reuse, multiple_devices
- Severity levels: low, medium, high
- Action taken: logged, disabled, investigation

#### DoorConfiguration Table
Door/gate setup and requirements:
- `door_id`: Unique door identifier
- `door_name`: Friendly name
- `location`: Physical location
- `door_type`: entrance, exit, restricted, emergency
- `requires_security_level`: Minimum employee level needed
- `scanner_device_id`: Hardware device identifier

#### EmployeeAccessPermissions Table
Role-based access control per employee:
- Who can access which doors
- Time-based restrictions
- Day-based restrictions

## Setup & Installation

### 1. Install Dependencies
```bash
cd security
pip install -r door_entry_requirements.txt
```

### 2. Initialize Door Entry System
```bash
python init_door_entry_system.py
```

This will:
- Create all database tables
- Create default door configurations
- Generate database indexes

### 3. Setup Employee with QR Code
```python
from init_door_entry_system import setup_employee_with_qr
from security.door_entry_manager import DoorEntryManager

# Setup employee with QR code
setup_employee_with_qr(user_id=1, door_ids=[1, 2, 3])
# user_id: Employee's user database ID
# door_ids: List of door IDs they can access (optional, defaults to main entrance)
```

## Usage Examples

### Generate QR Code for New Employee

```python
from security.qr_code_manager import QRCodeManager

manager = QRCodeManager()

# Create QR code
result = manager.create_qr_code_for_employee(
    user_id=5,
    employee_id='EMP005',
    expiration_days=365
)

if result['success']:
    # Save QR code image
    image_path = manager.save_qr_code_image(
        result['qr_image'],
        'EMP005',
        output_dir='qr_codes'
    )
    print(f"QR code saved to: {image_path}")
    print(f"QR Token: {result['qr_token']}")
    print(f"Expires: {result['expires_at']}")
```

### Configure Door Access

```python
from security.door_entry_manager import DoorEntryManager

manager = DoorEntryManager()

# Give employee access to Finance Office door
# Available Monday-Friday, 8AM-5PM
manager.set_employee_door_access(
    user_id=5,
    door_id=3,  # Finance Office
    can_access=True,
    access_hours_start='08:00',
    access_hours_end='17:00',
    allowed_days=[0, 1, 2, 3, 4]  # Mon-Fri (0=Monday, 6=Sunday)
)
```

### Validate QR Code at Door

```python
from security.door_scanner import DoorScanner

# Initialize scanner at a door
scanner = DoorScanner(
    scanner_device_id='SCANNER_FINANCE_OFFICE',
    door_id=3
)

# Scan QR code
result = scanner.scan_qr_code(qr_token)

if result['access'] == 'GRANTED':
    print("✓ Access Granted!")
    print(f"User: {result['user_id']}")
    if result['fraud_alert']:
        print(f"⚠ Fraud Alert: {result['fraud_alert']['message']}")
else:
    print(f"✗ Access Denied: {result['message']}")
```

### Simulate Employee Entry (Testing)

```python
from security.door_scanner import ScannerSimulator

simulator = ScannerSimulator()

# Simulate employee trying to access a door
result = simulator.simulate_employee_entry(
    user_id=5,
    door_id=3  # Finance Office
)

if result['success']:
    print(f"✓ {result['message']}")
else:
    print(f"✗ {result['message']}")
```

### Get Employee Access History

```python
from security.door_entry_manager import DoorEntryManager

manager = DoorEntryManager()

# Get all access logs for employee
logs = manager.get_access_log(user_id=5, days=30)

for log in logs:
    status = "✓ Allowed" if log['access_granted'] else "✗ Denied"
    print(f"{log['access_time']} - {log['door']} - {status} ({log['result']})")
```

### Get Door Access Summary

```python
from security.door_entry_manager import DoorEntryManager

manager = DoorEntryManager()

# Get summary for a door in last 24 hours
summary = manager.get_door_access_summary(door_id=3, hours=24)

print(f"Door: {summary['door_name']}")
print(f"Location: {summary['door_name']}")
print(f"Total accesses: {summary['total_accesses']}")
print(f"Successful: {summary['successful_accesses']}")
print(f"Failed: {summary['failed_accesses']}")
print(f"Success rate: {summary['success_rate']}")
```

### Detect Fraud

```python
from security.door_entry_manager import DoorEntryManager

manager = DoorEntryManager()

# Get suspected fraudulent activities in last 7 days
fraud_alerts = manager.get_fraudulent_activities(days=7)

for alert in fraud_alerts:
    print(f"Alert ID: {alert['alert_id']}")
    print(f"Type: {alert['alert_type']}")
    print(f"Severity: {alert['severity']}")
    print(f"Scans: {alert['scan_count']}")
    print(f"Action: {alert['action_taken']}")
    print()
```

### Regenerate QR Code

```python
from security.qr_code_manager import QRCodeManager

manager = QRCodeManager()

# Regenerate QR code (when employee loses card, etc.)
result = manager.regenerate_qr_code(
    user_id=5,
    reason='employee_lost_card',
    regenerated_by=3  # Admin user ID who did this
)

# Old QR code automatically deactivated
print(f"New QR Token: {result['new_qr_token']}")
print(f"Old QR Token: {result['old_qr_token']} (now inactive)")
```

### Revoke Employee Access

```python
from security.qr_code_manager import QRCodeManager
from security.door_entry_manager import DoorEntryManager

# Disable QR code
qr_manager = QRCodeManager()
qr_manager.disable_qr_code(user_id=5, reason='employee_terminated')

# Remove specific door access
door_manager = DoorEntryManager()
door_manager.set_employee_door_access(
    user_id=5,
    door_id=3,
    can_access=False  # Revoke access
)
```

## Security Features

### 1. Cryptographic Security
- **AES-256 Encryption**: All tokens are encrypted
- **HMAC Signatures**: Verify token integrity
- **PBKDF2 Key Derivation**: Strong key generation from master secret
- **Random Components**: Each token includes random data

### 2. Anti-Tampering
- Server-side validation only (QR code not decoded at device)
- Signature verification prevents forged tokens
- Any tampering invalidates the QR code

### 3. Fraud Detection
- Real-time monitoring of access patterns
- Automatic detection of:
  - Same QR code scanned at multiple locations within seconds
  - Sudden location changes (physically impossible)
  - Multiple devices scanning same QR code
  - Unusual access times

### 4. Access Control Layers
1. **QR Code Validity**: Token must be valid and active
2. **Employee Permissions**: Employee must have access to that door
3. **Time-Based Access**: Can restrict by hours
4. **Day-Based Access**: Can restrict by weekday
5. **Security Level**: Door may require minimum employee level

### 5. Audit Trail
- All access attempts logged
- Cannot be modified (check before deleting)
- Includes success/failure details
- Device information tracked

## Administration

### Create New Door

```python
manager = DoorEntryManager()

result = manager.create_door(
    door_name='Lab Access',
    location='Building C - Level 2',
    door_type='restricted',
    requires_security_level=3,
    scanner_device_id='SCANNER_LAB_001'
)
```

### View All Doors

```python
manager = DoorEntryManager()
doors = manager.get_all_doors()

for door in doors:
    print(f"{door['door_name']} ({door['door_type']}) - {door['location']}")
```

### Get Employee Access Permissions

```python
manager = DoorEntryManager()

perms = manager.get_employee_access_permissions(user_id=5)

print(f"Employee {perms['user_id']} can access:")
for perm in perms['permissions']:
    status = "✓" if perm['can_access'] else "✗"
    hours = f" ({perm['access_hours_start']}-{perm['access_hours_end']})" if perm['access_hours_start'] else ""
    print(f"  {status} {perm['door_name']}{hours}")
```

## Configuration

### Master Secret
The system uses a master encryption key. Set via environment variable:
```bash
set DOOR_ACCESS_SECRET=your_secret_key_here
```

Or it defaults to: `vicinity_safety_qr_master_key_2026`

**IMPORTANT**: In production, use a strong, unique secret and store securely.

### QR Code Expiration
By default, QR codes expire after 365 days. Customize when generating:
```python
manager.create_qr_code_for_employee(
    user_id=5,
    employee_id='EMP005',
    expiration_days=180  # 6 months
)
```

### Access Hours Format
Times must be in 24-hour HH:MM format:
- `08:00` = 8:00 AM
- `17:00` = 5:00 PM
- `23:59` = 11:59 PM

### Allowed Days Format
Days are 0-6 where:
- 0 = Monday
- 1 = Tuesday
- 2 = Wednesday
- 3 = Thursday
- 4 = Friday
- 5 = Saturday
- 6 = Sunday

Example: `[0, 1, 2, 3, 4]` = Monday through Friday

## Compliance & Best Practices

### Best Practices
1. **Rotate QR Codes**: Periodically issue new QR codes (every 6-12 months)
2. **Monitor Fraud Alerts**: Review high-severity alerts immediately
3. **Audit Logs**: Review access logs regularly for unusual patterns
4. **Terminate Employees**: Immediately disable QR codes when employee leaves
5. **Time Limits**: Set reasonable access hours to detect unauthorized use
6. **Day Restrictions**: Use day restrictions for roles that don't work weekends

### Compliance
- **GDPR**: Access logs stored with employee ID (not name) for privacy
- **SOX**: Immutable audit trail for all access
- **ISO 27001**: Security levels and role-based access control
- **HIPAA**: Restricted area access controls with audit logging

## Troubleshooting

### QR Code Won't Scan
- Check that QR code image is clear (no damage/blur)
- Verify scanner device ID matches configuration
- Check QR code hasn't expired
- Verify employee has access to that door

### "Access Denied" for Valid Employee
- Check employee permissions for that door
- Verify access time is within allowed hours
- Check access time is on allowed day
- Verify employee security level >= door requirement

### Fraud Alert - Rapid Reuse
- Indicates QR code may have been copied
- Investigate which locations were accessed
- Review access log timestamps
- Consider regenerating QR code

### "Token Disabled" Error
Management team disabled the QR code. Request new QR code generation.

## API Integration

For REST API integration with a web/mobile scanner:

```python
from flask import Flask, request, jsonify
from security.door_scanner import DoorScanner

app = Flask(__name__)

@app.route('/api/scan', methods=['POST'])
def api_scan_qr():
    """REST endpoint for QR code validation"""
    data = request.json
    qr_token = data.get('qr_token')
    door_id = data.get('door_id')
    scanner_id = data.get('scanner_id', 'API_SCANNER')
    
    scanner = DoorScanner(scanner_id, door_id)
    result = scanner.scan_qr_code(qr_token)
    
    return jsonify(result)

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5000)
```

Request:
```json
{
    "qr_token": "encrypted_token_string",
    "door_id": 3,
    "scanner_id": "SCANNER_FINANCE"
}
```

Response:
```json
{
    "access": "GRANTED",
    "status_code": 200,
    "user_id": 5,
    "message": "Welcome! Access granted.",
    "timestamp": "2026-02-08T10:30:45.123456"
}
```

## Support & Maintenance

For issues or feature requests:
1. Check audit logs: Review DoorAccessLog table
2. Check fraud alerts: Review QRCodeFraudDetection table
3. Verify QR code status: Check QRCodeTokens.is_active
4. Check employee permissions: Verify EmployeeAccessPermissions table

## Summary

This door entry system provides:
- ✓ Unique QR codes per employee
- ✓ Cryptographic protection against copying
- ✓ Real-time fraud detection
- ✓ Role-based access control
- ✓ Complete audit trail
- ✓ Easy employee onboarding/offboarding
- ✓ Compliance-ready logging

Each employee's QR code is truly unique and cannot be duplicated without triggering fraud alerts in the system.
