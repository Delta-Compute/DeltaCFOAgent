// Delta CFO Agent - Advanced Dashboard JavaScript

let currentTransactions = [];
let currentPage = 1;
let itemsPerPage = 50;
let totalPages = 1;
let isLoading = false;

document.addEventListener('DOMContentLoaded', function() {
    // Load initial data
    loadTransactions();

    // Set up event listeners
    setupEventListeners();
});

function setupEventListeners() {
    // Column sorting
    document.querySelectorAll('.sortable').forEach(th => {
        th.style.cursor = 'pointer';
        th.addEventListener('click', () => {
            const sortField = th.dataset.sort;
            sortTransactions(sortField);
        });
    });

    // Filter button
    document.getElementById('applyFilters').addEventListener('click', () => {
        currentPage = 1;
        loadTransactions();
    });

    // Clear filters button
    document.getElementById('clearFilters').addEventListener('click', clearFilters);

    // Refresh button
    document.getElementById('refreshData').addEventListener('click', () => {
        currentPage = 1;
        loadTransactions();
    });

    // Export CSV button
    document.getElementById('exportCSV').addEventListener('click', exportToCSV);

    // Quick filter buttons
    document.getElementById('filterTodos').addEventListener('click', () => {
        document.getElementById('needsReview').value = 'true';
        currentPage = 1;
        loadTransactions();
    });

    document.getElementById('filter2025').addEventListener('click', () => {
        document.getElementById('startDate').value = '2025-01-01';
        document.getElementById('endDate').value = '2025-12-31';
        currentPage = 1;
        loadTransactions();
    });

    document.getElementById('filter2024').addEventListener('click', () => {
        document.getElementById('startDate').value = '2024-01-01';
        document.getElementById('endDate').value = '2024-12-31';
        currentPage = 1;
        loadTransactions();
    });

    document.getElementById('filterYTD').addEventListener('click', () => {
        const now = new Date();
        document.getElementById('startDate').value = '2025-01-01';
        document.getElementById('endDate').value = now.toISOString().split('T')[0];
        currentPage = 1;
        loadTransactions();
    });

    // Pagination buttons
    document.getElementById('prevPage').addEventListener('click', () => {
        if (currentPage > 1) {
            currentPage--;
            loadTransactions();
        }
    });

    document.getElementById('nextPage').addEventListener('click', () => {
        if (currentPage < totalPages) {
            currentPage++;
            loadTransactions();
        }
    });

    // Modal close handlers
    document.querySelector('.close').addEventListener('click', closeModal);
    document.getElementById('suggestionsModal').addEventListener('click', (e) => {
        if (e.target.id === 'suggestionsModal') {
            closeModal();
        }
    });

    // Keyboard shortcuts
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') {
            closeModal();
        }
    });
}

function clearFilters() {
    // Clear all filter inputs
    document.getElementById('entityFilter').value = '';
    document.getElementById('transactionType').value = '';
    document.getElementById('sourceFile').value = '';
    document.getElementById('needsReview').value = '';
    document.getElementById('minAmount').value = '';
    document.getElementById('maxAmount').value = '';
    document.getElementById('startDate').value = '';
    document.getElementById('endDate').value = '';
    document.getElementById('keywordFilter').value = '';

    // Reset to first page and reload
    currentPage = 1;
    loadTransactions();
}

function buildFilterQuery() {
    const params = new URLSearchParams();

    const entity = document.getElementById('entityFilter').value;
    if (entity) params.append('entity', entity);

    const transactionType = document.getElementById('transactionType').value;
    if (transactionType) params.append('transaction_type', transactionType);

    const sourceFile = document.getElementById('sourceFile').value;
    if (sourceFile) params.append('source_file', sourceFile);

    const needsReview = document.getElementById('needsReview').value;
    if (needsReview) params.append('needs_review', needsReview);

    const minAmount = document.getElementById('minAmount').value;
    if (minAmount) params.append('min_amount', minAmount);

    const maxAmount = document.getElementById('maxAmount').value;
    if (maxAmount) params.append('max_amount', maxAmount);

    const startDate = document.getElementById('startDate').value;
    if (startDate) params.append('start_date', startDate);

    const endDate = document.getElementById('endDate').value;
    if (endDate) params.append('end_date', endDate);

    const keyword = document.getElementById('keywordFilter').value;
    if (keyword) params.append('keyword', keyword);

    // Add pagination
    params.append('page', currentPage);
    params.append('per_page', 50);

    return params.toString();
}

