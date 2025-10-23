/**
 * White Listed Accounts Management
 * Handles both Bank Accounts and Crypto Wallets
 */

class AccountsManager {
    constructor() {
        this.bankAccounts = [];
        this.wallets = [];
        this.editingBankAccount = null;
        this.editingWallet = null;
    }

    async init() {
        console.log('Initializing accounts manager...');
        this.attachEventListeners();
        await this.loadBankAccounts();
        await this.loadWallets();
    }

    attachEventListeners() {
        // Tab switching
        document.querySelectorAll('.tab-button').forEach(button => {
            button.addEventListener('click', (e) => this.switchTab(e.target.dataset.tab));
        });

        // Add buttons
        document.getElementById('addBankAccountBtn').addEventListener('click', () => this.openBankModal());
        document.getElementById('addWalletBtn').addEventListener('click', () => this.openWalletModal());

        // Form submissions
        document.getElementById('bankAccountForm').addEventListener('submit', (e) => this.saveBankAccount(e));
        document.getElementById('walletForm').addEventListener('submit', (e) => this.saveWallet(e));

        // Modal close on background click
        document.getElementById('bankAccountModal').addEventListener('click', (e) => {
            if (e.target.id === 'bankAccountModal') closeBankModal();
        });
        document.getElementById('walletModal').addEventListener('click', (e) => {
            if (e.target.id === 'walletModal') closeWalletModal();
        });
    }

    switchTab(tabName) {
        // Update tab buttons
        document.querySelectorAll('.tab-button').forEach(btn => {
            btn.classList.remove('active');
        });
        document.querySelector(`[data-tab="${tabName}"]`).classList.add('active');

        // Update tab content
        document.querySelectorAll('.tab-content').forEach(content => {
            content.classList.remove('active');
        });
        document.getElementById(tabName).classList.add('active');
    }

    // ========================================
    // BANK ACCOUNTS CRUD
    // ========================================

    async loadBankAccounts() {
        try {
            const response = await fetch('/api/bank-accounts');
            const result = await response.json();

            if (result.success && result.accounts) {
                this.bankAccounts = result.accounts;
                this.renderBankAccounts();
            } else {
                throw new Error(result.error || 'Failed to load bank accounts');
            }
        } catch (error) {
            console.error('Error loading bank accounts:', error);
            document.getElementById('bankAccountsList').innerHTML = `
                <div class="empty-state">
                    <div class="empty-state-icon">⚠️</div>
                    <p>Error loading bank accounts: ${error.message}</p>
                </div>
            `;
        }
    }

    renderBankAccounts() {
        const container = document.getElementById('bankAccountsList');

        if (this.bankAccounts.length === 0) {
            container.innerHTML = `
                <div class="empty-state">
                    <div class="empty-state-icon">🏦</div>
                    <h3>No Bank Accounts Yet</h3>
                    <p>Click "Add Bank Account" to get started</p>
                </div>
            `;
            return;
        }

        container.innerHTML = this.bankAccounts.map(account => `
            <div class="account-card" style="border-left-color: ${this.getBankAccountColor(account.account_type)};">
                <div class="account-header">
                    <div>
                        <div class="account-name">
                            ${account.account_name}
                            ${account.is_primary ? '<span class="primary-badge">PRIMARY</span>' : ''}
                        </div>
                        <div style="color: #64748b; margin-top: 0.25rem;">
                            ${account.institution_name}
                            <span class="account-type-badge" style="background: ${this.getBankAccountColor(account.account_type)}; color: white;">
                                ${account.account_type}
                            </span>
                        </div>
                    </div>
                    <div class="button-group">
                        <button class="btn btn-edit" onclick="accountsManager.editBankAccount('${account.id}')">
                            ✏️ Edit
                        </button>
                        <button class="btn btn-delete" onclick="accountsManager.deleteBankAccount('${account.id}')">
                            🗑️ Delete
                        </button>
                    </div>
                </div>

                <div class="account-details">
                    ${account.account_number ? `
                        <div class="detail-item">
                            <div class="detail-label">Account Number</div>
                            <div class="detail-value">${account.account_number}</div>
                        </div>
                    ` : ''}
                    ${account.routing_number ? `
                        <div class="detail-item">
                            <div class="detail-label">Routing Number</div>
                            <div class="detail-value">${account.routing_number}</div>
                        </div>
                    ` : ''}
                    <div class="detail-item">
                        <div class="detail-label">Currency</div>
                        <div class="detail-value">${account.currency || 'USD'}</div>
                    </div>
                    ${account.current_balance !== null ? `
                        <div class="detail-item">
                            <div class="detail-label">Current Balance</div>
                            <div class="detail-value">${this.formatCurrency(account.current_balance, account.currency)}</div>
                        </div>
                    ` : ''}
                    <div class="detail-item">
                        <div class="detail-label">Status</div>
                        <div class="detail-value" style="color: ${this.getStatusColor(account.status)};">
                            ${account.status.toUpperCase()}
                        </div>
                    </div>
                    <div class="detail-item">
                        <div class="detail-label">Added</div>
                        <div class="detail-value">${new Date(account.created_at).toLocaleDateString()}</div>
                    </div>
                </div>

                ${account.notes ? `
                    <div style="margin-top: 1rem; padding: 1rem; background: #f8fafc; border-radius: 6px;">
                        <div class="detail-label">Notes</div>
                        <p style="margin: 0.5rem 0 0 0; color: #475569;">${account.notes}</p>
                    </div>
                ` : ''}
            </div>
        `).join('');
    }

