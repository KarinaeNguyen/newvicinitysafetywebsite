# Vicinity Safety Financial Management System

## Overview
A secure, ACCA-compliant financial management system with 5-level security architecture and immutable audit logging.

## System Architecture

### Databases
1. **db/FinancialDatabase.db** - Main financial data (ACCA-compliant)
   - Sales, Costs, Stock, Timeline, Balance, Products, Logs
   - ChartOfAccounts, GeneralLedger, JournalEntries, Periods

2. **security/security.db** - User management and access control
   - Users, SecurityLevels

3. **security/logs.db** - Immutable audit logs
   - AuditLog (append-only, cannot be modified)

### Security Levels
- **Level 5**: Police/Government (highest, immutable by owner)
- **Level 4**: Owner (cannot change Level 5)
- **Level 3**: Admin (can add and remove users)
- **Level 2**: Manager (can add users)
- **Level 1**: Employee (basic access)

**Important**: Only Admin and Owner know about Level 5. Employees and Managers see a 4-level system.

## Installation

### Prerequisites
- Python 3.9 or higher
- Windows OS

### Setup Steps

1. **Create Virtual Environment** (Already completed)
   ```
   python -m venv .venv
   ```

2. **Activate Virtual Environment**
   ```
   .venv\Scripts\Activate.ps1
   ```

3. **Install Dependencies**
   ```
   pip install bcrypt
   ```

4. **Initialize Databases**
   ```
   python security\init_security_databases.py
   python security\setup_initial_data.py
   ```

5. **Launch Application**
   ```
   python app\finance_ui.py
   ```

## Default Login Credentials
- **Username**: admin
- **Password**: admin123
- **Security Level**: 4 (Owner)

**IMPORTANT**: Change the default password immediately after first login!

## Features

### User Management
- Add new users (Level 2+)
- Edit user information globally from User Management (Level 3-4 only)
- Remove users (Level 3+)
- View all users with roles and security levels
- Password hashing with bcrypt
- User Management uses an editable `ID` field (`display_id`) for human-facing user identity
- Internal `user_id` remains hidden and immutable for data integrity/audit references
- User edits can update ID, username, name, DOB, role, and optionally reset password
- Level 3 can edit Level 1-2 users only; Level 4 can edit Level 1-4 users; Level 5 users cannot be edited through this flow

### Audit Logging
- All actions are logged to immutable audit database
- Logs include: timestamp, user, action, details
- Logs cannot be modified or deleted (integrity protection)

### Security
- Password encryption using bcrypt
- Role-based access control (RBAC)
- 5-level security hierarchy
- Session management

### Point of Sales (POS)
- Single Point of Sales tab (duplicate tab removed)
- POS management access is available to Level 2, Level 3, and Level 4
- Sales receipt form captures customer name, phone, email, and address
- Sales entry supports product and service line tables with unit price, quantity, and line totals
- GTGT tax rate entry is included in the Sales receipt form
- Sales receipt supports `Export to PDF` before submission
- Sales receipt submission is approval-first; approved entries are posted into the system
- Historical Sales log rows can be edited by Level 2, 3, and 4 through an approval request workflow
- Sales log edit requests use peer approval: Level 3 can approve Level 2 requests; Level 4 approves Level 3 and Level 4 requests
- Sales log edit requests cannot be self-approved and include before/after diffs in Approval view
- Financial Data is display-only for records review; sales-log edit work is performed from Point of Sales > Reports
- Point of Sales > Reports now provides a summary-style sales report with Quarterly/Yearly periods and drill-down into underlying sales rows
- Sales adjustments are submitted only from drill-down transaction rows in POS Reports; summary rows are never edited directly
- Inventory warnings are shown when stock is low (<=2) or critical (<=0)
- Sales, Costs, Stock, and Timeline entry are available inline from POS `Entry` navigation
- Stock entry uses a multi-row product table (date, SKU, unit cost, current unit price, qty, tax amount, total unit cost)
- Stock entry requires both unit cost and current unit price per row before submission
- Approving a stock entry updates the product current unit price and unit cost for that SKU
- Stock entry tax is selected per submission and limited to 8% or 10% for all rows
- Stock entry tax is calculated from Unit Cost (pre-tax) x Qty x Tax %; current unit price does not affect stock tax
- Stock entry Total Unit Cost is calculated as Unit Cost (pre-tax) x Qty (tax is displayed separately in Tax Amount)
- Stock entry footer shows Grand Total Unit Cost, Grand Tax Amount, and Grand Total (Incl. Tax)
- Manual Stock Adjustment applies mandatory 8% tax on stock totals
- Back Office Entry popup is removed to simplify POS workflows
- Manual stock adjustments are available from POS `Settings` with audit logging
- Product Management is launched from POS `Settings` as a pop-out window and keeps the same management screen
- Uploaded product images are copied to managed storage under `artifacts/product_images`
- POS product cards now display product images directly
- Hovering SKU fields/tables (records, POS cart/cards, product management, entry forms) shows product image preview
- Product-related tabs are renamed for clearer navigation (`Product Catalog`, `Catalog Requests`)
- Inventory integrity scan script: `python scripts/check_inventory_integrity.py`