async function loadTransactions() {
    if (isLoading) return;

    try {
        isLoading = true;
        showLoadingState();

        const query = buildFilterQuery();
        const url = `/api/transactions?${query}`;

        const response = await fetch(url);
        const data = await response.json();

        if (data.error) {
            throw new Error(data.error);
        }

        currentTransactions = data.transactions || [];

        // Update pagination info
        if (data.pagination) {
            currentPage = data.pagination.page;
            totalPages = data.pagination.pages;
            updatePaginationControls();
        }

        renderTransactionTable(currentTransactions);
        updateTableInfo(data.pagination);

    } catch (error) {
        console.error('Error loading transactions:', error);
        showToast('Error loading transactions: ' + error.message, 'error');
        document.getElementById('transactionTableBody').innerHTML =
            '<tr><td colspan="9" class="loading">Error loading transactions</td></tr>';
    } finally {
        isLoading = false;
    }
}

function showLoadingState() {
    document.getElementById('transactionTableBody').innerHTML =
        '<tr><td colspan="9" class="loading">Loading transactions...</td></tr>';
    document.getElementById('tableInfo').textContent = 'Loading...';
}

function renderTransactionTable(transactions) {
    const tbody = document.getElementById('transactionTableBody');

    if (transactions.length === 0) {
        tbody.innerHTML = '<tr><td colspan="12" class="loading">No transactions found</td></tr>';
        return;
    }

    tbody.innerHTML = transactions.map(transaction => {
        const amount = parseFloat(transaction.amount || 0);
        const amountClass = amount > 0 ? 'amount-positive' : amount < 0 ? 'amount-negative' : '';
        const formattedAmount = Math.abs(amount).toLocaleString('en-US', {
            style: 'currency',
            currency: 'USD'
        });

        const confidence = transaction.confidence ?
            (parseFloat(transaction.confidence) * 100).toFixed(0) + '%' : 'N/A';

        let confidenceClass = 'confidence-high';
        if (transaction.confidence) {
            const conf = parseFloat(transaction.confidence);
            if (conf < 0.6) confidenceClass = 'confidence-low';
            else if (conf < 0.8) confidenceClass = 'confidence-medium';
        } else {
            confidenceClass = 'confidence-low';
        }

        return `
            <tr data-transaction-id="${transaction.transaction_id || ''}">
                <td>${formatDate(transaction.date) || 'N/A'}</td>
                <td class="editable-field" data-field="origin" data-transaction-id="${transaction.transaction_id}">
                    ${transaction.origin || 'Unknown'}
                    <button class="ai-suggestions-btn" title="Get AI suggestions">🤖</button>
                </td>
                <td class="editable-field" data-field="destination" data-transaction-id="${transaction.transaction_id}">
                    ${transaction.destination || 'Unknown'}
                    <button class="ai-suggestions-btn" title="Get AI suggestions">🤖</button>
                </td>
                <td class="editable-field" data-field="description" data-transaction-id="${transaction.transaction_id}">
                    ${transaction.description || 'N/A'}
                    <button class="ai-suggestions-btn" title="Get AI suggestions">🤖</button>
                </td>
                <td class="${amountClass}">${formattedAmount}</td>
                <td>${transaction.crypto_amount && transaction.currency !== 'USD' ? `${transaction.crypto_amount} ${transaction.currency}` : ''}</td>
                <td class="editable-field smart-dropdown" data-field="classified_entity" data-transaction-id="${transaction.transaction_id}">
                    ${transaction.classified_entity || 'N/A'} ▼
                    <button class="ai-suggestions-btn" title="Get AI suggestions">🤖</button>
                    ${(!transaction.classified_entity || transaction.classified_entity === 'N/A') ?
                        '<button class="smart-btn" onclick="quickSuggest(\''+transaction.transaction_id+'\', \'classified_entity\')">Smart</button>' : ''}
                </td>
                <td class="editable-field smart-dropdown" data-field="accounting_category" data-transaction-id="${transaction.transaction_id}">
                    ${transaction.accounting_category || 'N/A'} ▼
                    <button class="ai-suggestions-btn" title="Get AI suggestions">🤖</button>
                </td>
                <td class="editable-field" data-field="justification" data-transaction-id="${transaction.transaction_id}">
                    ${transaction.justification || 'N/A'}
                    <button class="ai-suggestions-btn" title="Get AI suggestions">🤖</button>
                </td>
                <td class="${confidenceClass}">
                    ${confidence}
                    ${(!transaction.confidence || parseFloat(transaction.confidence) < 0.8) ? ' <span title="Needs Review">⚠️</span>' : ''}
                </td>
                <td>${transaction.source_file || 'N/A'}</td>
                <td>
                    <button class="btn-secondary btn-sm" onclick="viewTransactionDetails('${transaction.transaction_id || ''}')">
                        View
                    </button>
                </td>
            </tr>
        `;
    }).join('');

    // Set up inline editing
    setupInlineEditing();
}

