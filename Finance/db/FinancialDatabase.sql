-- Security Layer: 5-Level Security Schema --

-- Level 5: Police/Government (highest, immutable by owner)
-- Level 4: Owner (cannot change Level 5)
-- Level 3: Admin
-- Level 2: Manager
-- Level 1: Employee

CREATE TABLE SecurityLevels (
    level INTEGER PRIMARY KEY,
    level_name TEXT,
    description TEXT
);

CREATE TABLE Users (
    user_id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE,
    password_hash TEXT,
    security_level INTEGER,
    FOREIGN KEY(security_level) REFERENCES SecurityLevels(level)
);

-- Encryption protocol: Sensitive fields (e.g., password_hash, financial records) should be encrypted using AES-256 or similar. Application layer must enforce access control and encryption.

-- Only Admin and Owner know about Level 5; only Police/Government can access Level 5 data. Owner/Admin can access Level 4 and below. Managers and Employees access Level 2 and 1, respectively.

-- All access and changes must be logged for audit.
-- ACCA-compliant tables and fields added below --

CREATE TABLE ChartOfAccounts (
    account_code TEXT PRIMARY KEY,
    account_name TEXT,
    account_type TEXT,
    parent_code TEXT,
    description TEXT
);

CREATE TABLE GeneralLedger (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    entry_date DATE,
    account_code TEXT,
    debit REAL,
    credit REAL,
    balance REAL,
    reference TEXT,
    description TEXT,
    FOREIGN KEY(account_code) REFERENCES ChartOfAccounts(account_code)
);

CREATE TABLE JournalEntries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    journal_date DATE,
    account_code TEXT,
    debit REAL,
    credit REAL,
    entry_type TEXT,
    reference TEXT,
    description TEXT,
    FOREIGN KEY(account_code) REFERENCES ChartOfAccounts(account_code)
);

CREATE TABLE Periods (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    period_start DATE,
    period_end DATE,
    closing_balance REAL
);
-- FinancialDatabase master schema for Vicinity Safety
-- Created: 2026-02-07

CREATE TABLE Sales (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sale_date DATE,
    order_id TEXT,
    channel TEXT,
    product_sku TEXT,
    units_sold INTEGER,
    unit_price REAL,
    gross_sales REAL,
    vat_rate REAL,
    vat_amount REAL,
    service_fee REAL,
    shipping_fee REAL,
    note TEXT,
    approved_by INTEGER,
    approved_at TIMESTAMP
);

CREATE TABLE Costs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    cost_type TEXT,
    cost_date DATE,
    amount REAL,
    vat_rate REAL,
    vat_amount REAL,
    note TEXT
);

CREATE TABLE Stock (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date DATE,
    product_sku TEXT,
    unit_cost REAL,
    current_unit_price REAL,
    unit_in INTEGER,
    tax_rate REAL,
    tax_amount REAL,
    total REAL,
    note TEXT
);

CREATE TABLE Timeline (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_date DATE,
    event_name TEXT,
    cash_in REAL,
    cash_out REAL,
    balance REAL,
    note TEXT
);

CREATE TABLE Balance (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    balance_date DATE,
    amount REAL
);


-- Volunteers table removed as this is strictly a Financial Database.
CREATE TABLE Products (
    sku TEXT PRIMARY KEY,
    name TEXT,
    category TEXT,
    unit_cost REAL,
    current_unit_price REAL,
    image_path TEXT
);

CREATE TABLE Logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    log_date DATE,
    log_type TEXT,
    product_sku TEXT,
    details TEXT
);

-- Pending financial entries (approval workflow)
CREATE TABLE PendingEntries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    entry_type TEXT NOT NULL,
    payload TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'PENDING',
    created_by INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    approved_by INTEGER,
    approved_at TIMESTAMP,
    rejected_reason TEXT
);

CREATE TABLE CustomerProfiles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    full_name TEXT NOT NULL,
    phone TEXT,
    email TEXT,
    address TEXT,
    norm_phone TEXT,
    norm_email TEXT,
    norm_address TEXT,
    status TEXT NOT NULL DEFAULT 'ACTIVE',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE SalesReceipts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pending_entry_id INTEGER,
    customer_id INTEGER,
    receipt_no TEXT NOT NULL,
    sale_date DATE,
    tax_rate REAL,
    subtotal REAL,
    service_total REAL,
    tax_amount REAL,
    total REAL,
    status TEXT NOT NULL DEFAULT 'PENDING',
    pdf_path TEXT,
    note TEXT,
    created_by INTEGER,
    approved_by INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    approved_at TIMESTAMP
);

CREATE TABLE SalesReceiptLines (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    receipt_id INTEGER NOT NULL,
    line_type TEXT NOT NULL,
    item_name TEXT NOT NULL,
    product_sku TEXT,
    unit_price REAL,
    quantity INTEGER,
    line_total REAL
);

CREATE TABLE CustomerMatchFlags (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pending_entry_id INTEGER,
    submitted_name TEXT,
    submitted_phone TEXT,
    submitted_email TEXT,
    submitted_address TEXT,
    matched_customer_id INTEGER,
    matched_score INTEGER,
    status TEXT NOT NULL DEFAULT 'PENDING',
    review_note TEXT,
    reviewed_by INTEGER,
    reviewed_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- All fields are nullable for flexibility.
-- Add indexes and foreign keys as needed for relationships.
