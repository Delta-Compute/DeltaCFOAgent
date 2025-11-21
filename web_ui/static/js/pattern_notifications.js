/**
 * Pattern Notifications System
 *
 * Polls the server for new pattern suggestions that have been validated by Claude LLM
 * and displays toast notifications when patterns are approved.
 */

class PatternNotificationManager {
    constructor(options = {}) {
        this.pollInterval = options.pollInterval || 10000; // 10 seconds default
        this.pollTimer = null;
        this.isPolling = false;
        this.seenNotifications = new Set();
        this.toastContainer = null;

        this.init();
    }

    /**
     * Initialize the notification manager
     */
    init() {
        this.createToastContainer();
        this.loadSeenNotifications();
        this.startPolling();

        // Listen for visibility changes to pause/resume polling
        document.addEventListener('visibilitychange', () => {
            if (document.hidden) {
                this.stopPolling();
            } else {
                this.startPolling();
            }
        });
    }

    /**
     * Create the toast container element
     */
    createToastContainer() {
        this.toastContainer = document.createElement('div');
        this.toastContainer.id = 'pattern-toast-container';
        this.toastContainer.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            z-index: 10000;
            max-width: 400px;
        `;
        document.body.appendChild(this.toastContainer);
    }

    /**
     * Load seen notifications from localStorage
     */
    loadSeenNotifications() {
        try {
            const seen = localStorage.getItem('seenPatternNotifications');
            if (seen) {
                this.seenNotifications = new Set(JSON.parse(seen));
            }
        } catch (error) {
            console.error('Error loading seen notifications:', error);
        }
    }

    /**
     * Save seen notifications to localStorage
     */
    saveSeenNotifications() {
        try {
            localStorage.setItem('seenPatternNotifications',
                JSON.stringify([...this.seenNotifications]));
        } catch (error) {
            console.error('Error saving seen notifications:', error);
        }
    }

    /**
     * Start polling for new notifications
     */
    startPolling() {
        if (this.isPolling) return;

        this.isPolling = true;
        this.poll(); // Initial poll

        this.pollTimer = setInterval(() => {
            this.poll();
        }, this.pollInterval);
    }

    /**
     * Stop polling
     */
    stopPolling() {
        if (this.pollTimer) {
            clearInterval(this.pollTimer);
            this.pollTimer = null;
        }
        this.isPolling = false;
    }

    /**
     * Poll the server for new notifications
     */
    async poll() {
        try {
            const response = await fetch('/api/pattern-notifications?unread_only=true&limit=10');

            if (!response.ok) {
                console.error('Failed to fetch notifications:', response.status);
                return;
            }

            const data = await response.json();

            if (data.success && data.notifications && data.notifications.length > 0) {
                // Show new notifications
                data.notifications.forEach(notification => {
                    if (!this.seenNotifications.has(notification.id)) {
                        this.showToast(notification);
                        this.seenNotifications.add(notification.id);
                    }
                });

                this.saveSeenNotifications();
            }
        } catch (error) {
            console.error('Error polling for notifications:', error);
        }
    }

    /**
     * Show a toast notification
     */
    showToast(notification) {
        const toast = document.createElement('div');
        toast.className = 'pattern-toast';
        toast.style.cssText = `
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 16px 20px;
            border-radius: 12px;
            margin-bottom: 12px;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
            animation: slideIn 0.3s ease-out;
            cursor: pointer;
            position: relative;
            overflow: hidden;
        `;

        // Priority indicator
        const priorityColor = notification.priority === 'high' ? '#fbbf24' :
                             notification.priority === 'medium' ? '#60a5fa' : '#9ca3af';

        toast.innerHTML = `
            <div style="display: flex; align-items: start; gap: 12px;">
                <div style="flex-shrink: 0; font-size: 24px;">
                    ${notification.notification_type === 'pattern_approved' ? '✓' :
                      notification.notification_type === 'pattern_rejected' ? '✗' : 'ℹ'}
                </div>
                <div style="flex: 1; min-width: 0;">
                    <div style="font-weight: 600; font-size: 14px; margin-bottom: 4px;">
                        ${this.escapeHtml(notification.title)}
                    </div>
                    <div style="font-size: 13px; opacity: 0.95; line-height: 1.4;">
                        ${this.escapeHtml(notification.message)}
                    </div>
                    ${notification.pattern ? `
                        <div style="margin-top: 8px; padding-top: 8px; border-top: 1px solid rgba(255,255,255,0.2); font-size: 12px; opacity: 0.85;">
                            <div><strong>Pattern:</strong> ${this.escapeHtml(notification.pattern.description || 'N/A')}</div>
                            ${notification.pattern.entity ? `<div><strong>Entity:</strong> ${this.escapeHtml(notification.pattern.entity)}</div>` : ''}
                            ${notification.pattern.category ? `<div><strong>Category:</strong> ${this.escapeHtml(notification.pattern.category)}</div>` : ''}
                        </div>
                    ` : ''}
                </div>
                <button class="toast-close" style="
                    background: rgba(255,255,255,0.2);
                    border: none;
                    color: white;
                    width: 24px;
                    height: 24px;
                    border-radius: 50%;
                    cursor: pointer;
                    font-size: 16px;
                    line-height: 1;
                    flex-shrink: 0;
                    transition: background 0.2s;
                " onmouseover="this.style.background='rgba(255,255,255,0.3)'"
                   onmouseout="this.style.background='rgba(255,255,255,0.2)'">×</button>
            </div>
            <div style="position: absolute; left: 0; top: 0; width: 4px; height: 100%; background: ${priorityColor};"></div>
        `;

        // Add animation keyframes if not already added
        if (!document.getElementById('pattern-toast-styles')) {
            const style = document.createElement('style');
            style.id = 'pattern-toast-styles';
            style.textContent = `
                @keyframes slideIn {
                    from {
                        transform: translateX(420px);
                        opacity: 0;
                    }
                    to {
                        transform: translateX(0);
                        opacity: 1;
                    }
                }
                @keyframes slideOut {
                    from {
                        transform: translateX(0);
                        opacity: 1;
                    }
                    to {
                        transform: translateX(420px);
                        opacity: 0;
                    }
                }
            `;
            document.head.appendChild(style);
        }

        // Close button handler
        const closeBtn = toast.querySelector('.toast-close');
        closeBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            this.hideToast(toast, notification.id);
        });

        // Click to view details (optional - could link to patterns page)
        toast.addEventListener('click', () => {
            // Mark as read
            this.markAsRead(notification.id);
            // Could navigate to pattern details page here
            console.log('Toast clicked:', notification);
        });

        // Add to container
        this.toastContainer.appendChild(toast);

        // Auto-hide after 8 seconds
        setTimeout(() => {
            if (toast.parentElement) {
                this.hideToast(toast, notification.id);
            }
        }, 8000);
    }

    /**
     * Hide a toast notification
     */
    hideToast(toast, notificationId) {
        toast.style.animation = 'slideOut 0.3s ease-in';

        setTimeout(() => {
            if (toast.parentElement) {
                toast.remove();
            }
        }, 300);

        // Mark as read on the server
        this.markAsRead(notificationId);
    }

    /**
     * Mark a notification as read on the server
     */
    async markAsRead(notificationId) {
        try {
            await fetch(`/api/pattern-notifications/${notificationId}/mark-read`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                }
            });
        } catch (error) {
            console.error('Error marking notification as read:', error);
        }
    }

    /**
     * Escape HTML to prevent XSS
     */
    escapeHtml(text) {
        if (!text) return '';
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    /**
     * Manually check for new notifications (for testing)
     */
    checkNow() {
        this.poll();
    }

    /**
     * Clear all seen notifications (for testing)
     */
    clearSeen() {
        this.seenNotifications.clear();
        this.saveSeenNotifications();
        console.log('Cleared all seen notifications');
    }

    /**
     * Destroy the notification manager
     */
    destroy() {
        this.stopPolling();
        if (this.toastContainer && this.toastContainer.parentElement) {
            this.toastContainer.remove();
        }
    }
}

// Initialize the notification manager when DOM is ready
let patternNotificationManager = null;

document.addEventListener('DOMContentLoaded', () => {
    // Initialize with default settings
    patternNotificationManager = new PatternNotificationManager({
        pollInterval: 10000 // Poll every 10 seconds
    });

    // Expose to window for debugging
    window.patternNotificationManager = patternNotificationManager;

    console.log('Pattern notification manager initialized');
});