    openBankModal(account = null) {
        this.editingBankAccount = account;

        if (account) {
            document.getElementById('bankModalTitle').textContent = 'Edit Bank Account';
            document.getElementById('bankAccountId').value = account.id;
            document.getElementById('bankAccountName').value = account.account_name;
            document.getElementById('bankInstitution').value = account.institution_name;
            document.getElementById('bankAccountNumber').value = account.account_number || '';
            document.getElementById('bankRoutingNumber').value = account.routing_number || '';
            document.getElementById('bankAccountType').value = account.account_type;
            document.getElementById('bankCurrency').value = account.currency || 'USD';
            document.getElementById('bankCurrentBalance').value = account.current_balance || '';
            document.getElementById('bankIsPrimary').checked = account.is_primary;
            document.getElementById('bankNotes').value = account.notes || '';
        } else {
            document.getElementById('bankModalTitle').textContent = 'Add Bank Account';
            document.getElementById('bankAccountForm').reset();
            document.getElementById('bankAccountId').value = '';
        }

        document.getElementById('bankAccountModal').classList.add('active');
    }

    async saveBankAccount(e) {
        e.preventDefault();

        const accountId = document.getElementById('bankAccountId').value;
        const isEdit = !!accountId;

        const data = {
            account_name: document.getElementById('bankAccountName').value.trim(),
            institution_name: document.getElementById('bankInstitution').value.trim(),
            account_number: document.getElementById('bankAccountNumber').value.trim(),
            routing_number: document.getElementById('bankRoutingNumber').value.trim(),
            account_type: document.getElementById('bankAccountType').value,
            currency: document.getElementById('bankCurrency').value,
            current_balance: document.getElementById('bankCurrentBalance').value ? parseFloat(document.getElementById('bankCurrentBalance').value) : null,
            is_primary: document.getElementById('bankIsPrimary').checked,
            notes: document.getElementById('bankNotes').value.trim()
        };

        try {
            const url = isEdit ? `/api/bank-accounts/${accountId}` : '/api/bank-accounts';
            const method = isEdit ? 'PUT' : 'POST';

            const response = await fetch(url, {
                method,
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(data)
            });

            const result = await response.json();

            if (response.ok && result.success) {
                this.showNotification(`Bank account ${isEdit ? 'updated' : 'added'} successfully!`, 'success');
                closeBankModal();
                await this.loadBankAccounts();
            } else {
                throw new Error(result.error || 'Failed to save bank account');
            }
        } catch (error) {
            console.error('Error saving bank account:', error);
            this.showNotification(`Error: ${error.message}`, 'error');
        }
    }

    editBankAccount(accountId) {
        const account = this.bankAccounts.find(a => a.id === accountId);
        if (account) {
            this.openBankModal(account);
        }
    }

