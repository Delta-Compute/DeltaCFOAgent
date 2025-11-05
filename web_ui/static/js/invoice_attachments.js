/**
 * Invoice Attachments Manager
 * Handles file uploads, AI analysis, and attachment management for invoices
 */

window.InvoiceAttachments = (function() {
    'use strict';

    let currentInvoiceId = null;
    let attachments = [];

    /**
     * Initialize the attachments section for an invoice
     */
    function init(invoiceId) {
        currentInvoiceId = invoiceId;
        loadAttachments(invoiceId);
    }

    /**
     * Load all attachments for the current invoice
     */
    async function loadAttachments(invoiceId) {
        currentInvoiceId = invoiceId;

        try {
            const response = await fetch(`/api/invoices/${invoiceId}/attachments`);
            const data = await response.json();

            if (data.success) {
                attachments = data.attachments || [];
                renderAttachments();
            } else {
                showError('Failed to load attachments: ' + data.error);
            }
        } catch (error) {
            console.error('Error loading attachments:', error);
            showError('Error loading attachments: ' + error.message);
        }
    }

    /**
     * Render attachments list in the UI
     */
    function renderAttachments() {
        const section = document.getElementById('attachments-section');

        if (!attachments || attachments.length === 0) {
            section.innerHTML = `
                <div style="text-align: center; padding: 3rem; color: #94a3b8;">
                    <div style="font-size: 3rem; margin-bottom: 1rem;">📎</div>
                    <p>No attachments yet</p>
                    <button class="btn btn-primary" onclick="window.InvoiceAttachments.showUploadModal()">
                        Upload Attachment
                    </button>
                </div>
            `;
            return;
        }

        let html = `
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1.5rem;">
                <h3 style="margin: 0;">Attachments (${attachments.length})</h3>
                <button class="btn btn-primary btn-sm" onclick="window.InvoiceAttachments.showUploadModal()">
                    + Upload
                </button>
            </div>
            <div style="display: grid; gap: 1rem;">
        `;

        attachments.forEach(att => {
            const uploadedDate = new Date(att.uploaded_at).toLocaleDateString();
            const sizeKB = (att.file_size / 1024).toFixed(1);

            // Status badge
            let statusBadge = '';
            if (att.ai_analysis_status === 'analyzed') {
                statusBadge = '<span style="background: #10b981; color: white; padding: 0.25rem 0.5rem; border-radius: 4px; font-size: 0.75rem;">AI Analyzed</span>';
            } else if (att.ai_analysis_status === 'pending') {
                statusBadge = '<span style="background: #f59e0b; color: white; padding: 0.25rem 0.5rem; border-radius: 4px; font-size: 0.75rem;">Pending Analysis</span>';
            } else if (att.ai_analysis_status === 'failed') {
                statusBadge = '<span style="background: #ef4444; color: white; padding: 0.25rem 0.5rem; border-radius: 4px; font-size: 0.75rem;">Analysis Failed</span>';
            }

            html += `
                <div style="background: white; border: 1px solid #e2e8f0; border-radius: 8px; padding: 1rem;">
                    <div style="display: flex; justify-content: space-between; align-items: start;">
                        <div style="flex: 1;">
                            <div style="display: flex; align-items: center; gap: 0.5rem; margin-bottom: 0.5rem;">
                                <strong>${att.file_name}</strong>
                                ${statusBadge}
                            </div>
                            <div style="color: #64748b; font-size: 0.875rem;">
                                <div>Type: ${att.attachment_type || 'other'}</div>
                                <div>Size: ${sizeKB} KB</div>
                                <div>Uploaded: ${uploadedDate} by ${att.uploaded_by || 'system'}</div>
                                ${att.description ? `<div>Note: ${att.description}</div>` : ''}
                            </div>
                            ${att.ai_extracted_data ? renderAIData(att.ai_extracted_data) : ''}
                        </div>
                        <div style="display: flex; gap: 0.5rem; align-items: start;">
                            <button class="btn btn-sm btn-outline-primary" onclick="window.InvoiceAttachments.downloadAttachment('${att.id}')">
                                Download
                            </button>
                            ${att.ai_analysis_status === 'pending' || att.ai_analysis_status === 'failed' ? `
                                <button class="btn btn-sm btn-outline-success" onclick="window.InvoiceAttachments.analyzeAttachment('${att.id}')">
                                    Analyze
                                </button>
                            ` : ''}
                            <button class="btn btn-sm btn-outline-danger" onclick="window.InvoiceAttachments.deleteAttachment('${att.id}')">
                                Delete
                            </button>
                        </div>
                    </div>
                </div>
            `;
        });

        html += '</div>';
        section.innerHTML = html;
    }

    /**
     * Render AI extracted data in a readable format
     */
    function renderAIData(data) {
        if (!data || typeof data === 'string') {
            try {
                data = JSON.parse(data);
            } catch (e) {
                return '';
            }
        }

        let html = '<div style="margin-top: 0.75rem; padding: 0.75rem; background: #f1f5f9; border-radius: 4px; font-size: 0.875rem;">';
        html += '<strong style="color: #3b82f6;">AI Extracted Data:</strong><div style="margin-top: 0.5rem;">';

        if (data.payment_amount) {
            html += `<div>Amount: ${data.payment_currency || 'USD'} ${data.payment_amount}</div>`;
        }
        if (data.payment_date) {
            html += `<div>Date: ${data.payment_date}</div>`;
        }
        if (data.payment_method) {
            html += `<div>Method: ${data.payment_method}</div>`;
        }
        if (data.transaction_id) {
            html += `<div>Transaction ID: ${data.transaction_id}</div>`;
        }

        html += '</div></div>';
        return html;
    }

    /**
     * Show upload modal
     */
    function showUploadModal() {
        const modal = document.createElement('div');
        modal.className = 'modal active';
        modal.id = 'upload-attachment-modal';
        modal.innerHTML = `
            <div class="modal-content" style="max-width: 500px;">
                <div class="modal-header">
                    <div class="modal-title">Upload Attachment</div>
                    <button class="close-modal" onclick="window.InvoiceAttachments.closeUploadModal()">&times;</button>
                </div>
                <form id="upload-attachment-form" onsubmit="window.InvoiceAttachments.handleUpload(event)">
                    <div class="form-group">
                        <label for="attachment-file">File *</label>
                        <input type="file" id="attachment-file" required style="width: 100%; padding: 0.5rem; border: 1px solid #cbd5e1; border-radius: 4px;">
                    </div>
                    <div class="form-group">
                        <label for="attachment-type">Type</label>
                        <select id="attachment-type" style="width: 100%; padding: 0.5rem; border: 1px solid #cbd5e1; border-radius: 4px;">
                            <option value="payment_proof">Payment Proof</option>
                            <option value="invoice_pdf">Invoice PDF</option>
                            <option value="supporting_doc">Supporting Document</option>
                            <option value="contract">Contract</option>
                            <option value="other">Other</option>
                        </select>
                    </div>
                    <div class="form-group">
                        <label for="attachment-description">Description (optional)</label>
                        <textarea id="attachment-description" rows="3" style="width: 100%; padding: 0.5rem; border: 1px solid #cbd5e1; border-radius: 4px;"></textarea>
                    </div>
                    <div class="form-group">
                        <label style="display: flex; align-items: center; gap: 0.5rem;">
                            <input type="checkbox" id="attachment-analyze" checked>
                            <span>Analyze with AI immediately</span>
                        </label>
                    </div>
                    <div class="modal-footer" style="margin-top: 1.5rem; display: flex; gap: 0.5rem; justify-content: flex-end;">
                        <button type="button" class="btn btn-secondary" onclick="window.InvoiceAttachments.closeUploadModal()">Cancel</button>
                        <button type="submit" class="btn btn-primary">Upload</button>
                    </div>
                </form>
            </div>
        `;

        document.body.appendChild(modal);
    }

    /**
     * Close upload modal
     */
    function closeUploadModal() {
        const modal = document.getElementById('upload-attachment-modal');
        if (modal) {
            modal.remove();
        }
    }

    /**
     * Handle file upload
     */
    async function handleUpload(event) {
        event.preventDefault();

        const fileInput = document.getElementById('attachment-file');
        const typeSelect = document.getElementById('attachment-type');
        const descriptionInput = document.getElementById('attachment-description');
        const analyzeCheckbox = document.getElementById('attachment-analyze');

        if (!fileInput.files || fileInput.files.length === 0) {
            alert('Please select a file');
            return;
        }

        const formData = new FormData();
        formData.append('file', fileInput.files[0]);
        formData.append('attachment_type', typeSelect.value);
        formData.append('description', descriptionInput.value);
        formData.append('analyze_with_ai', analyzeCheckbox.checked);
        formData.append('uploaded_by', 'user'); // TODO: Get actual username

        try {
            // Show loading
            const submitBtn = event.target.querySelector('button[type="submit"]');
            const originalText = submitBtn.textContent;
            submitBtn.textContent = 'Uploading...';
            submitBtn.disabled = true;

            const response = await fetch(`/api/invoices/${currentInvoiceId}/attachments`, {
                method: 'POST',
                body: formData
            });

            const result = await response.json();
            console.log('Upload result:', result);

            if (result.success) {
                closeUploadModal();
                loadAttachments(currentInvoiceId);

                // Update badge count
                if (window.loadTabCounts) {
                    window.loadTabCounts(currentInvoiceId);
                }

                // Show matching transaction suggestions if found
                console.log('Checking for matching_transactions:', result.matching_transactions);
                if (result.matching_transactions && result.matching_transactions.length > 0) {
                    console.log('Found', result.matching_transactions.length, 'matching transactions - switching to matches tab');

                    // Show success message with timeout to allow it to be read
                    const matchCount = result.matching_transactions.length;
                    setTimeout(() => {
                        alert(result.message + `\n\nFound ${matchCount} matching transaction(s)!`);
                    }, 100);

                    // Switch to matches tab after a short delay
                    setTimeout(() => {
                        console.log('Switching to Transaction Matches tab...');

                        // Find and click the matches tab button
                        const tabButtons = document.querySelectorAll('.tab-btn');
                        console.log('Found', tabButtons.length, 'tab buttons');

                        for (let btn of tabButtons) {
                            console.log('Tab button text:', btn.textContent.trim());
                            if (btn.textContent.includes('Transaction Matches')) {
                                console.log('Clicking Transaction Matches tab');
                                btn.click();

                                // Force load after tab switch
                                setTimeout(() => {
                                    console.log('Forcing InvoiceMatches.load()');
                                    if (window.InvoiceMatches && window.InvoiceMatches.load) {
                                        window.InvoiceMatches.load(currentInvoiceId);
                                    }
                                }, 200);
                                break;
                            }
                        }
                    }, 500);
                } else {
                    console.log('No matching transactions found, showing alert');
                    alert(result.message || 'Attachment uploaded successfully!');
                }
            } else {
                alert('Upload failed: ' + result.error);
                submitBtn.textContent = originalText;
                submitBtn.disabled = false;
            }
        } catch (error) {
            console.error('Error uploading attachment:', error);
            alert('Error uploading attachment: ' + error.message);
        }
    }

    /**
     * Download attachment
     */
    async function downloadAttachment(attachmentId) {
        window.open(`/api/attachments/${attachmentId}/download`, '_blank');
    }

    /**
     * Trigger AI analysis for an attachment
     */
    async function analyzeAttachment(attachmentId) {
        if (!confirm('Analyze this attachment with AI? This may take a few moments.')) {
            return;
        }

        try {
            const response = await fetch(`/api/attachments/${attachmentId}/analyze`, {
                method: 'POST'
            });

            const result = await response.json();

            if (result.success) {
                alert('Analysis completed!');
                loadAttachments(currentInvoiceId);
            } else {
                alert('Analysis failed: ' + result.error);
            }
        } catch (error) {
            console.error('Error analyzing attachment:', error);
            alert('Error analyzing attachment: ' + error.message);
        }
    }

    /**
     * Delete attachment
     */
    async function deleteAttachment(attachmentId) {
        if (!confirm('Are you sure you want to delete this attachment? This cannot be undone.')) {
            return;
        }

        try {
            const response = await fetch(`/api/attachments/${attachmentId}`, {
                method: 'DELETE'
            });

            const result = await response.json();

            if (result.success) {
                loadAttachments(currentInvoiceId);

                // Update badge count
                if (window.loadTabCounts) {
                    window.loadTabCounts(currentInvoiceId);
                }

                alert('Attachment deleted successfully');
            } else {
                alert('Delete failed: ' + result.error);
            }
        } catch (error) {
            console.error('Error deleting attachment:', error);
            alert('Error deleting attachment: ' + error.message);
        }
    }

    /**
     * Show matching transaction suggestions modal after payment proof upload
     */
    function showMatchingSuggestionsModal(uploadResult) {
        const transactions = uploadResult.matching_transactions;
        const autoLinked = uploadResult.transaction_auto_linked;

        const modal = document.createElement('div');
        modal.className = 'modal active';
        modal.id = 'matching-suggestions-modal';

        let header = '';
        if (autoLinked) {
            header = `
                <div style="background: #d1fae5; color: #047857; padding: 1rem; border-radius: 8px; margin-bottom: 1rem;">
                    <strong>Transaction Auto-Linked!</strong><br>
                    A high-confidence match was found and linked automatically.
                </div>
            `;
        } else {
            header = `
                <div style="background: #fef3c7; color: #92400e; padding: 1rem; border-radius: 8px; margin-bottom: 1rem;">
                    <strong>Matching Transactions Found!</strong><br>
                    We found ${transactions.length} transaction(s) that may match this payment. Please review and select one to link.
                </div>
            `;
        }

        let transactionsHtml = transactions.map(txn => {
            const isPositive = txn.amount >= 0;
            const amountColor = isPositive ? '#10b981' : '#ef4444';

            let matchColor = '#94a3b8';
            let matchBg = '#f1f5f9';
            let matchLabel = 'Low';
            if (txn.match_score >= 80) {
                matchColor = '#10b981';
                matchBg = '#d1fae5';
                matchLabel = 'High';
            } else if (txn.match_score >= 60) {
                matchColor = '#f59e0b';
                matchBg = '#fef3c7';
                matchLabel = 'Medium';
            }

            const isAutoLinked = txn.auto_linked;

            return `
                <div style="background: ${isAutoLinked ? '#eff6ff' : 'white'};
                            border: 2px solid ${isAutoLinked ? '#3b82f6' : '#e2e8f0'};
                            border-radius: 8px; padding: 1rem; margin-bottom: 0.75rem;
                            ${isAutoLinked ? '' : 'cursor: pointer;'}
                            transition: all 0.2s;"
                     ${isAutoLinked ? '' : `onmouseover="this.style.borderColor='#3b82f6'; this.style.boxShadow='0 2px 8px rgba(59,130,246,0.1)'"
                     onmouseout="this.style.borderColor='#e2e8f0'; this.style.boxShadow='none'"
                     onclick="window.InvoiceAttachments.linkTransactionFromSuggestion('${txn.transaction_id}')"`}>

                    ${isAutoLinked ? '<div style="position: absolute; top: 0.5rem; right: 0.5rem; background: #3b82f6; color: white; padding: 0.25rem 0.5rem; border-radius: 4px; font-size: 0.75rem; font-weight: 600;">AUTO-LINKED</div>' : ''}

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
                                    ${txn.match_score}% ${matchLabel}
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
        }).join('');

        modal.innerHTML = `
            <div class="modal-content" style="max-width: 800px;">
                <div class="modal-header">
                    <div class="modal-title">Payment Proof Processed</div>
                    <button class="close-modal" onclick="window.InvoiceAttachments.closeMatchingSuggestionsModal()">&times;</button>
                </div>
                <div style="padding: 1.5rem;">
                    ${header}

                    <div style="margin-bottom: 1rem;">
                        <h3 style="margin: 0 0 0.75rem 0; font-size: 1rem; color: #475569;">
                            Matching Transaction${transactions.length > 1 ? 's' : ''}:
                        </h3>
                    </div>

                    <div style="max-height: 400px; overflow-y: auto;">
                        ${transactionsHtml}
                    </div>

                    <div style="margin-top: 1.5rem; padding-top: 1rem; border-top: 1px solid #e2e8f0; text-align: right;">
                        <button class="btn btn-primary" onclick="window.InvoiceAttachments.closeMatchingSuggestionsModal()">
                            ${autoLinked ? 'Done' : 'Skip for Now'}
                        </button>
                    </div>
                </div>
            </div>
        `;

        document.body.appendChild(modal);
    }

    /**
     * Link transaction from suggestion
     */
    async function linkTransactionFromSuggestion(transactionId) {
        try {
            const response = await fetch(`/api/invoices/${currentInvoiceId}/link-transaction`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ transaction_id: transactionId })
            });

            const result = await response.json();

            if (result.success) {
                closeMatchingSuggestionsModal();
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
     * Close matching suggestions modal
     */
    function closeMatchingSuggestionsModal() {
        const modal = document.getElementById('matching-suggestions-modal');
        if (modal) {
            modal.remove();
        }
    }

    /**
     * Show error message
     */
    function showError(message) {
        const section = document.getElementById('attachments-section');
        section.innerHTML = `
            <div style="text-align: center; padding: 2rem; color: #ef4444;">
                <p>${message}</p>
                <button class="btn btn-primary" onclick="window.InvoiceAttachments.loadAttachments('${currentInvoiceId}')">
                    Retry
                </button>
            </div>
        `;
    }

    // Public API
    return {
        init,
        loadAttachments,
        showUploadModal,
        closeUploadModal,
        handleUpload,
        downloadAttachment,
        analyzeAttachment,
        deleteAttachment,
        linkTransactionFromSuggestion,
        closeMatchingSuggestionsModal
    };
})();
