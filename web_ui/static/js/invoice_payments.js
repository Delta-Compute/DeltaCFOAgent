/**
 * Invoice Payments Manager
 * Handles multiple partial payments per invoice with automatic status calculation
 */

window.InvoicePayments = (function() {
    'use strict';

    let currentInvoiceId = null;
    let payments = [];
    let paymentSummary = null;

    /**
     * Initialize the payments section for an invoice
     */
    function init(invoiceId) {
        currentInvoiceId = invoiceId;
        loadPayments(invoiceId);
    }

    /**
     * Load all payments for the current invoice
     */
    async function loadPayments(invoiceId) {
        currentInvoiceId = invoiceId;

        try {
            // Load payments and summary in parallel
            const [paymentsResp, summaryResp] = await Promise.all([
                fetch(`/api/invoices/${invoiceId}/payments`),
                fetch(`/api/invoices/${invoiceId}/payment-summary`)
            ]);

            const paymentsData = await paymentsResp.json();
            const summaryData = await summaryResp.json();

            if (paymentsData.success && summaryData.success) {
                payments = paymentsData.payments || [];
                paymentSummary = summaryData.summary;
                renderPayments();
            } else {
                showError('Failed to load payments: ' + (paymentsData.error || summaryData.error));
            }
        } catch (error) {
            console.error('Error loading payments:', error);
            showError('Error loading payments: ' + error.message);
        }
    }

    /**
     * Render payments list and summary in the UI
     */
    function renderPayments() {
        const section = document.getElementById('payments-section');

        // Render payment summary
        let html = renderPaymentSummary();

        // Render add payment button and match transaction button
        html += `
            <div style="margin-top: 1.5rem; margin-bottom: 1rem; display: flex; gap: 0.75rem;">
                <button class="btn btn-primary" onclick="window.InvoicePayments.showAddPaymentModal()">
                    + Add Payment
                </button>
                <button class="btn btn-secondary" onclick="window.InvoicePayments.showTransactionMatchModal()"
                        style="background: #64748b; color: white; border: none;">
                    🔗 Match with Transaction
                </button>
            </div>
        `;

        // Render payments list
        if (!payments || payments.length === 0) {
            html += `
                <div style="text-align: center; padding: 2rem; color: #94a3b8; background: #f8fafc; border-radius: 8px;">
                    <div style="font-size: 3rem; margin-bottom: 1rem;">💰</div>
                    <p>No payments recorded yet</p>
                </div>
            `;
        } else {
            html += `<div style="display: grid; gap: 1rem;">`;

            payments.forEach(payment => {
                const paymentDate = new Date(payment.payment_date).toLocaleDateString();
                const amount = parseFloat(payment.payment_amount).toLocaleString(undefined, {
                    minimumFractionDigits: 2,
                    maximumFractionDigits: 2
                });

                html += `
                    <div style="background: white; border: 1px solid #e2e8f0; border-radius: 8px; padding: 1rem;">
                        <div style="display: flex; justify-content: space-between; align-items: start;">
                            <div style="flex: 1;">
                                <div style="display: flex; align-items: center; gap: 1rem; margin-bottom: 0.5rem;">
                                    <strong style="font-size: 1.25rem; color: #10b981;">
                                        ${payment.payment_currency || 'USD'} ${amount}
                                    </strong>
                                    <span style="color: #64748b; font-size: 0.875rem;">${paymentDate}</span>
                                </div>
                                <div style="color: #64748b; font-size: 0.875rem; display: grid; gap: 0.25rem;">
                                    ${payment.payment_method ? `<div>Method: ${payment.payment_method}</div>` : ''}
                                    ${payment.payment_reference ? `<div>Reference: ${payment.payment_reference}</div>` : ''}
                                    ${payment.payment_notes ? `<div>Notes: ${payment.payment_notes}</div>` : ''}
                                    ${payment.attachment_file_name ? `
                                        <div style="display: flex; align-items: center; gap: 0.5rem;">
                                            <span>Proof: ${payment.attachment_file_name}</span>
                                            <a href="/api/attachments/${payment.attachment_id}/download" target="_blank"
                                               style="color: #3b82f6; text-decoration: none; font-size: 0.75rem;">
                                                [Download]
                                            </a>
                                        </div>
                                    ` : ''}
                                    <div style="margin-top: 0.25rem; color: #94a3b8;">
                                        Recorded by ${payment.recorded_by || 'system'} on ${new Date(payment.created_at).toLocaleString()}
                                    </div>
                                </div>
                            </div>
                            <div style="display: flex; gap: 0.5rem; align-items: start;">
                                <button class="btn btn-sm btn-outline-primary"
                                        onclick="window.InvoicePayments.showEditPaymentModal('${payment.id}')">
                                    Edit
                                </button>
                                <button class="btn btn-sm btn-outline-danger"
                                        onclick="window.InvoicePayments.deletePayment('${payment.id}')">
                                    Delete
                                </button>
                            </div>
                        </div>
                    </div>
                `;
            });

            html += '</div>';
        }

        section.innerHTML = html;
    }

    /**
     * Render payment summary card
     */
    function renderPaymentSummary() {
        if (!paymentSummary) return '';

        const totalAmount = parseFloat(paymentSummary.total_amount).toLocaleString(undefined, {
            minimumFractionDigits: 2,
            maximumFractionDigits: 2
        });
        const totalPaid = parseFloat(paymentSummary.total_paid).toLocaleString(undefined, {
            minimumFractionDigits: 2,
            maximumFractionDigits: 2
        });
        const remaining = parseFloat(paymentSummary.remaining).toLocaleString(undefined, {
            minimumFractionDigits: 2,
            maximumFractionDigits: 2
        });
        const percentage = paymentSummary.percentage_paid.toFixed(1);

        // Status colors
        let statusColor = '#94a3b8';
        let statusBg = '#f1f5f9';
        if (paymentSummary.status === 'paid') {
            statusColor = '#10b981';
            statusBg = '#d1fae5';
        } else if (paymentSummary.status === 'partially_paid') {
            statusColor = '#f59e0b';
            statusBg = '#fef3c7';
        } else if (paymentSummary.status === 'overpaid') {
            statusColor = '#3b82f6';
            statusBg = '#dbeafe';
        }

        return `
            <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                        border-radius: 12px; padding: 1.5rem; color: white; margin-bottom: 1.5rem;">
                <h3 style="margin: 0 0 1rem 0; font-size: 1.25rem;">Payment Summary</h3>

                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 1rem; margin-bottom: 1rem;">
                    <div>
                        <div style="font-size: 0.875rem; opacity: 0.9;">Invoice Total</div>
                        <div style="font-size: 1.5rem; font-weight: 700;">$${totalAmount}</div>
                    </div>
                    <div>
                        <div style="font-size: 0.875rem; opacity: 0.9;">Total Paid</div>
                        <div style="font-size: 1.5rem; font-weight: 700;">$${totalPaid}</div>
                    </div>
                    <div>
                        <div style="font-size: 0.875rem; opacity: 0.9;">Remaining</div>
                        <div style="font-size: 1.5rem; font-weight: 700;">$${remaining}</div>
                    </div>
                    <div>
                        <div style="font-size: 0.875rem; opacity: 0.9;">Progress</div>
                        <div style="font-size: 1.5rem; font-weight: 700;">${percentage}%</div>
                    </div>
                </div>

                <!-- Progress Bar -->
                <div style="background: rgba(255,255,255,0.2); border-radius: 999px; height: 12px; overflow: hidden; margin-bottom: 0.75rem;">
                    <div style="background: white; height: 100%; width: ${Math.min(percentage, 100)}%;
                                transition: width 0.3s ease;"></div>
                </div>

                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <span style="font-size: 0.875rem; opacity: 0.9;">
                        ${paymentSummary.payment_count} payment${paymentSummary.payment_count !== 1 ? 's' : ''} recorded
                    </span>
                    <span style="background: ${statusBg}; color: ${statusColor};
                                 padding: 0.25rem 0.75rem; border-radius: 999px; font-weight: 600; font-size: 0.875rem;">
                        ${paymentSummary.status.toUpperCase().replace('_', ' ')}
                    </span>
                </div>
            </div>
        `;
    }

    /**
     * Show add payment modal
     */
    function showAddPaymentModal() {
        const modal = createPaymentModal('Add Payment', null);
        document.body.appendChild(modal);
    }

    /**
     * Show edit payment modal
     */
    async function showEditPaymentModal(paymentId) {
        try {
            const response = await fetch(`/api/payments/${paymentId}`);
            const data = await response.json();

            if (data.success) {
                const modal = createPaymentModal('Edit Payment', data.payment);
                document.body.appendChild(modal);
            } else {
                alert('Failed to load payment: ' + data.error);
            }
        } catch (error) {
            console.error('Error loading payment:', error);
            alert('Error loading payment: ' + error.message);
        }
    }

    /**
     * Create payment form modal (for add or edit)
     */
    function createPaymentModal(title, payment) {
        const isEdit = !!payment;
        const modal = document.createElement('div');
        modal.className = 'modal active';
        modal.id = 'payment-modal';

        modal.innerHTML = `
            <div class="modal-content" style="max-width: 600px;">
                <div class="modal-header">
                    <div class="modal-title">${title}</div>
                    <button class="close-modal" onclick="window.InvoicePayments.closePaymentModal()">&times;</button>
                </div>
                <form id="payment-form" onsubmit="window.InvoicePayments.handlePaymentSubmit(event, ${isEdit})">
                    <input type="hidden" id="payment-id" value="${payment ? payment.id : ''}">

                    <div class="form-group">
                        <label for="payment-amount">Payment Amount *</label>
                        <input type="number" id="payment-amount" step="0.01" required
                               value="${payment ? payment.payment_amount : ''}"
                               style="width: 100%; padding: 0.5rem; border: 1px solid #cbd5e1; border-radius: 4px;">
                    </div>

                    <div class="form-group">
                        <label for="payment-date">Payment Date *</label>
                        <input type="date" id="payment-date" required
                               value="${payment ? payment.payment_date : new Date().toISOString().split('T')[0]}"
                               style="width: 100%; padding: 0.5rem; border: 1px solid #cbd5e1; border-radius: 4px;">
                    </div>

                    <div class="form-group">
                        <label for="payment-currency">Currency</label>
                        <select id="payment-currency"
                                style="width: 100%; padding: 0.5rem; border: 1px solid #cbd5e1; border-radius: 4px;">
                            <option value="USD" ${!payment || payment.payment_currency === 'USD' ? 'selected' : ''}>USD</option>
                            <option value="BRL" ${payment && payment.payment_currency === 'BRL' ? 'selected' : ''}>BRL</option>
                            <option value="EUR" ${payment && payment.payment_currency === 'EUR' ? 'selected' : ''}>EUR</option>
                            <option value="USDT" ${payment && payment.payment_currency === 'USDT' ? 'selected' : ''}>USDT</option>
                            <option value="BTC" ${payment && payment.payment_currency === 'BTC' ? 'selected' : ''}>BTC</option>
                        </select>
                    </div>

                    <div class="form-group">
                        <label for="payment-method">Payment Method</label>
                        <select id="payment-method"
                                style="width: 100%; padding: 0.5rem; border: 1px solid #cbd5e1; border-radius: 4px;">
                            <option value="">Select...</option>
                            <option value="crypto" ${payment && payment.payment_method === 'crypto' ? 'selected' : ''}>Cryptocurrency</option>
                            <option value="wire" ${payment && payment.payment_method === 'wire' ? 'selected' : ''}>Wire Transfer</option>
                            <option value="check" ${payment && payment.payment_method === 'check' ? 'selected' : ''}>Check</option>
                            <option value="cash" ${payment && payment.payment_method === 'cash' ? 'selected' : ''}>Cash</option>
                            <option value="credit_card" ${payment && payment.payment_method === 'credit_card' ? 'selected' : ''}>Credit Card</option>
                            <option value="other" ${payment && payment.payment_method === 'other' ? 'selected' : ''}>Other</option>
                        </select>
                    </div>

                    <div class="form-group">
                        <label for="payment-reference">Transaction Reference / Hash</label>
                        <input type="text" id="payment-reference"
                               value="${payment ? payment.payment_reference || '' : ''}"
                               placeholder="Transaction ID, check number, etc."
                               style="width: 100%; padding: 0.5rem; border: 1px solid #cbd5e1; border-radius: 4px;">
                    </div>

                    <div class="form-group">
                        <label for="payment-notes">Notes</label>
                        <textarea id="payment-notes" rows="3"
                                  style="width: 100%; padding: 0.5rem; border: 1px solid #cbd5e1; border-radius: 4px;">${payment ? payment.payment_notes || '' : ''}</textarea>
                    </div>

                    <div class="modal-footer" style="margin-top: 1.5rem; display: flex; gap: 0.5rem; justify-content: flex-end;">
                        <button type="button" class="btn btn-secondary"
                                onclick="window.InvoicePayments.closePaymentModal()">Cancel</button>
                        <button type="submit" class="btn btn-primary">
                            ${isEdit ? 'Update' : 'Add'} Payment
                        </button>
                    </div>
                </form>
            </div>
        `;

        return modal;
    }

    /**
     * Close payment modal
     */
    function closePaymentModal() {
        const modal = document.getElementById('payment-modal');
        if (modal) {
            modal.remove();
        }
    }

    /**
     * Handle payment form submission
     */
    async function handlePaymentSubmit(event, isEdit) {
        event.preventDefault();

        const paymentId = document.getElementById('payment-id').value;
        const amount = parseFloat(document.getElementById('payment-amount').value);
        const date = document.getElementById('payment-date').value;
        const currency = document.getElementById('payment-currency').value;
        const method = document.getElementById('payment-method').value;
        const reference = document.getElementById('payment-reference').value;
        const notes = document.getElementById('payment-notes').value;

        const paymentData = {
            payment_amount: amount,
            payment_date: date,
            payment_currency: currency,
            payment_method: method || null,
            payment_reference: reference || null,
            payment_notes: notes || null,
            recorded_by: 'user' // TODO: Get actual username
        };

        try {
            // Show loading
            const submitBtn = event.target.querySelector('button[type="submit"]');
            const originalText = submitBtn.textContent;
            submitBtn.textContent = isEdit ? 'Updating...' : 'Adding...';
            submitBtn.disabled = true;

            let response;
            if (isEdit) {
                response = await fetch(`/api/payments/${paymentId}`, {
                    method: 'PUT',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(paymentData)
                });
            } else {
                response = await fetch(`/api/invoices/${currentInvoiceId}/payments`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(paymentData)
                });
            }

            const result = await response.json();

            if (result.success) {
                closePaymentModal();
                loadPayments(currentInvoiceId);

                // Update badge count
                if (window.loadTabCounts) {
                    window.loadTabCounts(currentInvoiceId);
                }

                // Refresh invoice list to show updated status
                if (window.loadInvoices) {
                    window.loadInvoices(window.currentPage);
                }

                alert(isEdit ? 'Payment updated successfully!' : 'Payment added successfully!');
            } else {
                alert('Failed: ' + result.error);
                submitBtn.textContent = originalText;
                submitBtn.disabled = false;
            }
        } catch (error) {
            console.error('Error saving payment:', error);
            alert('Error saving payment: ' + error.message);
        }
    }

    /**
     * Delete payment
     */
    async function deletePayment(paymentId) {
        if (!confirm('Are you sure you want to delete this payment? This will update the invoice status.')) {
            return;
        }

        try {
            const response = await fetch(`/api/payments/${paymentId}`, {
                method: 'DELETE'
            });

            const result = await response.json();

            if (result.success) {
                loadPayments(currentInvoiceId);

                // Update badge count
                if (window.loadTabCounts) {
                    window.loadTabCounts(currentInvoiceId);
                }

                // Refresh invoice list to show updated status
                if (window.loadInvoices) {
                    window.loadInvoices(window.currentPage);
                }

                alert('Payment deleted successfully');
            } else {
                alert('Delete failed: ' + result.error);
            }
        } catch (error) {
            console.error('Error deleting payment:', error);
            alert('Error deleting payment: ' + error.message);
        }
    }

    /**
     * Show error message
     */
    function showError(message) {
        const section = document.getElementById('payments-section');
        section.innerHTML = `
            <div style="text-align: center; padding: 2rem; color: #ef4444;">
                <p>${message}</p>
                <button class="btn btn-primary" onclick="window.InvoicePayments.loadPayments('${currentInvoiceId}')">
                    Retry
                </button>
            </div>
        `;
    }

    /**
     * Show transaction matching modal
     */
    async function showTransactionMatchModal() {
        if (!currentInvoiceId) {
            alert('No invoice selected');
            return;
        }

        try {
            // Fetch matching transactions
            const response = await fetch(`/api/invoices/${currentInvoiceId}/find-matching-transactions`);
            const data = await response.json();

            if (!data.success) {
                alert('Failed to find matching transactions: ' + data.error);
                return;
            }

            const modal = createTransactionMatchModal(data.invoice, data.matching_transactions);
            document.body.appendChild(modal);
        } catch (error) {
            console.error('Error loading matching transactions:', error);
            alert('Error loading matching transactions: ' + error.message);
        }
    }

    /**
     * Create transaction matching modal
     */
    function createTransactionMatchModal(invoice, transactions) {
        const modal = document.createElement('div');
        modal.className = 'modal active';
        modal.id = 'transaction-match-modal';

        let transactionsHtml = '';
        if (!transactions || transactions.length === 0) {
            transactionsHtml = `
                <div style="text-align: center; padding: 3rem; color: #64748b;">
                    <div style="font-size: 3rem; margin-bottom: 1rem;">🔍</div>
                    <p>No matching transactions found</p>
                    <p style="font-size: 0.875rem; margin-top: 0.5rem;">
                        Try adjusting the invoice date or amount
                    </p>
                </div>
            `;
        } else {
            transactionsHtml = `
                <div style="max-height: 400px; overflow-y: auto;">
                    ${transactions.map(txn => {
                        const isPositive = txn.amount >= 0;
                        const amountColor = isPositive ? '#10b981' : '#ef4444';

                        let matchColor = '#94a3b8';
                        let matchBg = '#f1f5f9';
                        if (txn.match_score >= 80) {
                            matchColor = '#10b981';
                            matchBg = '#d1fae5';
                        } else if (txn.match_score >= 60) {
                            matchColor = '#f59e0b';
                            matchBg = '#fef3c7';
                        }

                        return `
                            <div style="background: white; border: 1px solid #e2e8f0; border-radius: 8px;
                                        padding: 1rem; margin-bottom: 0.75rem; cursor: pointer;
                                        transition: all 0.2s;"
                                 onmouseover="this.style.borderColor='#3b82f6'; this.style.boxShadow='0 2px 8px rgba(59,130,246,0.1)'"
                                 onmouseout="this.style.borderColor='#e2e8f0'; this.style.boxShadow='none'"
                                 onclick="window.InvoicePayments.linkToTransaction('${txn.id}')">
                                <div style="display: flex; justify-content: space-between; align-items: start; margin-bottom: 0.5rem;">
                                    <div style="flex: 1;">
                                        <div style="font-weight: 600; color: #1e293b; margin-bottom: 0.25rem;">
                                            ${txn.description}
                                        </div>
                                        <div style="display: flex; gap: 1rem; font-size: 0.875rem; color: #64748b;">
                                            <span>${txn.date}</span>
                                            <span>${txn.entity || 'N/A'}</span>
                                            ${txn.category ? `<span>${txn.category}</span>` : ''}
                                        </div>
                                    </div>
                                    <div style="text-align: right;">
                                        <div style="font-size: 1.125rem; font-weight: 700; color: ${amountColor};">
                                            $${Math.abs(txn.amount).toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2})}
                                        </div>
                                        <div style="font-size: 0.75rem; margin-top: 0.25rem;">
                                            <span style="background: ${matchBg}; color: ${matchColor};
                                                       padding: 0.125rem 0.5rem; border-radius: 999px; font-weight: 600;">
                                                ${txn.match_score}% match
                                            </span>
                                        </div>
                                    </div>
                                </div>
                                <div style="font-size: 0.75rem; color: #94a3b8; display: flex; gap: 1rem;">
                                    <span>Amount diff: $${txn.amount_diff}</span>
                                    <span>Date diff: ${txn.date_diff_days} day${txn.date_diff_days !== 1 ? 's' : ''}</span>
                                </div>
                            </div>
                        `;
                    }).join('')}
                </div>
            `;
        }

        modal.innerHTML = `
            <div class="modal-content" style="max-width: 800px;">
                <div class="modal-header">
                    <div class="modal-title">Match Transaction to Invoice</div>
                    <button class="close-modal" onclick="window.InvoicePayments.closeTransactionMatchModal()">&times;</button>
                </div>
                <div style="padding: 1.5rem;">
                    <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                                border-radius: 12px; padding: 1rem; color: white; margin-bottom: 1.5rem;">
                        <div style="font-size: 0.875rem; opacity: 0.9;">Invoice #${invoice.invoice_number}</div>
                        <div style="font-size: 1.5rem; font-weight: 700; margin: 0.25rem 0;">
                            $${invoice.total_amount.toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2})}
                        </div>
                        <div style="font-size: 0.875rem; opacity: 0.9;">
                            ${invoice.vendor_name || invoice.customer_name || 'N/A'} | ${invoice.date}
                        </div>
                    </div>

                    <div style="margin-bottom: 1rem;">
                        <h3 style="margin: 0 0 0.75rem 0; font-size: 1rem; color: #475569;">
                            Select a matching transaction:
                        </h3>
                    </div>

                    ${transactionsHtml}

                    <div style="margin-top: 1.5rem; padding-top: 1rem; border-top: 1px solid #e2e8f0;">
                        <button class="btn btn-secondary" onclick="window.InvoicePayments.closeTransactionMatchModal()">
                            Cancel
                        </button>
                    </div>
                </div>
            </div>
        `;

        return modal;
    }

    /**
     * Link invoice to transaction
     */
    async function linkToTransaction(transactionId) {
        if (!confirm('Link this transaction to the invoice?')) {
            return;
        }

        try {
            const response = await fetch(`/api/invoices/${currentInvoiceId}/link-transaction`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ transaction_id: transactionId })
            });

            const result = await response.json();

            if (result.success) {
                closeTransactionMatchModal();
                alert('Transaction linked successfully!');

                // Refresh invoice list
                if (window.loadInvoices) {
                    window.loadInvoices(window.currentPage);
                }
            } else {
                alert('Failed to link transaction: ' + result.error);
            }
        } catch (error) {
            console.error('Error linking transaction:', error);
            alert('Error linking transaction: ' + error.message);
        }
    }

    /**
     * Close transaction match modal
     */
    function closeTransactionMatchModal() {
        const modal = document.getElementById('transaction-match-modal');
        if (modal) {
            modal.remove();
        }
    }

    // Public API
    return {
        init,
        loadPayments,
        showAddPaymentModal,
        showEditPaymentModal,
        closePaymentModal,
        handlePaymentSubmit,
        deletePayment,
        showTransactionMatchModal,
        linkToTransaction,
        closeTransactionMatchModal
    };
})();
