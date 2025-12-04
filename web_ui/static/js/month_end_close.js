/**
 * Month-End Close Dashboard JavaScript
 * Handles period management, checklist operations, and workflow actions
 */

// Global state
let currentPeriodId = null;
let currentPeriod = null;
let checklistItems = [];
let skipItemId = null;

// Initialize on page load
document.addEventListener('DOMContentLoaded', function() {
    loadPeriods();
});

// ========================================
// PERIOD MANAGEMENT
// ========================================

async function loadPeriods() {
    try {
        const response = await fetch('/api/close/periods?per_page=100');
        const data = await response.json();

        if (data.error) {
            showNotification(data.error, 'error');
            return;
        }

        const select = document.getElementById('periodSelect');
        select.innerHTML = '<option value="">Select Period...</option>';

        data.periods.forEach(period => {
            const option = document.createElement('option');
            option.value = period.id;
            option.textContent = `${period.period_name} (${period.status})`;
            select.appendChild(option);
        });

        // Auto-select first in-progress or open period
        const activePeriod = data.periods.find(p =>
            p.status === 'in_progress' || p.status === 'pending_approval'
        ) || data.periods.find(p => p.status === 'open');

        if (activePeriod) {
            select.value = activePeriod.id;
            loadPeriod(activePeriod.id);
        }
    } catch (error) {
        console.error('Error loading periods:', error);
        showNotification('Failed to load periods', 'error');
    }
}

async function loadPeriod(periodId) {
    if (!periodId) {
        document.getElementById('periodContent').style.display = 'none';
        document.getElementById('emptyState').style.display = 'block';
        currentPeriodId = null;
        currentPeriod = null;
        return;
    }

    currentPeriodId = periodId;

    try {
        const response = await fetch(`/api/close/periods/${periodId}`);
        const data = await response.json();

        if (data.error) {
            showNotification(data.error, 'error');
            return;
        }

        currentPeriod = data.period;
        document.getElementById('periodContent').style.display = 'block';
        document.getElementById('emptyState').style.display = 'none';

        // Update status badge
        const statusBadge = document.getElementById('periodStatus');
        statusBadge.className = `status-badge ${currentPeriod.status}`;
        statusBadge.textContent = formatStatus(currentPeriod.status);

        // Update dates
        document.getElementById('periodDates').textContent =
            `${formatDate(currentPeriod.start_date)} - ${formatDate(currentPeriod.end_date)}`;

        // Update progress
        updateProgress(data.progress);

        // Load checklist
        loadChecklist();

        // Update action buttons
        updateActionButtons();

    } catch (error) {
        console.error('Error loading period:', error);
        showNotification('Failed to load period', 'error');
    }
}

function updateProgress(progress) {
    const percentage = progress.percentage || 0;
    const total = progress.total || 0;
    const completed = progress.completed || 0;
    const skipped = progress.skipped || 0;

    document.getElementById('progressBar').style.width = `${percentage}%`;
    document.getElementById('progressText').textContent =
        `${completed + skipped} of ${total} tasks complete (${percentage}%)`;

    // Update stats
    document.getElementById('statCompleted').textContent = completed;
    document.getElementById('statPending').textContent = progress.pending || 0;
    document.getElementById('statBlocked').textContent = progress.blocked || 0;
    document.getElementById('statSkipped').textContent = skipped;
}

function updateActionButtons() {
    const status = currentPeriod.status;

    // Hide all buttons first
    document.getElementById('btnLock').style.display = 'none';
    document.getElementById('btnUnlock').style.display = 'none';
    document.getElementById('btnSubmit').style.display = 'none';
    document.getElementById('btnApprove').style.display = 'none';
    document.getElementById('btnReject').style.display = 'none';
    document.getElementById('btnClose').style.display = 'none';

    switch (status) {
        case 'open':
            // Period needs to be started first - show start button in checklist
            break;
        case 'in_progress':
            document.getElementById('btnLock').style.display = 'inline-block';
            document.getElementById('btnSubmit').style.display = 'inline-block';
            break;
        case 'pending_approval':
            document.getElementById('btnLock').style.display = 'inline-block';
            document.getElementById('btnApprove').style.display = 'inline-block';
            document.getElementById('btnReject').style.display = 'inline-block';
            break;
        case 'locked':
            document.getElementById('btnUnlock').style.display = 'inline-block';
            if (currentPeriod.approved_at) {
                document.getElementById('btnClose').style.display = 'inline-block';
            }
            break;
        case 'closed':
            // No actions available for closed periods
            break;
    }
}