function setupInlineEditing() {
    document.querySelectorAll('.editable-field').forEach(field => {
        // Click to edit
        field.addEventListener('click', (e) => {
            if (e.target.classList.contains('ai-suggestions-btn')) {
                e.stopPropagation();
                showAISuggestions(field);
                return;
            }

            if (!field.classList.contains('editing')) {
                startEditing(field);
            }
        });

        // AI suggestions button
        const aiBtn = field.querySelector('.ai-suggestions-btn');
        if (aiBtn) {
            aiBtn.addEventListener('click', (e) => {
                e.stopPropagation();
                showAISuggestions(field);
            });
        }
    });
}

function startEditing(field) {
    const currentValue = field.textContent.trim();
    const fieldName = field.dataset.field;
    const transactionId = field.dataset.transactionId;

    field.classList.add('editing');

    // Check if this is a smart dropdown field
    if (field.classList.contains('smart-dropdown')) {
        createSmartDropdown(field, currentValue, fieldName);
    } else {
        field.innerHTML = `<input type="text" class="inline-input" value="${currentValue === 'N/A' ? '' : currentValue}" />`;
    }

    const input = field.querySelector('.inline-input, .smart-select');
    input.focus();
    if (input.select) input.select();

    // Save on Enter or blur
    const saveEdit = async () => {
        const newValue = input.value.trim();
        await updateTransactionField(transactionId, fieldName, newValue, field);
    };

    // Cancel on Escape
    const cancelEdit = () => {
        field.classList.remove('editing');
        field.innerHTML = `${currentValue}<button class="ai-suggestions-btn" title="Get AI suggestions">🤖</button>`;
        setupInlineEditing(); // Re-setup event listeners
    };

    input.addEventListener('blur', saveEdit);
    input.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') {
            e.preventDefault();
            saveEdit();
        } else if (e.key === 'Escape') {
            e.preventDefault();
            cancelEdit();
        }
    });
}

function createSmartDropdown(field, currentValue, fieldName) {
    // Define options for different field types
    const fieldOptions = {
        'classified_entity': [
            'Delta LLC',
            'Delta Prop Shop LLC',
            'Infinity Validator',
            'Delta Mining Paraguay S.A.',
            'Delta Brazil Operations',
            'Internal Transfer',
            'Personal'
        ],
        'accounting_category': [
            'Revenue - Trading',
            'Revenue - Mining',
            'Revenue - Challenge',
            'Interest Income',
            'Cost of Goods Sold (COGS)',
            'Technology Expenses',
            'General and Administrative',
            'Bank Fees',
            'Internal Transfer'
        ]
    };

    const options = fieldOptions[fieldName] || [];

    // Create smart dropdown with existing options + custom input
    let selectHTML = `<select class="smart-select inline-input">`;

    // Add current value as first option if not in list
    if (currentValue !== 'N/A' && !options.includes(currentValue)) {
        selectHTML += `<option value="${currentValue}" selected>${currentValue}</option>`;
    }

    // Add predefined options
    options.forEach(option => {
        const selected = option === currentValue ? 'selected' : '';
        selectHTML += `<option value="${option}" ${selected}>${option}</option>`;
    });

    // Add custom option
    selectHTML += `<option value="__custom__">+ Add Custom...</option>`;
    selectHTML += `</select>`;

    field.innerHTML = selectHTML;

    // Handle custom option selection
    const select = field.querySelector('.smart-select');
    select.addEventListener('change', function() {
        if (this.value === '__custom__') {
            // Replace with text input for custom entry
            field.innerHTML = `<input type="text" class="inline-input" value="" placeholder="Enter custom value..." />`;
            const input = field.querySelector('.inline-input');
            input.focus();
        }
    });
}

