"""
Month-End Closing API Routes
Blueprint for managing accounting periods, checklists, and closing workflow.
"""

from flask import Blueprint, request, jsonify, g
import logging

logger = logging.getLogger(__name__)

# Create blueprint
close_bp = Blueprint('close', __name__, url_prefix='/api/close')


def get_current_tenant_id():
    """Get tenant ID from session or context."""
    from flask import session
    tenant_id = session.get('tenant_id') or getattr(g, 'tenant_id', None)
    if not tenant_id:
        logger.warning("[SECURITY] Missing tenant context in close routes")
    return tenant_id


def get_current_user_id():
    """Get current user ID from session."""
    from flask import session
    return session.get('user_id') or getattr(g, 'user_id', None)


# ========================================
# PERIOD MANAGEMENT ROUTES
# ========================================

@close_bp.route('/periods', methods=['GET'])
def list_periods():
    """List all accounting periods for the tenant."""
    try:
        from services.month_end_close import MonthEndCloseService

        tenant_id = get_current_tenant_id()
        if not tenant_id:
            return jsonify({'error': 'Tenant context required'}), 401

        status = request.args.get('status')
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 20))

        periods, total = MonthEndCloseService.list_periods(
            tenant_id, status=status, page=page, per_page=per_page
        )

        return jsonify({
            'periods': periods,
            'total': total,
            'page': page,
            'per_page': per_page,
            'pages': (total + per_page - 1) // per_page
        })

    except Exception as e:
        logger.error(f"Error listing periods: {e}")
        return jsonify({'error': str(e)}), 500


@close_bp.route('/periods', methods=['POST'])
def create_period():
    """Create a new accounting period."""
    try:
        from services.month_end_close import MonthEndCloseService

        tenant_id = get_current_tenant_id()
        if not tenant_id:
            return jsonify({'error': 'Tenant context required'}), 401

        data = request.get_json()
        if not data:
            return jsonify({'error': 'Request body required'}), 400

        required = ['period_name', 'period_type', 'start_date', 'end_date']
        missing = [f for f in required if not data.get(f)]
        if missing:
            return jsonify({'error': f'Missing required fields: {missing}'}), 400

        period = MonthEndCloseService.create_period(
            tenant_id=tenant_id,
            period_name=data['period_name'],
            period_type=data['period_type'],
            start_date=data['start_date'],
            end_date=data['end_date'],
            notes=data.get('notes')
        )

        return jsonify({'period': period, 'message': 'Period created successfully'}), 201

    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        logger.error(f"Error creating period: {e}")
        return jsonify({'error': str(e)}), 500


@close_bp.route('/periods/<period_id>', methods=['GET'])
def get_period(period_id):
    """Get a specific accounting period."""
    try:
        from services.month_end_close import MonthEndCloseService

        tenant_id = get_current_tenant_id()
        if not tenant_id:
            return jsonify({'error': 'Tenant context required'}), 401

        period = MonthEndCloseService.get_period(period_id, tenant_id)
        if not period:
            return jsonify({'error': 'Period not found'}), 404

        # Get checklist progress
        progress = MonthEndCloseService.get_checklist_progress(period_id, tenant_id)

        return jsonify({
            'period': period,
            'progress': progress
        })

    except Exception as e:
        logger.error(f"Error getting period: {e}")
        return jsonify({'error': str(e)}), 500


@close_bp.route('/periods/<period_id>', methods=['PUT'])
def update_period(period_id):
    """Update an accounting period."""
    try:
        from services.month_end_close import MonthEndCloseService

        tenant_id = get_current_tenant_id()
        if not tenant_id:
            return jsonify({'error': 'Tenant context required'}), 401

        data = request.get_json() or {}

        period = MonthEndCloseService.update_period(
            period_id, tenant_id,
            period_name=data.get('period_name'),
            notes=data.get('notes')
        )

        if not period:
            return jsonify({'error': 'Period not found'}), 404

        return jsonify({'period': period, 'message': 'Period updated'})

    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        logger.error(f"Error updating period: {e}")
        return jsonify({'error': str(e)}), 500


