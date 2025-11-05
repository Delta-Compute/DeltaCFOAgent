/**
 * Invoice Transaction Matches Module
 * Handles finding and linking matching transactions to invoices
 */

(function() {
    'use strict';

    let currentInvoiceId = null;
    let currentMatches = [];

    /**
     * Initialize the matches module
     */
    function init(invoiceId) {
        console.log('[InvoiceMatches] init called with invoiceId:', invoiceId);
        currentInvoiceId = invoiceId;
        // Don't load immediately - wait for tab to be clicked
        // This avoids unnecessary API calls
    }

    /**
     * Load transaction matches for an invoice
     */
    async function loadMatches(invoiceId) {
        console.log('[InvoiceMatches] loadMatches called with invoiceId:', invoiceId);

        // Update current invoice ID
        if (invoiceId) {
            currentInvoiceId = invoiceId;
        }

        // Use stored ID if not provided
        if (!currentInvoiceId) {
            console.error('[InvoiceMatches] No invoice ID available');
            return;
        }

        const container = document.getElementById('matches-section');
        if (!container) {
            console.error('[InvoiceMatches] matches-section container not found');
            return;
        }

        try {
            console.log('[InvoiceMatches] Fetching matches for invoice:', currentInvoiceId);
            container.innerHTML = '<div class="loading">Loading transaction matches...</div>';

            const response = await fetch(`/api/invoices/${currentInvoiceId}/find-matching-transactions`);
            const data = await response.json();

            console.log('[InvoiceMatches] API response:', data);

            if (!response.ok) {
                throw new Error(data.error || 'Failed to load matches');
            }

            // API returns 'matching_transactions', not 'matches'
            currentMatches = data.matching_transactions || data.matches || [];
            console.log('[InvoiceMatches] Found', currentMatches.length, 'matches');

            updateMatchesBadge(currentMatches.length);
            renderMatches(currentMatches);

        } catch (error) {
            console.error('[InvoiceMatches] Error loading matches:', error);
            container.innerHTML = `
                <div class="error-message">
                    <p>Error loading transaction matches: ${error.message}</p>
                    <button class="btn btn-secondary" onclick="window.InvoiceMatches.reload()">Retry</button>
                </div>
            `;
        }
    }

    /**
     * Render matches list
     */
    function renderMatches(matches) {
        console.log('[InvoiceMatches] renderMatches called with', matches.length, 'matches:', matches);

        const container = document.getElementById('matches-section');
        if (!container) {
            console.error('[InvoiceMatches] matches-section container not found in renderMatches');
            return;
        }

        if (matches.length === 0) {
            console.log('[InvoiceMatches] No matches to render, showing empty state');
            container.innerHTML = `
                <div class="empty-state" style="text-align: center; padding: 3rem;">
                    <div style="font-size: 3rem; margin-bottom: 1rem;">🔍</div>
                    <h3 style="color: #64748b; margin-bottom: 0.5rem;">No Matching Transactions Found</h3>
                    <p style="color: #94a3b8;">No transactions match this invoice based on amount and date proximity.</p>
                    <button class="btn btn-primary" onclick="window.InvoiceMatches.reload()" style="margin-top: 1rem;">
                        Refresh Matches
                    </button>
                </div>
            `;
            return;
        }

        let html = `
            <div style="padding: 1.5rem;">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1.5rem;">
                    <div>
                        <h3 style="margin: 0; color: #1e293b;">Possible Transaction Matches</h3>
                        <p style="margin: 0.5rem 0 0 0; color: #64748b; font-size: 0.9rem;">
                            Found ${matches.length} potential ${matches.length === 1 ? 'match' : 'matches'} based on amount similarity and date proximity
                        </p>
                    </div>
                    <button class="btn btn-secondary" onclick="window.InvoiceMatches.reload()">
                        Refresh
                    </button>
                </div>

                <div class="matches-list">
        `;

        matches.forEach((match, index) => {
            const matchScore = match.match_score || 0;
            const scoreColor = matchScore >= 95 ? '#10b981' : matchScore >= 80 ? '#f59e0b' : '#64748b';
            const scoreLabel = matchScore >= 95 ? 'Excellent' : matchScore >= 80 ? 'Good' : 'Fair';

            const amountDiff = match.amount_diff || 0;
            const dateDiff = match.date_diff_days || 0;

            html += `
                <div class="match-card" style="background: white; border: 2px solid #e2e8f0; border-radius: 8px; padding: 1.5rem; margin-bottom: 1rem;">
                    <div style="display: flex; justify-content: space-between; align-items: start;">
                        <div style="flex: 1;">
                            <div style="display: flex; align-items: center; gap: 1rem; margin-bottom: 0.75rem;">
                                <div style="background: ${scoreColor}; color: white; padding: 0.25rem 0.75rem; border-radius: 20px; font-size: 0.85rem; font-weight: 600;">
                                    ${matchScore.toFixed(1)}% ${scoreLabel} Match
                                </div>
                                ${match.linked ? '<span style="background: #10b981; color: white; padding: 0.25rem 0.75rem; border-radius: 20px; font-size: 0.85rem;">Already Linked</span>' : ''}
                            </div>

                            <div style="margin-bottom: 0.5rem;">
                                <strong style="color: #1e293b; font-size: 1.1rem;">${escapeHtml(match.description)}</strong>
                            </div>

                            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 1rem; margin-top: 1rem;">
                                <div>
                                    <div style="color: #64748b; font-size: 0.85rem; margin-bottom: 0.25rem;">Transaction Date</div>
                                    <div style="color: #1e293b; font-weight: 500;">${match.date}</div>
                                    ${dateDiff > 0 ? `<div style="color: #94a3b8; font-size: 0.8rem;">${dateDiff} days difference</div>` : ''}
                                </div>
                                <div>
                                    <div style="color: #64748b; font-size: 0.85rem; margin-bottom: 0.25rem;">Amount</div>
                                    <div style="color: #1e293b; font-weight: 500;">$${Math.abs(match.amount).toFixed(2)}</div>
                                    ${amountDiff > 0 ? `<div style="color: #94a3b8; font-size: 0.8rem;">$${amountDiff.toFixed(2)} difference</div>` : ''}
                                </div>
                                <div>
                                    <div style="color: #64748b; font-size: 0.85rem; margin-bottom: 0.25rem;">Category</div>
                                    <div style="color: #1e293b; font-weight: 500;">${match.category || 'N/A'}</div>
                                </div>
                                <div>
                                    <div style="color: #64748b; font-size: 0.85rem; margin-bottom: 0.25rem;">Entity</div>
                                    <div style="color: #1e293b; font-weight: 500;">${match.entity || 'N/A'}</div>
                                </div>
                            </div>
                        </div>

                        <div style="margin-left: 1rem;">
                            ${match.linked ?
                                `<button class="btn btn-secondary" disabled style="background: #e2e8f0; color: #94a3b8; cursor: not-allowed;">Linked</button>` :
                                `<button class="btn btn-primary" onclick="window.InvoiceMatches.linkTransaction('${match.id}', ${matchScore})">Link Transaction</button>`
                            }
                        </div>
                    </div>
                </div>
            `;
        });

        html += `
                </div>
            </div>
        `;

        container.innerHTML = html;
    }

    /**
     * Link a transaction to the invoice
     */
    async function linkTransaction(transactionId, matchScore) {
        if (!confirm('Link this transaction to the invoice?')) {
            return;
        }

        try {
            const response = await fetch(`/api/invoices/${currentInvoiceId}/link-transaction`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    transaction_id: transactionId,
                    match_score: matchScore
                })
            });

            const data = await response.json();

            if (data.success) {
                alert('Transaction linked successfully!');

                // Reload matches to update the UI
                loadMatches(currentInvoiceId);

                // Reload linked transaction section in overview tab
                if (window.loadLinkedTransaction) {
                    window.loadLinkedTransaction(currentInvoiceId);
                }

                // Reload payments tab to show the linked transaction
                if (window.InvoicePayments && window.InvoicePayments.load) {
                    window.InvoicePayments.load(currentInvoiceId);
                }
            } else {
                alert('Failed to link transaction: ' + (data.error || 'Unknown error'));
            }
        } catch (error) {
            console.error('Error linking transaction:', error);
            alert('Error linking transaction: ' + error.message);
        }
    }

    /**
     * Update matches count badge
     */
    function updateMatchesBadge(count) {
        const badge = document.getElementById('matches-count-badge');
        if (badge) {
            badge.textContent = count;
            badge.style.display = count > 0 ? 'inline-block' : 'none';
        }
    }

    /**
     * Escape HTML to prevent XSS
     */
    function escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    /**
     * Reload matches
     */
    function reload() {
        if (currentInvoiceId) {
            loadMatches(currentInvoiceId);
        }
    }

    // Export public API
    window.InvoiceMatches = {
        init,
        load: loadMatches,
        reload,
        linkTransaction
    };

})();
