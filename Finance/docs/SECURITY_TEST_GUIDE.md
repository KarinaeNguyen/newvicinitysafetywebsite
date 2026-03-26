# Security Level Testing Guide

## Current Users

| Username | Password   | Level | Role              |
|----------|------------|-------|-------------------|
| admin    | admin123   | 4     | Owner             |
| officer  | officer123 | 5     | Police/Government |

---

## Test Scenario 1: Level 4 CANNOT Remove Level 5

### Steps:
1. **Launch the application**
   - Double-click `launch\launch_finance_ui.bat`

2. **Login as admin (Level 4)**
   - Username: `admin`
   - Password: `admin123`

3. **Try to remove officer**
   - Go to "User Management"
   - Click "Remove User"
   - Enter username: `officer`
   - Click "Remove User"

### Expected Result: ❌ DENIED
```
Access Denied

Level 4 (Owner) cannot remove Level 5 (Police/Government) users.

Level 5 is immutable by owner.
Only Level 5 can manage Level 5 users.
```

---

## Test Scenario 2: Cannot Remove Last Level 5 User

### Steps:
1. **Login as officer (Level 5)**
   - Username: `officer`
   - Password: `officer123`

2. **Try to remove yourself (last Level 5)**
   - Go to "User Management"
   - Click "Remove User"  
   - Enter username: `officer`
   - Click "Remove User"

### Expected Result: ❌ DENIED
```
Access Denied

Cannot remove the last Level 5 (Police/Government) user.

At least one Level 5 user must exist in the system at all times.
```

---

## Test Scenario 3: Level 5 CAN Remove Level 4

### Steps:
1. **Login as officer (Level 5)**
   - Username: `officer`
   - Password: `officer123`

2. **Remove admin user**
   - Go to "User Management"
   - Click "Remove User"
   - Enter username: `admin`
   - Confirm removal

### Expected Result: ✅ SUCCESS
```
Success

User 'admin' removed successfully
```

---

## Test Scenario 4: Level 5 Can Add New Level 5 Users

### Steps:
1. **Login as officer (Level 5)**

2. **Add a second Level 5 user**
   - Click "Add User"
   - Username: `officer2`
   - Password: `secure456`
   - First Name: `Jane`
   - Last Name: `Smith`
   - Security Level: `5` (Police/Government)
   - Role: `Police/Government`
   - Access Type: `Full`
   - Click "Save User"

3. **Now try to remove officer (first Level 5)**
   - Click "Remove User"
   - Enter: `officer`
   - Confirm

### Expected Result: ✅ SUCCESS
```
Success

User 'officer' removed successfully
```

**Why it works now**: There are 2 Level 5 users, so removing one is allowed.

---

## Security Rules Summary

### ✅ Allowed Operations:
- Level 5 can manage ALL users (including other Level 5)
- Level 4 can manage users Level 1-4
- Level 3 can manage users Level 1-3
- Level 5 can remove another Level 5 IF at least 2 Level 5 users exist

### ❌ Denied Operations:
- Level 4 CANNOT remove or modify Level 5 users (immutable by owner)
- Level 4 CANNOT add Level 5 users
- CANNOT remove the last Level 5 user (system protection)
- Lower levels cannot manage higher levels

---

## Reset Users Again

To reset back to 2 users (admin and officer):
```bash
cd "d:\Vicinity Safety\Finance"
.\.venv\Scripts\python.exe security\reset_users.py
```

---

## Quick Launch

Double-click: `launch\launch_finance_ui.bat` to start the application

---

## Audit Log

All user management actions are logged in the immutable audit log:
- Who performed the action
- What action was performed
- When it was performed
- Success or failure

View audit logs in the application: **Audit Logs** menu