## User Permissions

| Action | Level 1 | Level 2 | Level 3 | Level 4 | Level 5 |
|--------|---------|---------|---------|---------|---------|
| Financial Data Access | View & Edit | View & Edit | View & Edit | View & Edit | View Only |
| Add Users | ✗ | Level 1 only | Level 1-3 | Level 1-4 | Level 1-5 |
| Remove Users | ✗ | Level 1 only | Level 1-2 only | Level 1-4 | Level 1-5* |
| View Audit Logs | ✓ | ✓ | ✓ | ✓ | ✓ |
| Modify Level 5 | ✗ | ✗ | ✗ | ✗ | ✓** |

*Level 5 removal is blocked if it would leave zero Level 5 users.

**Level 5 users can manage Level 5 accounts, but the last Level 5 user is protected.

## Professional User Policy

The following user policy applies across all roles and is enforced by the system where applicable, and by administrative procedure otherwise.

1. **Least Privilege**: Assign the minimum level required for job duties. Review access quarterly.
2. **Separation of Duties**: Oversight roles (Level 5) are read-only for financial data and focus on audit and supervision.
3. **Named Accounts Only**: Shared or generic accounts are prohibited. Each user must have a unique, identifiable account.
4. **Password Standard**: Minimum 10 characters with a mix of letters and numbers. Do not reuse the last 5 passwords. Rotate every 90 days.
5. **Level 5 Governance**: Only authorized government or police officials may hold Level 5. Level 4 cannot modify Level 5.
6. **User Lifecycle**: Disable accounts within 24 hours of termination or role change. Inactive accounts are reviewed monthly.
7. **Audit Review**: Audit logs are reviewed weekly by Level 4 or Level 5.
8. **Emergency Access**: Emergency access is time-limited and must be documented in the audit log with reason and approver.

## File Structure
```
Finance/
├── app/
│   └── finance_ui.py              # Windows UI application
├── db/
│   ├── FinancialDatabase.sql      # Main database schema
│   └── FinancialDatabase.db       # Main database file (to be created)
├── launch/
│   ├── launch_finance_ui.bat      # Double-click launcher (no console)
│   └── start_finance_system.bat   # Console launcher (shows errors)
├── scripts/
│   ├── clean_financial_data.py    # Data cleanup utilities
│   ├── init_financial_database.py # Database initialization script
│   ├── migrate_old_data.py        # Legacy data migration
│   └── show_test_credentials.py   # Test credential helper
├── docs/                          # System documentation
├── security/
│   ├── security.db                # User management database
│   ├── security.db.sql            # Security database schema
│   ├── logs.db                    # Immutable audit log database
│   ├── logs.db.sql                # Logs database schema
│   ├── init_security_databases.py # Database initialization script
│   ├── setup_initial_data.py      # Initial data setup script
│   └── user_management.py         # User management utilities
└── Old/                           # Legacy financial data
```

## Usage

### Adding a New User
1. Login with Level 2+ credentials
2. Navigate to "User Management"
3. Click "Add User"
4. Fill in user details:
   - Username (required)
   - Password (required)
   - First Name, Last Name
   - Date of Birth (YYYY-MM-DD)
   - Role
   - Access Type
   - Security Level (1-5)
5. Click "Save User"

### Removing a User
1. Login with Level 3+ credentials
2. Navigate to "User Management"
3. Click "Remove User"
4. Enter username to remove
5. Confirm deletion

### Viewing Audit Logs
1. Login with any credentials
2. Navigate to "View Audit Logs"
3. View recent system activity (last 100 entries)

## Security Best Practices

1. **Change Default Password**: Immediately change the default admin password
2. **Regular Audits**: Review audit logs regularly for suspicious activity
3. **Principle of Least Privilege**: Assign users the minimum security level needed
4. **Password Policy**: Enforce strong passwords for all users
5. **Level 5 Protection**: Only grant Level 5 access to authorized government/police officials
6. **Backup**: Regularly backup all databases

## ACCA Compliance

The system follows ACCA (Association of Chartered Certified Accountants) standards:
- Double-entry bookkeeping support
- Chart of Accounts
- General Ledger
- Journal Entries
- Period management
- Audit trail (immutable logs)

## Troubleshooting

### Cannot Connect to Database
- Ensure all database files exist in correct locations
- Run `init_security_databases.py` to recreate databases

### Login Failed
- Verify username and password
- Check that user exists in security.db
- Ensure password was hashed correctly

### Permission Denied
- Check user's security level
- Verify action is allowed for that level
- Review permission matrix above

## Development

### Adding New Features
1. Update database schema if needed
2. Add UI components to app/finance_ui.py
3. Implement access control checks
4. Add audit logging for all actions
5. Test with different security levels

### Database Migrations
1. Backup existing databases
2. Update .sql schema files
3. Create migration script
4. Test with sample data

## Support
For issues or questions, contact Vicinity Safety IT Department.

## License
Proprietary - Vicinity Safety © 2026
