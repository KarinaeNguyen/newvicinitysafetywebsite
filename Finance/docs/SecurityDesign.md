# Security Design for Vicinity Safety Financial System

## 1. User Authentication
- Store user credentials in Users table (username, password_hash, security_level).
- Use strong password hashing (bcrypt or Argon2).
- Enforce password complexity and periodic changes.

## 2. Access Control
- SecurityLevels table defines 5 levels:
  - Level 5: Police/Government (highest, immutable by owner)
  - Level 4: Owner
  - Level 3: Admin
  - Level 2: Manager
  - Level 1: Employee
- Application logic restricts access to data and actions based on security_level.
- Only Admin and Owner know about Level 5; only Police/Government can access Level 5 data.

## 2.1 Professional User Policy
- Least privilege: assign the minimum level required, and review access quarterly.
- Separation of duties: Level 5 is oversight only and remains read-only for financial data.
- Named accounts only: no shared or generic user accounts.
- Password standard: minimum 10 characters with letters and numbers, rotate every 90 days, no reuse of last 5.
- Level 5 governance: only authorized officials hold Level 5; Level 4 cannot modify Level 5.
- User lifecycle: disable accounts within 24 hours of termination or role change; review inactive accounts monthly.
- Audit review: review audit logs weekly and document findings.
- Emergency access: time-limited and logged with reason and approver.

## 3. Data Encryption
- Encrypt sensitive fields (e.g., password_hash, financial records) using AES-256 or similar.
- Store encryption keys securely (never in database).
- Use field-level encryption for critical financial data.

## 4. Audit Logging
- Log all access, changes, and failed attempts in a dedicated AuditLog table.
- Include timestamp, user_id, action, affected table/record, and security_level.

## 5. Application Layer Enforcement
- All access control and encryption protocols enforced in application code (Python recommended).
- Use role-based access control (RBAC) for permissions.
- Regularly review and update security policies.

## 6. Security Awareness
- Train Admin and Owner on security protocols.
- Document procedures for Police/Government access (Level 5).

---

This document outlines the security design for the financial system. Implementation will require secure coding practices and regular audits.
