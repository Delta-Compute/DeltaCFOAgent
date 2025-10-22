// Receipt Upload JavaScript
// Handles drag-and-drop, upload, processing, and matching workflow

let currentReceipt = null;
let selectedMatch = null;

// Initialize on page load
document.addEventListener('DOMContentLoaded', function() {
    initializeUploadArea();
    loadRecentReceipts();
});

function initializeUploadArea() {
    const uploadArea = document.getElementById('uploadArea');
    const fileInput = document.getElementById('fileInput');

    // Drag and drop handlers
    uploadArea.addEventListener('dragover', (e) => {
        e.preventDefault();
        uploadArea.classList.add('drag-over');
    });

    uploadArea.addEventListener('dragleave', (e) => {
        e.preventDefault();
        uploadArea.classList.remove('drag-over');
    });

    uploadArea.addEventListener('drop', (e) => {
        e.preventDefault();
        uploadArea.classList.remove('drag-over');

        const files = e.dataTransfer.files;
        if (files.length > 0) {
            handleFileUpload(files[0]);
        }
    });

    // File input change handler
    fileInput.addEventListener('change', (e) => {
        if (e.target.files.length > 0) {
            handleFileUpload(e.target.files[0]);
        }
    });
}

async function handleFileUpload(file) {
    // Validate file
    const validExtensions = ['.pdf', '.png', '.jpg', '.jpeg', '.heic', '.webp', '.tiff', '.tif'];
    const fileExtension = '.' + file.name.split('.').pop().toLowerCase();

    if (!validExtensions.includes(fileExtension)) {
        alert('Invalid file type. Please upload PDF or image files.');
        return;
    }

    if (file.size > 25 * 1024 * 1024) {
        alert('File too large. Maximum size is 25MB.');
        return;
    }

    // Show uploading state
    const uploadArea = document.getElementById('uploadArea');
    const uploadIcon = document.getElementById('uploadIcon');
    const uploadText = document.getElementById('uploadText');
    const uploadHint = document.getElementById('uploadHint');
    const progressInfo = document.getElementById('progressInfo');
    const progressText = document.getElementById('progressText');

    uploadArea.classList.add('uploading');
    uploadIcon.textContent = '⬆️';
    uploadText.textContent = 'Uploading...';
    uploadHint.textContent = file.name;

    // Show modal
    showModal();

    try {
        // Prepare form data
        const formData = new FormData();
        formData.append('file', file);
        formData.append('auto_process', 'true');

        // Upload and process
        progressText.textContent = 'Uploading file...';
        const response = await fetch('/api/receipts/upload', {
            method: 'POST',
            body: formData
        });

        if (!response.ok) {
            throw new Error('Upload failed');
        }

        const result = await response.json();

        if (!result.success) {
            throw new Error(result.error || 'Upload failed');
        }

        // Store current receipt
        currentReceipt = result;

        // Display results
        displayReceiptResults(result);

        // Reset upload area
        uploadArea.classList.remove('uploading');
        uploadIcon.textContent = '✅';
        uploadText.textContent = 'Upload Complete!';
        uploadHint.textContent = 'Upload another receipt';

        // Reload recent receipts
        setTimeout(() => {
            uploadIcon.textContent = '📄';
            uploadText.textContent = 'Drag & Drop Receipt Here';
            uploadHint.textContent = 'or click to browse files';
            document.getElementById('fileInput').value = '';
            loadRecentReceipts();
        }, 2000);

    } catch (error) {
        console.error('Upload error:', error);
        alert('Error uploading receipt: ' + error.message);

        // Reset upload area
        uploadArea.classList.remove('uploading');
        uploadIcon.textContent = '❌';
        uploadText.textContent = 'Upload Failed';
        uploadHint.textContent = 'Click to try again';

        setTimeout(() => {
            uploadIcon.textContent = '📄';
            uploadText.textContent = 'Drag & Drop Receipt Here';
            uploadHint.textContent = 'or click to browse files';
        }, 3000);

        closeModal();
    }
}

function showModal() {
    const modal = document.getElementById('processingModal');
    const modalLoading = document.getElementById('modalLoading');
    const modalResults = document.getElementById('modalResults');

    modal.classList.add('active');
    modalLoading.style.display = 'block';
    modalResults.style.display = 'none';
}

function closeModal() {
    const modal = document.getElementById('processingModal');
    modal.classList.remove('active');
    currentReceipt = null;
    selectedMatch = null;
}