@close_bp.route('/periods/<period_id>/start', methods=['POST'])
def start_close_process(period_id):
    """Start the closing process for a period."""
    try:
        from services.month_end_close import MonthEndCloseService

        tenant_id = get_current_tenant_id()
        user_id = get_current_user_id()
        if not tenant_id:
            return jsonify({'error': 'Tenant context required'}), 401

        period = MonthEndCloseService.start_close_process(period_id, tenant_id, user_id)
        if not period:
            return jsonify({'error': 'Period not found'}), 404

        return jsonify({
            'period': period,
            'message': 'Close process started. Checklist items created.'
        })

    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        logger.error(f"Error starting close process: {e}")
        return jsonify({'error': str(e)}), 500


@close_bp.route('/periods/<period_id>/lock', methods=['POST'])
def lock_period(period_id):
    """Lock a period to prevent transaction modifications."""
    try:
        from services.month_end_close import MonthEndCloseService

        tenant_id = get_current_tenant_id()
        user_id = get_current_user_id()
        if not tenant_id:
            return jsonify({'error': 'Tenant context required'}), 401

        period = MonthEndCloseService.lock_period(period_id, tenant_id, user_id)
        if not period:
            return jsonify({'error': 'Period not found'}), 404

        return jsonify({
            'period': period,
            'message': 'Period locked. Transactions cannot be modified.'
        })

    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        logger.error(f"Error locking period: {e}")
        return jsonify({'error': str(e)}), 500


@close_bp.route('/periods/<period_id>/unlock', methods=['POST'])
def unlock_period(period_id):
    """Unlock a period (emergency unlock)."""
    try:
        from services.month_end_close import MonthEndCloseService

        tenant_id = get_current_tenant_id()
        user_id = get_current_user_id()
        if not tenant_id:
            return jsonify({'error': 'Tenant context required'}), 401

        data = request.get_json() or {}
        reason = data.get('reason')
        if not reason:
            return jsonify({'error': 'Unlock reason is required'}), 400

        period = MonthEndCloseService.unlock_period(period_id, tenant_id, reason, user_id)
        if not period:
            return jsonify({'error': 'Period not found'}), 404

        return jsonify({
            'period': period,
            'message': 'Period unlocked. Reason logged.'
        })

    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        logger.error(f"Error unlocking period: {e}")
        return jsonify({'error': str(e)}), 500


@close_bp.route('/periods/<period_id>/submit', methods=['POST'])
def submit_for_approval(period_id):
    """Submit period for approval."""
    try:
        from services.month_end_close import MonthEndCloseService

        tenant_id = get_current_tenant_id()
        user_id = get_current_user_id()
        if not tenant_id:
            return jsonify({'error': 'Tenant context required'}), 401

        period = MonthEndCloseService.submit_for_approval(period_id, tenant_id, user_id)
        if not period:
            return jsonify({'error': 'Period not found'}), 404

        return jsonify({
            'period': period,
            'message': 'Period submitted for approval'
        })

    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        logger.error(f"Error submitting period: {e}")
        return jsonify({'error': str(e)}), 500


@close_bp.route('/periods/<period_id>/approve', methods=['POST'])
def approve_period(period_id):
    """Approve period close."""
    try:
        from services.month_end_close import MonthEndCloseService

        tenant_id = get_current_tenant_id()
        user_id = get_current_user_id()
        if not tenant_id:
            return jsonify({'error': 'Tenant context required'}), 401

        period = MonthEndCloseService.approve_period(period_id, tenant_id, user_id)
        if not period:
            return jsonify({'error': 'Period not found'}), 404

        return jsonify({
            'period': period,
            'message': 'Period approved'
        })

    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        logger.error(f"Error approving period: {e}")
        return jsonify({'error': str(e)}), 500


@close_bp.route('/periods/<period_id>/reject', methods=['POST'])
def reject_period(period_id):
    """Reject period close."""
    try:
        from services.month_end_close import MonthEndCloseService

        tenant_id = get_current_tenant_id()
        user_id = get_current_user_id()
        if not tenant_id:
            return jsonify({'error': 'Tenant context required'}), 401

        data = request.get_json() or {}
        reason = data.get('reason')
        if not reason:
            return jsonify({'error': 'Rejection reason is required'}), 400

        period = MonthEndCloseService.reject_period(period_id, tenant_id, reason, user_id)
        if not period:
            return jsonify({'error': 'Period not found'}), 404

        return jsonify({
            'period': period,
            'message': 'Period rejected and sent back for corrections'
        })

    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        logger.error(f"Error rejecting period: {e}")
        return jsonify({'error': str(e)}), 500