async function updateTransactionField(transactionId, field, value, fieldElement) {
    try {
        const response = await fetch('/api/update_transaction', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                transaction_id: transactionId,
                field: field,
                value: value
            })
        });

        const result = await response.json();

        if (result.success) {
            fieldElement.classList.remove('editing');
            fieldElement.innerHTML = `${value || 'N/A'}<button class="ai-suggestions-btn" title="Get AI suggestions">🤖</button>`;
            showToast('Transaction updated successfully', 'success');
            setupInlineEditing(); // Re-setup event listeners

            // For description changes, check if we should update similar transactions
            if (field === 'description') {
                checkForSimilarTransactions(transactionId, value);
            }

            // For entity changes, check if we should update similar transactions from same source
            if (field === 'classified_entity') {
                checkForSimilarEntities(transactionId, value);
            }

            // For accounting category changes, check if we should update similar transactions
            if (field === 'accounting_category') {
                checkForSimilarAccountingCategories(transactionId, value);
            }
            // For description changes, check if we should update similar transactions
            if (field === 'description') {
                checkForSimilarTransactions(transactionId, value);
            }
        } else {
            throw new Error(result.error || 'Failed to update');
        }

    } catch (error) {
        console.error('Error updating transaction:', error);
        showToast('Error updating transaction: ' + error.message, 'error');

        // Restore original value
        fieldElement.classList.remove('editing');
        const originalValue = fieldElement.dataset.originalValue || 'N/A';
        fieldElement.innerHTML = `${originalValue}<button class="ai-suggestions-btn" title="Get AI suggestions">🤖</button>`;
        setupInlineEditing();
    }
}

async function showAISuggestions(field) {
    const fieldType = field.dataset.field;
    const transactionId = field.dataset.transactionId;
    const currentValue = field.textContent.trim();

    try {
        showModal();
        document.getElementById('suggestionsList').innerHTML = '<div class="loading">Loading AI suggestions...</div>';

        const url = `/api/suggestions?field_type=${fieldType}&transaction_id=${transactionId}&current_value=${encodeURIComponent(currentValue)}`;
        const response = await fetch(url);
        const data = await response.json();

        if (data.error) {
            // Create a more descriptive error message
            const errorMsg = data.error.includes('ANTHROPIC_API_KEY')
                ? 'Claude AI not configured - contact administrator'
                : data.error.includes('failed to generate')
                ? 'AI service temporarily unavailable'
                : data.error;
            throw new Error(errorMsg);
        }

        if (data.suggestions && data.suggestions.length > 0) {
            document.getElementById('suggestionsList').innerHTML = data.suggestions.map(suggestion =>
                `<div class="suggestion-item" onclick="applySuggestion('${transactionId}', '${fieldType}', '${suggestion.replace(/'/g, "\\'")}', this)">${suggestion}</div>`
            ).join('') + `
                <div class="custom-input-section">
                    <input type="text" id="customInput" placeholder="Or type your own..." class="custom-input"
                           onkeypress="if(event.key==='Enter') applyCustomInput('${transactionId}', '${fieldType}')" />
                    <button onclick="applyCustomInput('${transactionId}', '${fieldType}')" class="apply-custom-btn">Apply</button>
                </div>
            `;
        } else {
            document.getElementById('suggestionsList').innerHTML = `
                <div class="loading">No AI suggestions available</div>
                <div class="custom-input-section">
                    <input type="text" id="customInput" placeholder="Type your custom value..." class="custom-input"
                           onkeypress="if(event.key==='Enter') applyCustomInput('${transactionId}', '${fieldType}')" />
                    <button onclick="applyCustomInput('${transactionId}', '${fieldType}')" class="apply-custom-btn">Apply</button>
                </div>
            `;
        }

    } catch (error) {
        console.error('Error getting AI suggestions:', error);
        let errorMessage = 'Error loading AI suggestions';

        // Check if the error response has more specific information
        if (error.message && error.message.includes('API')) {
            errorMessage = error.message;
        } else if (error instanceof TypeError) {
            errorMessage = 'Network error - check your connection';
        }

        document.getElementById('suggestionsList').innerHTML = `
            <div class="loading">${errorMessage}</div>
            <div class="custom-input-section">
                <input type="text" id="customInput" placeholder="Type your custom value..." class="custom-input"
                       onkeypress="if(event.key==='Enter') applyCustomInput('${transactionId}', '${fieldType}')" />
                <button onclick="applyCustomInput('${transactionId}', '${fieldType}')" class="apply-custom-btn">Apply</button>
            </div>
        `;
    }
}

async function applySuggestion(transactionId, field, value, element) {
    try {
        // Find the field element
        const fieldElement = document.querySelector(`[data-transaction-id="${transactionId}"][data-field="${field}"]`);

        if (fieldElement) {
            await updateTransactionField(transactionId, field, value, fieldElement);

            // Log user interaction for learning system
            await logUserInteraction(transactionId, field, fieldElement.textContent.trim(), value, 'accepted_ai_suggestion');

            // Remove the AI suggestion button after applying suggestion
            const aiBtn = fieldElement.querySelector('.ai-suggestions-btn');
            if (aiBtn) {
                aiBtn.remove();
            }

            // For description field, automatically check for similar transactions
            if (field === 'description') {
                checkForSimilarTransactions(transactionId, value);
            }

            closeModal();
        }
    } catch (error) {
        console.error('Error applying suggestion:', error);
        showToast('Error applying suggestion: ' + error.message, 'error');
    }
}

