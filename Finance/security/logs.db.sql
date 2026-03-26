-- Security Log Database: Immutable Audit Log
-- Created: 2026-02-07

CREATE TABLE AuditLog (
    log_id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    user_id INTEGER,
    action TEXT,
    affected_table TEXT,
    affected_record TEXT,
    security_level INTEGER,
    details TEXT,
    FOREIGN KEY(user_id) REFERENCES Users(user_id)
);

-- AuditLog is append-only and cannot be changed or deleted.
-- All financial changes and access attempts must be recorded here.