@close_bp.route('/periods/<period_id>/close', methods=['POST'])
def close_period(period_id):
    """Finalize and close the period."""
    try:
        from services.month_end_close import MonthEndCloseService

        tenant_id = get_current_tenant_id()
        user_id = get_current_user_id()
        if not tenant_id:
            return jsonify({'error': 'Tenant context required'}), 401

        period = MonthEndCloseService.close_period(period_id, tenant_id, user_id)
        if not period:
            return jsonify({'error': 'Period not found'}), 404

        return jsonify({
            'period': period,
            'message': 'Period closed successfully'
        })

    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        logger.error(f"Error closing period: {e}")
        return jsonify({'error': str(e)}), 500


# ========================================
# CHECKLIST ROUTES
# ========================================

@close_bp.route('/periods/<period_id>/checklist', methods=['GET'])
def get_checklist(period_id):
    """Get checklist items for a period."""
    try:
        from services.month_end_close import MonthEndCloseService

        tenant_id = get_current_tenant_id()
        if not tenant_id:
            return jsonify({'error': 'Tenant context required'}), 401

        items = MonthEndCloseService.get_checklist(period_id, tenant_id)
        progress = MonthEndCloseService.get_checklist_progress(period_id, tenant_id)

        return jsonify({
            'items': items,
            'progress': progress
        })

    except Exception as e:
        logger.error(f"Error getting checklist: {e}")
        return jsonify({'error': str(e)}), 500


@close_bp.route('/checklist/<item_id>', methods=['PUT'])
def update_checklist_item(item_id):
    """Update a checklist item."""
    try:
        from services.month_end_close import MonthEndCloseService

        tenant_id = get_current_tenant_id()
        user_id = get_current_user_id()
        if not tenant_id:
            return jsonify({'error': 'Tenant context required'}), 401

        data = request.get_json() or {}

        item = MonthEndCloseService.update_checklist_item(
            item_id, tenant_id,
            status=data.get('status'),
            notes=data.get('notes'),
            blockers=data.get('blockers'),
            skip_reason=data.get('skip_reason'),
            user_id=user_id
        )

        if not item:
            return jsonify({'error': 'Checklist item not found'}), 404

        return jsonify({'item': item, 'message': 'Item updated'})

    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        logger.error(f"Error updating checklist item: {e}")
        return jsonify({'error': str(e)}), 500


@close_bp.route('/checklist/<item_id>/complete', methods=['POST'])
def complete_checklist_item(item_id):
    """Mark a checklist item as completed."""
    try:
        from services.month_end_close import MonthEndCloseService

        tenant_id = get_current_tenant_id()
        user_id = get_current_user_id()
        if not tenant_id:
            return jsonify({'error': 'Tenant context required'}), 401

        data = request.get_json() or {}

        item = MonthEndCloseService.complete_checklist_item(
            item_id, tenant_id, user_id=user_id, notes=data.get('notes')
        )

        if not item:
            return jsonify({'error': 'Checklist item not found'}), 404

        return jsonify({'item': item, 'message': 'Item completed'})

    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        logger.error(f"Error completing checklist item: {e}")
        return jsonify({'error': str(e)}), 500


@close_bp.route('/checklist/<item_id>/skip', methods=['POST'])
def skip_checklist_item(item_id):
    """Skip a checklist item with reason."""
    try:
        from services.month_end_close import MonthEndCloseService

        tenant_id = get_current_tenant_id()
        user_id = get_current_user_id()
        if not tenant_id:
            return jsonify({'error': 'Tenant context required'}), 401

        data = request.get_json() or {}
        reason = data.get('reason')
        if not reason:
            return jsonify({'error': 'Skip reason is required'}), 400

        item = MonthEndCloseService.skip_checklist_item(
            item_id, tenant_id, reason=reason, user_id=user_id
        )

        if not item:
            return jsonify({'error': 'Checklist item not found'}), 404

        return jsonify({'item': item, 'message': 'Item skipped'})

    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        logger.error(f"Error skipping checklist item: {e}")
        return jsonify({'error': str(e)}), 500


# ========================================
# ACTIVITY LOG ROUTES
# ========================================

