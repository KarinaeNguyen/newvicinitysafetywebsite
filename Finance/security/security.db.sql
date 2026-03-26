-- Security Database: Users and Access Level Management
-- Created: 2026-02-07

CREATE TABLE SecurityLevels (
    level INTEGER PRIMARY KEY,
    level_name TEXT,
    description TEXT
);

CREATE TABLE Users (
    user_id INTEGER PRIMARY KEY AUTOINCREMENT,
    display_id TEXT,
    username TEXT UNIQUE,
    password_hash TEXT,
    security_level INTEGER,
    first_name TEXT,
    last_name TEXT,
    dob DATE,
    role TEXT,
    access_type TEXT,
    FOREIGN KEY(security_level) REFERENCES SecurityLevels(level)
);

-- Use strong password hashing (bcrypt/argon2).
-- Only Admin and Owner can manage users.

CREATE TABLE RemovalRequests (
    request_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id_to_remove INTEGER,
    requested_by_id INTEGER,
    status TEXT DEFAULT 'PENDING',
    reason TEXT,
    created_date DATETIME DEFAULT CURRENT_TIMESTAMP,
    approved_by_id INTEGER,
    approved_date DATETIME,
    FOREIGN KEY(user_id_to_remove) REFERENCES Users(user_id),
    FOREIGN KEY(requested_by_id) REFERENCES Users(user_id),
    FOREIGN KEY(approved_by_id) REFERENCES Users(user_id)
);

-- Dual-Control Rules:
-- 1. Minimum 2 Level 5 users required before any removal
-- 2. Only Level 5 users can approve removal of Level 5 users
-- 3. Cannot self-approve (different users required)
-- 4. Status values: PENDING, APPROVED, REJECTED, CANCELLED
