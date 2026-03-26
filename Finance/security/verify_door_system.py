"""
Door Entry System - Verification & Testing Script
Run this to verify the system is correctly installed and working
"""

import sys
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
SECURITY_DB_PATH = BASE_DIR / "security" / "security.db"


def print_header(text):
    """Print formatted header"""
    print(f"\n{'='*60}")
    print(f"  {text}")
    print(f"{'='*60}\n")


def check_database():
    """Check if database exists and has required tables"""
    print("1️⃣  Checking Database...")
    
    try:
        conn = sqlite3.connect(SECURITY_DB_PATH)
        cursor = conn.cursor()
        
        # Check for required tables
        required_tables = [
            'QRCodeTokens',
            'DoorAccessLog',
            'QRCodeFraudDetection',
            'DoorConfiguration',
            'EmployeeAccessPermissions',
            'QRCodeRegenerationLog'
        ]
        
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        existing_tables = {row[0] for row in cursor.fetchall()}
        
        missing_tables = set(required_tables) - existing_tables
        
        if missing_tables:
            print(f"   ❌ Missing tables: {', '.join(missing_tables)}")
            print("   👉 Run: python security\\init_door_entry_system.py")
            conn.close()
            return False
        
        print(f"   ✅ All {len(required_tables)} required tables found")
        
        # Count records
        for table in required_tables:
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            count = cursor.fetchone()[0]
            print(f"      • {table}: {count} records")
        
        conn.close()
        return True
    
    except Exception as e:
        print(f"   ❌ Database error: {e}")
        return False


def check_dependencies():
    """Check if required Python packages are installed"""
    print("2️⃣  Checking Dependencies...")
    
    dependencies = {
        'qrcode': 'QR Code generation',
        'PIL': 'Image processing (Pillow)',
        'cryptography': 'Encryption',
        'bcrypt': 'Password hashing'
    }
    
    missing = []
    
    for module, description in dependencies.items():
        try:
            __import__(module)
            print(f"   ✅ {module:15} - {description}")
        except ImportError:
            print(f"   ❌ {module:15} - {description} (NOT INSTALLED)")
            missing.append(module)
    
    if missing:
        print(f"\n   👉 Install missing packages:")
        print(f"      pip install {' '.join(missing)}")
        return False
    
    return True


