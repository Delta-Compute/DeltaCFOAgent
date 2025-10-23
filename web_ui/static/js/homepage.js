/**
 * Homepage Dynamic Content and AI Regeneration
 * Handles loading AI-generated content and KPI animations
 */

class HomepageManager {
    constructor() {
        this.content = null;
        this.kpis = null;
        this.isLoading = false;
        this.isRegenerating = false;
    }

    async init() {
        console.log('Initializing homepage...');
        await this.loadContent();
        this.attachEventListeners();
    }

    async loadContent(useCache = true) {
        try {
            this.isLoading = true;
            this.showLoading();

            const url = `/api/homepage/content?use_cache=${useCache}`;
            const response = await fetch(url);
            const result = await response.json();

            if (result.success && result.content) {
                this.content = result.content;
                this.renderContent();
                this.animateKPIs();

                if (result.cached) {
                    console.log('Loaded cached content');
                    this.showCacheStatus(true);
                } else {
                    console.log('Loaded fresh AI-generated content');
                    this.showCacheStatus(false);
                }
            } else {
                throw new Error(result.error || 'Failed to load content');
            }

        } catch (error) {
            console.error('Error loading homepage content:', error);
            this.showError(`Failed to load content: ${error.message}`);
        } finally {
            this.isLoading = false;
            this.hideLoading();
        }
    }

    async regenerateContent() {
        if (this.isRegenerating) {
            console.log('Already regenerating...');
            return;
        }

        if (!confirm('Regenerate homepage content with Claude AI?\n\nThis will analyze all your financial data and create new personalized content. This may take 10-30 seconds.')) {
            return;
        }

        try {
            this.isRegenerating = true;
            this.showRegeneratingStatus();

            const response = await fetch('/api/homepage/regenerate', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                }
            });

            const result = await response.json();