function displayReceiptResults(result) {
    const modalTitle = document.getElementById('modalTitle');
    const modalLoading = document.getElementById('modalLoading');
    const modalResults = document.getElementById('modalResults');

    modalTitle.textContent = 'Receipt Processed';
    modalLoading.style.display = 'none';
    modalResults.style.display = 'block';

    // Display extracted data
    displayExtractedData(result.extracted_data);

    // Display matches
    displayMatches(result.matches || []);

    // Display categorization
    displayCategorization(result.extracted_data);
}

function displayExtractedData(data) {
    const grid = document.getElementById('extractedDataGrid');
    const confidenceBadge = document.getElementById('overallConfidence');

    if (!data) {
        grid.innerHTML = '<p style="color: #999;">No data extracted</p>';
        return;
    }

    // Build data grid
    let html = '';

    // Vendor
    if (data.vendor) {
        html += `
            <div class="data-item">
                <div class="data-label">Vendor</div>
                <div class="data-value">${escapeHtml(data.vendor)}</div>
            </div>
        `;
    }

    // Date
    if (data.date) {
        html += `
            <div class="data-item">
                <div class="data-label">Date</div>
                <div class="data-value">${escapeHtml(data.date)}</div>
            </div>
        `;
    }

    // Amount
    if (data.amount) {
        html += `
            <div class="data-item">
                <div class="data-label">Amount</div>
                <div class="data-value">$${data.amount.toFixed(2)} ${data.currency || 'USD'}</div>
            </div>
        `;
    }

    // Payment Method
    if (data.payment_method) {
        html += `
            <div class="data-item">
                <div class="data-label">Payment Method</div>
                <div class="data-value">${escapeHtml(data.payment_method)}</div>
            </div>
        `;
    }

    // Quality
    if (data.quality) {
        html += `
            <div class="data-item">
                <div class="data-label">Receipt Quality</div>
                <div class="data-value">${escapeHtml(data.quality)}</div>
            </div>
        `;
    }

    grid.innerHTML = html;

    // Confidence badge
    const confidence = data.confidence || 0;
    let badgeClass = 'confidence-low';
    if (confidence >= 0.8) badgeClass = 'confidence-high';
    else if (confidence >= 0.6) badgeClass = 'confidence-medium';

    confidenceBadge.innerHTML = `
        <span class="confidence-badge ${badgeClass}">
            ${(confidence * 100).toFixed(0)}% Confident
        </span>
    `;
}

function displayMatches(matches) {
    const matchesList = document.getElementById('matchesList');
    const confirmButton = document.getElementById('confirmButton');

    if (!matches || matches.length === 0) {
        matchesList.innerHTML = `
            <div class="no-matches-message">
                <p style="font-size: 1.1rem; margin-bottom: 1rem;">🔍 No matching transactions found</p>
                <p style="color: #999;">This might be a new transaction. You can create it manually in the dashboard.</p>
                <div class="create-transaction-suggestion">
                    <strong>Suggested New Transaction:</strong><br>
                    <span>${currentReceipt.extracted_data.description || 'New transaction'}</span>
                </div>
            </div>
        `;
        confirmButton.disabled = true;
        return;
    }

    // Build matches list
    let html = '';
    matches.forEach((match, index) => {
        const txData = match.transaction_data;
        const isFirst = index === 0;

        // Recommendation badge
        let recClass = 'rec-uncertain';
        let recText = 'Uncertain';
        if (match.recommendation === 'auto_apply') {
            recClass = 'rec-auto';
            recText = 'Auto-Apply (95%+)';
        } else if (match.recommendation === 'suggested') {
            recClass = 'rec-suggested';
            recText = 'Suggested (80-95%)';
        } else if (match.recommendation === 'possible') {
            recClass = 'rec-possible';
            recText = 'Possible (60-80%)';
        }

        html += `
            <div class="match-card ${isFirst ? 'selected' : ''}" onclick="selectMatch(${index})" data-match-index="${index}">
                <div class="match-header">
                    <span class="match-confidence">${(match.confidence * 100).toFixed(0)}% Match</span>
                    <span class="match-recommendation ${recClass}">${recText}</span>
                </div>
                <div class="match-details">
                    <div class="match-detail-row">
                        <strong>Description:</strong> ${escapeHtml(txData.description || 'N/A')}
                    </div>
                    <div class="match-detail-row">
                        <strong>Date:</strong> ${txData.date || 'N/A'} |
                        <strong>Amount:</strong> $${Math.abs(txData.amount || 0).toFixed(2)}
                    </div>
                    <div class="match-detail-row">
                        <strong>Entity:</strong> ${escapeHtml(txData.entity || 'N/A')}
                        ${txData.category ? ` | <strong>Category:</strong> ${escapeHtml(txData.category)}` : ''}
                    </div>
                    <div class="match-detail-row" style="font-size: 0.85rem; color: #999;">
                        <strong>Why:</strong> ${match.matching_strategies.join(', ')}
                    </div>
                </div>
            </div>
        `;
    });

    matchesList.innerHTML = html;

    // Select first match by default
    if (matches.length > 0) {
        selectedMatch = matches[0];
        confirmButton.disabled = false;
    }
}