async function applyCustomInput(transactionId, fieldType) {
    try {
        const customInput = document.getElementById('customInput');
        const value = customInput.value.trim();

        if (!value) {
            showToast('Please enter a value', 'error');
            return;
        }

        // Find the field element
        const fieldElement = document.querySelector(`[data-transaction-id="${transactionId}"][data-field="${fieldType}"]`);

        if (fieldElement) {
            await updateTransactionField(transactionId, fieldType, value, fieldElement);

            // Log user interaction for learning system
            await logUserInteraction(transactionId, fieldType, fieldElement.textContent.trim(), value, 'custom_input');

            // Remove the AI suggestion button after applying custom input
            const aiBtn = fieldElement.querySelector('.ai-suggestions-btn');
            if (aiBtn) {
                aiBtn.remove();
            }

            // For description field, automatically check for similar transactions
            if (fieldType === 'description') {
                checkForSimilarTransactions(transactionId, value);
            }

            closeModal();
        }
    } catch (error) {
        console.error('Error applying custom input:', error);
        showToast('Error applying custom input: ' + error.message, 'error');
    }
}

async function checkForSimilarEntities(transactionId, newEntity) {
    try {
        // Find current transaction to get source file
        const currentTx = currentTransactions.find(t => t.transaction_id === transactionId);
        if (!currentTx) return;

        // Find similar transactions from same source file
        const similarTxs = currentTransactions.filter(t =>
            t.source_file === currentTx.source_file &&
            t.transaction_id !== transactionId &&
            (!t.classified_entity || t.classified_entity === 'N/A' || t.confidence < 0.7)
        );

        if (similarTxs.length > 0) {
            const modal = document.getElementById('suggestionsModal');
            const content = document.getElementById('suggestionsContent');

            content.innerHTML = `
                <h3>Update Similar Transactions?</h3>
                <p>Found ${similarTxs.length} similar transactions from ${currentTx.source_file}.</p>
                <p>Would you like to update their entity to "${newEntity}" as well?</p>
                <div class="suggestions-list">
                    ${similarTxs.slice(0, 5).map(t =>
                        `<div class="suggestion-item">${t.description.substring(0, 80)}...</div>`
                    ).join('')}
                    ${similarTxs.length > 5 ? `<div>... and ${similarTxs.length - 5} more</div>` : ''}
                </div>
                <button onclick="applyEntityToSimilar('${currentTx.source_file}', '${newEntity}')">Update All Similar</button>
                <button onclick="closeModal()">Skip</button>
            `;
            showModal();
        }
    } catch (error) {
        console.error('Error checking similar entities:', error);
    }
}

async function checkForSimilarAccountingCategories(transactionId, newCategory) {
    try {
        // Find current transaction to get context
        const currentTx = currentTransactions.find(t => t.transaction_id === transactionId);
        if (!currentTx) return;

        // Find similar transactions that might benefit from the same accounting category
        // Look for transactions with similar descriptions, amounts, or from same entity
        const similarTxs = currentTransactions.filter(t =>
            t.transaction_id !== transactionId &&
            (!t.accounting_category || t.accounting_category === 'N/A') &&
            (
                // Same entity classification
                (t.classified_entity === currentTx.classified_entity) ||
                // Similar description (first 20 characters)
                (t.description && currentTx.description &&
                 t.description.substring(0, 20).toLowerCase() === currentTx.description.substring(0, 20).toLowerCase()) ||
                // Same amount
                (Math.abs(parseFloat(t.amount) - parseFloat(currentTx.amount)) < 0.01)
            )
        );

        if (similarTxs.length > 0) {
            const modal = document.getElementById('suggestionsModal');
            const content = document.getElementById('suggestionsContent');

            content.innerHTML = `
                <h3>Update Similar Transactions?</h3>
                <p>Found ${similarTxs.length} similar transactions that might also be "${newCategory}".</p>
                <p>These transactions have similar characteristics (entity, description, or amount).</p>
                <div class="suggestions-list">
                    ${similarTxs.slice(0, 5).map(t =>
                        `<div class="suggestion-item">
                            <strong>${t.classified_entity || 'Unknown'}</strong> - ${t.description.substring(0, 60)}...
                            <span class="amount">$${parseFloat(t.amount || 0).toFixed(2)}</span>
                        </div>`
                    ).join('')}
                    ${similarTxs.length > 5 ? `<div>... and ${similarTxs.length - 5} more</div>` : ''}
                </div>
                <button onclick="applyCategoryToSimilar('${transactionId}', '${newCategory}')">Update All Similar</button>
                <button onclick="closeModal()">Skip</button>
            `;
            showModal();
        }
    } catch (error) {
        console.error('Error checking similar accounting categories:', error);
    }
}

