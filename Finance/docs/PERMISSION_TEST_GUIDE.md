# Complete Permission System Testing Guide

## Current Users

| ID | Username | Password   | Level | Role              | Financial Access |
|----|----------|------------|-------|-------------------|------------------|
| 1  | admin    | admin123   | 4     | Owner             | View & Edit      |
| 2  | officer  | officer123 | 5     | Police/Government | **View Only**    |

---

## Permission Structure

### Level 1 (Employee)
- ✅ **Financial Data**: View & Edit
- ❌ **User Management**: None

### Level 2 (Manager)
- ✅ **Financial Data**: View & Edit
- ✅ **Add Users**: Level 1 only
- ✅ **Remove Users**: Level 1 only

### Level 3 (Admin)
- ✅ **Financial Data**: View & Edit
- ✅ **Add Users**: Level 1, 2, 3
- ✅ **Remove Users**: Level 1, 2 only
- ❌ **Cannot Remove**: Level 3, 4, or 5

### Level 4 (Owner)
- ✅ **Financial Data**: Full access (View & Edit)
- ✅ **Add Users**: Level 1, 2, 3, 4
- ✅ **Remove Users**: Level 1, 2, 3, 4
- ❌ **Cannot Modify**: Level 5 users (immutable)

### Level 5 (Police/Government)
- ⚠️ **Financial Data**: **VIEW ONLY** (read-only for oversight)
- ✅ **Add Users**: All levels (1-5)
- ✅ **Remove Users**: All levels (1-5)
- 🔒 **Protection**: At least 1 Level 5 must always exist

---

## Test Scenario 1: Admin (Level 4) Permissions

### Login
- Username: `admin`
- Password: `admin123`

### Dashboard Check
✅ Should show:
- Security Level: Owner
- Financial Access: **View & Edit**
- Permissions listed:
  - ✓ View & Edit financial data
  - ✓ Add users: Level 1, 2, 3, 4
  - ✓ Remove users: Level 1, 2, 3, 4

### Test 1.1: Try to Add Level 5 User
**Steps:**
1. Go to User Management
2. Click "Add User"
3. Notice dropdown only shows: 1, 2, 3, 4
4. Level 5 option is NOT available

**Expected:** ✅ Cannot add Level 5 - restricted by system

### Test 1.2: Try to Remove Officer (Level 5)
**Steps:**
1. Go to User Management
2. Click "Remove User"
3. Enter username: `officer`
4. Click Remove

**Expected:** ❌ DENIED
```
Access Denied

Level 4 (Owner) cannot remove Level 5 users.

You can only remove: Level 1, 2, 3, 4
```

### Test 1.3: Add Level 1 Employee
**Steps:**
1. Click "Add User"
2. Fill in:
   - Username: `employee1`
   - Password: `emp123`
   - First Name: `John`
   - Last Name: `Employee`
   - DOB: `1995-01-01`
   - Role: `Staff`
   - Access Type: `Limited`
   - Security Level: `1`
3. Save

**Expected:** ✅ SUCCESS - User added

### Test 1.4: Add Level 3 Admin
**Steps:**
1. Click "Add User"
2. Fill in:
   - Username: `manager`
   - Password: `mgr123`
   - First Name: `Jane`
   - Last Name: `Manager`
   - Security Level: `3`
3. Save

**Expected:** ✅ SUCCESS - Level 4 can add Level 3

---

## Test Scenario 2: Officer (Level 5) Permissions

### Login
- Username: `officer`
- Password: `officer123`

### Dashboard Check
✅ Should show:
- Security Level: Police/Government
- Financial Access: **View Only** ⚠️
- Warning message: "Level 5 has READ-ONLY access to financial data for oversight purposes"
- Permissions:
  - ✓ View financial data (READ ONLY)
  - ✓ Add users: Level 1, 2, 3, 4, 5
  - ✓ Remove users: Level 1, 2, 3, 4, 5

### Test 2.1: Financial Data Access
**Expected:**
- Can VIEW all financial records
- **Cannot EDIT** financial data (read-only oversight role)

### Test 2.2: Remove Admin (Level 4)
**Steps:**
1. User Management → Remove User
2. Enter: `admin`
3. Confirm removal