            if (result.success && result.content) {
                this.content = result.content;
                this.renderContent();
                this.animateKPIs();
                this.showSuccess('Content regenerated successfully!');
            } else {
                throw new Error(result.error || 'Failed to regenerate content');
            }

        } catch (error) {
            console.error('Error regenerating content:', error);
            this.showError(`Failed to regenerate: ${error.message}`);
        } finally {
            this.isRegenerating = false;
            this.hideRegeneratingStatus();
        }
    }

    renderContent() {
        if (!this.content) return;

        // Update company name
        const titleElement = document.getElementById('companyTitle');
        if (titleElement && this.content.company_name) {
            titleElement.textContent = this.content.company_name;
        }

        // Update tagline
        const taglineElement = document.getElementById('companyTagline');
        if (taglineElement && this.content.tagline) {
            taglineElement.textContent = this.content.tagline;
        }

        // Update description
        const descElement = document.getElementById('companyDescription');
        if (descElement && this.content.description) {
            descElement.textContent = this.content.description;
        }

        // Update KPI highlights in metrics section
        if (this.content.kpi_highlights && this.content.kpi_highlights.length > 0) {
            this.renderKPIHighlights(this.content.kpi_highlights);
        } else if (this.content.kpis) {
            // Fallback to basic KPIs
            this.renderBasicKPIs(this.content.kpis);
        }

        // Update AI insights
        if (this.content.ai_insights) {
            this.renderInsights(this.content.ai_insights);
        }

        // Update generated timestamp
        const timestampElement = document.getElementById('generatedTimestamp');
        if (timestampElement && this.content.generated_at) {
            const date = new Date(this.content.generated_at);
            timestampElement.textContent = `Last updated: ${date.toLocaleString()}`;
        }
    }

    renderKPIHighlights(highlights) {
        const container = document.getElementById('kpiMetricsGrid');
        if (!container) return;

        container.innerHTML = highlights.map(kpi => `
            <div class="metric-card">
                <div class="metric-number" data-target="${this.parseNumber(kpi.value)}">${kpi.icon || '📊'} 0</div>
                <div class="metric-title">${kpi.label}</div>
            </div>
        `).join('');
    }

    renderBasicKPIs(kpis) {
        const highlights = [
            { label: 'Transactions Processed', value: kpis.total_transactions || 0, icon: '📊' },
            { label: 'Revenue Generated', value: `$${this.formatNumber(kpis.total_revenue || 0)}`, icon: '💰' },
            { label: 'Years of Data', value: kpis.years_of_data || 0, icon: '📅' },
            { label: 'Active Entities', value: kpis.top_entities?.length || 0, icon: '🏢' }
        ];

        this.renderKPIHighlights(highlights);
    }

    renderInsights(insights) {
        const container = document.getElementById('aiInsights');
        if (!container) return;

        if (insights.length === 0) {
            container.innerHTML = '<p style="color: #94a3b8;">No insights available yet.</p>';
            return;
        }

        container.innerHTML = `
            <h3 style="color: #1e293b; margin-bottom: 1rem; font-size: 1.2rem;">💡 AI Insights</h3>
            <ul style="list-style: none; padding: 0; margin: 0;">
                ${insights.map(insight => `
                    <li style="padding: 0.5rem 0; padding-left: 1.5rem; position: relative; color: #475569;">
                        <span style="position: absolute; left: 0; color: #3b82f6;">•</span>
                        ${insight}
                    </li>
                `).join('')}
            </ul>
        `;
    }

    animateKPIs() {
        const metricNumbers = document.querySelectorAll('.metric-number[data-target]');

        metricNumbers.forEach(element => {
            const target = parseFloat(element.dataset.target) || 0;
            const icon = element.textContent.trim().split(' ')[0]; // Extract emoji if present
            const duration = 2000; // 2 seconds
            const steps = 60;
            const increment = target / steps;
            const stepDuration = duration / steps;
            let current = 0;

            const timer = setInterval(() => {
                current += increment;
                if (current >= target) {
                    current = target;
                    clearInterval(timer);
                }
                element.textContent = `${icon} ${this.formatAnimatedNumber(current, target)}`;
            }, stepDuration);
        });
    }

    formatAnimatedNumber(current, target) {
        // Format based on the target value type
        if (target >= 1000000) {
            return `${(current / 1000000).toFixed(1)}M`;
        } else if (target >= 1000) {
            return `${(current / 1000).toFixed(1)}K`;
        } else if (target % 1 !== 0) {
            return current.toFixed(1);
        } else {
            return Math.round(current).toString();
        }
    }

    parseNumber(value) {
        // Parse formatted numbers like "$1,234" or "1.5K" or "2.4M"
        if (typeof value === 'number') return value;

        const str = value.toString().replace(/[$,]/g, '');

        if (str.includes('M')) {
            return parseFloat(str) * 1000000;
        } else if (str.includes('K')) {
            return parseFloat(str) * 1000;
        }

        return parseFloat(str) || 0;
    }

    formatNumber(num) {
        if (num >= 1000000) {
            return (num / 1000000).toFixed(1) + 'M';
        } else if (num >= 1000) {
            return (num / 1000).toFixed(1) + 'K';
        }
        return num.toLocaleString();
    }

    attachEventListeners() {
        const regenerateBtn = document.getElementById('regenerateBtn');
        if (regenerateBtn) {
            regenerateBtn.addEventListener('click', () => this.regenerateContent());
        }

        const refreshBtn = document.getElementById('refreshBtn');
        if (refreshBtn) {
            refreshBtn.addEventListener('click', () => this.loadContent(false));
        }
    }

    showLoading() {
        const loadingEl = document.getElementById('loadingIndicator');
        if (loadingEl) {
            loadingEl.style.display = 'block';
        }
    }

    hideLoading() {
        const loadingEl = document.getElementById('loadingIndicator');
        if (loadingEl) {
            loadingEl.style.display = 'none';
        }
    }

    showRegeneratingStatus() {
        const btn = document.getElementById('regenerateBtn');
        if (btn) {
            btn.disabled = true;
            btn.innerHTML = '🔄 Regenerating... (this may take 30 seconds)';
            btn.style.opacity = '0.6';
        }
    }

    hideRegeneratingStatus() {
        const btn = document.getElementById('regenerateBtn');
        if (btn) {
            btn.disabled = false;
            btn.innerHTML = '🔄 Regenerate with AI';
            btn.style.opacity = '1';
        }
    }

    showCacheStatus(isCached) {
        const statusEl = document.getElementById('cacheStatus');
        if (statusEl) {
            if (isCached) {
                statusEl.innerHTML = '💾 Cached content (less than 24 hours old)';
                statusEl.style.color = '#10b981';
            } else {
                statusEl.innerHTML = '✨ Fresh AI-generated content';
                statusEl.style.color = '#3b82f6';
            }
            statusEl.style.display = 'block';
        }
    }

    showSuccess(message) {
        this.showNotification(message, 'success');
    }

    showError(message) {
        this.showNotification(message, 'error');
    }

    showNotification(message, type = 'info') {
        // Create notification element
        const notification = document.createElement('div');
        notification.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            padding: 1rem 1.5rem;
            border-radius: 8px;
            color: white;
            font-weight: 600;
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
            z-index: 10000;
            animation: slideIn 0.3s ease-out;
        `;

        if (type === 'success') {
            notification.style.background = 'linear-gradient(135deg, #10b981, #059669)';
            notification.textContent = '✅ ' + message;
        } else if (type === 'error') {
            notification.style.background = 'linear-gradient(135deg, #ef4444, #dc2626)';
            notification.textContent = '❌ ' + message;
        } else {
            notification.style.background = 'linear-gradient(135deg, #3b82f6, #1d4ed8)';
            notification.textContent = 'ℹ️ ' + message;
        }

        document.body.appendChild(notification);

        // Auto-remove after 5 seconds
        setTimeout(() => {
            notification.style.animation = 'slideOut 0.3s ease-out';
            setTimeout(() => notification.remove(), 300);
        }, 5000);
    }
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    window.homepageManager = new HomepageManager();
    window.homepageManager.init();
});

// Add CSS animations
const style = document.createElement('style');
style.textContent = `
    @keyframes slideIn {
        from {
            transform: translateX(400px);
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
            transform: translateX(400px);
            opacity: 0;
        }
    }

    .metric-number {
        transition: all 0.3s ease;
    }

    #regenerateBtn:hover:not(:disabled) {
        transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba(59, 130, 246, 0.4);
    }

    #regenerateBtn:disabled {
        cursor: not-allowed;
    }
`;
document.head.appendChild(style);