@close_bp.route('/periods/<period_id>/activity-log', methods=['GET'])
def get_activity_log(period_id):
    """Get activity log for a period."""
    try:
        from services.month_end_close import MonthEndCloseService

        tenant_id = get_current_tenant_id()
        if not tenant_id:
            return jsonify({'error': 'Tenant context required'}), 401

        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 50))

        activities, total = MonthEndCloseService.get_activity_log(
            period_id, tenant_id, page=page, per_page=per_page
        )

        return jsonify({
            'activities': activities,
            'total': total,
            'page': page,
            'per_page': per_page
        })

    except Exception as e:
        logger.error(f"Error getting activity log: {e}")
        return jsonify({'error': str(e)}), 500


# ========================================
# UTILITY ROUTES
# ========================================

@close_bp.route('/check-period-lock', methods=['GET'])
def check_period_lock():
    """Check if a date falls within a locked period."""
    try:
        from services.month_end_close import MonthEndCloseService

        tenant_id = get_current_tenant_id()
        if not tenant_id:
            return jsonify({'error': 'Tenant context required'}), 401

        transaction_date = request.args.get('date')
        if not transaction_date:
            return jsonify({'error': 'Date parameter required'}), 400

        is_locked, message = MonthEndCloseService.is_period_locked(tenant_id, transaction_date)

        return jsonify({
            'is_locked': is_locked,
            'message': message
        })

    except Exception as e:
        logger.error(f"Error checking period lock: {e}")
        return jsonify({'error': str(e)}), 500


# ========================================
# RECONCILIATION STATUS ROUTES (PHASE 2)
# ========================================

@close_bp.route('/periods/<period_id>/reconciliation-status', methods=['GET'])
def get_reconciliation_status(period_id):
    """Get comprehensive reconciliation status for a period."""
    try:
        from services.month_end_close import MonthEndCloseService

        tenant_id = get_current_tenant_id()
        if not tenant_id:
            return jsonify({'error': 'Tenant context required'}), 401

        status = MonthEndCloseService.get_reconciliation_status(period_id, tenant_id)

        if 'error' in status:
            return jsonify({'error': status['error']}), 404

        return jsonify(status)

    except Exception as e:
        logger.error(f"Error getting reconciliation status: {e}")
        return jsonify({'error': str(e)}), 500


@close_bp.route('/periods/<period_id>/invoice-stats', methods=['GET'])
def get_invoice_stats(period_id):
    """Get invoice matching statistics for a period."""
    try:
        from services.month_end_close import MonthEndCloseService

        tenant_id = get_current_tenant_id()
        if not tenant_id:
            return jsonify({'error': 'Tenant context required'}), 401

        period = MonthEndCloseService.get_period(period_id, tenant_id)
        if not period:
            return jsonify({'error': 'Period not found'}), 404

        stats = MonthEndCloseService.get_invoice_matching_stats(
            tenant_id, period['start_date'], period['end_date']
        )

        return jsonify(stats)

    except Exception as e:
        logger.error(f"Error getting invoice stats: {e}")
        return jsonify({'error': str(e)}), 500


@close_bp.route('/periods/<period_id>/payslip-stats', methods=['GET'])
def get_payslip_stats(period_id):
    """Get payslip matching statistics for a period."""
    try:
        from services.month_end_close import MonthEndCloseService

        tenant_id = get_current_tenant_id()
        if not tenant_id:
            return jsonify({'error': 'Tenant context required'}), 401

        period = MonthEndCloseService.get_period(period_id, tenant_id)
        if not period:
            return jsonify({'error': 'Period not found'}), 404

        stats = MonthEndCloseService.get_payslip_matching_stats(
            tenant_id, period['start_date'], period['end_date']
        )

        return jsonify(stats)

    except Exception as e:
        logger.error(f"Error getting payslip stats: {e}")
        return jsonify({'error': str(e)}), 500


@close_bp.route('/periods/<period_id>/transaction-stats', methods=['GET'])
def get_transaction_stats(period_id):
    """Get transaction classification statistics for a period."""
    try:
        from services.month_end_close import MonthEndCloseService

        tenant_id = get_current_tenant_id()
        if not tenant_id:
            return jsonify({'error': 'Tenant context required'}), 401

        period = MonthEndCloseService.get_period(period_id, tenant_id)
        if not period:
            return jsonify({'error': 'Period not found'}), 404

        stats = MonthEndCloseService.get_transaction_classification_stats(
            tenant_id, period['start_date'], period['end_date']
        )

        return jsonify(stats)

    except Exception as e:
        logger.error(f"Error getting transaction stats: {e}")
        return jsonify({'error': str(e)}), 500