**Expected:** ✅ SUCCESS
```
Success

User 'admin' removed successfully
```

**Why:** Level 5 has supreme authority over all levels

### Test 2.3: Try to Remove Self (Last Level 5)
**Steps:**
1. User Management → Remove User
2. Enter: `officer`
3. Try to remove

**Expected:** ❌ DENIED
```
Access Denied

Cannot remove the last Level 5 (Police/Government) user.

At least one Level 5 user must exist in the system at all times.
```

### Test 2.4: Add Second Level 5 User
**Steps:**
1. Add User
2. Fill in:
   - Username: `officer2`
   - Password: `off456`
   - First Name: `Sarah`
   - Last Name: `Commander`
   - Security Level: `5`
3. Save

**Expected:** ✅ SUCCESS - Level 5 can add Level 5

### Test 2.5: Now Remove First Officer
**Steps:**
1. Remove User → Enter: `officer`
2. Confirm

**Expected:** ✅ SUCCESS
```
(Now allowed because 2 Level 5 users exist)
```

---

## Test Scenario 3: Manager (Level 3) Permissions

First, reset and add a Level 3 user:
```bash
# As admin (after reset):
Add user: manager / mgr123 / Level 3
```

### Login as Manager
- Username: `manager`
- Password: `mgr123`

### Dashboard Check
✅ Should show:
- Security Level: Admin
- Financial Access: **View & Edit**
- Permissions:
  - ✓ View & Edit financial data
  - ✓ Add users: Level 1, 2, 3
  - ✓ Remove users: Level 1, 2 **only**

### Test 3.1: Add Level 1 or 2
**Expected:** ✅ SUCCESS - Level 3 can add 1-3

### Test 3.2: Try to Add Level 4
**Expected:** Dropdown only shows 1, 2, 3

### Test 3.3: Try to Remove Level 3 User
**Steps:**
1. Add another Level 3 user first
2. Try to remove the other Level 3

---

## Test Scenario 5: User Management Edit

### Test 5.1: Level 3 edits Level 2 user
**Steps:**
1. Login as Level 3 user.
2. Open User Management.
3. Select a Level 2 user and click `Edit Selected User`.
4. Confirm the dialog shows editable `ID` (human-facing user ID).
5. Change ID, first name, or role.
6. Save changes.

**Expected:** ✅ SUCCESS
- User record updates immediately.
- Updated information appears wherever the user is referenced in the UI.
- Internal database `user_id` remains hidden and unchanged.
- Duplicate `ID` values are blocked.

### Test 5.2: Level 3 tries to edit Level 3, 4, or 5 user
**Expected:** ❌ DENIED
- Clear access message states Level 3 can edit Level 1-2 only.

### Test 5.3: Level 4 edits Level 4 or below
**Steps:**
1. Login as Level 4 user.
2. Open User Management.
3. Select a Level 1-4 user.
4. Change username and optionally set a new password.

**Expected:** ✅ SUCCESS
- Username uniqueness is enforced.
- New password works for next login.

### Test 5.4: Level 4 tries to edit Level 5 user
**Expected:** ❌ DENIED
- Message states Level 5 users cannot be edited through User Management.

### Test 5.5: Duplicate username validation
**Expected:** ❌ DENIED
- Attempting to change a user to an existing username is blocked.

---

## Test Scenario 4: Sales Log Edit Peer Approval

### Preconditions
- At least one user exists at Level 2, one at Level 3, and two users at Level 4.
- A Sales record exists in Financial Data > Records > Sales.

### Test 4.1: Level 2 submits Sales edit request
**Steps:**
1. Login as Level 2 user.
2. Open Point of Sales > Reports.
3. Confirm Quarterly/Yearly summary rows appear at the top.
4. Select a summary period and verify underlying sales rows load below.
3. Select a row and click `Edit Selected (Submit for Approval)`.
4. Change one or more sales fields, enter Edit Reason, submit.

**Expected:**
- Request is created in Approval as `Sales Edit` with status `PENDING`.
- Original Sales row is unchanged before approval.

### Test 4.1b: POS Reports summary matches Financial Data summary
**Steps:**
1. Compare the same Quarterly or Yearly period in Financial Data > Summary and Point of Sales > Reports.

**Expected:** ✅ MATCH
- Sales, Costs, and Net Cash values match because both views read from the same approved ledger data.