    async deleteBankAccount(accountId) {
        const account = this.bankAccounts.find(a => a.id === accountId);
        if (!account) return;

        if (!confirm(`Are you sure you want to close the account "${account.account_name}"?\n\nThis will mark it as closed but preserve the record.`)) {
            return;
        }

        try {
            const response = await fetch(`/api/bank-accounts/${accountId}`, {
                method: 'DELETE'
            });

            const result = await response.json();

            if (response.ok && result.success) {
                this.showNotification('Bank account closed successfully!', 'success');
                await this.loadBankAccounts();
            } else {
                throw new Error(result.error || 'Failed to close bank account');
            }
        } catch (error) {
            console.error('Error deleting bank account:', error);
            this.showNotification(`Error: ${error.message}`, 'error');
        }
    }

    // ========================================
    // CRYPTO WALLETS CRUD
    // ========================================

    async loadWallets() {
        try {
            const response = await fetch('/api/wallets');
            const result = await response.json();

            if (result.success && result.wallets) {
                this.wallets = result.wallets;
                this.renderWallets();
            } else {
                throw new Error(result.error || 'Failed to load wallets');
            }
        } catch (error) {
            console.error('Error loading wallets:', error);
            document.getElementById('walletsList').innerHTML = `
                <div class="empty-state">
                    <div class="empty-state-icon">⚠️</div>
                    <p>Error loading wallets: ${error.message}</p>
                </div>
            `;
        }
    }

    renderWallets() {
        const container = document.getElementById('walletsList');

        if (this.wallets.length === 0) {
            container.innerHTML = `
                <div class="empty-state">
                    <div class="empty-state-icon">₿</div>
                    <h3>No Crypto Wallets Yet</h3>
                    <p>Click "Add Crypto Wallet" to get started</p>
                </div>
            `;
            return;
        }

        container.innerHTML = this.wallets.map(wallet => `
            <div class="account-card" style="border-left-color: ${this.getWalletTypeColor(wallet.wallet_type)};">
                <div class="account-header">
                    <div>
                        <div class="account-name">
                            ${wallet.entity_name}
                        </div>
                        <div style="color: #64748b; margin-top: 0.25rem;">
                            <span class="account-type-badge" style="background: ${this.getWalletTypeColor(wallet.wallet_type)}; color: white;">
                                ${wallet.wallet_type}
                            </span>
                            ${wallet.blockchain ? `<span style="margin-left: 0.5rem; font-size: 0.9rem;">📡 ${wallet.blockchain}</span>` : ''}
                        </div>
                    </div>
                    <div class="button-group">
                        <button class="btn btn-edit" onclick="accountsManager.editWallet('${wallet.id}')">
                            ✏️ Edit
                        </button>
                        <button class="btn btn-delete" onclick="accountsManager.deleteWallet('${wallet.id}')">
                            🗑️ Delete
                        </button>
                    </div>
                </div>

                <div class="account-details">
                    <div class="detail-item" style="grid-column: 1 / -1;">
                        <div class="detail-label">Wallet Address</div>
                        <div class="detail-value" style="word-break: break-all; color: #3b82f6;">
                            ${wallet.wallet_address}
                        </div>
                    </div>
                    ${wallet.purpose ? `
                        <div class="detail-item">
                            <div class="detail-label">Purpose</div>
                            <div class="detail-value">${wallet.purpose}</div>
                        </div>
                    ` : ''}
                    <div class="detail-item">
                        <div class="detail-label">Confidence</div>
                        <div class="detail-value">${Math.round(wallet.confidence_score * 100)}%</div>
                    </div>
                    <div class="detail-item">
                        <div class="detail-label">Added</div>
                        <div class="detail-value">${new Date(wallet.created_at).toLocaleDateString()}</div>
                    </div>
                </div>

                ${wallet.notes ? `
                    <div style="margin-top: 1rem; padding: 1rem; background: #f8fafc; border-radius: 6px;">
                        <div class="detail-label">Notes</div>
                        <p style="margin: 0.5rem 0 0 0; color: #475569;">${wallet.notes}</p>
                    </div>
                ` : ''}
            </div>
        `).join('');
    }