async function applyCategoryToSimilar(transactionId, newCategory) {
    try {
        const response = await fetch('/api/update_similar_categories', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                transaction_id: transactionId,
                accounting_category: newCategory
            })
        });

        const data = await response.json();

        if (data.success) {
            // Reload the table to show updated transactions
            loadTransactions();
            closeModal();
            showNotification(`Updated ${data.updated_count} similar transactions with category: ${newCategory}`);
        } else {
            showNotification('Error updating similar transactions', 'error');
        }
    } catch (error) {
        console.error('Error applying category to similar transactions:', error);
        showNotification('Error updating similar transactions', 'error');
    }
}

async function applyToSimilar(transactionId, newDescription) {
    try {
        const response = await fetch('/api/update_similar_descriptions', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                transaction_id: transactionId,
                description: newDescription
            })
        });

        const data = await response.json();

        if (data.success) {
            // Reload the table to show updated transactions
            loadTransactions();
            closeModal();
            showNotification(`Updated ${data.updated_count} similar transactions with description: ${newDescription}`);
        } else {
            showNotification('Error updating similar transactions', 'error');
        }
    } catch (error) {
        console.error('Error applying description to similar transactions:', error);
        showNotification('Error updating similar transactions', 'error');
    }
}

async function checkForSimilarTransactions(transactionId, newDescription) {
    try {
        // Show loading modal first
        const modal = document.getElementById('suggestionsModal');
        const content = document.getElementById('suggestionsContent');

        // Clear suggestionsList to use suggestionsContent
        document.getElementById('suggestionsList').innerHTML = '';

        // Show loading state
        content.innerHTML = `
            <div class="ai-suggestion-header">
                <h3>🤖 AI Suggestion</h3>
            </div>
            <div class="loading-state" style="text-align: center; padding: 40px;">
                <div style="font-size: 24px; margin-bottom: 15px;">🔍</div>
                <p>Claude is analyzing similar transactions...</p>
                <div style="margin-top: 10px; color: #666; font-size: 14px;">This may take a few seconds</div>
            </div>
        `;

        // Show modal with loading state
        modal.style.display = 'block';

        // Get AI suggestions for similar transactions
        const response = await fetch(`/api/suggestions?transaction_id=${transactionId}&field_type=similar_descriptions&value=${encodeURIComponent(newDescription)}`);
        const data = await response.json();

        if (data.suggestions && data.suggestions.length > 0) {
            // Show enhanced modal matching the AI suggestion format
            const modal = document.getElementById('suggestionsModal');
            const content = document.getElementById('suggestionsContent');

            // Clear suggestionsList to use suggestionsContent
            document.getElementById('suggestionsList').innerHTML = '';

            content.innerHTML = `
                <div class="ai-suggestion-header">
                    <h3>🤖 AI Suggestion</h3>
                </div>

                <p>I found ${data.suggestions.length} similar transactions that might benefit from the same description:</p>

                <div class="ai-recommendation-section">
                    <h4>🤖 AI Recommendations:</h4>
                    <div class="standardized-recommendation">
                        <strong>Proposed description:</strong> "${newDescription}"
                    </div>
                </div>

                <div class="transaction-selection">
                    <div class="select-all-container">
                        <label class="checkbox-container">
                            <input type="checkbox" id="selectAllSimilar" onchange="toggleAllSimilarTransactions()" checked>
                            <span class="checkmark"></span>
                            Select All (${data.suggestions.length} transactions)
                        </label>
                    </div>

                    <div class="similar-transactions-list">
                        ${data.suggestions.map((tx, index) => `
                            <label class="checkbox-container transaction-item">
                                <input type="checkbox" class="similar-transaction-cb" data-transaction-id="${tx.transaction_id || ''}" checked>
                                <span class="checkmark"></span>
                                <div class="transaction-details">
                                    <div class="transaction-date">${tx.date || 'N/A'}</div>
                                    <div class="transaction-description">${tx.description}</div>
                                    <div class="transaction-confidence">Confidence: ${tx.confidence || 'N/A'}</div>
                                </div>
                            </label>
                        `).join('')}
                    </div>

                    <div class="selection-counter">
                        <span id="similarSelectionCounter">Selected: ${data.suggestions.length} of ${data.suggestions.length} transactions</span>
                    </div>
                </div>

                <div class="action-buttons">
                    <button class="btn-primary" onclick="applyToSelectedSimilar('${transactionId}', '${newDescription}')">Apply to Selected</button>
                    <button class="btn-secondary" onclick="closeModal()">Cancel</button>
                </div>
            `;
            showModal();
        } else {
            // No similar transactions found - just close the modal
            modal.style.display = 'none';
        }
    } catch (error) {
        console.error('Error checking similar transactions:', error);
        // Close modal on error
        const modal = document.getElementById('suggestionsModal');
        if (modal) modal.style.display = 'none';
    }
}

