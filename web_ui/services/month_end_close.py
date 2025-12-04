"""
Month-End Closing Service
Manages accounting periods, closing checklists, adjusting entries, and audit logging.
"""

from datetime import datetime, date
from typing import Optional, Dict, Any, List, Tuple
from database import db_manager
import json
import logging

logger = logging.getLogger(__name__)


class MonthEndCloseService:
    """Service for managing month-end closing workflow"""

    # Period statuses
    STATUS_OPEN = 'open'
    STATUS_IN_PROGRESS = 'in_progress'
    STATUS_PENDING_APPROVAL = 'pending_approval'
    STATUS_LOCKED = 'locked'
    STATUS_CLOSED = 'closed'

    # Checklist item statuses
    ITEM_PENDING = 'pending'
    ITEM_IN_PROGRESS = 'in_progress'
    ITEM_COMPLETED = 'completed'
    ITEM_SKIPPED = 'skipped'
    ITEM_BLOCKED = 'blocked'

    # Entry statuses
    ENTRY_DRAFT = 'draft'
    ENTRY_PENDING_APPROVAL = 'pending_approval'
    ENTRY_APPROVED = 'approved'
    ENTRY_POSTED = 'posted'
    ENTRY_REJECTED = 'rejected'

    # Lock types
    LOCK_TRANSACTIONS = 'transactions'
    LOCK_INVOICES = 'invoices'
    LOCK_PAYROLL = 'payroll'
    LOCK_ADJUSTMENTS = 'adjustments'
    LOCK_ALL = 'all'

    # ========================================
    # PERIOD MANAGEMENT
    # ========================================

    @staticmethod
    def list_periods(tenant_id: str, status: Optional[str] = None,
                     page: int = 1, per_page: int = 20) -> Tuple[List[Dict], int]:
        """List accounting periods for a tenant."""
        try:
            with db_manager.get_connection() as conn:
                cursor = conn.cursor()

                # Build query
                where_clauses = ["tenant_id = %s"]
                params = [tenant_id]

                if status:
                    where_clauses.append("status = %s")
                    params.append(status)

                where_sql = " AND ".join(where_clauses)

                # Count total
                cursor.execute(f"""
                    SELECT COUNT(*) FROM cfo_accounting_periods
                    WHERE {where_sql}
                """, params)
                total = cursor.fetchone()[0]

                # Get periods
                offset = (page - 1) * per_page
                cursor.execute(f"""
                    SELECT id, period_name, period_type, start_date, end_date,
                           status, locked_at, locked_by, approved_at, approved_by,
                           closed_at, closed_by, notes, created_at, updated_at
                    FROM cfo_accounting_periods
                    WHERE {where_sql}
                    ORDER BY start_date DESC
                    LIMIT %s OFFSET %s
                """, params + [per_page, offset])

                columns = [desc[0] for desc in cursor.description]
                periods = []
                for row in cursor.fetchall():
                    period = dict(zip(columns, row))
                    # Convert dates to strings
                    for key in ['start_date', 'end_date']:
                        if period.get(key):
                            period[key] = period[key].isoformat()
                    for key in ['locked_at', 'approved_at', 'closed_at', 'created_at', 'updated_at']:
                        if period.get(key):
                            period[key] = period[key].isoformat()
                    if period.get('id'):
                        period['id'] = str(period['id'])
                    periods.append(period)

                cursor.close()
                return periods, total

        except Exception as e:
            logger.error(f"Error listing periods: {e}")
            return [], 0

    @staticmethod
    def get_period(period_id: str, tenant_id: str) -> Optional[Dict]:
        """Get a specific accounting period."""
        try:
            with db_manager.get_connection() as conn:
                cursor = conn.cursor()

                cursor.execute("""
                    SELECT id, tenant_id, period_name, period_type, start_date, end_date,
                           status, locked_at, locked_by, submitted_at, submitted_by,
                           approved_at, approved_by, rejection_reason,
                           closed_at, closed_by, notes, created_at, updated_at
                    FROM cfo_accounting_periods
                    WHERE id = %s AND tenant_id = %s
                """, (period_id, tenant_id))

                row = cursor.fetchone()
                if not row:
                    cursor.close()
                    return None

                columns = [desc[0] for desc in cursor.description]
                period = dict(zip(columns, row))

                # Convert types
                if period.get('id'):
                    period['id'] = str(period['id'])
                for key in ['start_date', 'end_date']:
                    if period.get(key):
                        period[key] = period[key].isoformat()
                for key in ['locked_at', 'submitted_at', 'approved_at', 'closed_at', 'created_at', 'updated_at']:
                    if period.get(key):
                        period[key] = period[key].isoformat()

                cursor.close()
                return period

        except Exception as e:
            logger.error(f"Error getting period: {e}")
            return None

    @staticmethod
    def create_period(tenant_id: str, period_name: str, period_type: str,
                      start_date: str, end_date: str, notes: Optional[str] = None) -> Optional[Dict]:
        """Create a new accounting period."""
        try:
            with db_manager.get_connection() as conn:
                cursor = conn.cursor()

                # Check for overlapping periods
                cursor.execute("""
                    SELECT id FROM cfo_accounting_periods
                    WHERE tenant_id = %s
                    AND (
                        (start_date <= %s AND end_date >= %s)
                        OR (start_date <= %s AND end_date >= %s)
                        OR (start_date >= %s AND end_date <= %s)
                    )
                """, (tenant_id, start_date, start_date, end_date, end_date, start_date, end_date))

                if cursor.fetchone():
                    cursor.close()
                    raise ValueError("Period overlaps with an existing period")

                cursor.execute("""
                    INSERT INTO cfo_accounting_periods
                    (tenant_id, period_name, period_type, start_date, end_date, notes, status)
                    VALUES (%s, %s, %s, %s, %s, %s, 'open')
                    RETURNING id
                """, (tenant_id, period_name, period_type, start_date, end_date, notes))

                period_id = str(cursor.fetchone()[0])
                conn.commit()
                cursor.close()

                # Log activity
                MonthEndCloseService.log_activity(
                    period_id, tenant_id, 'period_created', 'period', period_id,
                    details={'period_name': period_name}
                )

                return MonthEndCloseService.get_period(period_id, tenant_id)

        except Exception as e:
            logger.error(f"Error creating period: {e}")
            raise

    @staticmethod
    def update_period(period_id: str, tenant_id: str, **kwargs) -> Optional[Dict]:
        """Update an accounting period."""
        allowed_fields = ['period_name', 'notes']
        updates = {k: v for k, v in kwargs.items() if k in allowed_fields and v is not None}

        if not updates:
            return MonthEndCloseService.get_period(period_id, tenant_id)

        try:
            with db_manager.get_connection() as conn:
                cursor = conn.cursor()

                # Check period status - can only update open periods
                cursor.execute("""
                    SELECT status FROM cfo_accounting_periods
                    WHERE id = %s AND tenant_id = %s
                """, (period_id, tenant_id))
                row = cursor.fetchone()
                if not row:
                    cursor.close()
                    return None
                if row[0] not in [MonthEndCloseService.STATUS_OPEN, MonthEndCloseService.STATUS_IN_PROGRESS]:
                    cursor.close()
                    raise ValueError(f"Cannot update period in {row[0]} status")

                set_clauses = [f"{k} = %s" for k in updates.keys()]
                params = list(updates.values()) + [period_id, tenant_id]

                cursor.execute(f"""
                    UPDATE cfo_accounting_periods
                    SET {', '.join(set_clauses)}, updated_at = CURRENT_TIMESTAMP
                    WHERE id = %s AND tenant_id = %s
                """, params)

                conn.commit()
                cursor.close()

                return MonthEndCloseService.get_period(period_id, tenant_id)

        except Exception as e:
            logger.error(f"Error updating period: {e}")
            raise

    @staticmethod
    def start_close_process(period_id: str, tenant_id: str, user_id: Optional[str] = None) -> Optional[Dict]:
        """Start the closing process for a period."""
        try:
            with db_manager.get_connection() as conn:
                cursor = conn.cursor()

                # Check current status
                cursor.execute("""
                    SELECT status FROM cfo_accounting_periods
                    WHERE id = %s AND tenant_id = %s
                """, (period_id, tenant_id))
                row = cursor.fetchone()
                if not row:
                    cursor.close()
                    return None
                if row[0] != MonthEndCloseService.STATUS_OPEN:
                    cursor.close()
                    raise ValueError(f"Can only start close process for open periods (current: {row[0]})")

                # Update status
                cursor.execute("""
                    UPDATE cfo_accounting_periods
                    SET status = 'in_progress', updated_at = CURRENT_TIMESTAMP
                    WHERE id = %s AND tenant_id = %s
                """, (period_id, tenant_id))

                conn.commit()
                cursor.close()

                # Create checklist items from templates
                MonthEndCloseService.create_checklist_from_templates(period_id, tenant_id)

                # Log activity
                MonthEndCloseService.log_activity(
                    period_id, tenant_id, 'period_started', 'period', period_id,
                    user_id=user_id
                )

                return MonthEndCloseService.get_period(period_id, tenant_id)

        except Exception as e:
            logger.error(f"Error starting close process: {e}")
            raise

    @staticmethod
    def lock_period(period_id: str, tenant_id: str, user_id: Optional[str] = None) -> Optional[Dict]:
        """Lock a period (prevent transaction modifications)."""
        try:
            with db_manager.get_connection() as conn:
                cursor = conn.cursor()

                # Check current status
                cursor.execute("""
                    SELECT status FROM cfo_accounting_periods
                    WHERE id = %s AND tenant_id = %s
                """, (period_id, tenant_id))
                row = cursor.fetchone()
                if not row:
                    cursor.close()
                    return None
                if row[0] not in [MonthEndCloseService.STATUS_IN_PROGRESS, MonthEndCloseService.STATUS_PENDING_APPROVAL]:
                    cursor.close()
                    raise ValueError(f"Cannot lock period in {row[0]} status")

                # Update status
                cursor.execute("""
                    UPDATE cfo_accounting_periods
                    SET status = 'locked', locked_at = CURRENT_TIMESTAMP, locked_by = %s,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = %s AND tenant_id = %s
                """, (user_id, period_id, tenant_id))

                # Create/update all locks
                for lock_type in [MonthEndCloseService.LOCK_TRANSACTIONS, MonthEndCloseService.LOCK_INVOICES,
                                  MonthEndCloseService.LOCK_PAYROLL, MonthEndCloseService.LOCK_ADJUSTMENTS]:
                    cursor.execute("""
                        INSERT INTO period_locks (period_id, lock_type, is_locked, locked_at, locked_by)
                        VALUES (%s, %s, true, CURRENT_TIMESTAMP, %s)
                        ON CONFLICT (period_id, lock_type)
                        DO UPDATE SET is_locked = true, locked_at = CURRENT_TIMESTAMP, locked_by = %s
                    """, (period_id, lock_type, user_id, user_id))

                conn.commit()
                cursor.close()

                # Log activity
                MonthEndCloseService.log_activity(
                    period_id, tenant_id, 'period_locked', 'period', period_id,
                    user_id=user_id
                )

                return MonthEndCloseService.get_period(period_id, tenant_id)

        except Exception as e:
            logger.error(f"Error locking period: {e}")
            raise

    @staticmethod
    def unlock_period(period_id: str, tenant_id: str, reason: str,
                      user_id: Optional[str] = None) -> Optional[Dict]:
        """Unlock a period (emergency unlock)."""
        try:
            with db_manager.get_connection() as conn:
                cursor = conn.cursor()

                # Check current status
                cursor.execute("""
                    SELECT status FROM cfo_accounting_periods
                    WHERE id = %s AND tenant_id = %s
                """, (period_id, tenant_id))
                row = cursor.fetchone()
                if not row:
                    cursor.close()
                    return None
                if row[0] != MonthEndCloseService.STATUS_LOCKED:
                    cursor.close()
                    raise ValueError(f"Can only unlock locked periods (current: {row[0]})")

                # Update status back to in_progress
                cursor.execute("""
                    UPDATE cfo_accounting_periods
                    SET status = 'in_progress', updated_at = CURRENT_TIMESTAMP
                    WHERE id = %s AND tenant_id = %s
                """, (period_id, tenant_id))

                # Update all locks
                cursor.execute("""
                    UPDATE period_locks
                    SET is_locked = false, unlocked_at = CURRENT_TIMESTAMP,
                        unlocked_by = %s, unlock_reason = %s
                    WHERE period_id = %s
                """, (user_id, reason, period_id))

                conn.commit()
                cursor.close()

                # Log activity
                MonthEndCloseService.log_activity(
                    period_id, tenant_id, 'period_unlocked', 'period', period_id,
                    user_id=user_id, details={'reason': reason}
                )

                return MonthEndCloseService.get_period(period_id, tenant_id)

        except Exception as e:
            logger.error(f"Error unlocking period: {e}")
            raise

    @staticmethod
    def submit_for_approval(period_id: str, tenant_id: str, user_id: Optional[str] = None) -> Optional[Dict]:
        """Submit period for CFO/Controller approval."""
        try:
            with db_manager.get_connection() as conn:
                cursor = conn.cursor()

                # Check status and required checklist items
                cursor.execute("""
                    SELECT status FROM cfo_accounting_periods
                    WHERE id = %s AND tenant_id = %s
                """, (period_id, tenant_id))
                row = cursor.fetchone()
                if not row:
                    cursor.close()
                    return None
                if row[0] != MonthEndCloseService.STATUS_IN_PROGRESS:
                    cursor.close()
                    raise ValueError(f"Can only submit in_progress periods (current: {row[0]})")

                # Check required items are complete
                cursor.execute("""
                    SELECT COUNT(*) FROM close_checklist_items
                    WHERE period_id = %s AND is_required = true AND status NOT IN ('completed', 'skipped')
                """, (period_id,))
                incomplete = cursor.fetchone()[0]
                if incomplete > 0:
                    cursor.close()
                    raise ValueError(f"{incomplete} required checklist items are not complete")

                # Update status
                cursor.execute("""
                    UPDATE cfo_accounting_periods
                    SET status = 'pending_approval', submitted_at = CURRENT_TIMESTAMP,
                        submitted_by = %s, updated_at = CURRENT_TIMESTAMP
                    WHERE id = %s AND tenant_id = %s
                """, (user_id, period_id, tenant_id))

                conn.commit()
                cursor.close()

                # Log activity
                MonthEndCloseService.log_activity(
                    period_id, tenant_id, 'period_submitted', 'period', period_id,
                    user_id=user_id
                )

                return MonthEndCloseService.get_period(period_id, tenant_id)

        except Exception as e:
            logger.error(f"Error submitting period: {e}")
            raise

    @staticmethod
    def approve_period(period_id: str, tenant_id: str, user_id: Optional[str] = None) -> Optional[Dict]:
        """Approve period close."""
        try:
            with db_manager.get_connection() as conn:
                cursor = conn.cursor()

                cursor.execute("""
                    SELECT status FROM cfo_accounting_periods
                    WHERE id = %s AND tenant_id = %s
                """, (period_id, tenant_id))
                row = cursor.fetchone()
                if not row:
                    cursor.close()
                    return None
                if row[0] != MonthEndCloseService.STATUS_PENDING_APPROVAL:
                    cursor.close()
                    raise ValueError(f"Can only approve pending_approval periods (current: {row[0]})")

                cursor.execute("""
                    UPDATE cfo_accounting_periods
                    SET approved_at = CURRENT_TIMESTAMP, approved_by = %s,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = %s AND tenant_id = %s
                """, (user_id, period_id, tenant_id))

                conn.commit()
                cursor.close()

                # Log activity
                MonthEndCloseService.log_activity(
                    period_id, tenant_id, 'period_approved', 'period', period_id,
                    user_id=user_id
                )

                return MonthEndCloseService.get_period(period_id, tenant_id)

        except Exception as e:
            logger.error(f"Error approving period: {e}")
            raise

    @staticmethod
    def reject_period(period_id: str, tenant_id: str, reason: str,
                      user_id: Optional[str] = None) -> Optional[Dict]:
        """Reject period close and send back for corrections."""
        try:
            with db_manager.get_connection() as conn:
                cursor = conn.cursor()

                cursor.execute("""
                    SELECT status FROM cfo_accounting_periods
                    WHERE id = %s AND tenant_id = %s
                """, (period_id, tenant_id))
                row = cursor.fetchone()
                if not row:
                    cursor.close()
                    return None
                if row[0] != MonthEndCloseService.STATUS_PENDING_APPROVAL:
                    cursor.close()
                    raise ValueError(f"Can only reject pending_approval periods (current: {row[0]})")

                cursor.execute("""
                    UPDATE cfo_accounting_periods
                    SET status = 'in_progress', rejection_reason = %s,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = %s AND tenant_id = %s
                """, (reason, period_id, tenant_id))

                conn.commit()
                cursor.close()

                # Log activity
                MonthEndCloseService.log_activity(
                    period_id, tenant_id, 'period_rejected', 'period', period_id,
                    user_id=user_id, details={'reason': reason}
                )

                return MonthEndCloseService.get_period(period_id, tenant_id)

        except Exception as e:
            logger.error(f"Error rejecting period: {e}")
            raise

    @staticmethod
    def close_period(period_id: str, tenant_id: str, user_id: Optional[str] = None) -> Optional[Dict]:
        """Finalize and close the period."""
        try:
            with db_manager.get_connection() as conn:
                cursor = conn.cursor()

                cursor.execute("""
                    SELECT status, approved_at FROM cfo_accounting_periods
                    WHERE id = %s AND tenant_id = %s
                """, (period_id, tenant_id))
                row = cursor.fetchone()
                if not row:
                    cursor.close()
                    return None
                status, approved_at = row
                if status not in [MonthEndCloseService.STATUS_PENDING_APPROVAL, MonthEndCloseService.STATUS_LOCKED]:
                    cursor.close()
                    raise ValueError(f"Cannot close period in {status} status")
                if not approved_at:
                    cursor.close()
                    raise ValueError("Period must be approved before closing")

                cursor.execute("""
                    UPDATE cfo_accounting_periods
                    SET status = 'closed', closed_at = CURRENT_TIMESTAMP, closed_by = %s,
                        locked_at = COALESCE(locked_at, CURRENT_TIMESTAMP),
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = %s AND tenant_id = %s
                """, (user_id, period_id, tenant_id))

                # Ensure all locks are in place
                for lock_type in [MonthEndCloseService.LOCK_TRANSACTIONS, MonthEndCloseService.LOCK_INVOICES,
                                  MonthEndCloseService.LOCK_PAYROLL, MonthEndCloseService.LOCK_ADJUSTMENTS]:
                    cursor.execute("""
                        INSERT INTO period_locks (period_id, lock_type, is_locked, locked_at, locked_by)
                        VALUES (%s, %s, true, CURRENT_TIMESTAMP, %s)
                        ON CONFLICT (period_id, lock_type)
                        DO UPDATE SET is_locked = true, locked_at = CURRENT_TIMESTAMP
                    """, (period_id, lock_type, user_id))

                conn.commit()
                cursor.close()

                # Log activity
                MonthEndCloseService.log_activity(
                    period_id, tenant_id, 'period_closed', 'period', period_id,
                    user_id=user_id
                )

                return MonthEndCloseService.get_period(period_id, tenant_id)

        except Exception as e:
            logger.error(f"Error closing period: {e}")
            raise

    # ========================================
    # PERIOD VALIDATION
    # ========================================

    @staticmethod
    def is_period_locked(tenant_id: str, transaction_date: str) -> Tuple[bool, Optional[str]]:
        """Check if a date falls within a locked/closed period."""
        try:
            with db_manager.get_connection() as conn:
                cursor = conn.cursor()

                cursor.execute("""
                    SELECT id, period_name, status FROM cfo_accounting_periods
                    WHERE tenant_id = %s
                    AND %s BETWEEN start_date AND end_date
                    AND status IN ('locked', 'closed')
                """, (tenant_id, transaction_date))

                row = cursor.fetchone()
                cursor.close()

                if row:
                    return True, f"Period {row[1]} is {row[2]}"
                return False, None

        except Exception as e:
            logger.error(f"Error checking period lock: {e}")
            return False, None

    # ========================================
    # CHECKLIST MANAGEMENT
    # ========================================

    @staticmethod
    def create_checklist_from_templates(period_id: str, tenant_id: str) -> int:
        """Create checklist items from templates for a period."""
        try:
            with db_manager.get_connection() as conn:
                cursor = conn.cursor()

                # Get templates (tenant-specific or default)
                cursor.execute("""
                    SELECT id, name, description, category, sequence_order, is_required,
                           auto_check_type, assigned_role
                    FROM close_checklist_templates
                    WHERE (tenant_id = %s OR tenant_id = 'default')
                    AND is_active = true
                    ORDER BY sequence_order
                """, (tenant_id,))

                templates = cursor.fetchall()
                count = 0

                for template in templates:
                    template_id, name, description, category, sequence_order, is_required, auto_check_type, assigned_role = template

                    # Check if item already exists
                    cursor.execute("""
                        SELECT id FROM close_checklist_items
                        WHERE period_id = %s AND template_id = %s
                    """, (period_id, template_id))

                    if not cursor.fetchone():
                        cursor.execute("""
                            INSERT INTO close_checklist_items
                            (period_id, template_id, name, description, category, sequence_order,
                             is_required, auto_check_type, status)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'pending')
                        """, (period_id, template_id, name, description, category, sequence_order,
                              is_required, auto_check_type))
                        count += 1

                conn.commit()
                cursor.close()
                return count

        except Exception as e:
            logger.error(f"Error creating checklist: {e}")
            return 0

    @staticmethod
    def get_checklist(period_id: str, tenant_id: str) -> List[Dict]:
        """Get all checklist items for a period."""
        try:
            with db_manager.get_connection() as conn:
                cursor = conn.cursor()

                # Verify period belongs to tenant
                cursor.execute("""
                    SELECT id FROM cfo_accounting_periods
                    WHERE id = %s AND tenant_id = %s
                """, (period_id, tenant_id))
                if not cursor.fetchone():
                    cursor.close()
                    return []

                cursor.execute("""
                    SELECT id, period_id, template_id, name, description, category,
                           sequence_order, is_required, status, auto_check_type,
                           auto_check_result, last_auto_check_at, started_at,
                           completed_at, completed_by, reviewed_by, reviewed_at,
                           notes, blockers, skip_reason, created_at, updated_at
                    FROM close_checklist_items
                    WHERE period_id = %s
                    ORDER BY sequence_order
                """, (period_id,))

                columns = [desc[0] for desc in cursor.description]
                items = []
                for row in cursor.fetchall():
                    item = dict(zip(columns, row))
                    # Convert UUIDs to strings
                    for key in ['id', 'period_id', 'template_id', 'completed_by', 'reviewed_by']:
                        if item.get(key):
                            item[key] = str(item[key])
                    # Convert timestamps
                    for key in ['last_auto_check_at', 'started_at', 'completed_at', 'reviewed_at', 'created_at', 'updated_at']:
                        if item.get(key):
                            item[key] = item[key].isoformat()
                    items.append(item)

                cursor.close()
                return items

        except Exception as e:
            logger.error(f"Error getting checklist: {e}")
            return []

    @staticmethod
    def update_checklist_item(item_id: str, tenant_id: str, **kwargs) -> Optional[Dict]:
        """Update a checklist item."""
        allowed_fields = ['status', 'notes', 'blockers', 'skip_reason']
        updates = {k: v for k, v in kwargs.items() if k in allowed_fields}

        if not updates:
            return None

        try:
            with db_manager.get_connection() as conn:
                cursor = conn.cursor()

                # Verify item belongs to tenant's period
                cursor.execute("""
                    SELECT ci.id, ci.status, p.tenant_id, p.status as period_status
                    FROM close_checklist_items ci
                    JOIN cfo_accounting_periods p ON ci.period_id = p.id
                    WHERE ci.id = %s AND p.tenant_id = %s
                """, (item_id, tenant_id))
                row = cursor.fetchone()
                if not row:
                    cursor.close()
                    return None

                period_status = row[3]
                if period_status in [MonthEndCloseService.STATUS_LOCKED, MonthEndCloseService.STATUS_CLOSED]:
                    cursor.close()
                    raise ValueError("Cannot modify checklist in locked/closed period")

                # Handle status changes
                new_status = updates.get('status')
                if new_status == MonthEndCloseService.ITEM_IN_PROGRESS:
                    updates['started_at'] = datetime.now()
                elif new_status == MonthEndCloseService.ITEM_COMPLETED:
                    updates['completed_at'] = datetime.now()
                    if 'user_id' in kwargs:
                        updates['completed_by'] = kwargs['user_id']

                set_clauses = [f"{k} = %s" for k in updates.keys()]
                params = list(updates.values()) + [item_id]

                cursor.execute(f"""
                    UPDATE close_checklist_items
                    SET {', '.join(set_clauses)}, updated_at = CURRENT_TIMESTAMP
                    WHERE id = %s
                    RETURNING period_id
                """, params)

                period_id = str(cursor.fetchone()[0])
                conn.commit()
                cursor.close()

                # Get updated item
                items = MonthEndCloseService.get_checklist(period_id, tenant_id)
                return next((i for i in items if i['id'] == item_id), None)

        except Exception as e:
            logger.error(f"Error updating checklist item: {e}")
            raise

    @staticmethod
    def complete_checklist_item(item_id: str, tenant_id: str, user_id: Optional[str] = None,
                                notes: Optional[str] = None) -> Optional[Dict]:
        """Mark a checklist item as completed."""
        return MonthEndCloseService.update_checklist_item(
            item_id, tenant_id,
            status=MonthEndCloseService.ITEM_COMPLETED,
            notes=notes,
            user_id=user_id
        )

    @staticmethod
    def skip_checklist_item(item_id: str, tenant_id: str, reason: str,
                            user_id: Optional[str] = None) -> Optional[Dict]:
        """Skip a checklist item with reason."""
        return MonthEndCloseService.update_checklist_item(
            item_id, tenant_id,
            status=MonthEndCloseService.ITEM_SKIPPED,
            skip_reason=reason,
            user_id=user_id
        )

    @staticmethod
    def get_checklist_progress(period_id: str, tenant_id: str) -> Dict:
        """Get checklist completion progress."""
        try:
            with db_manager.get_connection() as conn:
                cursor = conn.cursor()

                cursor.execute("""
                    SELECT
                        COUNT(*) as total,
                        COUNT(*) FILTER (WHERE status = 'completed') as completed,
                        COUNT(*) FILTER (WHERE status = 'skipped') as skipped,
                        COUNT(*) FILTER (WHERE status = 'in_progress') as in_progress,
                        COUNT(*) FILTER (WHERE status = 'blocked') as blocked,
                        COUNT(*) FILTER (WHERE status = 'pending') as pending,
                        COUNT(*) FILTER (WHERE is_required = true) as required_total,
                        COUNT(*) FILTER (WHERE is_required = true AND status IN ('completed', 'skipped')) as required_done
                    FROM close_checklist_items ci
                    JOIN cfo_accounting_periods p ON ci.period_id = p.id
                    WHERE ci.period_id = %s AND p.tenant_id = %s
                """, (period_id, tenant_id))

                row = cursor.fetchone()
                cursor.close()

                if not row:
                    return {'total': 0, 'completed': 0, 'percentage': 0}

                total, completed, skipped, in_progress, blocked, pending, required_total, required_done = row

                return {
                    'total': total,
                    'completed': completed,
                    'skipped': skipped,
                    'in_progress': in_progress,
                    'blocked': blocked,
                    'pending': pending,
                    'required_total': required_total,
                    'required_done': required_done,
                    'percentage': round((completed + skipped) / total * 100, 1) if total > 0 else 0,
                    'required_percentage': round(required_done / required_total * 100, 1) if required_total > 0 else 0
                }

        except Exception as e:
            logger.error(f"Error getting checklist progress: {e}")
            return {'total': 0, 'completed': 0, 'percentage': 0}

    # ========================================
    # ACTIVITY LOGGING
    # ========================================

    @staticmethod
    def log_activity(period_id: str, tenant_id: str, action: str,
                     entity_type: Optional[str] = None, entity_id: Optional[str] = None,
                     user_id: Optional[str] = None, user_name: Optional[str] = None,
                     user_role: Optional[str] = None, details: Optional[Dict] = None,
                     old_value: Optional[Dict] = None, new_value: Optional[Dict] = None,
                     ip_address: Optional[str] = None, user_agent: Optional[str] = None) -> bool:
        """Log an activity for the close process."""
        try:
            with db_manager.get_connection() as conn:
                cursor = conn.cursor()

                cursor.execute("""
                    INSERT INTO close_activity_log
                    (period_id, tenant_id, action, entity_type, entity_id, user_id,
                     user_name, user_role, details, old_value, new_value, ip_address, user_agent)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    period_id, tenant_id, action, entity_type, entity_id, user_id,
                    user_name, user_role,
                    json.dumps(details) if details else None,
                    json.dumps(old_value) if old_value else None,
                    json.dumps(new_value) if new_value else None,
                    ip_address, user_agent
                ))

                conn.commit()
                cursor.close()
                return True

        except Exception as e:
            logger.error(f"Error logging activity: {e}")
            return False

    @staticmethod
    def get_activity_log(period_id: str, tenant_id: str, page: int = 1,
                         per_page: int = 50) -> Tuple[List[Dict], int]:
        """Get activity log for a period."""
        try:
            with db_manager.get_connection() as conn:
                cursor = conn.cursor()

                # Verify period belongs to tenant
                cursor.execute("""
                    SELECT id FROM cfo_accounting_periods
                    WHERE id = %s AND tenant_id = %s
                """, (period_id, tenant_id))
                if not cursor.fetchone():
                    cursor.close()
                    return [], 0

                # Count total
                cursor.execute("""
                    SELECT COUNT(*) FROM close_activity_log WHERE period_id = %s
                """, (period_id,))
                total = cursor.fetchone()[0]

                # Get activities
                offset = (page - 1) * per_page
                cursor.execute("""
                    SELECT id, period_id, tenant_id, action, entity_type, entity_id,
                           user_id, user_name, user_role, details, old_value, new_value,
                           ip_address, created_at
                    FROM close_activity_log
                    WHERE period_id = %s
                    ORDER BY created_at DESC
                    LIMIT %s OFFSET %s
                """, (period_id, per_page, offset))

                columns = [desc[0] for desc in cursor.description]
                activities = []
                for row in cursor.fetchall():
                    activity = dict(zip(columns, row))
                    for key in ['id', 'period_id', 'entity_id', 'user_id']:
                        if activity.get(key):
                            activity[key] = str(activity[key])
                    if activity.get('created_at'):
                        activity['created_at'] = activity['created_at'].isoformat()
                    activities.append(activity)

                cursor.close()
                return activities, total

        except Exception as e:
            logger.error(f"Error getting activity log: {e}")
            return [], 0