// ========================================
// CHECKLIST MANAGEMENT
// ========================================

async function loadChecklist() {
    if (!currentPeriodId) return;

    const container = document.getElementById('checklistItems');
    container.innerHTML = '<div class="loading"><div class="spinner"></div></div>';

    try {
        const response = await fetch(`/api/close/periods/${currentPeriodId}/checklist`);
        const data = await response.json();

        if (data.error) {
            container.innerHTML = `<div class="empty-state"><p>${data.error}</p></div>`;
            return;
        }

        checklistItems = data.items;
        updateProgress(data.progress);

        if (checklistItems.length === 0) {
            if (currentPeriod.status === 'open') {
                container.innerHTML = `
                    <div class="empty-state">
                        <h3>Period Not Started</h3>
                        <p>Start the close process to generate the checklist.</p>
                        <button class="btn btn-primary" onclick="startCloseProcess()" style="margin-top: 1rem;">
                            Start Close Process
                        </button>
                    </div>
                `;
            } else {
                container.innerHTML = '<div class="empty-state"><p>No checklist items found.</p></div>';
            }
            return;
        }

        renderChecklist(checklistItems);

    } catch (error) {
        console.error('Error loading checklist:', error);
        container.innerHTML = '<div class="empty-state"><p>Failed to load checklist</p></div>';
    }
}

function renderChecklist(items) {
    const container = document.getElementById('checklistItems');

    // Group by category
    const categories = {};
    items.forEach(item => {
        if (!categories[item.category]) {
            categories[item.category] = [];
        }
        categories[item.category].push(item);
    });

    let html = '';
    for (const [category, categoryItems] of Object.entries(categories)) {
        html += `
            <div class="category-group">
                <div class="category-header">${formatCategory(category)}</div>
                ${categoryItems.map(item => renderChecklistItem(item)).join('')}
            </div>
        `;
    }

    container.innerHTML = html;
}

function renderChecklistItem(item) {
    const isCompleted = item.status === 'completed';
    const isSkipped = item.status === 'skipped';
    const isBlocked = item.status === 'blocked';
    const isInProgress = item.status === 'in_progress';
    const canModify = currentPeriod.status === 'in_progress';

    let checkboxClass = 'checklist-checkbox';
    let checkboxContent = '';
    if (isCompleted) {
        checkboxClass += ' completed';
        checkboxContent = '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3"><polyline points="20 6 9 17 4 12"></polyline></svg>';
    } else if (isSkipped) {
        checkboxClass += ' skipped';
        checkboxContent = '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3"><line x1="18" y1="6" x2="6" y2="18"></line><line x1="6" y1="6" x2="18" y2="18"></line></svg>';
    } else if (isInProgress) {
        checkboxClass += ' in_progress';
    }

    let metaInfo = '';
    if (item.auto_check_result) {
        const result = item.auto_check_result;
        metaInfo = `Auto-check: ${result.matched}/${result.total} (${result.percentage}%)`;
    }
    if (item.completed_at) {
        metaInfo += metaInfo ? ' | ' : '';
        metaInfo += `Completed: ${formatDateTime(item.completed_at)}`;
    }
    if (item.skip_reason) {
        metaInfo += metaInfo ? ' | ' : '';
        metaInfo += `Skipped: ${item.skip_reason}`;
    }

    let actions = '';
    if (canModify && !isCompleted && !isSkipped) {
        actions = `
            <div class="checklist-actions">
                <button class="btn btn-success btn-sm" onclick="completeItem('${item.id}')">Complete</button>
                <button class="btn btn-secondary btn-sm" onclick="showSkipModal('${item.id}', '${escapeHtml(item.name)}')">Skip</button>
            </div>
        `;
    }

    return `
        <div class="checklist-item" data-item-id="${item.id}">
            <div class="${checkboxClass}">${checkboxContent}</div>
            <div class="checklist-content">
                <div class="checklist-name">${item.name}${item.is_required ? ' <span style="color: #ef4444;">*</span>' : ''}</div>
                <div class="checklist-description">${item.description || ''}</div>
                ${metaInfo ? `<div class="checklist-meta">${metaInfo}</div>` : ''}
            </div>
            ${actions}
        </div>
    `;
}

