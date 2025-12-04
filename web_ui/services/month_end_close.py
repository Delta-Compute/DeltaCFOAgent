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

    # ========================================
    # RECONCILIATION STATUS (PHASE 2)
    # ========================================

    @staticmethod
    def get_reconciliation_status(period_id: str, tenant_id: str) -> Dict:
        """
        Get comprehensive reconciliation status for a period.
        Includes invoice matching, payslip matching, and transaction classification stats.
        """
        period = MonthEndCloseService.get_period(period_id, tenant_id)
        if not period:
            return {'error': 'Period not found'}

        start_date = period['start_date']
        end_date = period['end_date']

        # Get all reconciliation metrics
        invoice_stats = MonthEndCloseService.get_invoice_matching_stats(tenant_id, start_date, end_date)
        payslip_stats = MonthEndCloseService.get_payslip_matching_stats(tenant_id, start_date, end_date)
        transaction_stats = MonthEndCloseService.get_transaction_classification_stats(tenant_id, start_date, end_date)

        return {
            'period_id': period_id,
            'period_name': period['period_name'],
            'start_date': start_date,
            'end_date': end_date,
            'invoices': invoice_stats,
            'payslips': payslip_stats,
            'transactions': transaction_stats,
            'overall_health': MonthEndCloseService._calculate_overall_health(invoice_stats, payslip_stats, transaction_stats)
        }

    @staticmethod
    def _calculate_overall_health(invoice_stats: Dict, payslip_stats: Dict, transaction_stats: Dict) -> Dict:
        """Calculate overall reconciliation health score."""
        scores = []

        # Invoice matching score
        if invoice_stats.get('total', 0) > 0:
            scores.append(invoice_stats.get('match_rate', 0))

        # Payslip matching score
        if payslip_stats.get('total', 0) > 0:
            scores.append(payslip_stats.get('match_rate', 0))

        # Transaction classification score
        if transaction_stats.get('total', 0) > 0:
            scores.append(transaction_stats.get('classified_rate', 0))
            # High confidence rate bonus
            scores.append(transaction_stats.get('high_confidence_rate', 0))

        if not scores:
            return {'score': 100.0, 'status': 'good', 'message': 'No items to reconcile'}

        avg_score = sum(scores) / len(scores)

        if avg_score >= 95:
            status = 'excellent'
            message = 'All reconciliation tasks are complete'
        elif avg_score >= 85:
            status = 'good'
            message = 'Most reconciliation tasks are complete'
        elif avg_score >= 70:
            status = 'warning'
            message = 'Some reconciliation tasks need attention'
        else:
            status = 'critical'
            message = 'Significant reconciliation work required'

        return {
            'score': round(avg_score, 1),
            'status': status,
            'message': message
        }

    @staticmethod
    def get_invoice_matching_stats(tenant_id: str, start_date: str, end_date: str) -> Dict:
        """Get invoice-to-payment matching statistics for a date range."""
        try:
            with db_manager.get_connection() as conn:
                cursor = conn.cursor()

                # Count invoices in period and their match status
                cursor.execute("""
                    SELECT
                        COUNT(*) as total,
                        COUNT(*) FILTER (WHERE linked_transaction_id IS NOT NULL AND linked_transaction_id != '') as matched,
                        COUNT(*) FILTER (WHERE linked_transaction_id IS NULL OR linked_transaction_id = '') as unmatched,
                        COALESCE(SUM(total_amount), 0) as total_amount,
                        COALESCE(SUM(CASE WHEN linked_transaction_id IS NOT NULL AND linked_transaction_id != '' THEN total_amount ELSE 0 END), 0) as matched_amount,
                        COALESCE(SUM(CASE WHEN linked_transaction_id IS NULL OR linked_transaction_id = '' THEN total_amount ELSE 0 END), 0) as unmatched_amount
                    FROM invoices
                    WHERE tenant_id = %s
                    AND date >= %s AND date <= %s
                """, (tenant_id, start_date, end_date))

                row = cursor.fetchone()
                cursor.close()

                if not row:
                    return {'total': 0, 'matched': 0, 'unmatched': 0, 'match_rate': 0}

                total, matched, unmatched, total_amount, matched_amount, unmatched_amount = row

                return {
                    'total': total or 0,
                    'matched': matched or 0,
                    'unmatched': unmatched or 0,
                    'match_rate': round((matched / total) * 100, 1) if total > 0 else 100.0,
                    'total_amount': float(total_amount or 0),
                    'matched_amount': float(matched_amount or 0),
                    'unmatched_amount': float(unmatched_amount or 0)
                }

        except Exception as e:
            logger.error(f"Error getting invoice matching stats: {e}")
            return {'total': 0, 'matched': 0, 'unmatched': 0, 'match_rate': 0, 'error': str(e)}

    @staticmethod
    def get_payslip_matching_stats(tenant_id: str, start_date: str, end_date: str) -> Dict:
        """Get payslip-to-payment matching statistics for a date range."""
        try:
            with db_manager.get_connection() as conn:
                cursor = conn.cursor()

                # Count payslips in period and their match status
                cursor.execute("""
                    SELECT
                        COUNT(*) as total,
                        COUNT(*) FILTER (WHERE linked_transaction_id IS NOT NULL) as matched,
                        COUNT(*) FILTER (WHERE linked_transaction_id IS NULL) as unmatched,
                        COALESCE(SUM(net_amount), 0) as total_amount,
                        COALESCE(SUM(CASE WHEN linked_transaction_id IS NOT NULL THEN net_amount ELSE 0 END), 0) as matched_amount,
                        COALESCE(SUM(CASE WHEN linked_transaction_id IS NULL THEN net_amount ELSE 0 END), 0) as unmatched_amount
                    FROM payslips
                    WHERE tenant_id = %s
                    AND payment_date >= %s AND payment_date <= %s
                """, (tenant_id, start_date, end_date))

                row = cursor.fetchone()
                cursor.close()

                if not row:
                    return {'total': 0, 'matched': 0, 'unmatched': 0, 'match_rate': 0}

                total, matched, unmatched, total_amount, matched_amount, unmatched_amount = row

                return {
                    'total': total or 0,
                    'matched': matched or 0,
                    'unmatched': unmatched or 0,
                    'match_rate': round((matched / total) * 100, 1) if total > 0 else 100.0,
                    'total_amount': float(total_amount or 0),
                    'matched_amount': float(matched_amount or 0),
                    'unmatched_amount': float(unmatched_amount or 0)
                }

        except Exception as e:
            logger.error(f"Error getting payslip matching stats: {e}")
            return {'total': 0, 'matched': 0, 'unmatched': 0, 'match_rate': 0, 'error': str(e)}

    @staticmethod
    def get_transaction_classification_stats(tenant_id: str, start_date: str, end_date: str) -> Dict:
        """Get transaction classification statistics for a date range."""
        try:
            with db_manager.get_connection() as conn:
                cursor = conn.cursor()

                # Count transactions and their classification status
                cursor.execute("""
                    SELECT
                        COUNT(*) as total,
                        COUNT(*) FILTER (WHERE category IS NOT NULL AND category != '' AND category != 'Uncategorized') as classified,
                        COUNT(*) FILTER (WHERE category IS NULL OR category = '' OR category = 'Uncategorized') as unclassified,
                        COUNT(*) FILTER (WHERE confidence IS NOT NULL AND confidence >= 0.7) as high_confidence,
                        COUNT(*) FILTER (WHERE confidence IS NOT NULL AND confidence < 0.7 AND confidence >= 0.4) as medium_confidence,
                        COUNT(*) FILTER (WHERE confidence IS NULL OR confidence < 0.4) as low_confidence,
                        COUNT(*) FILTER (WHERE user_reviewed = true) as user_reviewed
                    FROM transactions
                    WHERE tenant_id = %s
                    AND date >= %s AND date <= %s
                """, (tenant_id, start_date, end_date))

                row = cursor.fetchone()
                cursor.close()

                if not row:
                    return {'total': 0, 'classified': 0, 'unclassified': 0, 'classified_rate': 0}

                total, classified, unclassified, high_conf, medium_conf, low_conf, user_reviewed = row

                return {
                    'total': total or 0,
                    'classified': classified or 0,
                    'unclassified': unclassified or 0,
                    'classified_rate': round((classified / total) * 100, 1) if total > 0 else 100.0,
                    'high_confidence': high_conf or 0,
                    'medium_confidence': medium_conf or 0,
                    'low_confidence': low_conf or 0,
                    'high_confidence_rate': round((high_conf / total) * 100, 1) if total > 0 else 100.0,
                    'user_reviewed': user_reviewed or 0,
                    'needs_review': (low_conf or 0) - (user_reviewed or 0)
                }

        except Exception as e:
            logger.error(f"Error getting transaction classification stats: {e}")
            return {'total': 0, 'classified': 0, 'unclassified': 0, 'classified_rate': 0, 'error': str(e)}

    @staticmethod
    def get_unmatched_items(period_id: str, tenant_id: str, item_type: str = 'all',
                            page: int = 1, per_page: int = 20) -> Tuple[List[Dict], int]:
        """Get unmatched items (invoices, payslips, or transactions) for a period."""
        period = MonthEndCloseService.get_period(period_id, tenant_id)
        if not period:
            return [], 0

        start_date = period['start_date']
        end_date = period['end_date']

        try:
            with db_manager.get_connection() as conn:
                cursor = conn.cursor()
                items = []
                total = 0
                offset = (page - 1) * per_page

                if item_type in ['all', 'invoices']:
                    cursor.execute("""
                        SELECT id, invoice_number, date, vendor_name, total_amount, currency, 'invoice' as type
                        FROM invoices
                        WHERE tenant_id = %s
                        AND date >= %s AND date <= %s
                        AND (linked_transaction_id IS NULL OR linked_transaction_id = '')
                        ORDER BY date DESC
                        LIMIT %s OFFSET %s
                    """, (tenant_id, start_date, end_date, per_page, offset))
                    for row in cursor.fetchall():
                        items.append({
                            'id': str(row[0]),
                            'reference': row[1],
                            'date': row[2].isoformat() if row[2] else None,
                            'description': row[3],
                            'amount': float(row[4]) if row[4] else 0,
                            'currency': row[5],
                            'type': row[6]
                        })

                    cursor.execute("""
                        SELECT COUNT(*) FROM invoices
                        WHERE tenant_id = %s
                        AND date >= %s AND date <= %s
                        AND (linked_transaction_id IS NULL OR linked_transaction_id = '')
                    """, (tenant_id, start_date, end_date))
                    total += cursor.fetchone()[0]

                if item_type in ['all', 'payslips']:
                    cursor.execute("""
                        SELECT p.id, p.payslip_number, p.payment_date, w.full_name, p.net_amount, p.currency, 'payslip' as type
                        FROM payslips p
                        LEFT JOIN workforce_members w ON p.workforce_member_id = w.id
                        WHERE p.tenant_id = %s
                        AND p.payment_date >= %s AND p.payment_date <= %s
                        AND p.linked_transaction_id IS NULL
                        ORDER BY p.payment_date DESC
                        LIMIT %s OFFSET %s
                    """, (tenant_id, start_date, end_date, per_page, offset))
                    for row in cursor.fetchall():
                        items.append({
                            'id': str(row[0]),
                            'reference': row[1],
                            'date': row[2].isoformat() if row[2] else None,
                            'description': row[3] or 'Unknown Employee',
                            'amount': float(row[4]) if row[4] else 0,
                            'currency': row[5],
                            'type': row[6]
                        })

                    cursor.execute("""
                        SELECT COUNT(*) FROM payslips
                        WHERE tenant_id = %s
                        AND payment_date >= %s AND payment_date <= %s
                        AND linked_transaction_id IS NULL
                    """, (tenant_id, start_date, end_date))
                    total += cursor.fetchone()[0]

                if item_type in ['all', 'transactions']:
                    cursor.execute("""
                        SELECT transaction_id, date, description, amount, currency, 'transaction' as type
                        FROM transactions
                        WHERE tenant_id = %s
                        AND date >= %s AND date <= %s
                        AND (category IS NULL OR category = '' OR category = 'Uncategorized')
                        ORDER BY date DESC
                        LIMIT %s OFFSET %s
                    """, (tenant_id, start_date, end_date, per_page, offset))
                    for row in cursor.fetchall():
                        items.append({
                            'id': str(row[0]),
                            'reference': str(row[0])[:8],
                            'date': row[1].isoformat() if row[1] else None,
                            'description': row[2],
                            'amount': float(row[3]) if row[3] else 0,
                            'currency': row[4],
                            'type': row[5]
                        })

                    cursor.execute("""
                        SELECT COUNT(*) FROM transactions
                        WHERE tenant_id = %s
                        AND date >= %s AND date <= %s
                        AND (category IS NULL OR category = '' OR category = 'Uncategorized')
                    """, (tenant_id, start_date, end_date))
                    total += cursor.fetchone()[0]

                cursor.close()
                return items, total

        except Exception as e:
            logger.error(f"Error getting unmatched items: {e}")
            return [], 0

    # ========================================
    # AUTO-CHECK SYSTEM (PHASE 2)
    # ========================================

    @staticmethod
    def run_auto_checks(period_id: str, tenant_id: str, user_id: Optional[str] = None) -> Dict:
        """Run all auto-checks for a period's checklist items."""
        period = MonthEndCloseService.get_period(period_id, tenant_id)
        if not period:
            return {'error': 'Period not found', 'results': []}

        if period['status'] in [MonthEndCloseService.STATUS_LOCKED, MonthEndCloseService.STATUS_CLOSED]:
            return {'error': 'Cannot run auto-checks on locked/closed period', 'results': []}

        items = MonthEndCloseService.get_checklist(period_id, tenant_id)
        results = []

        for item in items:
            if item.get('auto_check_type'):
                result = MonthEndCloseService.run_single_auto_check(
                    item['id'], period_id, tenant_id, item['auto_check_type'], user_id
                )
                results.append({
                    'item_id': item['id'],
                    'item_name': item['name'],
                    'auto_check_type': item['auto_check_type'],
                    'result': result
                })

        # Log activity
        MonthEndCloseService.log_activity(
            period_id, tenant_id, 'auto_checks_run', 'period', period_id,
            user_id=user_id, details={'checks_run': len(results)}
        )

        return {
            'period_id': period_id,
            'checks_run': len(results),
            'results': results
        }

    @staticmethod
    def run_single_auto_check(item_id: str, period_id: str, tenant_id: str,
                               auto_check_type: str, user_id: Optional[str] = None) -> Dict:
        """Run auto-check for a single checklist item."""
        period = MonthEndCloseService.get_period(period_id, tenant_id)
        if not period:
            return {'success': False, 'error': 'Period not found'}

        start_date = period['start_date']
        end_date = period['end_date']

        # Get threshold from template
        threshold = 95.0  # default
        try:
            with db_manager.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT t.auto_check_threshold
                    FROM close_checklist_items ci
                    JOIN close_checklist_templates t ON ci.template_id = t.id
                    WHERE ci.id = %s
                """, (item_id,))
                row = cursor.fetchone()
                if row and row[0]:
                    threshold = float(row[0])
                cursor.close()
        except Exception as e:
            logger.warning(f"Could not get threshold for item {item_id}: {e}")

        # Run the appropriate check
        result = {}
        if auto_check_type == 'invoices_matched':
            stats = MonthEndCloseService.get_invoice_matching_stats(tenant_id, start_date, end_date)
            result = {
                'matched': stats.get('matched', 0),
                'total': stats.get('total', 0),
                'percentage': stats.get('match_rate', 0),
                'threshold': threshold,
                'passed': stats.get('match_rate', 0) >= threshold,
                'details': stats
            }

        elif auto_check_type == 'payslips_matched':
            stats = MonthEndCloseService.get_payslip_matching_stats(tenant_id, start_date, end_date)
            result = {
                'matched': stats.get('matched', 0),
                'total': stats.get('total', 0),
                'percentage': stats.get('match_rate', 0),
                'threshold': threshold,
                'passed': stats.get('match_rate', 0) >= threshold,
                'details': stats
            }

        elif auto_check_type == 'low_confidence_reviewed':
            stats = MonthEndCloseService.get_transaction_classification_stats(tenant_id, start_date, end_date)
            low_conf = stats.get('low_confidence', 0)
            reviewed = stats.get('user_reviewed', 0)
            percentage = (reviewed / low_conf * 100) if low_conf > 0 else 100.0
            result = {
                'matched': reviewed,
                'total': low_conf,
                'percentage': round(percentage, 1),
                'threshold': threshold,
                'passed': percentage >= threshold,
                'details': stats
            }

        elif auto_check_type == 'unclassified_resolved':
            stats = MonthEndCloseService.get_transaction_classification_stats(tenant_id, start_date, end_date)
            result = {
                'matched': stats.get('classified', 0),
                'total': stats.get('total', 0),
                'percentage': stats.get('classified_rate', 0),
                'threshold': threshold,
                'passed': stats.get('classified_rate', 0) >= threshold,
                'details': stats
            }

        elif auto_check_type == 'bank_reconciled':
            # For now, use transaction classification as proxy
            # In future, implement dedicated bank reconciliation tracking
            stats = MonthEndCloseService.get_transaction_classification_stats(tenant_id, start_date, end_date)
            result = {
                'matched': stats.get('classified', 0),
                'total': stats.get('total', 0),
                'percentage': stats.get('classified_rate', 0),
                'threshold': threshold,
                'passed': stats.get('classified_rate', 0) >= threshold,
                'details': stats,
                'note': 'Using transaction classification as proxy for bank reconciliation'
            }

        else:
            result = {
                'matched': 0,
                'total': 0,
                'percentage': 0,
                'threshold': threshold,
                'passed': False,
                'error': f'Unknown auto-check type: {auto_check_type}'
            }

        # Update the checklist item with auto-check result
        try:
            with db_manager.get_connection() as conn:
                cursor = conn.cursor()

                # Determine new status based on result
                new_status = None
                if result.get('passed'):
                    new_status = 'completed'

                cursor.execute("""
                    UPDATE close_checklist_items
                    SET auto_check_result = %s,
                        last_auto_check_at = CURRENT_TIMESTAMP,
                        status = COALESCE(%s, status),
                        completed_at = CASE WHEN %s = 'completed' THEN CURRENT_TIMESTAMP ELSE completed_at END,
                        completed_by = CASE WHEN %s = 'completed' THEN %s ELSE completed_by END,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = %s
                """, (json.dumps(result), new_status, new_status, new_status, user_id, item_id))

                conn.commit()
                cursor.close()

        except Exception as e:
            logger.error(f"Error updating auto-check result: {e}")
            result['update_error'] = str(e)

        return result

    # ========================================
    # ADJUSTING ENTRIES (PHASE 3)
    # ========================================

    # Entry status constants
    ENTRY_DRAFT = 'draft'
    ENTRY_PENDING = 'pending_approval'
    ENTRY_APPROVED = 'approved'
    ENTRY_POSTED = 'posted'
    ENTRY_REJECTED = 'rejected'

    # Entry type constants
    ENTRY_TYPES = ['accrual', 'depreciation', 'prepaid', 'deferral', 'correction', 'reclassification', 'other']

    @staticmethod
    def list_adjusting_entries(period_id: str, tenant_id: str,
                                status: Optional[str] = None,
                                page: int = 1, per_page: int = 20) -> Tuple[List[Dict], int]:
        """List adjusting entries for a period."""
        try:
            with db_manager.get_connection() as conn:
                cursor = conn.cursor()

                # Build query
                where_clause = "WHERE period_id = %s AND tenant_id = %s"
                params = [period_id, tenant_id]

                if status:
                    where_clause += " AND status = %s"
                    params.append(status)

                # Get total count
                cursor.execute(f"""
                    SELECT COUNT(*) FROM close_adjusting_entries {where_clause}
                """, params)
                total = cursor.fetchone()[0]

                # Get entries
                offset = (page - 1) * per_page
                cursor.execute(f"""
                    SELECT id, period_id, tenant_id, entry_type, description,
                           debit_account, credit_account, amount, currency, entity,
                           status, created_by, submitted_at, approved_by, approved_at,
                           rejected_by, rejected_at, rejection_reason, posted_at, posted_by,
                           transaction_id, is_reversing, reversal_period_id, original_entry_id,
                           notes, supporting_documents, created_at, updated_at
                    FROM close_adjusting_entries
                    {where_clause}
                    ORDER BY created_at DESC
                    LIMIT %s OFFSET %s
                """, params + [per_page, offset])

                columns = [desc[0] for desc in cursor.description]
                entries = []
                for row in cursor.fetchall():
                    entry = dict(zip(columns, row))
                    # Convert UUIDs and dates to strings
                    for key in ['id', 'period_id', 'created_by', 'approved_by', 'rejected_by',
                                'posted_by', 'reversal_period_id', 'original_entry_id']:
                        if entry.get(key):
                            entry[key] = str(entry[key])
                    for key in ['submitted_at', 'approved_at', 'rejected_at', 'posted_at', 'created_at', 'updated_at']:
                        if entry.get(key):
                            entry[key] = entry[key].isoformat()
                    if entry.get('amount'):
                        entry['amount'] = float(entry['amount'])
                    entries.append(entry)

                cursor.close()
                return entries, total

        except Exception as e:
            logger.error(f"Error listing adjusting entries: {e}")
            return [], 0

    @staticmethod
    def get_adjusting_entry(entry_id: str, tenant_id: str) -> Optional[Dict]:
        """Get a single adjusting entry."""
        try:
            with db_manager.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT id, period_id, tenant_id, entry_type, description,
                           debit_account, credit_account, amount, currency, entity,
                           status, created_by, submitted_at, approved_by, approved_at,
                           rejected_by, rejected_at, rejection_reason, posted_at, posted_by,
                           transaction_id, is_reversing, reversal_period_id, original_entry_id,
                           notes, supporting_documents, created_at, updated_at
                    FROM close_adjusting_entries
                    WHERE id = %s AND tenant_id = %s
                """, (entry_id, tenant_id))

                row = cursor.fetchone()
                cursor.close()

                if not row:
                    return None

                columns = [desc[0] for desc in cursor.description]
                entry = dict(zip(columns, row))

                # Convert UUIDs and dates to strings
                for key in ['id', 'period_id', 'created_by', 'approved_by', 'rejected_by',
                            'posted_by', 'reversal_period_id', 'original_entry_id']:
                    if entry.get(key):
                        entry[key] = str(entry[key])
                for key in ['submitted_at', 'approved_at', 'rejected_at', 'posted_at', 'created_at', 'updated_at']:
                    if entry.get(key):
                        entry[key] = entry[key].isoformat()
                if entry.get('amount'):
                    entry['amount'] = float(entry['amount'])

                return entry

        except Exception as e:
            logger.error(f"Error getting adjusting entry: {e}")
            return None

    @staticmethod
    def create_adjusting_entry(period_id: str, tenant_id: str, entry_type: str,
                                description: str, debit_account: str, credit_account: str,
                                amount: float, currency: str = 'USD', entity: Optional[str] = None,
                                notes: Optional[str] = None, is_reversing: bool = False,
                                user_id: Optional[str] = None) -> Optional[Dict]:
        """Create a new adjusting entry."""
        # Validate period
        period = MonthEndCloseService.get_period(period_id, tenant_id)
        if not period:
            raise ValueError("Period not found")

        if period['status'] in [MonthEndCloseService.STATUS_LOCKED, MonthEndCloseService.STATUS_CLOSED]:
            raise ValueError("Cannot create entries for locked/closed period")

        # Validate entry type
        if entry_type not in MonthEndCloseService.ENTRY_TYPES:
            raise ValueError(f"Invalid entry type. Must be one of: {MonthEndCloseService.ENTRY_TYPES}")

        try:
            with db_manager.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO close_adjusting_entries
                    (period_id, tenant_id, entry_type, description, debit_account, credit_account,
                     amount, currency, entity, notes, is_reversing, created_by, status)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'draft')
                    RETURNING id
                """, (period_id, tenant_id, entry_type, description, debit_account, credit_account,
                      amount, currency, entity, notes, is_reversing, user_id))

                entry_id = str(cursor.fetchone()[0])
                conn.commit()
                cursor.close()

                # Log activity
                MonthEndCloseService.log_activity(
                    period_id, tenant_id, 'entry_created', 'adjusting_entry', entry_id,
                    user_id=user_id, details={'entry_type': entry_type, 'amount': amount}
                )

                return MonthEndCloseService.get_adjusting_entry(entry_id, tenant_id)

        except Exception as e:
            logger.error(f"Error creating adjusting entry: {e}")
            raise

    @staticmethod
    def update_adjusting_entry(entry_id: str, tenant_id: str,
                                entry_type: Optional[str] = None,
                                description: Optional[str] = None,
                                debit_account: Optional[str] = None,
                                credit_account: Optional[str] = None,
                                amount: Optional[float] = None,
                                currency: Optional[str] = None,
                                entity: Optional[str] = None,
                                notes: Optional[str] = None,
                                user_id: Optional[str] = None) -> Optional[Dict]:
        """Update an adjusting entry (only if draft)."""
        entry = MonthEndCloseService.get_adjusting_entry(entry_id, tenant_id)
        if not entry:
            return None

        if entry['status'] != MonthEndCloseService.ENTRY_DRAFT:
            raise ValueError("Can only update draft entries")

        # Validate entry type if provided
        if entry_type and entry_type not in MonthEndCloseService.ENTRY_TYPES:
            raise ValueError(f"Invalid entry type. Must be one of: {MonthEndCloseService.ENTRY_TYPES}")

        try:
            with db_manager.get_connection() as conn:
                cursor = conn.cursor()

                updates = []
                params = []

                if entry_type is not None:
                    updates.append("entry_type = %s")
                    params.append(entry_type)
                if description is not None:
                    updates.append("description = %s")
                    params.append(description)
                if debit_account is not None:
                    updates.append("debit_account = %s")
                    params.append(debit_account)
                if credit_account is not None:
                    updates.append("credit_account = %s")
                    params.append(credit_account)
                if amount is not None:
                    updates.append("amount = %s")
                    params.append(amount)
                if currency is not None:
                    updates.append("currency = %s")
                    params.append(currency)
                if entity is not None:
                    updates.append("entity = %s")
                    params.append(entity)
                if notes is not None:
                    updates.append("notes = %s")
                    params.append(notes)

                if updates:
                    updates.append("updated_at = CURRENT_TIMESTAMP")
                    params.extend([entry_id, tenant_id])

                    cursor.execute(f"""
                        UPDATE close_adjusting_entries
                        SET {', '.join(updates)}
                        WHERE id = %s AND tenant_id = %s
                    """, params)

                    conn.commit()

                cursor.close()
                return MonthEndCloseService.get_adjusting_entry(entry_id, tenant_id)

        except Exception as e:
            logger.error(f"Error updating adjusting entry: {e}")
            raise

    @staticmethod
    def delete_adjusting_entry(entry_id: str, tenant_id: str, user_id: Optional[str] = None) -> bool:
        """Delete an adjusting entry (only if draft)."""
        entry = MonthEndCloseService.get_adjusting_entry(entry_id, tenant_id)
        if not entry:
            return False

        if entry['status'] != MonthEndCloseService.ENTRY_DRAFT:
            raise ValueError("Can only delete draft entries")

        try:
            with db_manager.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    DELETE FROM close_adjusting_entries
                    WHERE id = %s AND tenant_id = %s
                """, (entry_id, tenant_id))
                conn.commit()
                cursor.close()

                # Log activity
                MonthEndCloseService.log_activity(
                    entry['period_id'], tenant_id, 'entry_deleted', 'adjusting_entry', entry_id,
                    user_id=user_id, details={'entry_type': entry['entry_type'], 'amount': entry['amount']}
                )

                return True

        except Exception as e:
            logger.error(f"Error deleting adjusting entry: {e}")
            return False

    @staticmethod
    def submit_adjusting_entry(entry_id: str, tenant_id: str, user_id: Optional[str] = None) -> Optional[Dict]:
        """Submit an adjusting entry for approval."""
        entry = MonthEndCloseService.get_adjusting_entry(entry_id, tenant_id)
        if not entry:
            return None

        if entry['status'] != MonthEndCloseService.ENTRY_DRAFT:
            raise ValueError("Can only submit draft entries")

        try:
            with db_manager.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE close_adjusting_entries
                    SET status = 'pending_approval',
                        submitted_at = CURRENT_TIMESTAMP,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = %s AND tenant_id = %s
                """, (entry_id, tenant_id))
                conn.commit()
                cursor.close()

                # Log activity
                MonthEndCloseService.log_activity(
                    entry['period_id'], tenant_id, 'entry_submitted', 'adjusting_entry', entry_id,
                    user_id=user_id, details={'amount': entry['amount']}
                )

                return MonthEndCloseService.get_adjusting_entry(entry_id, tenant_id)

        except Exception as e:
            logger.error(f"Error submitting adjusting entry: {e}")
            raise

    @staticmethod
    def approve_adjusting_entry(entry_id: str, tenant_id: str, user_id: Optional[str] = None) -> Optional[Dict]:
        """Approve an adjusting entry."""
        entry = MonthEndCloseService.get_adjusting_entry(entry_id, tenant_id)
        if not entry:
            return None

        if entry['status'] != MonthEndCloseService.ENTRY_PENDING:
            raise ValueError("Can only approve entries pending approval")

        try:
            with db_manager.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE close_adjusting_entries
                    SET status = 'approved',
                        approved_by = %s,
                        approved_at = CURRENT_TIMESTAMP,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = %s AND tenant_id = %s
                """, (user_id, entry_id, tenant_id))
                conn.commit()
                cursor.close()

                # Log activity
                MonthEndCloseService.log_activity(
                    entry['period_id'], tenant_id, 'entry_approved', 'adjusting_entry', entry_id,
                    user_id=user_id, details={'amount': entry['amount']}
                )

                return MonthEndCloseService.get_adjusting_entry(entry_id, tenant_id)

        except Exception as e:
            logger.error(f"Error approving adjusting entry: {e}")
            raise

    @staticmethod
    def reject_adjusting_entry(entry_id: str, tenant_id: str, reason: str,
                                user_id: Optional[str] = None) -> Optional[Dict]:
        """Reject an adjusting entry."""
        entry = MonthEndCloseService.get_adjusting_entry(entry_id, tenant_id)
        if not entry:
            return None

        if entry['status'] != MonthEndCloseService.ENTRY_PENDING:
            raise ValueError("Can only reject entries pending approval")

        try:
            with db_manager.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE close_adjusting_entries
                    SET status = 'rejected',
                        rejected_by = %s,
                        rejected_at = CURRENT_TIMESTAMP,
                        rejection_reason = %s,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = %s AND tenant_id = %s
                """, (user_id, reason, entry_id, tenant_id))
                conn.commit()
                cursor.close()

                # Log activity
                MonthEndCloseService.log_activity(
                    entry['period_id'], tenant_id, 'entry_rejected', 'adjusting_entry', entry_id,
                    user_id=user_id, details={'reason': reason}
                )

                return MonthEndCloseService.get_adjusting_entry(entry_id, tenant_id)

        except Exception as e:
            logger.error(f"Error rejecting adjusting entry: {e}")
            raise

    @staticmethod
    def post_adjusting_entry(entry_id: str, tenant_id: str, user_id: Optional[str] = None) -> Optional[Dict]:
        """Post an approved adjusting entry to the transactions table."""
        entry = MonthEndCloseService.get_adjusting_entry(entry_id, tenant_id)
        if not entry:
            return None

        if entry['status'] != MonthEndCloseService.ENTRY_APPROVED:
            raise ValueError("Can only post approved entries")

        period = MonthEndCloseService.get_period(entry['period_id'], tenant_id)
        if not period:
            raise ValueError("Period not found")

        try:
            with db_manager.get_connection() as conn:
                cursor = conn.cursor()

                # Create transaction record for the adjusting entry
                # Using the period end date as the transaction date
                transaction_date = period['end_date']

                # Build description for transaction
                tx_description = f"[Adjusting Entry] {entry['description']}"
                if entry['entity']:
                    tx_description = f"[{entry['entity']}] {tx_description}"

                # Insert the transaction (as a debit entry)
                cursor.execute("""
                    INSERT INTO transactions
                    (tenant_id, date, description, amount, currency, category, subcategory,
                     entity, justification, confidence, source)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING transaction_id
                """, (
                    tenant_id,
                    transaction_date,
                    tx_description,
                    entry['amount'],
                    entry['currency'],
                    'Adjusting Entry',
                    entry['entry_type'].replace('_', ' ').title(),
                    entry['entity'],
                    f"Debit: {entry['debit_account']}, Credit: {entry['credit_account']}",
                    1.0,  # High confidence for manual entries
                    'adjusting_entry'
                ))

                transaction_id = cursor.fetchone()[0]

                # Update the entry with posted status
                cursor.execute("""
                    UPDATE close_adjusting_entries
                    SET status = 'posted',
                        posted_by = %s,
                        posted_at = CURRENT_TIMESTAMP,
                        transaction_id = %s,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = %s AND tenant_id = %s
                """, (user_id, transaction_id, entry_id, tenant_id))

                conn.commit()
                cursor.close()

                # Log activity
                MonthEndCloseService.log_activity(
                    entry['period_id'], tenant_id, 'entry_posted', 'adjusting_entry', entry_id,
                    user_id=user_id, details={'transaction_id': transaction_id, 'amount': entry['amount']}
                )

                return MonthEndCloseService.get_adjusting_entry(entry_id, tenant_id)

        except Exception as e:
            logger.error(f"Error posting adjusting entry: {e}")
            raise

    @staticmethod
    def revert_adjusting_entry(entry_id: str, tenant_id: str, user_id: Optional[str] = None) -> Optional[Dict]:
        """Revert a rejected entry back to draft status for editing."""
        entry = MonthEndCloseService.get_adjusting_entry(entry_id, tenant_id)
        if not entry:
            return None

        if entry['status'] != MonthEndCloseService.ENTRY_REJECTED:
            raise ValueError("Can only revert rejected entries")

        try:
            with db_manager.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE close_adjusting_entries
                    SET status = 'draft',
                        rejection_reason = NULL,
                        rejected_by = NULL,
                        rejected_at = NULL,
                        submitted_at = NULL,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = %s AND tenant_id = %s
                """, (entry_id, tenant_id))
                conn.commit()
                cursor.close()

                # Log activity
                MonthEndCloseService.log_activity(
                    entry['period_id'], tenant_id, 'entry_reverted', 'adjusting_entry', entry_id,
                    user_id=user_id
                )

                return MonthEndCloseService.get_adjusting_entry(entry_id, tenant_id)

        except Exception as e:
            logger.error(f"Error reverting adjusting entry: {e}")
            raise

    @staticmethod
    def get_entries_summary(period_id: str, tenant_id: str) -> Dict:
        """Get summary statistics for adjusting entries in a period."""
        try:
            with db_manager.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT
                        COUNT(*) as total,
                        COUNT(*) FILTER (WHERE status = 'draft') as draft,
                        COUNT(*) FILTER (WHERE status = 'pending_approval') as pending,
                        COUNT(*) FILTER (WHERE status = 'approved') as approved,
                        COUNT(*) FILTER (WHERE status = 'posted') as posted,
                        COUNT(*) FILTER (WHERE status = 'rejected') as rejected,
                        COALESCE(SUM(amount), 0) as total_amount,
                        COALESCE(SUM(CASE WHEN status = 'posted' THEN amount ELSE 0 END), 0) as posted_amount
                    FROM close_adjusting_entries
                    WHERE period_id = %s AND tenant_id = %s
                """, (period_id, tenant_id))

                row = cursor.fetchone()
                cursor.close()

                return {
                    'total': row[0] or 0,
                    'draft': row[1] or 0,
                    'pending': row[2] or 0,
                    'approved': row[3] or 0,
                    'posted': row[4] or 0,
                    'rejected': row[5] or 0,
                    'total_amount': float(row[6] or 0),
                    'posted_amount': float(row[7] or 0)
                }

        except Exception as e:
            logger.error(f"Error getting entries summary: {e}")
            return {
                'total': 0, 'draft': 0, 'pending': 0, 'approved': 0,
                'posted': 0, 'rejected': 0, 'total_amount': 0, 'posted_amount': 0
            }