### Test 4.2: Level 3 approves Level 2 request
**Steps:**
1. Login as Level 3 user.
2. Open Approval and select pending `Sales Edit`.
3. Confirm diff details and approve.

**Expected:**
- Approval succeeds.
- Sales row is updated to requested values.

### Test 4.3: Level 3 cannot self-approve
**Steps:**
1. Login as Level 3 user and submit a Sales edit request.
2. Without changing user, attempt to approve same request.

**Expected:**
- Approval is blocked with self-approval error.

### Test 4.4: Level 3 cannot approve Level 3 request
**Steps:**
1. Login as a different Level 3 user.
2. Attempt to approve the Level 3-submitted request.

**Expected:**
- Approval is blocked.
- Message states only Level 4 can approve Level 3 submissions.

### Test 4.5: Level 4 approves Level 3 and Level 4 requests
**Steps:**
1. Login as Level 4 user A and submit Sales edit request.
2. Login as Level 4 user B and approve request.

**Expected:**
- Approval succeeds for different Level 4 approver.
- Same-user Level 4 self-approval is blocked.

**Expected:** ❌ DENIED
```
Access Denied

Level 3 (Admin) cannot remove Level 3 users.

You can only remove: Level 1, 2
```

### Test 3.4: Remove Level 1 Employee
**Expected:** ✅ SUCCESS

---

## Test Scenario 4: Manager (Level 2) Permissions

Create Level 2 user:
```bash
# As admin:
Add user: manager2 / emp123 / Level 2
```

### Login as Manager
- Username: `manager2`
- Password: `emp123`

### Dashboard Check
✅ Should show:
- Financial Access: **View & Edit**
- Permissions:
  - ✓ View & Edit financial data
  - ✓ Add users: Level 1
  - ✓ Remove users: Level 1

### Test 4.1: Add Level 1 Employee
**Expected:** ✅ SUCCESS - Dropdown only shows Level 1

### Test 4.2: Try to Remove Level 2 User
**Expected:** ❌ DENIED - Can only remove Level 1

---

## Test Scenario 5: Employee (Level 1) Permissions

Create Level 1 user:
```bash
# As admin:
Add user: employee / staff123 / Level 1
```

### Login as Employee
- Username: `employee`
- Password: `staff123`

### Dashboard Check
✅ Should show:
- Financial Access: **View & Edit**
- User Management: Not available (no buttons)

### Test 5.1: Access User Management
**Expected:** "Insufficient permissions for user management" message

### Test 5.2: Financial Data
**Expected:** ✅ Can view and edit financial records

---

## Quick Reset Command

Reset to default 2 users (admin ID:1, officer ID:2):
```bash
cd "d:\Vicinity Safety\Finance"
.\.venv\Scripts\python.exe security\reset_users.py
```

---

## Permission Matrix Summary

| Level | Financial Data | Add Users  | Remove Users | Notes |
|-------|----------------|------------|--------------|-------|
| 1     | View & Edit    | None       | None         | Basic access |
| 2     | View & Edit    | Level 1    | Level 1      | Can manage employees |
| 3     | View & Edit    | Level 1-3  | Level 1-2    | Cannot remove same level+ |
| 4     | View & Edit    | Level 1-4  | Level 1-4    | Cannot touch Level 5 |
| 5     | **View Only**  | All (1-5)  | All (1-5)    | Supreme authority, oversight |

---

## Security Rules Enforced

✅ **Immutability**: Level 5 cannot be modified by Level 4
✅ **Self-Protection**: Level 3 cannot remove other Level 3s
✅ **Hierarchy**: Lower levels cannot manage higher levels
✅ **System Protection**: Last Level 5 cannot be removed
✅ **Oversight**: Level 5 has read-only financial access for oversight
✅ **Separation of Duties**: Financial editing vs. oversight viewing

---

## Audit Trail

All operations are logged in the audit log:
- User additions/removals
- Permission checks
- Access attempts (granted/denied)

View in app: **Audit Logs** menu

---

## Launch Application

Double-click: `launch\launch_finance_ui.bat`

Or run:
```bash
cd "d:\Vicinity Safety\Finance"
.\.venv\Scripts\python.exe app\finance_ui.py
```