async function completeItem(itemId) {
    try {
        const response = await fetch(`/api/close/checklist/${itemId}/complete`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });

        const data = await response.json();
        if (data.error) {
            showNotification(data.error, 'error');
            return;
        }

        showNotification('Item completed', 'success');
        loadChecklist();
    } catch (error) {
        console.error('Error completing item:', error);
        showNotification('Failed to complete item', 'error');
    }
}

function showSkipModal(itemId, itemName) {
    skipItemId = itemId;
    document.getElementById('skipItemName').textContent = `Skip: ${itemName}`;
    document.getElementById('skipReason').value = '';
    document.getElementById('skipModal').classList.add('active');
}

async function skipItem() {
    const reason = document.getElementById('skipReason').value.trim();
    if (!reason) {
        showNotification('Please provide a reason for skipping', 'error');
        return;
    }

    try {
        const response = await fetch(`/api/close/checklist/${skipItemId}/skip`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ reason })
        });

        const data = await response.json();
        if (data.error) {
            showNotification(data.error, 'error');
            return;
        }

        closeModal('skipModal');
        showNotification('Item skipped', 'success');
        loadChecklist();
    } catch (error) {
        console.error('Error skipping item:', error);
        showNotification('Failed to skip item', 'error');
    }
}

async function runAutoChecks() {
    showNotification('Running auto-checks... (Feature coming soon)', 'info');
    // TODO: Implement auto-checks API
}

// ========================================
// PERIOD WORKFLOW ACTIONS
// ========================================

async function startCloseProcess() {
    try {
        const response = await fetch(`/api/close/periods/${currentPeriodId}/start`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });

        const data = await response.json();
        if (data.error) {
            showNotification(data.error, 'error');
            return;
        }

        showNotification('Close process started', 'success');
        loadPeriod(currentPeriodId);
        loadPeriods(); // Refresh period list
    } catch (error) {
        console.error('Error starting close process:', error);
        showNotification('Failed to start close process', 'error');
    }
}

async function lockPeriod() {
    if (!confirm('Are you sure you want to lock this period? Transactions within this period will be protected from modifications.')) {
        return;
    }

    try {
        const response = await fetch(`/api/close/periods/${currentPeriodId}/lock`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });

        const data = await response.json();
        if (data.error) {
            showNotification(data.error, 'error');
            return;
        }

        showNotification('Period locked', 'success');
        loadPeriod(currentPeriodId);
        loadPeriods();
    } catch (error) {
        console.error('Error locking period:', error);
        showNotification('Failed to lock period', 'error');
    }
}

function showUnlockModal() {
    document.getElementById('unlockReason').value = '';
    document.getElementById('unlockModal').classList.add('active');
}

async function unlockPeriod() {
    const reason = document.getElementById('unlockReason').value.trim();
    if (!reason) {
        showNotification('Please provide a reason for unlocking', 'error');
        return;
    }

    try {
        const response = await fetch(`/api/close/periods/${currentPeriodId}/unlock`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ reason })
        });

        const data = await response.json();
        if (data.error) {
            showNotification(data.error, 'error');
            return;
        }

        closeModal('unlockModal');
        showNotification('Period unlocked', 'success');
        loadPeriod(currentPeriodId);
        loadPeriods();
    } catch (error) {
        console.error('Error unlocking period:', error);
        showNotification('Failed to unlock period', 'error');
    }
}

async function submitForApproval() {
    try {
        const response = await fetch(`/api/close/periods/${currentPeriodId}/submit`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });

        const data = await response.json();
        if (data.error) {
            showNotification(data.error, 'error');
            return;
        }

        showNotification('Submitted for approval', 'success');
        loadPeriod(currentPeriodId);
        loadPeriods();
    } catch (error) {
        console.error('Error submitting for approval:', error);
        showNotification('Failed to submit for approval', 'error');
    }
}

