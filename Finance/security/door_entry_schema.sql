-- Door Entry System with Secure QR Codes
-- This schema extends the security system to include physical access control

-- QR Code Token Storage (each employee gets a unique, non-copyable QR code)
CREATE TABLE IF NOT EXISTS QRCodeTokens (
    token_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    qr_token TEXT UNIQUE NOT NULL,  -- Encrypted token unique to this employee
    qr_secret TEXT NOT NULL,  -- HMAC secret for validation
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP,  -- QR code expiration (optional, for rotation)
    is_active BOOLEAN DEFAULT 1,
    signature TEXT NOT NULL,  -- Cryptographic signature (prevents tampering)
    FOREIGN KEY(user_id) REFERENCES Users(user_id)
);

-- Door Entry Log (tracks all access attempts)
CREATE TABLE IF NOT EXISTS DoorAccessLog (
    access_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    qr_token TEXT NOT NULL,
    access_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    door_location TEXT,  -- Which door/gate
    access_granted BOOLEAN,
    validation_result TEXT,  -- 'valid', 'expired', 'disabled', 'forged', etc.
    device_info TEXT,  -- Scanner device identifier
    ip_address TEXT,
    FOREIGN KEY(user_id) REFERENCES Users(user_id),
    FOREIGN KEY(qr_token) REFERENCES QRCodeTokens(qr_token)
);

-- QR Code Scan Fraud Detection (detect copied QR codes)
CREATE TABLE IF NOT EXISTS QRCodeFraudDetection (
    fraud_alert_id INTEGER PRIMARY KEY AUTOINCREMENT,
    qr_token TEXT NOT NULL,
    alert_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    alert_type TEXT,  -- 'unusual_location', 'rapid_reuse', 'multiple_devices'
    scan_count_in_period INTEGER,
    time_period_seconds INTEGER,
    locations_list TEXT,  -- JSON list of locations in short time period
    severity TEXT,  -- 'low', 'medium', 'high'
    action_taken TEXT,  -- 'logged', 'disabled', 'investigation'
    FOREIGN KEY(qr_token) REFERENCES QRCodeTokens(qr_token)
);

-- Door/Gate Configuration
CREATE TABLE IF NOT EXISTS DoorConfiguration (
    door_id INTEGER PRIMARY KEY AUTOINCREMENT,
    door_name TEXT UNIQUE NOT NULL,
    location TEXT,
    door_type TEXT,  -- 'entrance', 'exit', 'emergency', 'restricted'
    requires_security_level INTEGER,  -- Minimum security level needed
    is_active BOOLEAN DEFAULT 1,
    scanner_device_id TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Employee Access Levels per Door (role-based door access)
CREATE TABLE IF NOT EXISTS EmployeeAccessPermissions (
    permission_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    door_id INTEGER NOT NULL,
    can_access BOOLEAN DEFAULT 1,
    access_hours_start TEXT,  -- Time format HH:MM
    access_hours_end TEXT,
    allowed_days TEXT,  -- JSON list of days (0-6)
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, door_id),
    FOREIGN KEY(user_id) REFERENCES Users(user_id),
    FOREIGN KEY(door_id) REFERENCES DoorConfiguration(door_id)
);

-- QR Code Regeneration History (track when QR codes are renewed)
CREATE TABLE IF NOT EXISTS QRCodeRegenerationLog (
    regen_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    old_qr_token TEXT,
    new_qr_token TEXT NOT NULL,
    regeneration_reason TEXT,  -- 'expired', 'compromised', 'manual_renewal'
    regenerated_by INTEGER,  -- Admin user ID who triggered
    regenerated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(user_id) REFERENCES Users(user_id),
    FOREIGN KEY(regenerated_by) REFERENCES Users(user_id)
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_qr_token ON QRCodeTokens(qr_token);
CREATE INDEX IF NOT EXISTS idx_user_qr ON QRCodeTokens(user_id);
CREATE INDEX IF NOT EXISTS idx_access_log_user ON DoorAccessLog(user_id);
CREATE INDEX IF NOT EXISTS idx_access_log_time ON DoorAccessLog(access_time);
CREATE INDEX IF NOT EXISTS idx_fraud_detection_token ON QRCodeFraudDetection(qr_token);
CREATE INDEX IF NOT EXISTS idx_access_permissions_user ON EmployeeAccessPermissions(user_id);