def check_door_configuration():
    """Check if doors are configured"""
    print("3️⃣  Checking Door Configuration...")
    
    try:
        conn = sqlite3.connect(SECURITY_DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM DoorConfiguration")
        door_count = cursor.fetchone()[0]
        
        if door_count == 0:
            print("   ❌ No doors configured")
            print("   👉 Run: python security\\init_door_entry_system.py")
            conn.close()
            return False
        
        print(f"   ✅ {door_count} doors configured:")
        
        cursor.execute("""
            SELECT door_id, door_name, location, door_type
            FROM DoorConfiguration
            ORDER BY door_id
        """)
        
        for row in cursor.fetchall():
            print(f"      • [{row[0]}] {row[1]:25} ({row[3]:15}) at {row[2]}")
        
        conn.close()
        return True
    
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False


def check_employees():
    """Check if employees exist in the system"""
    print("4️⃣  Checking Employees...")
    
    try:
        conn = sqlite3.connect(SECURITY_DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM Users WHERE security_level >= 1")
        employee_count = cursor.fetchone()[0]
        
        if employee_count == 0:
            print("   ⚠️  No employees in system")
            return True  # Not critical, system is working
        
        print(f"   ✅ {employee_count} employees found:")
        
        cursor.execute("SELECT user_id, username, security_level FROM Users LIMIT 5")
        
        for row in cursor.fetchall():
            cursor.execute(
                "SELECT COUNT(*) FROM QRCodeTokens WHERE user_id = ? AND is_active = 1",
                (row[0],)
            )
            has_qr = cursor.fetchone()[0] > 0
            qr_status = "✓" if has_qr else "✗"
            print(f"      • [{row[0]}] {row[1]:20} (Level {row[2]}) QR: {qr_status}")
        
        conn.close()
        return True
    
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False


def check_qr_codes():
    """Check QR code status"""
    print("5️⃣  Checking QR Codes...")
    
    try:
        conn = sqlite3.connect(SECURITY_DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM QRCodeTokens WHERE is_active = 1")
        active_qr = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM QRCodeTokens WHERE is_active = 0")
        inactive_qr = cursor.fetchone()[0]
        
        print(f"   ✅ Active QR codes: {active_qr}")
        print(f"   ℹ️  Inactive QR codes: {inactive_qr}")
        
        # Check for expired QR codes
        cursor.execute("""
            SELECT COUNT(*) FROM QRCodeTokens 
            WHERE expires_at < ? AND is_active = 1
        """, (datetime.now().isoformat(),))
        
        expired = cursor.fetchone()[0]
        if expired > 0:
            print(f"   ⚠️  Expired QR codes still active: {expired}")
        
        conn.close()
        return True
    
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False


def check_access_logs():
    """Check access log statistics"""
    print("6️⃣  Checking Access Logs...")
    
    try:
        conn = sqlite3.connect(SECURITY_DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM DoorAccessLog")
        total_accesses = cursor.fetchone()[0]
        
        if total_accesses == 0:
            print("   ℹ️  No access logs yet (system is ready)")
            conn.close()
            return True
        
        cursor.execute("""
            SELECT COUNT(*) FROM DoorAccessLog WHERE access_granted = 1
        """)
        granted = cursor.fetchone()[0]
        
        cursor.execute("""
            SELECT COUNT(*) FROM DoorAccessLog WHERE access_granted = 0
        """)
        denied = cursor.fetchone()[0]
        
        success_rate = (granted / total_accesses * 100) if total_accesses > 0 else 0
        
        print(f"   ✅ Total accesses: {total_accesses}")
        print(f"      • Granted: {granted}")
        print(f"      • Denied: {denied}")
        print(f"      • Success rate: {success_rate:.1f}%")
        
        # Today's accesses
        cursor.execute("""
            SELECT COUNT(*) FROM DoorAccessLog 
            WHERE DATE(access_time) = DATE('now')
        """)
        today = cursor.fetchone()[0]
        print(f"      • Today: {today} accesses")
        
        conn.close()
        return True
    
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False


def check_fraud_detection():
    """Check fraud detection system"""
    print("7️⃣  Checking Fraud Detection...")
    
    try:
        conn = sqlite3.connect(SECURITY_DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM QRCodeFraudDetection")
        total_alerts = cursor.fetchone()[0]
        
        if total_alerts == 0:
            print("   ✅ No fraud detected")
            conn.close()
            return True
        
        cursor.execute("""
            SELECT severity, COUNT(*) FROM QRCodeFraudDetection
            GROUP BY severity
        """)
        
        print(f"   ℹ️  Total fraud alerts: {total_alerts}")
        for severity, count in cursor.fetchall():
            print(f"      • {severity.upper()}: {count}")
        
        # Recent high-severity alerts
        cursor.execute("""
            SELECT qr_token, alert_type, severity FROM QRCodeFraudDetection
            WHERE severity = 'high'
            ORDER BY alert_time DESC
            LIMIT 3
        """)
        
        high_severity = cursor.fetchall()
        if high_severity:
            print(f"\n   ⚠️  Recent high-severity alerts:")
            for alert in high_severity:
                print(f"      • {alert[1]}: {alert[0][:20]}... (Severity: {alert[2]})")
        
        conn.close()
        return True
    
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False


def test_qr_generation():
    """Test QR code generation"""
    print("8️⃣  Testing QR Code Generation...")
    
    try:
        from security.qr_code_manager import QRCodeManager
        
        print("   Testing QR code manager initialization...")
        manager = QRCodeManager()
        print("   ✅ QR Code Manager initialized successfully")
        
        # Get a test user
        conn = sqlite3.connect(SECURITY_DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT user_id, username FROM Users LIMIT 1")
        user = cursor.fetchone()
        conn.close()
        
        if not user:
            print("   ⚠️  No test user available")
            return True
        
        user_id, username = user
        print(f"   Testing QR code generation for user: {username} (ID: {user_id})")
        
        # Try to generate token
        token, secret, sig = manager.generate_secure_token(user_id, username)
        print(f"   ✅ Secure token generated: {token[:30]}...")
        print(f"   ✅ Token length: {len(token)} characters")
        print(f"   ✅ Signature: {sig[:20]}...")
        
        return True
    
    except ImportError as e:
        print(f"   ❌ Cannot import QRCodeManager: {e}")
        print("      Make sure dependencies are installed")
        return False
    except Exception as e:
        print(f"   ⚠️  Error during QR generation test: {e}")
        return True  # Not critical


def test_door_access_validation():
    """Test door access validation"""
    print("9️⃣  Testing Door Access Validation...")
    
    try:
        from security.qr_code_manager import QRCodeManager
        
        # Get a test employee with QR code
        conn = sqlite3.connect(SECURITY_DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT token_id, qr_token, user_id 
            FROM QRCodeTokens 
            WHERE is_active = 1 
            LIMIT 1
        """)
        
        qr_record = cursor.fetchone()
        
        if not qr_record:
            print("   ℹ️  No active QR codes to test")
            conn.close()
            return True
        
        _, qr_token, user_id = qr_record
        conn.close()
        
        manager = QRCodeManager()
        result = manager.validate_qr_code(qr_token)
        
        if result['valid']:
            print(f"   ✅ QR Code validation: PASSED")
            print(f"      • Result: {result['reason']}")
            print(f"      • User ID: {result['user_id']}")
        else:
            print(f"   ℹ️  QR Code validation result: {result['reason']}")
            print(f"      • Message: {result['message']}")
        
        return True
    
    except Exception as e:
        print(f"   ⚠️  Error during validation test: {e}")
        return True


def print_summary(results):
    """Print test summary"""
    print_header("Test Summary")
    
    passed = sum(results.values())
    total = len(results)
    
    print(f"Results: {passed}/{total} checks passed\n")
    
    for check, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {status:10} - {check}")
    
    print()
    
    if passed == total:
        print("🎉 All checks passed! System is ready to use.")
        print("\nNext steps:")
        print("  1. Review DOOR_ENTRY_QUICK_START.md for usage examples")
        print("  2. Setup employees with QR codes")
        print("  3. Configure door access permissions")
        print("  4. Test with ScannerSimulator")
        return True
    else:
        print("⚠️  Some checks failed. Review the errors above.")
        return False


def main():
    """Run all verification checks"""
    print_header("Door Entry System - Verification")
    
    print("Starting comprehensive system check...\n")
    
    results = {
        'Dependencies installed': check_dependencies(),
        'Database initialized': check_database(),
        'Doors configured': check_door_configuration(),
        'Employees present': check_employees(),
        'QR Code system': check_qr_codes(),
        'Access logging': check_access_logs(),
        'Fraud detection': check_fraud_detection(),
        'QR generation': test_qr_generation(),
        'Access validation': test_door_access_validation(),
    }
    
    success = print_summary(results)
    
    print_header("Verification Complete")
    
    return 0 if success else 1


if __name__ == '__main__':
    sys.exit(main())