    openWalletModal(wallet = null) {
        this.editingWallet = wallet;

        if (wallet) {
            document.getElementById('walletModalTitle').textContent = 'Edit Crypto Wallet';
            document.getElementById('walletId').value = wallet.id;
            document.getElementById('walletAddress').value = wallet.wallet_address;
            document.getElementById('walletEntityName').value = wallet.entity_name;
            document.getElementById('walletType').value = wallet.wallet_type;
            document.getElementById('walletBlockchain').value = wallet.blockchain || '';
            document.getElementById('walletPurpose').value = wallet.purpose || '';
            document.getElementById('walletNotes').value = wallet.notes || '';
        } else {
            document.getElementById('walletModalTitle').textContent = 'Add Crypto Wallet';
            document.getElementById('walletForm').reset();
            document.getElementById('walletId').value = '';
        }

        document.getElementById('walletModal').classList.add('active');
    }

    async saveWallet(e) {
        e.preventDefault();

        const walletId = document.getElementById('walletId').value;
        const isEdit = !!walletId;

        const data = {
            wallet_address: document.getElementById('walletAddress').value.trim(),
            entity_name: document.getElementById('walletEntityName').value.trim(),
            wallet_type: document.getElementById('walletType').value,
            blockchain: document.getElementById('walletBlockchain').value,
            purpose: document.getElementById('walletPurpose').value.trim(),
            notes: document.getElementById('walletNotes').value.trim()
        };

        try {
            const url = isEdit ? `/api/wallets/${walletId}` : '/api/wallets';
            const method = isEdit ? 'PUT' : 'POST';

            const response = await fetch(url, {
                method,
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(data)
            });

            const result = await response.json();

            if (response.ok && result.success) {
                this.showNotification(`Wallet ${isEdit ? 'updated' : 'added'} successfully!`, 'success');
                closeWalletModal();
                await this.loadWallets();
            } else {
                throw new Error(result.error || 'Failed to save wallet');
            }
        } catch (error) {
            console.error('Error saving wallet:', error);
            this.showNotification(`Error: ${error.message}`, 'error');
        }
    }

    editWallet(walletId) {
        const wallet = this.wallets.find(w => w.id === walletId);
        if (wallet) {
            this.openWalletModal(wallet);
        }
    }

    async deleteWallet(walletId) {
        const wallet = this.wallets.find(w => w.id === walletId);
        if (!wallet) return;

        if (!confirm(`Are you sure you want to delete the wallet "${wallet.entity_name}"?\n\nThis action cannot be undone.`)) {
            return;
        }

        try {
            const response = await fetch(`/api/wallets/${walletId}`, {
                method: 'DELETE'
            });

            const result = await response.json();

            if (response.ok && result.success) {
                this.showNotification('Wallet deleted successfully!', 'success');
                await this.loadWallets();
            } else {
                throw new Error(result.error || 'Failed to delete wallet');
            }
        } catch (error) {
            console.error('Error deleting wallet:', error);
            this.showNotification(`Error: ${error.message}`, 'error');
        }
    }

    // ========================================
    // UTILITY FUNCTIONS
    // ========================================

    getBankAccountColor(type) {
        const colors = {
            'checking': '#3b82f6',
            'savings': '#10b981',
            'credit': '#f59e0b',
            'investment': '#8b5cf6',
            'loan': '#ef4444'
        };
        return colors[type] || '#6b7280';
    }

    getWalletTypeColor(type) {
        const colors = {
            'internal': '#3b82f6',
            'exchange': '#10b981',
            'customer': '#06b6d4',
            'vendor': '#f59e0b',
            'partner': '#8b5cf6'
        };
        return colors[type] || '#6b7280';
    }

    getStatusColor(status) {
        const colors = {
            'active': '#10b981',
            'inactive': '#f59e0b',
            'closed': '#ef4444',
            'pending': '#3b82f6'
        };
        return colors[status] || '#6b7280';
    }

    formatCurrency(amount, currency = 'USD') {
        return new Intl.NumberFormat('en-US', {
            style: 'currency',
            currency: currency
        }).format(amount);
    }

    showNotification(message, type = 'info') {
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

        setTimeout(() => {
            notification.style.animation = 'slideOut 0.3s ease-out';
            setTimeout(() => notification.remove(), 300);
        }, 5000);
    }
}

// Global functions for modal management
function closeBankModal() {
    document.getElementById('bankAccountModal').classList.remove('active');
    document.getElementById('bankAccountForm').reset();
}

function closeWalletModal() {
    document.getElementById('walletModal').classList.remove('active');
    document.getElementById('walletForm').reset();
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    window.accountsManager = new AccountsManager();
    window.accountsManager.init();
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
`;
document.head.appendChild(style);