function toggleAllSimilarTransactions() {
    const selectAllCheckbox = document.getElementById('selectAllSimilar');
    const transactionCheckboxes = document.querySelectorAll('.similar-transaction-cb');

    transactionCheckboxes.forEach(cb => {
        cb.checked = selectAllCheckbox.checked;
    });

    updateSimilarSelectionCounter();
}

function updateSimilarSelectionCounter() {
    const checkboxes = document.querySelectorAll('.similar-transaction-cb');
    const selectedCount = document.querySelectorAll('.similar-transaction-cb:checked').length;
    const totalCount = checkboxes.length;

    const counter = document.getElementById('similarSelectionCounter');
    if (counter) {
        counter.textContent = `Selected: ${selectedCount} of ${totalCount} transactions`;
    }

    // Update "Select All" checkbox state
    const selectAllCheckbox = document.getElementById('selectAllSimilar');
    if (selectAllCheckbox) {
        selectAllCheckbox.checked = selectedCount === totalCount;
        selectAllCheckbox.indeterminate = selectedCount > 0 && selectedCount < totalCount;
    }
}

async function updateTransactionOnly(transactionId, field, value) {
    /**
     * Simple transaction update function without UI updates
     */
    const response = await fetch('/api/update_transaction', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            transaction_id: transactionId,
            field: field,
            value: value
        })
    });

    const result = await response.json();
    if (!result.success) {
        throw new Error(result.error || 'Failed to update transaction');
    }
    return result;
}

async function applyToSelectedSimilar(originalTransactionId, newDescription) {
    try {
        const selectedCheckboxes = document.querySelectorAll('.similar-transaction-cb:checked');
        const selectedTransactionIds = Array.from(selectedCheckboxes).map(cb => cb.dataset.transactionId);

        if (selectedTransactionIds.length === 0) {
            showToast('Please select at least one transaction to update', 'warning');
            return;
        }

        // Update each selected transaction
        const updatePromises = selectedTransactionIds.map(transactionId =>
            updateTransactionOnly(transactionId, 'description', newDescription)
        );

        await Promise.all(updatePromises);

        showToast(`Updated ${selectedTransactionIds.length} similar transactions`, 'success');
        closeModal();

        // Refresh the transaction list to show updates
        loadTransactions(currentPage, itemsPerPage);

    } catch (error) {
        console.error('Error applying to selected similar transactions:', error);
        showToast('Error updating selected transactions: ' + error.message, 'error');
    }
}

function showModal() {
    document.getElementById('suggestionsModal').style.display = 'block';
}

// Add event listener to update counter when individual checkboxes change
document.addEventListener('change', function(e) {
    if (e.target.classList.contains('similar-transaction-cb')) {
        updateSimilarSelectionCounter();
    }
});

function closeModal() {
    document.getElementById('suggestionsModal').style.display = 'none';
}

function showNotification(message, type = 'success') {
    // Simple notification using alert for now
    // Can be upgraded to a more sophisticated notification system later
    if (type === 'error') {
        alert(`Error: ${message}`);
    } else {
        alert(message);
    }
}

async function logUserInteraction(transactionId, fieldType, originalValue, userChoice, actionType) {
    try {
        // Get transaction context
        const transaction = currentTransactions.find(t => t.transaction_id === transactionId);
        if (!transaction) return;

        const context = {
            amount: transaction.amount,
            classified_entity: transaction.classified_entity,
            description: transaction.description,
            original_value: originalValue
        };

        const response = await fetch('/api/log_interaction', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                transaction_id: transactionId,
                field_type: fieldType,
                original_value: originalValue,
                user_choice: userChoice,
                action_type: actionType,
                transaction_context: context,
                session_id: `session_${Date.now()}`
            })
        });

        if (!response.ok) {
            console.error('Failed to log user interaction');
        }
    } catch (error) {
        console.error('Error logging user interaction:', error);
    }
}

