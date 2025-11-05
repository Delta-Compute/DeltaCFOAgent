// Payment Receipts Upload Handler
// Handles uploading payment proof/receipts with automatic invoice matching

document.addEventListener('DOMContentLoaded', function() {
    // Elements
    const uploadReceiptButton = document.getElementById('upload-receipt-button');
    const fileInputReceipts = document.getElementById('file-input-receipts');
    const receiptProgress = document.getElementById('receipt-progress');
    const receiptStatusText = document.getElementById('receipt-status-text');
    const receiptProgressBar = document.getElementById('receipt-progress-bar');
    const receiptResult = document.getElementById('receipt-result');
    const uploadBoxReceipts = document.getElementById('upload-box-receipts');
    const customerFilterSelect = document.getElementById('customer-filter-receipts');

    // Load customers for filter
    loadCustomersForFilter();

    // Handle file selection (single or multiple files)
    fileInputReceipts.addEventListener('change', function(e) {
        if (e.target.files.length > 0) {
            const files = Array.from(e.target.files);

            if (files.length === 1) {
                // Single file - use existing flow with modal UI
                uploadReceipt(files[0]);
            } else {
                // Multiple files - use batch processing
                uploadMultipleReceipts(files);
            }
        }
    });

    // Drag and drop for receipts
    ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
        uploadBoxReceipts.addEventListener(eventName, preventDefaults, false);
    });

    function preventDefaults(e) {
        e.preventDefault();
        e.stopPropagation();
    }

    ['dragenter', 'dragover'].forEach(eventName => {
        uploadBoxReceipts.addEventListener(eventName, () => {
            uploadBoxReceipts.style.borderColor = '#667eea';
            uploadBoxReceipts.style.background = '#ebf8ff';
        }, false);
    });

    ['dragleave', 'drop'].forEach(eventName => {
        uploadBoxReceipts.addEventListener(eventName, () => {
            uploadBoxReceipts.style.borderColor = '#cbd5e1';
            uploadBoxReceipts.style.background = '#f8fafc';
        }, false);
    });

    uploadBoxReceipts.addEventListener('drop', (e) => {
        const files = Array.from(e.dataTransfer.files);
        if (files.length === 1) {
            uploadReceipt(files[0]);
        } else if (files.length > 1) {
            uploadMultipleReceipts(files);
        }
    });

    // Upload receipt to server with auto-matching
    async function uploadReceipt(file) {
        // Show progress
        receiptProgress.style.display = 'block';
        receiptResult.style.display = 'none';
        receiptStatusText.textContent = 'Uploading receipt...';
        receiptProgressBar.style.width = '20%';
        receiptProgressBar.style.background = '#3b82f6';

        const formData = new FormData();
        formData.append('file', file);

        try {
            receiptStatusText.textContent = 'Extracting payment data with Claude AI...';
            receiptProgressBar.style.width = '50%';

            const response = await fetch('/api/payment-proof/upload', {
                method: 'POST',
                body: formData
            });

            receiptProgressBar.style.width = '80%';
            receiptStatusText.textContent = 'Matching invoice...';

            const result = await response.json();
            receiptProgressBar.style.width = '100%';

            // Show result
            receiptResult.style.display = 'block';

            if (result.success) {
                const matchInfo = result.match_info;
                const invoice = result.matched_invoice;
                const paymentData = result.payment_data;

                // Format confidence level
                const confidenceLabels = {
                    'very_high': { text: 'Very High (Almost Certain)', color: '#16a34a' },
                    'high': { text: 'High (Strong Match)', color: '#16a34a' },
                    'medium': { text: 'Medium (Possible)', color: '#ca8a04' },
                    'low': { text: 'Low (Weak)', color: '#dc2626' }
                };
                const confInfo = confidenceLabels[matchInfo.confidence] || { text: 'Unknown', color: '#64748b' };

                receiptResult.innerHTML = `
                    <div style="background: #dcfce7; border: 1px solid #86efac; border-radius: 8px; padding: 1rem;">
                        <h4 style="color: #166534; margin: 0 0 0.75rem 0;">Payment Receipt Processed & Matched Successfully!</h4>

                        <!-- Matched Invoice Info -->
                        <div style="background: white; border-radius: 6px; padding: 0.75rem; margin-bottom: 0.75rem;">
                            <div style="font-weight: 600; color: #1e293b; margin-bottom: 0.5rem;">Matched to Invoice:</div>
                            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 0.5rem; font-size: 0.9rem;">
                                <div><strong>Invoice #:</strong> ${invoice.invoice_number || 'N/A'}</div>
                                <div><strong>Customer:</strong> ${invoice.customer_name || invoice.vendor_name || 'N/A'}</div>
                                <div><strong>Amount:</strong> $${invoice.amount.toFixed(2)} ${invoice.currency || 'USD'}</div>
                                <div style="color: ${confInfo.color};"><strong>Match Confidence:</strong> ${confInfo.text}</div>
                            </div>
                            <div style="margin-top: 0.5rem; font-size: 0.85rem; color: #64748b;">
                                Match Score: ${matchInfo.score}/100
                                (Amount: ${matchInfo.score_breakdown.amount_score}/50,
                                Date: ${matchInfo.score_breakdown.date_score}/30,
                                Currency: ${matchInfo.score_breakdown.currency_score}/10)
                            </div>
                        </div>

                        <!-- Payment Data -->
                        <div style="background: white; border-radius: 6px; padding: 0.75rem; margin-bottom: 0.75rem;">
                            <div style="font-weight: 600; color: #1e293b; margin-bottom: 0.5rem;">Extracted Payment Data:</div>
                            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 0.5rem; font-size: 0.9rem;">
                                <div><strong>Date:</strong> ${paymentData.date || 'N/A'}</div>
                                <div><strong>Amount:</strong> $${paymentData.amount || 'N/A'} ${paymentData.currency || ''}</div>
                                <div><strong>Method:</strong> ${paymentData.method || 'N/A'}</div>
                                <div><strong>Confirmation:</strong> ${paymentData.confirmation_number || 'N/A'}</div>
                            </div>
                            <div style="margin-top: 0.5rem; font-size: 0.85rem; color: #64748b;">
                                <strong>Extraction Confidence:</strong> ${Math.round((paymentData.confidence || 0) * 100)}%
                            </div>
                        </div>

                        ${result.validation && !result.validation.is_valid ? `
                            <div style="background: #fee2e2; border: 1px solid #f87171; border-radius: 6px; padding: 0.75rem; margin-bottom: 0.75rem;">
                                <strong style="color: #991b1b;">Validation Issues:</strong>
                                <div style="margin-top: 0.5rem; font-size: 0.85rem;">
                                    ${result.validation.errors.map(err => `<div style="color: #7f1d1d;">• ${err}</div>`).join('')}
                                    ${result.validation.warnings.map(warn => `<div style="color: #92400e;">⚠ ${warn}</div>`).join('')}
                                </div>
                            </div>
                        ` : ''}

                        <div style="margin-top: 0.75rem; padding: 0.5rem; background: ${result.payment_status === 'paid' ? '#dcfce7' : '#fef3c7'}; border-radius: 6px; font-size: 0.9rem;">
                            <strong>Status:</strong> ${result.payment_status === 'paid' ? '✓ Paid' : '⏳ Pending Review'}
                        </div>

                        <button onclick="location.reload()" style="margin-top: 0.75rem; background: #16a34a; color: white; border: none; padding: 0.5rem 1rem; border-radius: 6px; cursor: pointer; font-size: 1rem;">
                            Upload Another Receipt
                        </button>
                    </div>
                `;
            } else if (response.status === 404) {
                // No automatic match found - show candidates for manual selection
                const paymentData = result.payment_data;
                const debug = result.debug;
                const candidates = debug?.top_candidates || [];

                // Store file and payment data for confirm endpoint
                window.pendingReceiptFile = file;
                window.pendingPaymentData = paymentData;

                let candidatesHTML = '';
                if (candidates.length > 0) {
                    candidatesHTML = `
                        <div style="margin-top: 1rem;">
                            <div style="font-weight: 600; color: #1e293b; margin-bottom: 0.75rem;">
                                Found ${candidates.length} Possible ${candidates.length === 1 ? 'Match' : 'Matches'}:
                            </div>
                            ${candidates.map((cand, idx) => {
                                const scoreColor = cand.score >= 70 ? '#10b981' : cand.score >= 50 ? '#f59e0b' : '#ef4444';
                                const statusBadgeColor = cand.status === 'pending' ? '#eab308' :
                                                        cand.status === 'paid' ? '#10b981' :
                                                        cand.status === 'partially_paid' ? '#3b82f6' : '#64748b';
                                return `
                                <div style="background: white; border: 2px solid ${idx === 0 ? '#10b981' : '#e2e8f0'}; border-radius: 8px; padding: 1.25rem; margin-bottom: 0.75rem; position: relative;">
                                    ${idx === 0 ? '<div style="position: absolute; top: 0.5rem; left: 0.5rem; background: #10b981; color: white; padding: 0.25rem 0.5rem; border-radius: 4px; font-size: 0.75rem; font-weight: 600;">BEST MATCH</div>' : ''}

                                    <div style="display: flex; justify-content: space-between; align-items: start; ${idx === 0 ? 'margin-top: 1.5rem;' : ''}">
                                        <div style="flex: 1;">
                                            <div style="display: flex; align-items: center; gap: 0.75rem; margin-bottom: 0.75rem;">
                                                <div style="font-weight: 700; color: #1e293b; font-size: 1.1rem;">
                                                    Invoice #${cand.invoice_number}
                                                </div>
                                                <div style="background: ${scoreColor}; color: white; padding: 0.25rem 0.6rem; border-radius: 12px; font-size: 0.8rem; font-weight: 600;">
                                                    ${cand.score.toFixed(0)}% Match
                                                </div>
                                                <div style="background: ${statusBadgeColor}; color: white; padding: 0.25rem 0.6rem; border-radius: 12px; font-size: 0.8rem; text-transform: capitalize;">
                                                    ${cand.status.replace('_', ' ')}
                                                </div>
                                            </div>

                                            ${cand.customer_name ? `<div style="color: #64748b; font-size: 0.95rem; margin-bottom: 0.75rem;">
                                                <strong>Customer:</strong> ${cand.customer_name}
                                            </div>` : ''}

                                            <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 0.75rem; margin-bottom: 0.75rem;">
                                                <div>
                                                    <div style="color: #94a3b8; font-size: 0.75rem; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 0.25rem;">Amount</div>
                                                    <div style="color: #1e293b; font-weight: 600; font-size: 1rem;">$${cand.amount.toFixed(2)} ${cand.currency || 'USD'}</div>
                                                </div>
                                                <div>
                                                    <div style="color: #94a3b8; font-size: 0.75rem; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 0.25rem;">Invoice Date</div>
                                                    <div style="color: #1e293b; font-weight: 600; font-size: 1rem;">${cand.invoice_date || 'N/A'}</div>
                                                </div>
                                                <div>
                                                    <div style="color: #94a3b8; font-size: 0.75rem; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 0.25rem;">Confidence</div>
                                                    <div style="color: #1e293b; font-weight: 600; font-size: 1rem;">${cand.confidence.replace('_', ' ').toUpperCase()}</div>
                                                </div>
                                            </div>

                                            ${cand.score_breakdown ? `
                                            <details style="margin-top: 0.5rem;">
                                                <summary style="cursor: pointer; color: #64748b; font-size: 0.85rem; user-select: none;">
                                                    View Score Breakdown
                                                </summary>
                                                <div style="margin-top: 0.5rem; padding: 0.75rem; background: #f8fafc; border-radius: 6px; font-size: 0.85rem;">
                                                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 0.5rem;">
                                                        <div><strong>Amount Match:</strong> ${cand.score_breakdown.amount_score}/50 pts</div>
                                                        <div><strong>Date Match:</strong> ${cand.score_breakdown.date_score}/30 pts</div>
                                                        <div><strong>Currency Match:</strong> ${cand.score_breakdown.currency_score}/10 pts</div>
                                                        <div><strong>Status Score:</strong> ${cand.score_breakdown.status_score}/10 pts</div>
                                                    </div>
                                                </div>
                                            </details>
                                            ` : ''}
                                        </div>

                                        <button
                                            onclick="window.confirmPaymentMatch('${cand.invoice_number}', this)"
                                            style="background: #16a34a; color: white; border: none; padding: 0.75rem 1.25rem; border-radius: 8px; cursor: pointer; margin-left: 1rem; white-space: nowrap; font-weight: 600; box-shadow: 0 2px 4px rgba(0,0,0,0.1); transition: all 0.2s;"
                                            onmouseover="this.style.background='#15803d'; this.style.transform='translateY(-2px)'; this.style.boxShadow='0 4px 8px rgba(0,0,0,0.15)'"
                                            onmouseout="this.style.background='#16a34a'; this.style.transform='translateY(0)'; this.style.boxShadow='0 2px 4px rgba(0,0,0,0.1)'">
                                            Select This Invoice
                                        </button>
                                    </div>
                                </div>
                            `}).join('')}
                        </div>
                    `;
                }

                receiptResult.innerHTML = `
                    <div style="background: #dcfce7; border: 1px solid #86efac; border-radius: 8px; padding: 1rem;">
                        <h4 style="color: #166534; margin: 0 0 0.75rem 0;">Payment Receipt Processed & Matched Successfully!</h4>

                        <div style="background: white; border-radius: 6px; padding: 0.75rem; margin-bottom: 0.75rem;">
                            <div style="font-weight: 600; color: #1e293b; margin-bottom: 0.5rem;">Extracted Payment Data:</div>
                            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 0.5rem; font-size: 0.9rem;">
                                <div><strong>Date:</strong> ${paymentData.date || 'N/A'}</div>
                                <div><strong>Amount:</strong> $${paymentData.amount || 'N/A'} ${paymentData.currency || 'USDT'}</div>
                                <div><strong>Method:</strong> ${paymentData.method || 'N/A'}</div>
                                <div><strong>Confirmation:</strong> ${paymentData.confirmation_number || 'N/A'}</div>
                            </div>
                            <div style="margin-top: 0.5rem; font-size: 0.85rem; color: #64748b;">
                                <strong>Extraction Confidence:</strong> ${Math.round((paymentData.confidence || 0) * 100)}%
                            </div>
                        </div>

                        ${candidates.length === 0 ? `
                            <div style="background: #fef3c7; border: 1px solid #fbbf24; border-radius: 6px; padding: 0.75rem; margin-bottom: 0.75rem;">
                                <div style="color: #92400e; font-weight: 600; margin-bottom: 0.5rem;">⚠ No Matching Invoices Found</div>
                                <div style="color: #78350f; font-size: 0.9rem;">
                                    Could not find any invoices matching this payment amount and date.
                                </div>
                            </div>
                        ` : candidatesHTML}

                        <button onclick="location.reload()" style="background: #16a34a; color: white; border: none; padding: 0.5rem 1rem; border-radius: 6px; cursor: pointer; font-size: 1rem; margin-top: 0.5rem;">
                            Upload Another Receipt
                        </button>
                    </div>
                `;
            } else {
                receiptProgressBar.style.background = '#dc2626';
                receiptResult.innerHTML = `
                    <div style="background: #fee2e2; border: 1px solid #f87171; border-radius: 8px; padding: 1rem;">
                        <h4 style="color: #991b1b; margin: 0 0 0.5rem 0;">Upload Failed</h4>
                        <p style="color: #7f1d1d; margin: 0;">${result.error || 'Unknown error occurred'}</p>
                        <button onclick="location.reload()" style="margin-top: 0.75rem; background: #dc2626; color: white; border: none; padding: 0.5rem 1rem; border-radius: 6px; cursor: pointer;">
                            Try Again
                        </button>
                    </div>
                `;
            }

        } catch (error) {
            console.error('Error uploading receipt:', error);
            receiptProgressBar.style.width = '100%';
            receiptProgressBar.style.background = '#dc2626';

            receiptResult.style.display = 'block';
            receiptResult.innerHTML = `
                <div style="background: #fee2e2; border: 1px solid #f87171; border-radius: 8px; padding: 1rem;">
                    <h4 style="color: #991b1b; margin: 0 0 0.5rem 0;">Upload Error</h4>
                    <p style="color: #7f1d1d; margin: 0;">${error.message}</p>
                    <button onclick="location.reload()" style="margin-top: 0.75rem; background: #dc2626; color: white; border: none; padding: 0.5rem 1rem; border-radius: 6px; cursor: pointer;">
                        Try Again
                    </button>
                </div>
            `;
        }
    }

    // Global function to confirm a payment match
    window.confirmPaymentMatch = async function(invoiceNumber, button) {
        if (!window.pendingReceiptFile || !window.pendingPaymentData) {
            alert('Error: Payment data not available. Please try uploading again.');
            return;
        }

        const originalButtonText = button.textContent;
        button.textContent = 'Confirming...';
        button.disabled = true;

        try {
            // Get invoice ID by invoice number
            const invoicesResponse = await fetch(`/api/invoices?per_page=1000`);
            const invoicesData = await invoicesResponse.json();
            const invoice = invoicesData.invoices?.find(inv => inv.invoice_number === invoiceNumber);

            if (!invoice) {
                throw new Error(`Invoice ${invoiceNumber} not found`);
            }

            // Prepare form data
            const formData = new FormData();
            formData.append('file', window.pendingReceiptFile);
            formData.append('invoice_id', invoice.id);
            formData.append('payment_data', JSON.stringify(window.pendingPaymentData));

            // Call confirm endpoint
            const response = await fetch('/api/payment-proof/confirm-match', {
                method: 'POST',
                body: formData
            });

            const result = await response.json();

            if (result.success) {
                // Show success message with transaction candidates
                const receiptResult = document.getElementById('receipt-result');

                const transactionCandidates = result.transaction_candidates || [];
                const unlinkedCandidates = transactionCandidates.filter(t => !t.linked);

                let transactionMatchesHTML = '';
                if (unlinkedCandidates.length > 0) {
                    transactionMatchesHTML = `
                        <div style="background: white; border-radius: 6px; padding: 1rem; margin-bottom: 0.75rem;">
                            <div style="font-weight: 600; color: #1e293b; margin-bottom: 0.75rem;">
                                📊 Found ${unlinkedCandidates.length} Possible Transaction ${unlinkedCandidates.length === 1 ? 'Match' : 'Matches'}:
                            </div>
                            ${unlinkedCandidates.map((txn, idx) => {
                                const scoreColor = txn.match_score >= 80 ? '#10b981' : txn.match_score >= 60 ? '#f59e0b' : '#64748b';
                                return `
                                <div style="background: #f8fafc; border: 1px solid ${idx === 0 ? '#10b981' : '#e2e8f0'}; border-radius: 6px; padding: 1rem; margin-bottom: 0.75rem; position: relative;">
                                    ${idx === 0 ? '<div style="position: absolute; top: 0.5rem; right: 0.5rem; background: #10b981; color: white; padding: 0.25rem 0.5rem; border-radius: 4px; font-size: 0.7rem; font-weight: 600;">BEST MATCH</div>' : ''}

                                    <div style="display: flex; justify-content: space-between; align-items: start;">
                                        <div style="flex: 1;">
                                            <div style="font-weight: 600; color: #1e293b; margin-bottom: 0.5rem;">${txn.description}</div>

                                            <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 0.5rem; font-size: 0.85rem; margin-bottom: 0.5rem;">
                                                <div>
                                                    <div style="color: #94a3b8; font-size: 0.75rem;">Date</div>
                                                    <div style="color: #1e293b;">${txn.date}</div>
                                                    ${txn.date_diff_days > 0 ? `<div style="color: #94a3b8; font-size: 0.7rem;">${txn.date_diff_days} days diff</div>` : ''}
                                                </div>
                                                <div>
                                                    <div style="color: #94a3b8; font-size: 0.75rem;">Amount</div>
                                                    <div style="color: #1e293b;">$${Math.abs(txn.amount).toFixed(2)}</div>
                                                    ${txn.amount_diff > 0 ? `<div style="color: #94a3b8; font-size: 0.7rem;">$${txn.amount_diff} diff</div>` : ''}
                                                </div>
                                                <div>
                                                    <div style="color: #94a3b8; font-size: 0.75rem;">Category</div>
                                                    <div style="color: #1e293b;">${txn.category || 'N/A'}</div>
                                                </div>
                                                <div>
                                                    <div style="color: #94a3b8; font-size: 0.75rem;">Match Score</div>
                                                    <div style="color: ${scoreColor}; font-weight: 600;">${txn.match_score.toFixed(1)}%</div>
                                                </div>
                                            </div>
                                        </div>

                                        <button
                                            onclick="window.linkTransactionToInvoice('${result.invoice_id}', '${txn.id}', ${txn.match_score}, this)"
                                            style="background: #16a34a; color: white; border: none; padding: 0.5rem 1rem; border-radius: 6px; cursor: pointer; margin-left: 1rem; white-space: nowrap; font-size: 0.85rem;">
                                            Link Transaction
                                        </button>
                                    </div>
                                </div>
                            `}).join('')}
                        </div>
                    `;
                }

                receiptResult.innerHTML = `
                    <div style="background: #dcfce7; border: 1px solid #86efac; border-radius: 8px; padding: 1rem;">
                        <h4 style="color: #166534; margin: 0 0 0.75rem 0;">✓ Payment Confirmed Successfully!</h4>

                        <div style="background: white; border-radius: 6px; padding: 0.75rem; margin-bottom: 0.75rem;">
                            <div style="font-weight: 600; color: #1e293b; margin-bottom: 0.5rem;">Completed Actions:</div>
                            <div style="font-size: 0.9rem; color: #1e293b;">
                                ✓ Payment proof attached to invoice<br>
                                ✓ Payment record created<br>
                                ${result.transaction_linked ? `✓ Transaction auto-linked (Score: ${result.transaction_linked.match_score.toFixed(1)}%)` : '⚠ No transaction auto-linked (score < 80%)'}
                            </div>
                        </div>

                        ${transactionMatchesHTML}

                        <div style="margin-top: 0.75rem;">
                            <a href="/invoices" style="background: #16a34a; color: white; border: none; padding: 0.5rem 1rem; border-radius: 6px; text-decoration: none; display: inline-block; margin-right: 0.5rem;">
                                View Invoices
                            </a>
                            <button onclick="location.reload()" style="background: #6366f1; color: white; border: none; padding: 0.5rem 1rem; border-radius: 6px; cursor: pointer;">
                                Upload Another Receipt
                            </button>
                        </div>
                    </div>
                `;
            } else {
                throw new Error(result.error || 'Failed to confirm match');
            }

        } catch (error) {
            console.error('Error confirming match:', error);
            button.textContent = originalButtonText;
            button.disabled = false;
            alert(`Error confirming match: ${error.message}`);
        }
    };

    // Global function to link a transaction to an invoice
    window.linkTransactionToInvoice = async function(invoiceId, transactionId, matchScore, button) {
        if (!confirm(`Link this transaction to the invoice?\nMatch Score: ${matchScore.toFixed(1)}%`)) {
            return;
        }

        const originalButtonText = button.textContent;
        button.textContent = 'Linking...';
        button.disabled = true;

        try {
            const response = await fetch(`/api/invoices/${invoiceId}/link-transaction`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    transaction_id: transactionId,
                    match_score: matchScore
                })
            });

            const result = await response.json();

            if (result.success) {
                // Find the parent containers before removing
                const cardElement = button.closest('div[style*="background: #f8fafc"]');
                const whiteContainer = button.closest('div[style*="background: white"]');

                // Show success message first
                const tempMessage = document.createElement('div');
                tempMessage.style = 'background: #dcfce7; border: 1px solid #86efac; border-radius: 6px; padding: 0.75rem; margin-bottom: 0.75rem;';
                tempMessage.innerHTML = `
                    <div style="color: #166534; font-weight: 600;">✓ Transaction Linked Successfully!</div>
                    <div style="color: #16803d; font-size: 0.9rem; margin-top: 0.25rem;">
                        Match Score: ${matchScore.toFixed(1)}%<br>
                        ${result.enhanced_description ? `Updated: ${result.enhanced_description}` : ''}
                    </div>
                `;

                if (whiteContainer) {
                    whiteContainer.insertBefore(tempMessage, cardElement);
                }

                // Remove the card from display
                if (cardElement) {
                    cardElement.remove();
                }

                // Remove success message after 5 seconds
                setTimeout(() => {
                    if (tempMessage.parentNode) {
                        tempMessage.remove();
                    }
                }, 5000);
            } else {
                throw new Error(result.error || 'Failed to link transaction');
            }

        } catch (error) {
            console.error('Error linking transaction:', error);
            button.textContent = originalButtonText;
            button.disabled = false;
            alert(`Error linking transaction: ${error.message}`);
        }
    };

    // Load customers with invoices for filter dropdown
    async function loadCustomersForFilter() {
        try {
            const response = await fetch('/api/invoices/customers');
            const data = await response.json();

            if (data.success && data.customers) {
                // Clear loading option
                customerFilterSelect.innerHTML = '<option value="">All Customers (No Filter)</option>';

                // Add customers to dropdown
                data.customers.forEach(customer => {
                    const option = document.createElement('option');
                    option.value = customer.name;
                    option.textContent = `${customer.name} (${customer.invoice_count} ${customer.invoice_count === 1 ? 'invoice' : 'invoices'})`;
                    customerFilterSelect.appendChild(option);
                });
            }
        } catch (error) {
            console.error('Error loading customers:', error);
            customerFilterSelect.innerHTML = '<option value="">All Customers (No Filter)</option>';
        }
    }

    // Batch upload multiple receipts
    async function uploadMultipleReceipts(files) {
        // Show batch progress UI
        const batchProgress = document.getElementById('batch-progress-receipts');
        const progressText = document.getElementById('progress-text-receipts');
        const progressPercent = document.getElementById('progress-percent-receipts');
        const progressBar = document.getElementById('progress-bar-receipts');
        const currentFileText = document.getElementById('current-file-receipts');
        const resultsSummary = document.getElementById('results-summary-receipts');
        const successCountEl = document.getElementById('success-count-receipts');
        const errorCountEl = document.getElementById('error-count-receipts');
        const errorDetailsEl = document.getElementById('error-details-receipts');

        // Hide single upload UI, show batch UI
        if (receiptProgress) receiptProgress.style.display = 'none';
        if (receiptResult) receiptResult.style.display = 'none';
        batchProgress.style.display = 'block';
        resultsSummary.style.display = 'none';

        let successCount = 0;
        let errorCount = 0;
        const errors = [];

        // Process each file sequentially
        for (let i = 0; i < files.length; i++) {
            const file = files[i];
            const progress = Math.round(((i + 1) / files.length) * 100);

            // Update progress
            progressText.textContent = `${i + 1} / ${files.length}`;
            progressPercent.textContent = `${progress}%`;
            progressBar.style.width = `${progress}%`;
            currentFileText.textContent = `Processing: ${file.name}`;

            try {
                // Upload and process receipt
                const formData = new FormData();
                formData.append('file', file);

                // Get customer filter value
                const customerFilter = customerFilterSelect.value;
                let url = '/api/payment-proof/upload-and-confirm';
                if (customerFilter) {
                    url += `?customer_filter=${encodeURIComponent(customerFilter)}`;
                }

                const response = await fetch(url, {
                    method: 'POST',
                    body: formData
                });

                const result = await response.json();

                if (result.success) {
                    successCount++;
                } else {
                    errorCount++;
                    errors.push({ file: file.name, error: result.error || 'Unknown error' });
                }

            } catch (error) {
                errorCount++;
                errors.push({ file: file.name, error: error.message });
            }
        }

        // Show results
        currentFileText.textContent = 'Processing complete!';
        resultsSummary.style.display = 'block';
        successCountEl.textContent = successCount;
        errorCountEl.textContent = errorCount;

        // Show error details if any
        if (errors.length > 0) {
            errorDetailsEl.innerHTML = `
                <div style="background: #fee2e2; border: 1px solid #f87171; border-radius: 6px; padding: 1rem;">
                    <strong style="color: #991b1b;">Errors:</strong>
                    <div style="margin-top: 0.5rem; font-size: 0.85rem;">
                        ${errors.map(e => `<div style="color: #7f1d1d; margin: 0.25rem 0;">• ${e.file}: ${e.error}</div>`).join('')}
                    </div>
                </div>
            `;
        } else {
            errorDetailsEl.innerHTML = '';
        }

        // Reset file input
        fileInputReceipts.value = '';

        // Show completion message
        if (successCount === files.length) {
            setTimeout(() => {
                if (confirm('All receipts processed successfully! Reload page to see updated data?')) {
                    location.reload();
                }
            }, 1000);
        }
    }
});
