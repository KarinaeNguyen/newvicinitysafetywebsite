"""
Security Governance Module
Implements Dual-Control enforcement for Level 5 users
"""

import sqlite3
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
SECURITY_DB = BASE_DIR / "security" / "security.db"
LOGS_DB = BASE_DIR / "security" / "logs.db"

class DualControlError(Exception):
    pass

class SecurityGovernance:
    
    @staticmethod
    def get_level5_count():
        """Get the number of Level 5 users in the system"""
        conn = sqlite3.connect(SECURITY_DB)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM Users WHERE security_level = 5")
        count = cursor.fetchone()[0]
        conn.close()
        return count
    
    @staticmethod
    def can_remove_level5():
        """Check if Level 5 removal is allowed (minimum 2 required)"""
        return SecurityGovernance.get_level5_count() >= 2
    
    @staticmethod
    def request_level5_removal(requested_by_id, user_id_to_remove, reason):
        """
        Level 4 (Owner) requests removal of a Level 5 user
        Returns: request_id or raises DualControlError
        """
        conn = sqlite3.connect(SECURITY_DB)
        cursor = conn.cursor()
        
        try:
            # Verify Level 5 user exists
            cursor.execute("SELECT security_level FROM Users WHERE user_id = ?", (user_id_to_remove,))
            user = cursor.fetchone()
            
            if not user:
                raise DualControlError("User does not exist")
            
            if user[0] != 5:
                raise DualControlError("This user is not Level 5")
            
            # Check minimum 2 Level 5 requirement
            if not SecurityGovernance.can_remove_level5():
                raise DualControlError("Cannot remove Level 5 user: only 1 Level 5 user exists (minimum 2 required)")
            
            # Create removal request
            cursor.execute(
                "INSERT INTO RemovalRequests (user_id_to_remove, requested_by_id, status, reason) VALUES (?, ?, 'PENDING', ?)",
                (user_id_to_remove, requested_by_id, reason)
            )
            conn.commit()
            request_id = cursor.lastrowid
            
            # Log action
            SecurityGovernance._log_action(
                requested_by_id, 
                "REQUEST_LEVEL5_REMOVAL", 
                f"Requested removal of Level 5 user ID {user_id_to_remove}. Request ID: {request_id}. Reason: {reason}"
            )
            
            conn.close()
            return request_id
            
        except Exception as e:
            conn.close()
            raise DualControlError(f"Failed to create removal request: {str(e)}")
    
    @staticmethod
    def get_pending_removal_requests():
        """Get all pending removal requests"""
        conn = sqlite3.connect(SECURITY_DB)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("""
            SELECT r.*, 
                   u_remove.username as user_to_remove_username,
                   u_remove.first_name, u_remove.last_name,
                   u_req.username as requested_by_username
            FROM RemovalRequests r
            JOIN Users u_remove ON r.user_id_to_remove = u_remove.user_id
            JOIN Users u_req ON r.requested_by_id = u_req.user_id
            WHERE r.status = 'PENDING'
            ORDER BY r.created_date DESC
        """)
        requests = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return requests
    
    @staticmethod
    def approve_level5_removal(request_id, approved_by_id):
        """
        Level 5 user approves removal of another Level 5 user
        Enforces: Cannot self-approve, must be another Level 5
        """
        conn = sqlite3.connect(SECURITY_DB)
        cursor = conn.cursor()
        
        try:
            # Verify approver is Level 5
            cursor.execute("SELECT security_level FROM Users WHERE user_id = ?", (approved_by_id,))
            approver = cursor.fetchone()
            
            if not approver or approver[0] != 5:
                raise DualControlError("Only Level 5 users can approve Level 5 removal")
            
            # Get removal request
            cursor.execute("SELECT * FROM RemovalRequests WHERE request_id = ? AND status = 'PENDING'", (request_id,))
            request = cursor.fetchone()
            
            if not request:
                raise DualControlError("Request not found or already processed")
            
            _, user_id_to_remove, requested_by_id, _, _, _, _, _, _ = request
            
            # Prevent self-approval
            if approved_by_id == user_id_to_remove:
                raise DualControlError("Cannot self-approve removal request")
            
            # Approve request
            cursor.execute(
                "UPDATE RemovalRequests SET status = 'APPROVED', approved_by_id = ?, approved_date = CURRENT_TIMESTAMP WHERE request_id = ?",
                (approved_by_id, request_id)
            )
            
            # Execute removal
            cursor.execute("DELETE FROM Users WHERE user_id = ?", (user_id_to_remove,))
            
            conn.commit()
            
            # Log action
            SecurityGovernance._log_action(
                approved_by_id,
                "APPROVE_LEVEL5_REMOVAL",
                f"Approved and executed removal of Level 5 user ID {user_id_to_remove}. Request ID: {request_id}"
            )
            
            conn.close()
            return True
            
        except Exception as e:
            conn.close()
            raise DualControlError(f"Failed to approve removal: {str(e)}")
    
    @staticmethod
    def reject_level5_removal(request_id, rejected_by_id):
        """Level 5 user rejects a removal request"""
        conn = sqlite3.connect(SECURITY_DB)
        cursor = conn.cursor()
        
        try:
            # Verify rejector is Level 5
            cursor.execute("SELECT security_level FROM Users WHERE user_id = ?", (rejected_by_id,))
            rejector = cursor.fetchone()
            
            if not rejector or rejector[0] != 5:
                raise DualControlError("Only Level 5 users can reject Level 5 removal requests")
            
            cursor.execute(
                "UPDATE RemovalRequests SET status = 'REJECTED', approved_by_id = ?, approved_date = CURRENT_TIMESTAMP WHERE request_id = ?",
                (rejected_by_id, request_id)
            )
            conn.commit()
            
            SecurityGovernance._log_action(
                rejected_by_id,
                "REJECT_LEVEL5_REMOVAL",
                f"Rejected removal request ID {request_id}"
            )
            
            conn.close()
            return True
            
        except Exception as e:
            conn.close()
            raise DualControlError(f"Failed to reject removal: {str(e)}")
    
    @staticmethod
    def get_all_users_with_levels():
        """Get all users with their security levels"""
        conn = sqlite3.connect(SECURITY_DB)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("""
            SELECT u.user_id, u.username, u.first_name, u.last_name, u.security_level, 
                   s.level_name, u.role, u.access_type
            FROM Users u
            JOIN SecurityLevels s ON u.security_level = s.level
            ORDER BY u.security_level DESC, u.username
        """)
        users = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return users
    
    @staticmethod
    def _log_action(user_id, action, details):
        """Log security governance action to audit log"""
        try:
            conn = sqlite3.connect(LOGS_DB)
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO AuditLog (user_id, action, affected_table, affected_record, security_level, details) VALUES (?, ?, 'Users', 'RemovalRequests', 5, ?)",
                (user_id, action, details)
            )
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"Logging error: {e}")

if __name__ == '__main__':
    # Test the module
    print(f"Level 5 users in system: {SecurityGovernance.get_level5_count()}")
    print(f"Can remove Level 5: {SecurityGovernance.can_remove_level5()}")
    print(f"All users: {SecurityGovernance.get_all_users_with_levels()}")