@close_bp.route('/periods/<period_id>/unmatched-items', methods=['GET'])
def get_unmatched_items(period_id):
    """Get unmatched items (invoices, payslips, transactions) for a period."""
    try:
        from services.month_end_close import MonthEndCloseService

        tenant_id = get_current_tenant_id()
        if not tenant_id:
            return jsonify({'error': 'Tenant context required'}), 401

        item_type = request.args.get('type', 'all')  # all, invoices, payslips, transactions
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 20))

        items, total = MonthEndCloseService.get_unmatched_items(
            period_id, tenant_id, item_type=item_type, page=page, per_page=per_page
        )

        return jsonify({
            'items': items,
            'total': total,
            'page': page,
            'per_page': per_page,
            'pages': (total + per_page - 1) // per_page if per_page > 0 else 0
        })

    except Exception as e:
        logger.error(f"Error getting unmatched items: {e}")
        return jsonify({'error': str(e)}), 500


@close_bp.route('/periods/<period_id>/run-auto-checks', methods=['POST'])
def run_auto_checks(period_id):
    """Run all auto-checks for a period's checklist items."""
    try:
        from services.month_end_close import MonthEndCloseService

        tenant_id = get_current_tenant_id()
        user_id = get_current_user_id()
        if not tenant_id:
            return jsonify({'error': 'Tenant context required'}), 401

        result = MonthEndCloseService.run_auto_checks(period_id, tenant_id, user_id)

        if 'error' in result:
            return jsonify({'error': result['error']}), 400

        return jsonify({
            'message': f"Auto-checks completed. {result['checks_run']} checks run.",
            'result': result
        })

    except Exception as e:
        logger.error(f"Error running auto-checks: {e}")
        return jsonify({'error': str(e)}), 500