function selectMatch(index) {
    const matches = currentReceipt.matches;
    if (!matches || index < 0 || index >= matches.length) return;

    selectedMatch = matches[index];

    // Update UI
    const matchCards = document.querySelectorAll('.match-card');
    matchCards.forEach((card, i) => {
        if (i === index) {
            card.classList.add('selected');
        } else {
            card.classList.remove('selected');
        }
    });

    // Enable confirm button
    document.getElementById('confirmButton').disabled = false;

    // Update categorization display
    displayCategorization(currentReceipt.extracted_data);
}

function displayCategorization(data) {
    const section = document.getElementById('categorizationSection');
    const info = document.getElementById('categorizationInfo');

    if (!data || !data.suggested_category) {
        section.style.display = 'none';
        return;
    }

    section.style.display = 'block';

    let html = '<div style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 1rem;">';

    if (data.suggested_category) {
        html += `
            <div class="data-item">
                <div class="data-label">Suggested Category</div>
                <div class="data-value">${escapeHtml(data.suggested_category)}</div>
            </div>
        `;
    }

    if (data.suggested_business_unit) {
        html += `
            <div class="data-item">
                <div class="data-label">Suggested Business Unit</div>
                <div class="data-value">${escapeHtml(data.suggested_business_unit)}</div>
            </div>
        `;
    }

    html += '</div>';
    info.innerHTML = html;
}

async function confirmMatch() {
    if (!selectedMatch || !currentReceipt) {
        alert('Please select a transaction match');
        return;
    }

    const confirmButton = document.getElementById('confirmButton');
    confirmButton.disabled = true;
    confirmButton.textContent = 'Linking...';

    try {
        const applyCateg = document.getElementById('applyCategorizationCheckbox').checked;

        const response = await fetch(`/api/receipts/${currentReceipt.receipt_id}/link`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                transaction_ids: [selectedMatch.transaction_id],
                apply_categorization: applyCateg
            })
        });

        if (!response.ok) {
            throw new Error('Failed to link receipt');
        }

        const result = await response.json();

        if (!result.success) {
            throw new Error(result.error || 'Failed to link receipt');
        }

        // Success!
        alert('✅ Receipt linked successfully!');
        closeModal();

        // Optionally redirect to transactions page
        // window.location.href = '/dashboard';

    } catch (error) {
        console.error('Link error:', error);
        alert('Error linking receipt: ' + error.message);
        confirmButton.disabled = false;
        confirmButton.textContent = 'Link Receipt to Transaction';
    }
}

async function loadRecentReceipts() {
    try {
        const response = await fetch('/api/receipts?limit=6');
        if (!response.ok) return;

        const result = await response.json();
        const receipts = result.receipts || [];

        if (receipts.length === 0) return;

        const recentSection = document.getElementById('recentReceipts');
        const receiptGrid = document.getElementById('receiptGrid');

        let html = '';
        receipts.forEach(receipt => {
            const uploadDate = new Date(receipt.uploaded_at).toLocaleString();
            html += `
                <div class="receipt-card">
                    <div class="receipt-filename" title="${escapeHtml(receipt.filename)}">
                        📄 ${escapeHtml(receipt.filename)}
                    </div>
                    <div class="receipt-meta">
                        <div>Uploaded: ${uploadDate}</div>
                        <div>Status: ${escapeHtml(receipt.status)}</div>
                        <div>Size: ${formatFileSize(receipt.file_size)}</div>
                    </div>
                </div>
            `;
        });

        receiptGrid.innerHTML = html;
        recentSection.style.display = 'block';

    } catch (error) {
        console.error('Error loading receipts:', error);
    }
}

function formatFileSize(bytes) {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
    return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
}

function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}
