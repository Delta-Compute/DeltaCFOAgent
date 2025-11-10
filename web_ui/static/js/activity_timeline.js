/**
 * Activity Timeline Component
 * Reusable component for displaying activity history in detail pages
 */

(function(window) {
    'use strict';

    const ActivityTimeline = {
        /**
         * Render activity timeline
         * @param {Array} activities - Array of activity objects
         * @param {string} containerId - ID of the container element
         */
        render: function(activities, containerId) {
            const container = document.getElementById(containerId);
            if (!container) {
                console.error(`Container ${containerId} not found`);
                return;
            }

            if (!activities || activities.length === 0) {
                container.innerHTML = this.renderEmptyState();
                return;
            }

            container.innerHTML = activities.map(activity => this.renderActivityItem(activity)).join('');
        },

        /**
         * Render a single activity item
         * @param {Object} activity - Activity object
         * @returns {string} HTML string
         */
        renderActivityItem: function(activity) {
            const actionType = this.getActionType(activity.action);
            const icon = this.getActionIcon(activity.action);
            const timeAgo = this.getTimeAgo(activity.created_at);

            return `
                <div class="activity-item ${activity.action}">
                    <div class="activity-dot"></div>
                    <div class="activity-content">
                        <div class="activity-header">
                            <span class="activity-action">${icon} ${this.formatActionText(activity)}</span>
                            <span class="activity-time">${timeAgo}</span>
                        </div>
                        ${this.renderActivityDetails(activity)}
                        ${activity.user_email ? `<div class="activity-user">by ${activity.user_email}</div>` : ''}
                    </div>
                </div>
            `;
        },

        /**
         * Format action text based on activity type
         * @param {Object} activity - Activity object
         * @returns {string} Formatted action text
         */
        formatActionText: function(activity) {
            const actionMap = {
                'created': 'Created',
                'updated': 'Updated',
                'viewed': 'Viewed',
                'matched': 'Matched',
                'unmatched': 'Unmatched',
                'status_changed': 'Status Changed',
                'deleted': 'Deleted',
                'approved': 'Approved',
                'rejected': 'Rejected',
                'sent': 'Sent',
                'paid': 'Marked as Paid'
            };

            return actionMap[activity.action] || activity.action;
        },

        /**
         * Render activity details
         * @param {Object} activity - Activity object
         * @returns {string} HTML string for details
         */
        renderActivityDetails: function(activity) {
            if (!activity.field_changed && !activity.old_value && !activity.new_value) {
                return '';
            }

            let details = '';

            if (activity.field_changed) {
                details += `<div class="activity-details">`;
                details += `<strong>${this.formatFieldName(activity.field_changed)}</strong> changed`;

                if (activity.old_value || activity.new_value) {
                    details += '<br>';
                    if (activity.old_value) {
                        details += `<span style="color: #dc2626; text-decoration: line-through;">${activity.old_value}</span>`;
                    }
                    if (activity.old_value && activity.new_value) {
                        details += ' → ';
                    }
                    if (activity.new_value) {
                        details += `<span style="color: #059669; font-weight: 600;">${activity.new_value}</span>`;
                    }
                }

                details += `</div>`;
            }

            return details;
        },

        /**
         * Format field name for display
         * @param {string} fieldName - Database field name
         * @returns {string} Formatted field name
         */
        formatFieldName: function(fieldName) {
            if (!fieldName) return '';

            // Convert snake_case to Title Case
            return fieldName
                .split('_')
                .map(word => word.charAt(0).toUpperCase() + word.slice(1))
                .join(' ');
        },

        /**
         * Get action type for styling
         * @param {string} action - Action name
         * @returns {string} Action type
         */
        getActionType: function(action) {
            const typeMap = {
                'created': 'create',
                'updated': 'update',
                'viewed': 'view',
                'matched': 'match',
                'unmatched': 'match',
                'status_changed': 'status',
                'deleted': 'delete',
                'approved': 'approve',
                'rejected': 'reject',
                'sent': 'send',
                'paid': 'payment'
            };

            return typeMap[action] || 'other';
        },

        /**
         * Get icon for action type
         * @param {string} action - Action name
         * @returns {string} Icon HTML
         */
        getActionIcon: function(action) {
            const iconMap = {
                'created': '➕',
                'updated': '✏️',
                'viewed': '👁️',
                'matched': '🔗',
                'unmatched': '🔓',
                'status_changed': '🔄',
                'deleted': '🗑️',
                'approved': '✅',
                'rejected': '❌',
                'sent': '📤',
                'paid': '💰'
            };

            return iconMap[action] || '•';
        },

        /**
         * Get relative time (time ago)
         * @param {string} dateString - ISO date string
         * @returns {string} Relative time string
         */
        getTimeAgo: function(dateString) {
            if (!dateString) return 'Unknown';

            const date = new Date(dateString);
            const now = new Date();
            const seconds = Math.floor((now - date) / 1000);

            if (seconds < 60) return 'Just now';

            const minutes = Math.floor(seconds / 60);
            if (minutes < 60) return `${minutes} minute${minutes > 1 ? 's' : ''} ago`;

            const hours = Math.floor(minutes / 60);
            if (hours < 24) return `${hours} hour${hours > 1 ? 's' : ''} ago`;

            const days = Math.floor(hours / 24);
            if (days < 7) return `${days} day${days > 1 ? 's' : ''} ago`;

            const weeks = Math.floor(days / 7);
            if (weeks < 4) return `${weeks} week${weeks > 1 ? 's' : ''} ago`;

            const months = Math.floor(days / 30);
            if (months < 12) return `${months} month${months > 1 ? 's' : ''} ago`;

            const years = Math.floor(days / 365);
            return `${years} year${years > 1 ? 's' : ''} ago`;
        },

        /**
         * Render empty state when no activities
         * @returns {string} HTML string
         */
        renderEmptyState: function() {
            return `
                <div class="empty-state">
                    <div class="empty-state-icon">📋</div>
                    <div class="empty-state-text">No Activity Yet</div>
                    <div class="empty-state-hint">Activity history will appear here</div>
                </div>
            `;
        },

        /**
         * Filter activities by type
         * @param {Array} activities - Array of activities
         * @param {string} actionType - Action type to filter by
         * @returns {Array} Filtered activities
         */
        filterByType: function(activities, actionType) {
            if (!actionType || actionType === 'all') return activities;
            return activities.filter(activity => activity.action === actionType);
        },

        /**
         * Group activities by date
         * @param {Array} activities - Array of activities
         * @returns {Object} Activities grouped by date
         */
        groupByDate: function(activities) {
            const groups = {};

            activities.forEach(activity => {
                const date = new Date(activity.created_at);
                const dateKey = date.toLocaleDateString('en-US', {
                    year: 'numeric',
                    month: 'long',
                    day: 'numeric'
                });

                if (!groups[dateKey]) {
                    groups[dateKey] = [];
                }

                groups[dateKey].push(activity);
            });

            return groups;
        },

        /**
         * Render grouped activities (by date)
         * @param {Array} activities - Array of activities
         * @param {string} containerId - Container element ID
         */
        renderGrouped: function(activities, containerId) {
            const container = document.getElementById(containerId);
            if (!container) {
                console.error(`Container ${containerId} not found`);
                return;
            }

            if (!activities || activities.length === 0) {
                container.innerHTML = this.renderEmptyState();
                return;
            }

            const grouped = this.groupByDate(activities);
            let html = '';

            Object.keys(grouped).forEach(dateKey => {
                html += `
                    <div class="activity-date-group">
                        <div class="activity-date-header">${dateKey}</div>
                        <div class="activity-timeline">
                            ${grouped[dateKey].map(activity => this.renderActivityItem(activity)).join('')}
                        </div>
                    </div>
                `;
            });

            container.innerHTML = html;
        },

        /**
         * Export activities as CSV
         * @param {Array} activities - Array of activities
         * @param {string} filename - Output filename
         */
        exportToCSV: function(activities, filename = 'activity_log.csv') {
            if (!activities || activities.length === 0) {
                alert('No activities to export');
                return;
            }

            const headers = ['Date', 'Action', 'Field Changed', 'Old Value', 'New Value', 'User'];
            const rows = activities.map(activity => [
                new Date(activity.created_at).toLocaleString(),
                this.formatActionText(activity),
                this.formatFieldName(activity.field_changed) || '',
                activity.old_value || '',
                activity.new_value || '',
                activity.user_email || ''
            ]);

            let csvContent = headers.join(',') + '\n';
            rows.forEach(row => {
                csvContent += row.map(cell => `"${cell}"`).join(',') + '\n';
            });

            const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
            const link = document.createElement('a');
            const url = URL.createObjectURL(blob);

            link.setAttribute('href', url);
            link.setAttribute('download', filename);
            link.style.visibility = 'hidden';

            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
        }
    };

    // Expose to global scope
    window.ActivityTimeline = ActivityTimeline;

})(window);
