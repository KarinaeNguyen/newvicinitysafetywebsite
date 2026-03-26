-- FinancialDatabase draft schema for Vicinity Safety
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
    service_fee REAL,
    shipping_fee REAL,
    note TEXT
);

CREATE TABLE Costs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    cost_type TEXT,
    cost_date DATE,
    amount REAL,
    note TEXT
);

CREATE TABLE Stock (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date DATE,
    product_sku TEXT,
    unit_cost REAL,
    unit_in INTEGER,
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

CREATE TABLE Volunteers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    volunteer_id TEXT,
    group_name TEXT,
    hours INTEGER,
    certification TEXT,
    note TEXT
);

CREATE TABLE Products (
    sku TEXT PRIMARY KEY,
    name TEXT,
    category TEXT,
    unit_cost REAL
);

CREATE TABLE Logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    log_date DATE,
    log_type TEXT,
    product_sku TEXT,
    details TEXT
);

-- Add indexes and foreign keys as needed for relationships.