@close_bp.route('/checklist/<item_id>/run-auto-check', methods=['POST'])
def run_single_auto_check(item_id):
    """Run auto-check for a single checklist item."""
    try:
        from services.month_end_close import MonthEndCloseService
        from database import db_manager

        tenant_id = get_current_tenant_id()
        user_id = get_current_user_id()
        if not tenant_id:
            return jsonify({'error': 'Tenant context required'}), 401

        # Get item to find period_id and auto_check_type
        with db_manager.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT ci.period_id, ci.auto_check_type, p.tenant_id
                FROM close_checklist_items ci
                JOIN cfo_accounting_periods p ON ci.period_id = p.id
                WHERE ci.id = %s AND p.tenant_id = %s
            """, (item_id, tenant_id))
            row = cursor.fetchone()
            cursor.close()

            if not row:
                return jsonify({'error': 'Checklist item not found'}), 404

            period_id, auto_check_type, _ = row

            if not auto_check_type:
                return jsonify({'error': 'Item does not have auto-check configured'}), 400

        result = MonthEndCloseService.run_single_auto_check(
            item_id, str(period_id), tenant_id, auto_check_type, user_id
        )

        return jsonify({
            'item_id': item_id,
            'auto_check_type': auto_check_type,
            'result': result
        })

    except Exception as e:
        logger.error(f"Error running single auto-check: {e}")
        return jsonify({'error': str(e)}), 500


# ========================================
# ADJUSTING ENTRIES ROUTES (PHASE 3)
# ========================================

@close_bp.route('/periods/<period_id>/entries', methods=['GET'])
def list_adjusting_entries(period_id):
    """List adjusting entries for a period."""
    try:
        from services.month_end_close import MonthEndCloseService

        tenant_id = get_current_tenant_id()
        if not tenant_id:
            return jsonify({'error': 'Tenant context required'}), 401

        status = request.args.get('status')
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 20))

        entries, total = MonthEndCloseService.list_adjusting_entries(
            period_id, tenant_id, status=status, page=page, per_page=per_page
        )

        # Also get summary
        summary = MonthEndCloseService.get_entries_summary(period_id, tenant_id)

        return jsonify({
            'entries': entries,
            'total': total,
            'page': page,
            'per_page': per_page,
            'pages': (total + per_page - 1) // per_page if per_page > 0 else 0,
            'summary': summary
        })

    except Exception as e:
        logger.error(f"Error listing adjusting entries: {e}")
        return jsonify({'error': str(e)}), 500


@close_bp.route('/periods/<period_id>/entries', methods=['POST'])
def create_adjusting_entry(period_id):
    """Create a new adjusting entry."""
    try:
        from services.month_end_close import MonthEndCloseService

        tenant_id = get_current_tenant_id()
        user_id = get_current_user_id()
        if not tenant_id:
            return jsonify({'error': 'Tenant context required'}), 401

        data = request.get_json()
        if not data:
            return jsonify({'error': 'Request body required'}), 400

        required = ['entry_type', 'description', 'debit_account', 'credit_account', 'amount']
        missing = [f for f in required if not data.get(f)]
        if missing:
            return jsonify({'error': f'Missing required fields: {missing}'}), 400

        entry = MonthEndCloseService.create_adjusting_entry(
            period_id=period_id,
            tenant_id=tenant_id,
            entry_type=data['entry_type'],
            description=data['description'],
            debit_account=data['debit_account'],
            credit_account=data['credit_account'],
            amount=float(data['amount']),
            currency=data.get('currency', 'USD'),
            entity=data.get('entity'),
            notes=data.get('notes'),
            is_reversing=data.get('is_reversing', False),
            user_id=user_id
        )

        return jsonify({'entry': entry, 'message': 'Entry created successfully'}), 201

    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        logger.error(f"Error creating adjusting entry: {e}")
        return jsonify({'error': str(e)}), 500


@close_bp.route('/entries/<entry_id>', methods=['GET'])
def get_adjusting_entry(entry_id):
    """Get a single adjusting entry."""
    try:
        from services.month_end_close import MonthEndCloseService

        tenant_id = get_current_tenant_id()
        if not tenant_id:
            return jsonify({'error': 'Tenant context required'}), 401

        entry = MonthEndCloseService.get_adjusting_entry(entry_id, tenant_id)
        if not entry:
            return jsonify({'error': 'Entry not found'}), 404

        return jsonify(entry)

    except Exception as e:
        logger.error(f"Error getting adjusting entry: {e}")
        return jsonify({'error': str(e)}), 500


@close_bp.route('/entries/<entry_id>', methods=['PUT'])
def update_adjusting_entry(entry_id):
    """Update an adjusting entry."""
    try:
        from services.month_end_close import MonthEndCloseService

        tenant_id = get_current_tenant_id()
        user_id = get_current_user_id()
        if not tenant_id:
            return jsonify({'error': 'Tenant context required'}), 401

        data = request.get_json() or {}

        entry = MonthEndCloseService.update_adjusting_entry(
            entry_id=entry_id,
            tenant_id=tenant_id,
            entry_type=data.get('entry_type'),
            description=data.get('description'),
            debit_account=data.get('debit_account'),
            credit_account=data.get('credit_account'),
            amount=float(data['amount']) if data.get('amount') else None,
            currency=data.get('currency'),
            entity=data.get('entity'),
            notes=data.get('notes'),
            user_id=user_id
        )

        if not entry:
            return jsonify({'error': 'Entry not found'}), 404

        return jsonify({'entry': entry, 'message': 'Entry updated'})

    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        logger.error(f"Error updating adjusting entry: {e}")
        return jsonify({'error': str(e)}), 500


@close_bp.route('/entries/<entry_id>', methods=['DELETE'])
def delete_adjusting_entry(entry_id):
    """Delete an adjusting entry."""
    try:
        from services.month_end_close import MonthEndCloseService

        tenant_id = get_current_tenant_id()
        user_id = get_current_user_id()
        if not tenant_id:
            return jsonify({'error': 'Tenant context required'}), 401

        success = MonthEndCloseService.delete_adjusting_entry(entry_id, tenant_id, user_id)
        if not success:
            return jsonify({'error': 'Entry not found'}), 404

        return jsonify({'message': 'Entry deleted'})

    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        logger.error(f"Error deleting adjusting entry: {e}")
        return jsonify({'error': str(e)}), 500


@close_bp.route('/entries/<entry_id>/submit', methods=['POST'])
def submit_adjusting_entry(entry_id):
    """Submit an adjusting entry for approval."""
    try:
        from services.month_end_close import MonthEndCloseService

        tenant_id = get_current_tenant_id()
        user_id = get_current_user_id()
        if not tenant_id:
            return jsonify({'error': 'Tenant context required'}), 401

        entry = MonthEndCloseService.submit_adjusting_entry(entry_id, tenant_id, user_id)
        if not entry:
            return jsonify({'error': 'Entry not found'}), 404

        return jsonify({'entry': entry, 'message': 'Entry submitted for approval'})

    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        logger.error(f"Error submitting adjusting entry: {e}")
        return jsonify({'error': str(e)}), 500


@close_bp.route('/entries/<entry_id>/approve', methods=['POST'])
def approve_adjusting_entry(entry_id):
    """Approve an adjusting entry."""
    try:
        from services.month_end_close import MonthEndCloseService

        tenant_id = get_current_tenant_id()
        user_id = get_current_user_id()
        if not tenant_id:
            return jsonify({'error': 'Tenant context required'}), 401

        entry = MonthEndCloseService.approve_adjusting_entry(entry_id, tenant_id, user_id)
        if not entry:
            return jsonify({'error': 'Entry not found'}), 404

        return jsonify({'entry': entry, 'message': 'Entry approved'})

    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        logger.error(f"Error approving adjusting entry: {e}")
        return jsonify({'error': str(e)}), 500


@close_bp.route('/entries/<entry_id>/reject', methods=['POST'])
def reject_adjusting_entry(entry_id):
    """Reject an adjusting entry."""
    try:
        from services.month_end_close import MonthEndCloseService

        tenant_id = get_current_tenant_id()
        user_id = get_current_user_id()
        if not tenant_id:
            return jsonify({'error': 'Tenant context required'}), 401

        data = request.get_json() or {}
        reason = data.get('reason')
        if not reason:
            return jsonify({'error': 'Rejection reason is required'}), 400

        entry = MonthEndCloseService.reject_adjusting_entry(entry_id, tenant_id, reason, user_id)
        if not entry:
            return jsonify({'error': 'Entry not found'}), 404

        return jsonify({'entry': entry, 'message': 'Entry rejected'})

    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        logger.error(f"Error rejecting adjusting entry: {e}")
        return jsonify({'error': str(e)}), 500


@close_bp.route('/entries/<entry_id>/post', methods=['POST'])
def post_adjusting_entry(entry_id):
    """Post an approved adjusting entry to transactions."""
    try:
        from services.month_end_close import MonthEndCloseService

        tenant_id = get_current_tenant_id()
        user_id = get_current_user_id()
        if not tenant_id:
            return jsonify({'error': 'Tenant context required'}), 401

        entry = MonthEndCloseService.post_adjusting_entry(entry_id, tenant_id, user_id)
        if not entry:
            return jsonify({'error': 'Entry not found'}), 404

        return jsonify({
            'entry': entry,
            'message': f"Entry posted to transactions (ID: {entry.get('transaction_id')})"
        })

    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        logger.error(f"Error posting adjusting entry: {e}")
        return jsonify({'error': str(e)}), 500


@close_bp.route('/entries/<entry_id>/revert', methods=['POST'])
def revert_adjusting_entry(entry_id):
    """Revert a rejected entry back to draft."""
    try:
        from services.month_end_close import MonthEndCloseService

        tenant_id = get_current_tenant_id()
        user_id = get_current_user_id()
        if not tenant_id:
            return jsonify({'error': 'Tenant context required'}), 401

        entry = MonthEndCloseService.revert_adjusting_entry(entry_id, tenant_id, user_id)
        if not entry:
            return jsonify({'error': 'Entry not found'}), 404

        return jsonify({'entry': entry, 'message': 'Entry reverted to draft'})

    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        logger.error(f"Error reverting adjusting entry: {e}")
        return jsonify({'error': str(e)}), 500


@close_bp.route('/periods/<period_id>/entries-summary', methods=['GET'])
def get_entries_summary(period_id):
    """Get summary of adjusting entries for a period."""
    try:
        from services.month_end_close import MonthEndCloseService

        tenant_id = get_current_tenant_id()
        if not tenant_id:
            return jsonify({'error': 'Tenant context required'}), 401

        summary = MonthEndCloseService.get_entries_summary(period_id, tenant_id)
        return jsonify(summary)

    except Exception as e:
        logger.error(f"Error getting entries summary: {e}")
        return jsonify({'error': str(e)}), 500