function updateTableInfo(pagination) {
    const info = document.getElementById('tableInfo');

    if (pagination) {
        const start = ((pagination.page - 1) * pagination.per_page) + 1;
        const end = Math.min(pagination.page * pagination.per_page, pagination.total);
        info.textContent = `Showing ${start}-${end} of ${pagination.total} transactions`;
    } else {
        info.textContent = `Showing ${currentTransactions.length} transactions`;
    }
}

function updatePaginationControls() {
    const prevBtn = document.getElementById('prevPage');
    const nextBtn = document.getElementById('nextPage');
    const pageInfo = document.getElementById('pageInfo');

    prevBtn.disabled = currentPage <= 1;
    nextBtn.disabled = currentPage >= totalPages;
    pageInfo.textContent = `Page ${currentPage} of ${totalPages}`;
}

function viewTransactionDetails(id) {
    // Find the transaction
    const transaction = currentTransactions.find(t => t.transaction_id === id);
    if (transaction) {
        // Create a detailed view (could be a modal or new page)
        const details = Object.entries(transaction)
            .filter(([key, value]) => value != null && value !== '')
            .map(([key, value]) => `${key}: ${value}`)
            .join('\n');

        alert(`Transaction Details:\n\n${details}`);
    }
}

function quickSuggest(transactionId, fieldType) {
    // Quick AI suggestion for empty fields
    const fieldElement = document.querySelector(`[data-transaction-id="${transactionId}"][data-field="${fieldType}"]`);
    if (fieldElement) {
        showAISuggestions(fieldElement);
    }
}

function exportToCSV() {
    // Convert transactions to CSV
    const headers = [
        'Date', 'Description', 'Amount', 'Currency', 'Crypto Amount',
        'Origin', 'Destination', 'Entity', 'Accounting Category',
        'Justification', 'Confidence', 'Source File'
    ];

    const csvContent = [
        headers.join(','),
        ...currentTransactions.map(t => [
            t.date || '',
            `"${(t.description || '').replace(/"/g, '""')}"`,
            t.amount || 0,
            t.currency || 'USD',
            t.crypto_amount || '',
            `"${(t.origin || '').replace(/"/g, '""')}"`,
            `"${(t.destination || '').replace(/"/g, '""')}"`,
            `"${(t.classified_entity || '').replace(/"/g, '""')}"`,
            `"${(t.accounting_category || '').replace(/"/g, '""')}"`,
            `"${(t.justification || '').replace(/"/g, '""')}"`,
            t.confidence || 0,
            t.source_file || ''
        ].join(','))
    ].join('\n');

    // Download file
    const blob = new Blob([csvContent], { type: 'text/csv' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `transactions_export_${new Date().toISOString().split('T')[0]}.csv`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    window.URL.revokeObjectURL(url);

    showToast('Transactions exported successfully', 'success');
}

function showToast(message, type = 'success') {
    const container = document.getElementById('toastContainer');
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.textContent = message;

    container.appendChild(toast);

    // Trigger animation
    setTimeout(() => toast.classList.add('show'), 100);

    // Remove after 3 seconds
    setTimeout(() => {
        toast.classList.remove('show');
        setTimeout(() => container.removeChild(toast), 300);
    }, 3000);
}

// Format currency values
function formatCurrency(value) {
    const num = parseFloat(value || 0);
    return Math.abs(num).toLocaleString('en-US', {
        style: 'currency',
        currency: 'USD'
    });
}

// Format dates
let currentSortField = 'date';
let currentSortDirection = 'desc';

function sortTransactions(field) {
    if (field === currentSortField) {
        currentSortDirection = currentSortDirection === 'asc' ? 'desc' : 'asc';
    } else {
        currentSortField = field;
        currentSortDirection = 'asc';
    }

    currentTransactions.sort((a, b) => {
        let aVal = a[field];
        let bVal = b[field];

        // Handle nulls
        if (aVal === null || aVal === undefined) return 1;
        if (bVal === null || bVal === undefined) return -1;

        // Compare
        if (typeof aVal === 'number') {
            return currentSortDirection === 'asc' ? aVal - bVal : bVal - aVal;
        } else {
            const comparison = String(aVal).localeCompare(String(bVal));
            return currentSortDirection === 'asc' ? comparison : -comparison;
        }
    });

    renderTransactionTable(currentTransactions);
}

function formatDate(dateString) {
    if (!dateString) return 'N/A';
    try {
        const date = new Date(dateString);
        return date.toLocaleDateString('en-US');
    } catch {
        return dateString;
    }
}