async function approvePeriod() {
    try {
        const response = await fetch(`/api/close/periods/${currentPeriodId}/approve`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });

        const data = await response.json();
        if (data.error) {
            showNotification(data.error, 'error');
            return;
        }

        showNotification('Period approved', 'success');
        loadPeriod(currentPeriodId);
        loadPeriods();
    } catch (error) {
        console.error('Error approving period:', error);
        showNotification('Failed to approve period', 'error');
    }
}

function showRejectModal() {
    document.getElementById('rejectReason').value = '';
    document.getElementById('rejectModal').classList.add('active');
}

async function rejectPeriod() {
    const reason = document.getElementById('rejectReason').value.trim();
    if (!reason) {
        showNotification('Please provide a reason for rejection', 'error');
        return;
    }

    try {
        const response = await fetch(`/api/close/periods/${currentPeriodId}/reject`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ reason })
        });

        const data = await response.json();
        if (data.error) {
            showNotification(data.error, 'error');
            return;
        }

        closeModal('rejectModal');
        showNotification('Period rejected', 'success');
        loadPeriod(currentPeriodId);
        loadPeriods();
    } catch (error) {
        console.error('Error rejecting period:', error);
        showNotification('Failed to reject period', 'error');
    }
}

async function closePeriod() {
    if (!confirm('Are you sure you want to close this period? This action cannot be undone.')) {
        return;
    }

    try {
        const response = await fetch(`/api/close/periods/${currentPeriodId}/close`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });

        const data = await response.json();
        if (data.error) {
            showNotification(data.error, 'error');
            return;
        }

        showNotification('Period closed successfully', 'success');
        loadPeriod(currentPeriodId);
        loadPeriods();
    } catch (error) {
        console.error('Error closing period:', error);
        showNotification('Failed to close period', 'error');
    }
}

// ========================================
// CREATE PERIOD
// ========================================

