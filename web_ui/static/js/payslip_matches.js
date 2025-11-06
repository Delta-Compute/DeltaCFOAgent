/**
 * Payslip Transaction Matches Module
 * Handles finding and linking matching transactions to payslips
 * Adapted from invoice_matches.js for payroll use case
 */

(function() {
    'use strict';

    let currentPayslipId = null;
    let currentMatches = [];

    /**
     * Initialize the payslip matches module
     */
    function init(payslipId) {
        console.log('[PayslipMatches] init called with payslipId:', payslipId);
        currentPayslipId = payslipId;
    }

    /**
     * Load transaction matches for a payslip
     */
    async function loadMatches(payslipId) {
        console.log('[PayslipMatches] loadMatches called with payslipId:', payslipId);

        if (payslipId) {
            currentPayslipId = payslipId;
        }

        if (!currentPayslipId) {
            console.error('[PayslipMatches] No payslip ID available');
            return;
        }

        try {
            console.log('[PayslipMatches] Fetching matches for payslip:', currentPayslipId);

            const response = await fetch(`/api/payslips/${currentPayslipId}/find-matching-transactions`);
            const data = await response.json();

            console.log('[PayslipMatches] API response:', data);

            if (!response.ok) {
                throw new Error(data.error || 'Failed to load matches');
            }

            currentMatches = data.matching_transactions || [];
            console.log('[PayslipMatches] Found', currentMatches.length, 'matches');

            renderMatches(currentMatches, data.payslip);

        } catch (error) {
            console.error('[PayslipMatches] Error loading matches:', error);
            alert(`Error loading transaction matches: ${error.message}`);
        }
    }

    /**
     * Render matches list
     */
    function renderMatches(matches, payslip) {
        console.log('[PayslipMatches] renderMatches called with', matches.length, 'matches');

        if (matches.length === 0) {
            alert('No matching transactions found for this payslip');
            return;
        }

        // Create modal HTML
        const modalHtml = `
            <div class="modal show" id="payslip-matches-modal" style="display: flex;">
                <div class="modal-content" style="max-width: 900px; width: 95%;">
                    <div class="modal-header">
                        <div>
                            <h3 class="modal-title">Transaction Matches for Payslip</h3>
                            <p style="color: #64748b; margin-top: 0.5rem; font-size: 0.9rem;">
                                ${payslip.employee_name} - $${formatNumber(payslip.net_amount)} - ${formatDate(payslip.payment_date)}
                            </p>
                        </div>
                        <button class="close-btn" onclick="window.PayslipMatches.closeModal()">&times;</button>
                    </div>
                    <div style="padding: 1rem;">
                        <div style="margin-bottom: 1rem; padding: 1rem; background: #f1f5f9; border-radius: 8px;">
                            <p style="color: #475569; margin: 0;">
                                Found ${matches.length} potential ${matches.length === 1 ? 'match' : 'matches'} based on amount similarity and date proximity
                            </p>
                        </div>
                        <div class="matches-list" style="max-height: 60vh; overflow-y: auto;">
                            ${matches.map(match => renderMatchCard(match, payslip)).join('')}
                        </div>
                    </div>
                    <div class="modal-actions">
                        <button type="button" class="btn btn-secondary" onclick="window.PayslipMatches.closeModal()">Close</button>
                    </div>
                </div>
            </div>
        `;

        // Remove existing modal if any
        const existingModal = document.getElementById('payslip-matches-modal');
        if (existingModal) {
            existingModal.remove();
        }

        // Add modal to body
        document.body.insertAdjacentHTML('beforeend', modalHtml);
    }

    /**
     * Render a single match card
     */
    function renderMatchCard(match, payslip) {
        const matchScore = match.match_score || 0;
        const scoreColor = matchScore >= 95 ? '#10b981' : matchScore >= 80 ? '#f59e0b' : '#64748b';
        const scoreLabel = matchScore >= 95 ? 'Excellent' : matchScore >= 80 ? 'Good' : 'Fair';

        const amountDiff = match.amount_diff || 0;
        const dateDiff = match.date_diff_days || 0;

        return `
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
                                <div style="color: #1e293b; font-weight: 500;">${match.currency} ${formatNumber(Math.abs(match.amount))}</div>
                                ${amountDiff > 0 ? `<div style="color: #94a3b8; font-size: 0.8rem;">$${amountDiff.toFixed(2)} difference</div>` : ''}
                            </div>
                            <div>
                                <div style="color: #64748b; font-size: 0.85rem; margin-bottom: 0.25rem;">Category</div>
                                <div style="color: #1e293b; font-weight: 500;">${match.category || 'Uncategorized'}</div>
                                ${match.subcategory ? `<div style="color: #94a3b8; font-size: 0.8rem;">${match.subcategory}</div>` : ''}
                            </div>
                        </div>
                    </div>

                    <div style="display: flex; flex-direction: column; gap: 0.5rem; margin-left: 1rem;">
                        ${!match.linked ? `
                            <button class="btn btn-primary" onclick="window.PayslipMatches.confirmMatch('${payslip.id}', '${match.transaction_id}', ${matchScore})" style="padding: 0.5rem 1rem; font-size: 0.9rem;">
                                Link
                            </button>
                        ` : `
                            <button class="btn btn-secondary" disabled style="padding: 0.5rem 1rem; font-size: 0.9rem;">
                                Linked
                            </button>
                        `}
                    </div>
                </div>
            </div>
        `;
    }

    /**
     * Confirm a match
     */
    async function confirmMatch(payslipId, transactionId, matchScore) {
        if (!confirm('Link this transaction to the payslip?')) {
            return;
        }

        try {
            const response = await fetch(`/api/payslips/${payslipId}/link-transaction`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    transaction_id: transactionId,
                    match_confidence: Math.round(matchScore)
                })
            });

            const data = await response.json();

            if (data.success) {
                alert('Transaction linked successfully!');
                closeModal();
                // Refresh payslips list if function exists
                if (typeof refreshPayslips === 'function') {
                    refreshPayslips();
                }
            } else {
                alert('Error: ' + (data.error || 'Failed to link transaction'));
            }
        } catch (error) {
            console.error('[PayslipMatches] Error confirming match:', error);
            alert('Network error. Please try again.');
        }
    }

    /**
     * Close the matches modal
     */
    function closeModal() {
        const modal = document.getElementById('payslip-matches-modal');
        if (modal) {
            modal.remove();
        }
    }

    /**
     * Reload matches
     */
    function reload() {
        loadMatches(currentPayslipId);
    }

    // Utility functions
    function escapeHtml(text) {
        if (!text) return '';
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    function formatNumber(num) {
        if (num === null || num === undefined) return '0.00';
        return parseFloat(num).toLocaleString('en-US', {
            minimumFractionDigits: 2,
            maximumFractionDigits: 2
        });
    }

    function formatDate(dateString) {
        if (!dateString) return '-';
        const date = new Date(dateString);
        return date.toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric' });
    }

    // Export public API
    window.PayslipMatches = {
        init,
        loadMatches,
        confirmMatch,
        closeModal,
        reload
    };

})();

// Update workforce.js to use this module
function viewPayslipMatches(payslipId) {
    window.PayslipMatches.loadMatches(payslipId);
}
