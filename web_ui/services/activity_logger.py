"""
Activity Logger Service
Tracks all changes and activities on transactions, invoices, and payslips
"""

from datetime import datetime
from typing import Optional, Dict, Any, List
from database import db_manager


class ActivityLogger:
    """Service for logging and retrieving activity records"""

    # Supported record types
    RECORD_TYPE_TRANSACTION = 'transaction'
    RECORD_TYPE_INVOICE = 'invoice'
    RECORD_TYPE_PAYSLIP = 'payslip'

    # Action types
    ACTION_CREATED = 'created'
    ACTION_UPDATED = 'updated'
    ACTION_VIEWED = 'viewed'
    ACTION_MATCHED = 'matched'
    ACTION_UNMATCHED = 'unmatched'
    ACTION_STATUS_CHANGED = 'status_changed'
    ACTION_DELETED = 'deleted'
    ACTION_APPROVED = 'approved'
    ACTION_REJECTED = 'rejected'
    ACTION_SENT = 'sent'
    ACTION_PAID = 'paid'

    @staticmethod
    def log_activity(
        tenant_id: str,
        record_type: str,
        record_id: str,
        action: str,
        field_changed: Optional[str] = None,
        old_value: Optional[str] = None,
        new_value: Optional[str] = None,
        user_id: Optional[str] = None,
        user_email: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> bool:
        """
        Log an activity record

        Args:
            tenant_id: Tenant identifier
            record_type: Type of record (transaction, invoice, payslip)
            record_id: ID of the record
            action: Action performed (created, updated, viewed, etc.)
            field_changed: Specific field that was modified
            old_value: Previous value of the field
            new_value: New value of the field
            user_id: User who performed the action
            user_email: Email of the user
            ip_address: IP address of the request
            user_agent: User agent string

        Returns:
            bool: True if logged successfully, False otherwise
        """
        try:
            with db_manager.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        INSERT INTO record_activity_log (
                            tenant_id, record_type, record_id, action,
                            field_changed, old_value, new_value,
                            user_id, user_email, ip_address, user_agent
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """, (
                        tenant_id, record_type, record_id, action,
                        field_changed, old_value, new_value,
                        user_id, user_email, ip_address, user_agent
                    ))
                    conn.commit()
                    return True
        except Exception as e:
            print(f"Error logging activity: {e}")
            return False

    @staticmethod
    def log_field_change(
        tenant_id: str,
        record_type: str,
        record_id: str,
        field_name: str,
        old_value: Any,
        new_value: Any,
        user_id: Optional[str] = None,
        user_email: Optional[str] = None
    ) -> bool:
        """
        Log a specific field change

        Args:
            tenant_id: Tenant identifier
            record_type: Type of record
            record_id: ID of the record
            field_name: Name of the field that changed
            old_value: Previous value
            new_value: New value
            user_id: User who made the change
            user_email: Email of the user

        Returns:
            bool: True if logged successfully
        """
        # Convert values to strings for storage
        old_str = str(old_value) if old_value is not None else None
        new_str = str(new_value) if new_value is not None else None

        return ActivityLogger.log_activity(
            tenant_id=tenant_id,
            record_type=record_type,
            record_id=record_id,
            action=ActivityLogger.ACTION_UPDATED,
            field_changed=field_name,
            old_value=old_str,
            new_value=new_str,
            user_id=user_id,
            user_email=user_email
        )

    @staticmethod
    def log_bulk_update(
        tenant_id: str,
        record_type: str,
        record_id: str,
        changes: Dict[str, tuple],
        user_id: Optional[str] = None,
        user_email: Optional[str] = None
    ) -> bool:
        """
        Log multiple field changes in a single update

        Args:
            tenant_id: Tenant identifier
            record_type: Type of record
            record_id: ID of the record
            changes: Dictionary of {field_name: (old_value, new_value)}
            user_id: User who made the changes
            user_email: Email of the user

        Returns:
            bool: True if all changes logged successfully
        """
        success = True
        for field_name, (old_value, new_value) in changes.items():
            if old_value != new_value:  # Only log actual changes
                result = ActivityLogger.log_field_change(
                    tenant_id, record_type, record_id,
                    field_name, old_value, new_value,
                    user_id, user_email
                )
                success = success and result
        return success

    @staticmethod
    def track_view(
        tenant_id: str,
        record_type: str,
        record_id: str,
        user_id: Optional[str] = None,
        user_email: Optional[str] = None
    ) -> bool:
        """
        Track when a record is viewed and update view tracking columns

        Args:
            tenant_id: Tenant identifier
            record_type: Type of record
            record_id: ID of the record
            user_id: User who viewed the record
            user_email: Email of the user

        Returns:
            bool: True if tracked successfully
        """
        try:
            # Log the view activity
            ActivityLogger.log_activity(
                tenant_id=tenant_id,
                record_type=record_type,
                record_id=record_id,
                action=ActivityLogger.ACTION_VIEWED,
                user_id=user_id,
                user_email=user_email
            )

            # Update view tracking columns in the record table
            table_name = f"{record_type}s" if record_type != 'transaction' else 'transactions'

            with db_manager.get_connection() as conn:
                with conn.cursor() as cursor:
                    if record_type == 'transaction':
                        cursor.execute(f"""
                            UPDATE {table_name}
                            SET last_viewed_at = CURRENT_TIMESTAMP,
                                last_viewed_by = %s,
                                view_count = COALESCE(view_count, 0) + 1
                            WHERE id = %s AND tenant_id = %s
                        """, (user_id, record_id, tenant_id))
                    else:
                        cursor.execute(f"""
                            UPDATE {table_name}
                            SET last_viewed_at = CURRENT_TIMESTAMP,
                                last_viewed_by = %s,
                                view_count = COALESCE(view_count, 0) + 1
                            WHERE id = %s AND tenant_id = %s
                        """, (user_id, record_id, tenant_id))
                    conn.commit()
                    return True
        except Exception as e:
            print(f"Error tracking view: {e}")
            return False

    @staticmethod
    def get_activity_history(
        record_type: str,
        record_id: str,
        tenant_id: str,
        limit: int = 50,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Get activity history for a specific record

        Args:
            record_type: Type of record
            record_id: ID of the record
            tenant_id: Tenant identifier
            limit: Maximum number of records to return
            offset: Number of records to skip

        Returns:
            List of activity records
        """
        try:
            with db_manager.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        SELECT
                            id, action, field_changed, old_value, new_value,
                            user_id, user_email, created_at
                        FROM record_activity_log
                        WHERE record_type = %s
                        AND record_id = %s
                        AND tenant_id = %s
                        ORDER BY created_at DESC
                        LIMIT %s OFFSET %s
                    """, (record_type, record_id, tenant_id, limit, offset))

                    columns = [desc[0] for desc in cursor.description]
                    results = []

                    for row in cursor.fetchall():
                        activity = dict(zip(columns, row))
                        # Format datetime for JSON serialization
                        if activity.get('created_at'):
                            activity['created_at'] = activity['created_at'].isoformat()
                        results.append(activity)

                    return results
        except Exception as e:
            print(f"Error getting activity history: {e}")
            return []

    @staticmethod
    def get_recent_activities(
        tenant_id: str,
        record_type: Optional[str] = None,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Get recent activities across all records or for a specific record type

        Args:
            tenant_id: Tenant identifier
            record_type: Optional filter by record type
            limit: Maximum number of records to return

        Returns:
            List of recent activity records
        """
        try:
            with db_manager.get_connection() as conn:
                with conn.cursor() as cursor:
                    if record_type:
                        cursor.execute("""
                            SELECT
                                id, record_type, record_id, action,
                                field_changed, user_id, user_email, created_at
                            FROM record_activity_log
                            WHERE tenant_id = %s AND record_type = %s
                            ORDER BY created_at DESC
                            LIMIT %s
                        """, (tenant_id, record_type, limit))
                    else:
                        cursor.execute("""
                            SELECT
                                id, record_type, record_id, action,
                                field_changed, user_id, user_email, created_at
                            FROM record_activity_log
                            WHERE tenant_id = %s
                            ORDER BY created_at DESC
                            LIMIT %s
                        """, (tenant_id, limit))

                    columns = [desc[0] for desc in cursor.description]
                    results = []

                    for row in cursor.fetchall():
                        activity = dict(zip(columns, row))
                        if activity.get('created_at'):
                            activity['created_at'] = activity['created_at'].isoformat()
                        results.append(activity)

                    return results
        except Exception as e:
            print(f"Error getting recent activities: {e}")
            return []

    @staticmethod
    def get_activity_count(
        record_type: str,
        record_id: str,
        tenant_id: str
    ) -> int:
        """
        Get total count of activities for a record

        Args:
            record_type: Type of record
            record_id: ID of the record
            tenant_id: Tenant identifier

        Returns:
            Total count of activities
        """
        try:
            with db_manager.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        SELECT COUNT(*)
                        FROM record_activity_log
                        WHERE record_type = %s
                        AND record_id = %s
                        AND tenant_id = %s
                    """, (record_type, record_id, tenant_id))

                    result = cursor.fetchone()
                    return result[0] if result else 0
        except Exception as e:
            print(f"Error getting activity count: {e}")
            return 0