function showCreatePeriodModal() {
    // Set default dates to current month
    const now = new Date();
    const firstDay = new Date(now.getFullYear(), now.getMonth(), 1);
    const lastDay = new Date(now.getFullYear(), now.getMonth() + 1, 0);

    document.getElementById('periodName').value = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`;
    document.getElementById('periodType').value = 'monthly';
    document.getElementById('startDate').value = firstDay.toISOString().split('T')[0];
    document.getElementById('endDate').value = lastDay.toISOString().split('T')[0];
    document.getElementById('periodNotes').value = '';

    document.getElementById('createPeriodModal').classList.add('active');
}

async function createPeriod() {
    const periodName = document.getElementById('periodName').value.trim();
    const periodType = document.getElementById('periodType').value;
    const startDate = document.getElementById('startDate').value;
    const endDate = document.getElementById('endDate').value;
    const notes = document.getElementById('periodNotes').value.trim();

    if (!periodName || !startDate || !endDate) {
        showNotification('Please fill in all required fields', 'error');
        return;
    }

    try {
        const response = await fetch('/api/close/periods', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                period_name: periodName,
                period_type: periodType,
                start_date: startDate,
                end_date: endDate,
                notes: notes || null
            })
        });

        const data = await response.json();
        if (data.error) {
            showNotification(data.error, 'error');
            return;
        }

        closeModal('createPeriodModal');
        showNotification('Period created successfully', 'success');
        await loadPeriods();

        // Select the new period
        if (data.period && data.period.id) {
            document.getElementById('periodSelect').value = data.period.id;
            loadPeriod(data.period.id);
        }
    } catch (error) {
        console.error('Error creating period:', error);
        showNotification('Failed to create period', 'error');
    }
}

// ========================================
// ACTIVITY LOG
// ========================================

async function showActivityLog() {
    document.getElementById('activityModal').classList.add('active');
    const container = document.getElementById('activityLogContent');
    container.innerHTML = '<div class="loading"><div class="spinner"></div></div>';

    try {
        const response = await fetch(`/api/close/periods/${currentPeriodId}/activity-log?per_page=50`);
        const data = await response.json();

        if (data.error) {
            container.innerHTML = `<p>${data.error}</p>`;
            return;
        }

        if (data.activities.length === 0) {
            container.innerHTML = '<p style="text-align: center; color: #64748b;">No activity recorded yet.</p>';
            return;
        }

        container.innerHTML = data.activities.map(activity => `
            <div class="activity-item">
                <div class="activity-icon">${getActivityIcon(activity.action)}</div>
                <div class="activity-content">
                    <div class="activity-action">${formatAction(activity.action)}</div>
                    <div class="activity-time">${formatDateTime(activity.created_at)}</div>
                </div>
            </div>
        `).join('');

    } catch (error) {
        console.error('Error loading activity log:', error);
        container.innerHTML = '<p>Failed to load activity log</p>';
    }
}

// ========================================
// UTILITY FUNCTIONS
// ========================================

function closeModal(modalId) {
    document.getElementById(modalId).classList.remove('active');
}

function formatStatus(status) {
    const statusMap = {
        'open': 'Open',
        'in_progress': 'In Progress',
        'pending_approval': 'Pending Approval',
        'locked': 'Locked',
        'closed': 'Closed'
    };
    return statusMap[status] || status;
}

function formatCategory(category) {
    const categoryMap = {
        'bank_reconciliation': 'Bank Reconciliation',
        'revenue': 'Revenue',
        'expenses': 'Expenses',
        'payroll': 'Payroll',
        'adjustments': 'Adjustments',
        'review': 'Review & Approval'
    };
    return categoryMap[category] || category;
}

function formatDate(dateStr) {
    if (!dateStr) return '-';
    const date = new Date(dateStr);
    return date.toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric' });
}

function formatDateTime(dateStr) {
    if (!dateStr) return '-';
    const date = new Date(dateStr);
    return date.toLocaleString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    });
}

function formatAction(action) {
    const actionMap = {
        'period_created': 'Period created',
        'period_started': 'Close process started',
        'period_locked': 'Period locked',
        'period_unlocked': 'Period unlocked',
        'period_submitted': 'Submitted for approval',
        'period_approved': 'Period approved',
        'period_rejected': 'Period rejected',
        'period_closed': 'Period closed',
        'checklist_completed': 'Checklist item completed',
        'checklist_skipped': 'Checklist item skipped',
        'entry_created': 'Adjusting entry created',
        'entry_approved': 'Adjusting entry approved',
        'entry_posted': 'Adjusting entry posted'
    };
    return actionMap[action] || action;
}

function getActivityIcon(action) {
    if (action.includes('created')) return '+';
    if (action.includes('started')) return '>';
    if (action.includes('locked')) return 'L';
    if (action.includes('unlocked')) return 'U';
    if (action.includes('submitted')) return 'S';
    if (action.includes('approved')) return 'A';
    if (action.includes('rejected')) return 'R';
    if (action.includes('closed')) return 'X';
    if (action.includes('completed')) return 'C';
    if (action.includes('skipped')) return '-';
    return '*';
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function showNotification(message, type = 'info') {
    // Use existing notification system if available
    if (typeof window.showToast === 'function') {
        window.showToast(message, type);
        return;
    }

    // Fallback notification
    const notification = document.createElement('div');
    notification.className = `notification notification-${type}`;
    notification.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        padding: 1rem 1.5rem;
        border-radius: 8px;
        color: white;
        font-weight: 500;
        z-index: 10000;
        animation: slideIn 0.3s ease;
        background: ${type === 'error' ? '#ef4444' : type === 'success' ? '#10b981' : '#3b82f6'};
    `;
    notification.textContent = message;

    document.body.appendChild(notification);

    setTimeout(() => {
        notification.style.animation = 'slideOut 0.3s ease';
        setTimeout(() => notification.remove(), 300);
    }, 3000);
}

// Add CSS animation
const style = document.createElement('style');
style.textContent = `
    @keyframes slideIn {
        from { transform: translateX(100%); opacity: 0; }
        to { transform: translateX(0); opacity: 1; }
    }
    @keyframes slideOut {
        from { transform: translateX(0); opacity: 1; }
        to { transform: translateX(100%); opacity: 0; }
    }
`;
document.head.appendChild(style);
