// Tenant Knowledge Management JavaScript
console.log('Tenant Knowledge JS loaded');

// State
let patterns = [];
let entities = [];
let currentEditingPattern = null;
let currentEditingEntity = null;

// ===================================
// TAB SWITCHING
// ===================================

document.addEventListener('DOMContentLoaded', () => {
    // Tab switching
    const tabButtons = document.querySelectorAll('.tab-button');
    const tabContents = document.querySelectorAll('.tab-content');

    tabButtons.forEach(button => {
        button.addEventListener('click', () => {
            const targetTab = button.dataset.tab;

            // Update active states
            tabButtons.forEach(btn => btn.classList.remove('active'));
            tabContents.forEach(content => content.classList.remove('active'));

            button.classList.add('active');
            document.getElementById(targetTab).classList.add('active');

            // Load data for the tab
            if (targetTab === 'patterns') {
                loadPatterns();
            } else if (targetTab === 'entities') {
                loadEntities();
            } else if (targetTab === 'bank-accounts') {
                window.accountsManager?.loadBankAccounts();
            } else if (targetTab === 'crypto-wallets') {
                window.accountsManager?.loadWallets();
            } else if (targetTab === 'notifications') {
                loadPageNotifications();
            } else if (targetTab === 'settings') {
                loadSettings();
            } else if (targetTab === 'classification-setup') {
                initClassificationSetup();
            }
        });
    });

    // Load initial tab data
    loadPatterns();
    updateSuggestionsBadge();

    // Event listeners
    document.getElementById('addPatternBtn')?.addEventListener('click', () => openPatternModal());
    document.getElementById('addEntityBtn')?.addEventListener('click', () => openEntityModal());
    document.getElementById('testPatternsBtn')?.addEventListener('click', () => openPatternTester());
    document.getElementById('reviewSuggestionsBtn')?.addEventListener('click', () => openSuggestionsModal());
    document.getElementById('runKnowledgeGenBtn')?.addEventListener('click', () => runKnowledgeGenerator());

    document.getElementById('patternForm')?.addEventListener('submit', savePattern);
    document.getElementById('entityForm')?.addEventListener('submit', saveEntity);
    document.getElementById('saveSettingsBtn')?.addEventListener('click', saveSettings);
    document.getElementById('addEntityRuleBtn')?.addEventListener('click', addEntityRule);

    // Show/hide Currency Filter based on pattern type selection
    document.getElementById('patternType')?.addEventListener('change', function() {
        const currencyFilterGroup = document.getElementById('currencyFilterGroup');
        if (this.value === 'regional') {
            currencyFilterGroup.style.display = 'block';
        } else {
            currencyFilterGroup.style.display = 'none';
        }
    });

    // Search
    document.getElementById('patternSearchInput')?.addEventListener('input', filterPatterns);
    document.getElementById('entitySearchInput')?.addEventListener('input', filterEntities);
    document.getElementById('categorySearchInput')?.addEventListener('input', filterCategories);
    document.getElementById('subcategorySearchInput')?.addEventListener('input', filterSubcategories);

    // Notification filter buttons
    document.getElementById('filterAllNotifications')?.addEventListener('click', () => loadPageNotifications(false));
    document.getElementById('filterUnreadNotifications')?.addEventListener('click', () => loadPageNotifications(true));
    document.getElementById('markAllReadBtn')?.addEventListener('click', markAllNotificationsAsRead);

    // Initialize AccountsManager
    window.accountsManager = new AccountsManager();
    window.accountsManager.init();
});

// ===================================
// CLASSIFICATION PATTERNS - CRUD
// ===================================

async function loadPatterns() {
    const patternsList = document.getElementById('patternsList');
    patternsList.innerHTML = '<div class="loading">Loading patterns...</div>';

    try {
        const response = await fetch('/api/classification-patterns');
        const data = await response.json();

        if (data.success) {
            patterns = data.patterns || [];
            renderPatterns(patterns);
            updatePatternStats();
        } else {
            patternsList.innerHTML = `<div class="empty-state">
                <div class="empty-state-icon">⚠️</div>
                <p>Error loading patterns: ${data.message}</p>
            </div>`;
        }
    } catch (error) {
        console.error('Error loading patterns:', error);
        patternsList.innerHTML = `<div class="empty-state">
            <div class="empty-state-icon">❌</div>
            <p>Failed to load patterns. Please try again.</p>
        </div>`;
    }
}

function renderPatterns(patternsToRender) {
    const patternsList = document.getElementById('patternsList');

    if (patternsToRender.length === 0) {
        patternsList.innerHTML = `<div class="empty-state">
            <div class="empty-state-icon">📋</div>
            <h3>No Classification Patterns Yet</h3>
            <p>Create your first pattern to start auto-classifying transactions</p>
        </div>`;
        return;
    }

    patternsList.innerHTML = patternsToRender.map(pattern => {
        const confBadge = pattern.confidence_score >= 0.8 ? 'high' :
                         pattern.confidence_score >= 0.5 ? 'medium' : 'low';

        // Strip wildcards from display
        const displayPattern = stripWildcards(pattern.description_pattern);

        return `
            <div class="pattern-card">
                <div class="pattern-header">
                    <div>
                        <div class="pattern-name">${escapeHtml(displayPattern)}</div>
                        <span class="badge badge-active">Active</span>
                        ${pattern.created_by === 'ai' ? '<span class="badge badge-ai" style="background-color: #8b5cf6; color: white; margin-left: 0.5rem;">AI Generated</span>' : ''}
                    </div>
                    <div class="button-group">
                        <button class="btn btn-test" onclick="testPattern(${pattern.pattern_id})">
                            Test
                        </button>
                        <button class="btn btn-edit" onclick="editPattern(${pattern.pattern_id})">
                            Edit
                        </button>
                        <button class="btn btn-delete" onclick="deletePattern(${pattern.pattern_id})">
                            Delete
                        </button>
                    </div>
                </div>
                <div class="pattern-details">
                    <div class="detail-item">
                        <div class="detail-label">Entity</div>
                        <div class="detail-value">${escapeHtml(pattern.entity || 'N/A')}</div>
                    </div>
                    <div class="detail-item">
                        <div class="detail-label">Type</div>
                        <div class="detail-value">${escapeHtml(pattern.pattern_type)}</div>
                    </div>
                    <div class="detail-item">
                        <div class="detail-label">Category</div>
                        <div class="detail-value">${escapeHtml(pattern.accounting_category || 'N/A')}</div>
                    </div>
                    <div class="detail-item">
                        <div class="detail-label">Confidence</div>
                        <div class="detail-value">
                            <span class="badge badge-${confBadge}">
                                ${(pattern.confidence_score * 100).toFixed(0)}%
                            </span>
                        </div>
                    </div>
                    ${pattern.usage_count ? `
                    <div class="detail-item">
                        <div class="detail-label">Usage Count</div>
                        <div class="detail-value">${pattern.usage_count}</div>
                    </div>
                    ` : ''}
                </div>
            </div>
        `;
    }).join('');
}

function updatePatternStats() {
    const total = patterns.length;
    const active = total; // All patterns are active in current schema
    const highConf = patterns.filter(p => p.confidence_score >= 0.8).length;

    document.getElementById('totalPatternsCount').textContent = total;
    document.getElementById('activePatternsCount').textContent = active;
    document.getElementById('highConfidenceCount').textContent = highConf;
}

function filterPatterns() {
    const search = document.getElementById('patternSearchInput').value.toLowerCase();

    if (!search) {
        renderPatterns(patterns);
        return;
    }

    const filtered = patterns.filter(p =>
        p.description_pattern.toLowerCase().includes(search) ||
        (p.entity && p.entity.toLowerCase().includes(search)) ||
        (p.accounting_category && p.accounting_category.toLowerCase().includes(search)) ||
        (p.pattern_type && p.pattern_type.toLowerCase().includes(search))
    );

    renderPatterns(filtered);
}

async function openPatternModal(patternId = null) {
    const modal = document.getElementById('patternModal');
    const title = document.getElementById('patternModalTitle');
    const form = document.getElementById('patternForm');
    const currencyFilterGroup = document.getElementById('currencyFilterGroup');

    // Load categories and subcategories dynamically
    await loadCategoriesForDropdown();
    await loadSubcategoriesForDropdown();

    if (patternId) {
        // Edit mode
        const pattern = patterns.find(p => p.pattern_id === patternId);
        if (!pattern) return;

        currentEditingPattern = pattern;
        title.textContent = 'Edit Classification Pattern';

        document.getElementById('patternId').value = pattern.pattern_id;
        // Strip wildcards from pattern for display
        document.getElementById('patternDescription').value = stripWildcards(pattern.description_pattern);
        document.getElementById('patternType').value = pattern.pattern_type;
        document.getElementById('patternEntity').value = pattern.entity || '';
        document.getElementById('patternCategory').value = pattern.accounting_category || '';
        document.getElementById('patternSubcategory').value = pattern.accounting_subcategory || '';
        document.getElementById('patternJustification').value = pattern.justification || '';
        document.getElementById('patternConfidence').value = pattern.confidence_score;
        document.getElementById('patternPriority').value = pattern.priority || 500;
        document.getElementById('patternIsActive').checked = pattern.is_active !== false;
        document.getElementById('patternNotes').value = pattern.notes || '';

        // Load currency filter if present
        document.getElementById('patternCurrency').value = pattern.currency || '';

        // Show/hide currency filter based on pattern type
        if (pattern.pattern_type === 'regional') {
            currencyFilterGroup.style.display = 'block';
        } else {
            currencyFilterGroup.style.display = 'none';
        }
    } else {
        // Create mode
        currentEditingPattern = null;
        title.textContent = 'Add Classification Pattern';
        form.reset();
        document.getElementById('patternId').value = '';
        document.getElementById('patternConfidence').value = '0.8';
        document.getElementById('patternPriority').value = '500';
        document.getElementById('patternIsActive').checked = true;

        // Hide currency filter by default
        currencyFilterGroup.style.display = 'none';
    }

    modal.classList.add('active');
}

async function loadCategoriesForDropdown() {
    try {
        const response = await fetch('/api/categories-with-counts');
        const data = await response.json();

        if (data.success && data.categories) {
            const categorySelect = document.getElementById('patternCategory');

            // Store current value if any
            const currentValue = categorySelect.value;

            // Clear existing options except the first one (placeholder)
            while (categorySelect.options.length > 1) {
                categorySelect.remove(1);
            }

            // Add categories from the database
            data.categories.forEach(category => {
                const option = document.createElement('option');
                option.value = category.name;
                option.textContent = category.name;
                categorySelect.appendChild(option);
            });

            // Restore previous value if it exists
            if (currentValue) {
                categorySelect.value = currentValue;
            }
        }
    } catch (error) {
        console.error('Error loading categories for dropdown:', error);
    }
}

async function loadSubcategoriesForDropdown() {
    try {
        const response = await fetch('/api/subcategories-with-counts');
        const data = await response.json();

        if (data.success && data.subcategories) {
            const subcategoryInput = document.getElementById('patternSubcategory');

            // Store current value
            const currentValue = subcategoryInput.value;

            // Create datalist if it doesn't exist
            let datalist = document.getElementById('subcategoryList');
            if (!datalist) {
                datalist = document.createElement('datalist');
                datalist.id = 'subcategoryList';
                subcategoryInput.setAttribute('list', 'subcategoryList');
                subcategoryInput.parentNode.appendChild(datalist);
            }

            // Clear existing options
            datalist.innerHTML = '';

            // Add subcategories
            data.subcategories.forEach(subcategory => {
                const option = document.createElement('option');
                option.value = subcategory.name;
                datalist.appendChild(option);
            });

            // Restore previous value
            if (currentValue) {
                subcategoryInput.value = currentValue;
            }
        }
    } catch (error) {
        console.error('Error loading subcategories for dropdown:', error);
    }
}

function closePatternModal() {
    document.getElementById('patternModal').classList.remove('active');
    currentEditingPattern = null;
}

async function savePattern(e) {
    e.preventDefault();

    const patternId = document.getElementById('patternId').value;
    const descriptionValue = document.getElementById('patternDescription').value.trim();
    const patternType = document.getElementById('patternType').value;
    const currencyValue = document.getElementById('patternCurrency').value;

    // Add wildcards automatically before saving
    const pattern = {
        description_pattern: addWildcards(descriptionValue),
        pattern_type: patternType,
        entity: document.getElementById('patternEntity').value.trim() || null,
        accounting_category: document.getElementById('patternCategory').value,
        accounting_subcategory: document.getElementById('patternSubcategory').value.trim() || null,
        justification: document.getElementById('patternJustification').value.trim() || null,
        confidence_score: parseFloat(document.getElementById('patternConfidence').value),
        priority: parseInt(document.getElementById('patternPriority').value) || 500,
        is_active: document.getElementById('patternIsActive').checked,
        notes: document.getElementById('patternNotes').value.trim() || null
    };

    // Include currency filter for regional patterns
    if (patternType === 'regional' && currencyValue) {
        pattern.currency = currencyValue;
    }

    try {
        const url = patternId ? `/api/classification-patterns/${patternId}` : '/api/classification-patterns';
        const method = patternId ? 'PUT' : 'POST';

        const response = await fetch(url, {
            method: method,
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(pattern)
        });

        const data = await response.json();

        if (data.success) {
            closePatternModal();
            loadPatterns();
            alert(patternId ? 'Pattern updated successfully!' : 'Pattern created successfully!');
        } else {
            alert('Error saving pattern: ' + data.message);
        }
    } catch (error) {
        console.error('Error saving pattern:', error);
        alert('Failed to save pattern. Please try again.');
    }
}

async function deletePattern(patternId) {
    const pattern = patterns.find(p => p.pattern_id === patternId);
    if (!pattern) return;

    const displayPattern = stripWildcards(pattern.description_pattern);
    if (!confirm(`Are you sure you want to delete this pattern?\n\nPattern: ${displayPattern}\nEntity: ${pattern.entity || 'N/A'}`)) {
        return;
    }

    try {
        const response = await fetch(`/api/classification-patterns/${patternId}`, {
            method: 'DELETE'
        });

        const data = await response.json();

        if (data.success) {
            loadPatterns();
            alert('Pattern deleted successfully!');
        } else {
            alert('Error deleting pattern: ' + data.message);
        }
    } catch (error) {
        console.error('Error deleting pattern:', error);
        alert('Failed to delete pattern. Please try again.');
    }
}

function editPattern(patternId) {
    openPatternModal(patternId);
}

async function testPattern(patternId) {
    const pattern = patterns.find(p => p.pattern_id === patternId);
    if (!pattern) return;

    try {
        const response = await fetch(`/api/classification-patterns/${patternId}/test`);
        const data = await response.json();

        if (data.success) {
            const matchCount = data.matches || 0;
            const message = matchCount > 0
                ? `✓ This pattern matches ${matchCount} transaction(s) in your database.`
                : '✗ This pattern does not match any transactions in your database.';

            const displayPattern = stripWildcards(pattern.description_pattern);
            alert(message + '\n\nPattern: ' + displayPattern);
        } else {
            alert('Error testing pattern: ' + data.message);
        }
    } catch (error) {
        console.error('Error testing pattern:', error);
        alert('Failed to test pattern. Please try again.');
    }
}

function openPatternTester() {
    alert('Pattern testing tool coming soon!\n\nThis will allow you to:\n- Test all patterns against a sample of transactions\n- See which patterns match which transactions\n- Identify conflicting patterns\n- Calculate accuracy metrics');
}

// ===================================
// BUSINESS ENTITIES - CRUD
// ===================================

async function loadEntities() {
    const entitiesList = document.getElementById('entitiesList');
    entitiesList.innerHTML = '<div class="loading">Loading entities...</div>';

    try {
        const response = await fetch('/api/business-entities');
        const data = await response.json();

        if (data.success) {
            entities = data.entities || [];
            renderEntities(entities);
            updateEntityStats();
        } else {
            entitiesList.innerHTML = `<div class="empty-state">
                <div class="empty-state-icon">⚠️</div>
                <p>Error loading entities: ${data.message}</p>
            </div>`;
        }
    } catch (error) {
        console.error('Error loading entities:', error);
        entitiesList.innerHTML = `<div class="empty-state">
            <div class="empty-state-icon">❌</div>
            <p>Failed to load entities. Please try again.</p>
        </div>`;
    }
}

function renderEntities(entitiesToRender) {
    const entitiesList = document.getElementById('entitiesList');

    if (entitiesToRender.length === 0) {
        entitiesList.innerHTML = `<div class="empty-state">
            <div class="empty-state-icon">🏢</div>
            <h3>No Business Entities Yet</h3>
            <p>Add your first business entity to start organizing your transactions</p>
        </div>`;
        return;
    }

    entitiesList.innerHTML = entitiesToRender.map(entity => `
        <div class="pattern-card">
            <div class="pattern-header">
                <div>
                    <div class="pattern-name" style="font-family: inherit;">${escapeHtml(entity.name)}</div>
                    ${entity.type ? `<span class="badge" style="background: #e0e7ff; color: #4338ca;">${escapeHtml(entity.type)}</span>` : ''}
                </div>
                <div class="button-group">
                    <button class="btn btn-edit" onclick="editEntity('${escapeHtml(entity.name)}')">
                        Edit
                    </button>
                    <button class="btn btn-delete" onclick="deleteEntity('${escapeHtml(entity.name)}')">
                        Delete
                    </button>
                </div>
            </div>
            ${entity.transaction_count ? `
            <div class="pattern-details">
                <div class="detail-item">
                    <div class="detail-label">Transactions</div>
                    <div class="detail-value">${entity.transaction_count}</div>
                </div>
            </div>
            ` : ''}
            ${entity.description ? `
            <div style="margin-top: 1rem; padding-top: 1rem; border-top: 1px solid #e2e8f0;">
                <div class="detail-label">Description</div>
                <div style="color: #64748b; font-size: 0.9rem;">${escapeHtml(entity.description)}</div>
            </div>
            ` : ''}
        </div>
    `).join('');
}

function updateEntityStats() {
    const total = entities.length;
    const totalTransactions = entities.reduce((sum, e) => sum + (e.transaction_count || 0), 0);

    document.getElementById('totalEntitiesCount').textContent = total;
    document.getElementById('transactionsWithEntities').textContent = totalTransactions;
}

function filterEntities() {
    const search = document.getElementById('entitySearchInput').value.toLowerCase();

    if (!search) {
        renderEntities(entities);
        return;
    }

    const filtered = entities.filter(e =>
        e.name.toLowerCase().includes(search) ||
        (e.type && e.type.toLowerCase().includes(search)) ||
        (e.description && e.description.toLowerCase().includes(search))
    );

    renderEntities(filtered);
}

function openEntityModal(entityName = null) {
    const modal = document.getElementById('entityModal');
    const title = document.getElementById('entityModalTitle');
    const form = document.getElementById('entityForm');
    const mergeSection = document.getElementById('entityMergeSection');
    const mergeSelect = document.getElementById('mergeTargetEntity');

    if (entityName) {
        // Edit mode
        const entity = entities.find(e => e.name === entityName);
        if (!entity) return;

        currentEditingEntity = entity;
        title.textContent = 'Edit Business Entity';

        document.getElementById('entityId').value = entity.name;
        document.getElementById('entityName').value = entity.name;
        document.getElementById('entityType').value = entity.type || '';
        document.getElementById('entityDescription').value = entity.description || '';

        // Enable name field for editing
        document.getElementById('entityName').readOnly = false;

        // Show hint about renaming
        const nameHint = document.getElementById('entityNameHint');
        if (nameHint) {
            nameHint.style.display = 'block';
        }

        // Show merge section and populate target entity dropdown
        mergeSection.style.display = 'block';

        // Clear and populate merge target dropdown
        mergeSelect.innerHTML = '<option value="">-- Select target entity --</option>';
        entities.forEach(e => {
            // Don't include the current entity in the merge targets
            if (e.name !== entityName) {
                const option = document.createElement('option');
                option.value = e.name;
                option.textContent = `${e.name}${e.transaction_count ? ` (${e.transaction_count} transactions)` : ''}`;
                mergeSelect.appendChild(option);
            }
        });
    } else {
        // Create mode
        currentEditingEntity = null;
        title.textContent = 'Add Business Entity';
        form.reset();
        document.getElementById('entityId').value = '';

        // Enable name field when creating
        document.getElementById('entityName').readOnly = false;

        // Hide hint for new entities
        const nameHint = document.getElementById('entityNameHint');
        if (nameHint) {
            nameHint.style.display = 'none';
        }

        // Hide merge section for new entities
        mergeSection.style.display = 'none';
    }

    modal.classList.add('active');
}

function closeEntityModal() {
    document.getElementById('entityModal').classList.remove('active');
    currentEditingEntity = null;
}

async function saveEntity(e) {
    e.preventDefault();

    const originalName = document.getElementById('entityId').value;
    const newName = document.getElementById('entityName').value.trim();
    const entity = {
        name: newName,
        type: document.getElementById('entityType').value || null,
        description: document.getElementById('entityDescription').value.trim() || null
    };

    // Validation
    if (!newName) {
        alert('Entity name is required.');
        return;
    }

    // If editing and name changed, confirm the rename
    if (originalName && originalName !== newName) {
        const confirmRename = confirm(`⚠️ Rename Entity\n\nThis will rename "${originalName}" to "${newName}" and update all associated transactions and patterns.\n\nAre you sure you want to proceed?`);

        if (!confirmRename) {
            return;
        }
    }

    try {
        const url = originalName ? `/api/business-entities/${encodeURIComponent(originalName)}` : '/api/business-entities';
        const method = originalName ? 'PUT' : 'POST';

        const response = await fetch(url, {
            method: method,
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(entity)
        });

        const data = await response.json();

        if (data.success) {
            closeEntityModal();
            loadEntities();

            // Show detailed message for renames
            if (originalName && originalName !== newName && data.transactions_updated !== undefined) {
                alert(`✓ Entity renamed successfully!\n\n"${originalName}" → "${newName}"\n\n${data.transactions_updated || 0} transactions updated\n${data.patterns_updated || 0} patterns updated`);
            } else {
                alert(originalName ? 'Entity updated successfully!' : 'Entity created successfully!');
            }
        } else {
            alert('Error saving entity: ' + data.message);
        }
    } catch (error) {
        console.error('Error saving entity:', error);
        alert('Failed to save entity. Please try again.');
    }
}

async function deleteEntity(entityName) {
    const entity = entities.find(e => e.name === entityName);
    if (!entity) return;

    const transactionWarning = entity.transaction_count > 0
        ? `\n\nWarning: This entity is used in ${entity.transaction_count} transaction(s). They will be set to 'Unknown Entity'.`
        : '';

    if (!confirm(`Are you sure you want to delete this entity?\n\nEntity: ${entityName}${transactionWarning}`)) {
        return;
    }

    try {
        const response = await fetch(`/api/business-entities/${encodeURIComponent(entityName)}`, {
            method: 'DELETE'
        });

        const data = await response.json();

        if (data.success) {
            loadEntities();
            alert('Entity deleted successfully!');
        } else {
            alert('Error deleting entity: ' + data.message);
        }
    } catch (error) {
        console.error('Error deleting entity:', error);
        alert('Failed to delete entity. Please try again.');
    }
}

function editEntity(entityName) {
    openEntityModal(entityName);
}

async function confirmMergeEntity() {
    const sourceEntity = document.getElementById('entityId').value;
    const targetEntity = document.getElementById('mergeTargetEntity').value;

    if (!targetEntity) {
        alert('Please select a target entity to merge into.');
        return;
    }

    const sourceEntityData = entities.find(e => e.name === sourceEntity);
    const targetEntityData = entities.find(e => e.name === targetEntity);

    if (!sourceEntityData || !targetEntityData) {
        alert('Error: Could not find entity data.');
        return;
    }

    const transactionCount = sourceEntityData.transaction_count || 0;

    const confirmMessage = `⚠️ MERGE CONFIRMATION ⚠️

This will:
  • Merge "${sourceEntity}" into "${targetEntity}"
  • Update ${transactionCount} transaction(s) to use "${targetEntity}"
  • Delete "${sourceEntity}" from the system

This action CANNOT be undone!

Are you absolutely sure you want to proceed?`;

    if (!confirm(confirmMessage)) {
        return;
    }

    // Second confirmation for safety
    const secondConfirm = confirm(`Final confirmation: Merge "${sourceEntity}" into "${targetEntity}"?`);

    if (!secondConfirm) {
        return;
    }

    await mergeEntity(sourceEntity, targetEntity);
}

async function mergeEntity(sourceEntity, targetEntity) {
    try {
        const response = await fetch(`/api/business-entities/${encodeURIComponent(sourceEntity)}/merge`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ target_entity: targetEntity })
        });

        const data = await response.json();

        if (data.success) {
            closeEntityModal();
            loadEntities();
            alert(`✓ Successfully merged "${sourceEntity}" into "${targetEntity}"!\n\n${data.transactions_updated || 0} transactions updated.`);
        } else {
            alert('Error merging entities: ' + data.message);
        }
    } catch (error) {
        console.error('Error merging entities:', error);
        alert('Failed to merge entities. Please try again.');
    }
}

// ===================================
// CATEGORIES MANAGEMENT
// ===================================

let categories = [];
let currentEditingCategory = null;

async function loadCategories() {
    const categoriesList = document.getElementById('categoriesList');
    categoriesList.innerHTML = '<div class="loading">Loading categories...</div>';

    try {
        const response = await fetch('/api/categories-with-counts');
        const data = await response.json();

        if (data.success) {
            categories = data.categories || [];
            renderCategories(categories);
        } else {
            categoriesList.innerHTML = `<div class="empty-state">
                <div class="empty-state-icon">⚠️</div>
                <p>Error loading categories: ${data.message}</p>
            </div>`;
        }
    } catch (error) {
        console.error('Error loading categories:', error);
        categoriesList.innerHTML = `<div class="empty-state">
            <div class="empty-state-icon">❌</div>
            <p>Failed to load categories. Please try again.</p>
        </div>`;
    }
}

function renderCategories(categoriesToRender) {
    const categoriesList = document.getElementById('categoriesList');

    if (categoriesToRender.length === 0) {
        categoriesList.innerHTML = `<div class="empty-state">
            <div class="empty-state-icon">📊</div>
            <h3>No Categories Found</h3>
            <p>Categories will appear here once transactions are categorized</p>
        </div>`;
        return;
    }

    categoriesList.innerHTML = categoriesToRender.map(category => `
        <div class="pattern-card" style="padding: 0.75rem 1rem;">
            <div class="pattern-header">
                <div>
                    <span style="font-weight: 500; font-size: 0.95rem;">${escapeHtml(category.name)}</span>
                    <span class="badge" style="background: #e0e7ff; color: #4338ca; margin-left: 0.5rem; font-size: 0.85rem;">
                        ${category.count} transactions
                    </span>
                </div>
                <div class="button-group">
                    <button class="btn btn-edit" onclick="renameCategory('${escapeHtml(category.name)}')" style="font-size: 0.85rem; padding: 0.4rem 0.8rem;">
                        Rename
                    </button>
                    <button class="btn" onclick="mergeCategory('${escapeHtml(category.name)}')" style="font-size: 0.85rem; padding: 0.4rem 0.8rem; background: #10b981;">
                        Merge
                    </button>
                </div>
            </div>
        </div>
    `).join('');
}

function filterCategories() {
    const search = document.getElementById('categorySearchInput').value.toLowerCase();

    if (!search) {
        renderCategories(categories);
        return;
    }

    const filtered = categories.filter(c =>
        c.name.toLowerCase().includes(search)
    );

    renderCategories(filtered);
}

async function renameCategory(categoryName) {
    const newName = prompt(`Rename category:\n\nCurrent name: ${categoryName}\n\nEnter new name:`, categoryName);

    if (!newName || newName.trim() === '' || newName === categoryName) {
        return;
    }

    const trimmedName = newName.trim();

    if (!confirm(`Rename "${categoryName}" to "${trimmedName}"?\n\nThis will update all associated transactions.`)) {
        return;
    }

    try {
        const response = await fetch(`/api/categories/${encodeURIComponent(categoryName)}/rename`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ new_name: trimmedName })
        });

        const data = await response.json();

        if (data.success) {
            alert(`✓ Category renamed successfully!\n\n${data.transactions_updated || 0} transactions updated.`);
            loadCategories();
        } else {
            alert('Error renaming category: ' + data.message);
        }
    } catch (error) {
        console.error('Error renaming category:', error);
        alert('Failed to rename category. Please try again.');
    }
}

async function mergeCategory(sourceCategoryName) {
    const targetCategory = prompt(
        `Merge "${sourceCategoryName}" into another category:\n\nEnter the target category name:`,
        ''
    );

    if (!targetCategory || targetCategory.trim() === '') {
        return;
    }

    const trimmedTarget = targetCategory.trim();

    if (trimmedTarget === sourceCategoryName) {
        alert('Source and target categories cannot be the same.');
        return;
    }

    const sourceData = categories.find(c => c.name === sourceCategoryName);
    const confirmMessage = `⚠️ MERGE CONFIRMATION ⚠️

This will:
  • Merge "${sourceCategoryName}" into "${trimmedTarget}"
  • Update ${sourceData?.count || 0} transaction(s)
  • Remove "${sourceCategoryName}" from the system

This action CANNOT be undone!

Are you sure you want to proceed?`;

    if (!confirm(confirmMessage)) {
        return;
    }

    try {
        const response = await fetch(`/api/categories/${encodeURIComponent(sourceCategoryName)}/merge`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ target_category: trimmedTarget })
        });

        const data = await response.json();

        if (data.success) {
            alert(`✓ Successfully merged "${sourceCategoryName}" into "${trimmedTarget}"!\n\n${data.transactions_updated || 0} transactions updated.`);
            loadCategories();
        } else {
            alert('Error merging categories: ' + data.message);
        }
    } catch (error) {
        console.error('Error merging categories:', error);
        alert('Failed to merge categories. Please try again.');
    }
}

// ===================================
// SUBCATEGORIES MANAGEMENT
// ===================================

let subcategories = [];
let currentEditingSubcategory = null;

async function loadSubcategories() {
    const subcategoriesList = document.getElementById('subcategoriesList');
    subcategoriesList.innerHTML = '<div class="loading">Loading subcategories...</div>';

    try {
        const response = await fetch('/api/subcategories-with-counts');
        const data = await response.json();

        if (data.success) {
            subcategories = data.subcategories || [];
            renderSubcategories(subcategories);
        } else {
            subcategoriesList.innerHTML = `<div class="empty-state">
                <div class="empty-state-icon">⚠️</div>
                <p>Error loading subcategories: ${data.message}</p>
            </div>`;
        }
    } catch (error) {
        console.error('Error loading subcategories:', error);
        subcategoriesList.innerHTML = `<div class="empty-state">
            <div class="empty-state-icon">❌</div>
            <p>Failed to load subcategories. Please try again.</p>
        </div>`;
    }
}

function renderSubcategories(subcategoriesToRender) {
    const subcategoriesList = document.getElementById('subcategoriesList');

    if (subcategoriesToRender.length === 0) {
        subcategoriesList.innerHTML = `<div class="empty-state">
            <div class="empty-state-icon">📋</div>
            <h3>No Subcategories Found</h3>
            <p>Subcategories will appear here once transactions are categorized</p>
        </div>`;
        return;
    }

    subcategoriesList.innerHTML = subcategoriesToRender.map(subcategory => `
        <div class="pattern-card" style="padding: 0.75rem 1rem;">
            <div class="pattern-header">
                <div>
                    <span style="font-weight: 500; font-size: 0.95rem;">${escapeHtml(subcategory.name)}</span>
                    <span class="badge" style="background: #e0e7ff; color: #4338ca; margin-left: 0.5rem; font-size: 0.85rem;">
                        ${subcategory.count} transactions
                    </span>
                </div>
                <div class="button-group">
                    <button class="btn btn-edit" onclick="renameSubcategory('${escapeHtml(subcategory.name)}')" style="font-size: 0.85rem; padding: 0.4rem 0.8rem;">
                        Rename
                    </button>
                    <button class="btn" onclick="mergeSubcategory('${escapeHtml(subcategory.name)}')" style="font-size: 0.85rem; padding: 0.4rem 0.8rem; background: #10b981;">
                        Merge
                    </button>
                </div>
            </div>
        </div>
    `).join('');
}

function filterSubcategories() {
    const search = document.getElementById('subcategorySearchInput').value.toLowerCase();

    if (!search) {
        renderSubcategories(subcategories);
        return;
    }

    const filtered = subcategories.filter(s =>
        s.name.toLowerCase().includes(search)
    );

    renderSubcategories(filtered);
}

async function renameSubcategory(subcategoryName) {
    const newName = prompt(`Rename subcategory:\n\nCurrent name: ${subcategoryName}\n\nEnter new name:`, subcategoryName);

    if (!newName || newName.trim() === '' || newName === subcategoryName) {
        return;
    }

    const trimmedName = newName.trim();

    if (!confirm(`Rename "${subcategoryName}" to "${trimmedName}"?\n\nThis will update all associated transactions.`)) {
        return;
    }

    try {
        const response = await fetch(`/api/subcategories/${encodeURIComponent(subcategoryName)}/rename`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ new_name: trimmedName })
        });

        const data = await response.json();

        if (data.success) {
            alert(`✓ Subcategory renamed successfully!\n\n${data.transactions_updated || 0} transactions updated.`);
            loadSubcategories();
        } else {
            alert('Error renaming subcategory: ' + data.message);
        }
    } catch (error) {
        console.error('Error renaming subcategory:', error);
        alert('Failed to rename subcategory. Please try again.');
    }
}

async function mergeSubcategory(sourceSubcategoryName) {
    const targetSubcategory = prompt(
        `Merge "${sourceSubcategoryName}" into another subcategory:\n\nEnter the target subcategory name:`,
        ''
    );

    if (!targetSubcategory || targetSubcategory.trim() === '') {
        return;
    }

    const trimmedTarget = targetSubcategory.trim();

    if (trimmedTarget === sourceSubcategoryName) {
        alert('Source and target subcategories cannot be the same.');
        return;
    }

    const sourceData = subcategories.find(s => s.name === sourceSubcategoryName);
    const confirmMessage = `⚠️ MERGE CONFIRMATION ⚠️

This will:
  • Merge "${sourceSubcategoryName}" into "${trimmedTarget}"
  • Update ${sourceData?.count || 0} transaction(s)
  • Remove "${sourceSubcategoryName}" from the system

This action CANNOT be undone!

Are you sure you want to proceed?`;

    if (!confirm(confirmMessage)) {
        return;
    }

    try {
        const response = await fetch(`/api/subcategories/${encodeURIComponent(sourceSubcategoryName)}/merge`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ target_subcategory: trimmedTarget })
        });

        const data = await response.json();

        if (data.success) {
            alert(`✓ Successfully merged "${sourceSubcategoryName}" into "${trimmedTarget}"!\n\n${data.transactions_updated || 0} transactions updated.`);
            loadSubcategories();
        } else {
            alert('Error merging subcategories: ' + data.message);
        }
    } catch (error) {
        console.error('Error merging subcategories:', error);
        alert('Failed to merge subcategories. Please try again.');
    }
}

// ===================================
// CLASSIFICATION SETUP TAB (3-column layout)
// ===================================

let classificationSetupInitialized = false;

async function initClassificationSetup() {
    // Check if tenant is a holdco (has more than 1 entity)
    const isHoldco = await checkIsHoldco();

    // Show/hide entities column based on holdco status
    const entitiesColumn = document.getElementById('entitiesColumn');
    const grid = document.querySelector('.classification-setup-grid');

    if (entitiesColumn && grid) {
        if (isHoldco) {
            entitiesColumn.style.display = 'flex';
            grid.classList.remove('two-columns');
        } else {
            entitiesColumn.style.display = 'none';
            grid.classList.add('two-columns');
        }
    }

    // Load all columns
    await Promise.all([
        loadEntitiesColumn(),
        loadCategoriesColumn(),
        loadSubcategoriesColumn()
    ]);

    classificationSetupInitialized = true;
}

async function checkIsHoldco() {
    try {
        const response = await fetch('/api/business-entities');
        const data = await response.json();

        if (data.success) {
            const entityCount = (data.entities || []).length;
            return entityCount > 1;
        }
        return false;
    } catch (error) {
        console.error('Error checking holdco status:', error);
        return false;
    }
}

// --- Entities Column ---
async function loadEntitiesColumn() {
    const entitiesList = document.getElementById('entitiesList');
    if (!entitiesList) return;

    entitiesList.innerHTML = '<div class="loading" style="padding: 1rem; text-align: center; color: #64748b;">Loading...</div>';

    try {
        const response = await fetch('/api/business-entities');
        const data = await response.json();

        if (data.success) {
            entities = data.entities || [];
            renderEntitiesColumn(entities);
        } else {
            entitiesList.innerHTML = '<div class="column-empty">Error loading entities</div>';
        }
    } catch (error) {
        console.error('Error loading entities:', error);
        entitiesList.innerHTML = '<div class="column-empty">Failed to load entities</div>';
    }
}

function renderEntitiesColumn(entitiesToRender) {
    const entitiesList = document.getElementById('entitiesList');
    if (!entitiesList) return;

    if (entitiesToRender.length === 0) {
        entitiesList.innerHTML = '<div class="column-empty">No entities found. Click + to add one.</div>';
        return;
    }

    entitiesList.innerHTML = entitiesToRender.map(entity => `
        <div class="column-item" data-entity="${escapeHtml(entity.name)}">
            <div class="column-item-name">${escapeHtml(entity.name)}</div>
            <div class="column-item-meta">
                ${entity.type ? `<span>${escapeHtml(entity.type)}</span>` : ''}
                ${entity.transaction_count ? `<span>${entity.transaction_count} txns</span>` : ''}
            </div>
            <div class="column-item-actions">
                <button class="column-item-btn edit" onclick="editEntity('${escapeHtml(entity.name)}')">Edit</button>
                <button class="column-item-btn delete" onclick="deleteEntity('${escapeHtml(entity.name)}')">Delete</button>
            </div>
        </div>
    `).join('');
}

// --- Categories Column ---
async function loadCategoriesColumn() {
    const categoriesList = document.getElementById('categoriesList');
    if (!categoriesList) return;

    categoriesList.innerHTML = '<div class="loading" style="padding: 1rem; text-align: center; color: #64748b;">Loading...</div>';

    try {
        const response = await fetch('/api/categories-with-counts');
        const data = await response.json();

        if (data.success) {
            categories = data.categories || [];
            renderCategoriesColumn(categories);
        } else {
            categoriesList.innerHTML = '<div class="column-empty">Error loading categories</div>';
        }
    } catch (error) {
        console.error('Error loading categories:', error);
        categoriesList.innerHTML = '<div class="column-empty">Failed to load categories</div>';
    }
}

function renderCategoriesColumn(categoriesToRender) {
    const categoriesList = document.getElementById('categoriesList');
    if (!categoriesList) return;

    if (categoriesToRender.length === 0) {
        categoriesList.innerHTML = '<div class="column-empty">No categories found. Categories are created from transaction classifications.</div>';
        return;
    }

    categoriesList.innerHTML = categoriesToRender.map(category => `
        <div class="column-item" data-category="${escapeHtml(category.name)}">
            <div class="column-item-name">${escapeHtml(category.name)}</div>
            <div class="column-item-meta">${category.count || 0} transactions</div>
            <div class="column-item-actions">
                <button class="column-item-btn edit" onclick="renameCategory('${escapeHtml(category.name)}')">Rename</button>
                <button class="column-item-btn edit" onclick="mergeCategory('${escapeHtml(category.name)}')" style="background: #dcfce7; color: #166534;">Merge</button>
            </div>
        </div>
    `).join('');
}

// --- Subcategories Column ---
async function loadSubcategoriesColumn() {
    const subcategoriesList = document.getElementById('subcategoriesList');
    if (!subcategoriesList) return;

    subcategoriesList.innerHTML = '<div class="loading" style="padding: 1rem; text-align: center; color: #64748b;">Loading...</div>';

    try {
        const response = await fetch('/api/subcategories-with-counts');
        const data = await response.json();

        if (data.success) {
            subcategories = data.subcategories || [];
            renderSubcategoriesColumn(subcategories);
        } else {
            subcategoriesList.innerHTML = '<div class="column-empty">Error loading subcategories</div>';
        }
    } catch (error) {
        console.error('Error loading subcategories:', error);
        subcategoriesList.innerHTML = '<div class="column-empty">Failed to load subcategories</div>';
    }
}

function renderSubcategoriesColumn(subcategoriesToRender) {
    const subcategoriesList = document.getElementById('subcategoriesList');
    if (!subcategoriesList) return;

    if (subcategoriesToRender.length === 0) {
        subcategoriesList.innerHTML = '<div class="column-empty">No subcategories found. Subcategories are created from transaction classifications.</div>';
        return;
    }

    subcategoriesList.innerHTML = subcategoriesToRender.map(subcategory => `
        <div class="column-item" data-subcategory="${escapeHtml(subcategory.name)}">
            <div class="column-item-name">${escapeHtml(subcategory.name)}</div>
            <div class="column-item-meta">${subcategory.count || 0} transactions</div>
            <div class="column-item-actions">
                <button class="column-item-btn edit" onclick="renameSubcategory('${escapeHtml(subcategory.name)}')">Rename</button>
                <button class="column-item-btn edit" onclick="mergeSubcategory('${escapeHtml(subcategory.name)}')" style="background: #dcfce7; color: #166534;">Merge</button>
            </div>
        </div>
    `).join('');
}

// --- Column Search Filters ---
function filterEntitiesColumn() {
    const search = document.getElementById('entitySearchInput')?.value.toLowerCase() || '';

    if (!search) {
        renderEntitiesColumn(entities);
        return;
    }

    const filtered = entities.filter(e =>
        e.name.toLowerCase().includes(search) ||
        (e.type && e.type.toLowerCase().includes(search))
    );

    renderEntitiesColumn(filtered);
}

function filterCategoriesColumn() {
    const search = document.getElementById('categorySearchInput')?.value.toLowerCase() || '';

    if (!search) {
        renderCategoriesColumn(categories);
        return;
    }

    const filtered = categories.filter(c =>
        c.name.toLowerCase().includes(search)
    );

    renderCategoriesColumn(filtered);
}

function filterSubcategoriesColumn() {
    const search = document.getElementById('subcategorySearchInput')?.value.toLowerCase() || '';

    if (!search) {
        renderSubcategoriesColumn(subcategories);
        return;
    }

    const filtered = subcategories.filter(s =>
        s.name.toLowerCase().includes(search)
    );

    renderSubcategoriesColumn(filtered);
}

// Update the search event listeners for columns
document.addEventListener('DOMContentLoaded', function() {
    // Column search listeners
    document.getElementById('entitySearchInput')?.addEventListener('input', filterEntitiesColumn);
    document.getElementById('categorySearchInput')?.addEventListener('input', filterCategoriesColumn);
    document.getElementById('subcategorySearchInput')?.addEventListener('input', filterSubcategoriesColumn);
});

// ===================================
// SETTINGS
// ===================================

let entityRules = [];

async function loadSettings() {
    try {
        const response = await fetch('/api/tenant-settings');
        const data = await response.json();

        if (data.success && data.settings) {
            document.getElementById('minConfidenceThreshold').value = data.settings.min_confidence_threshold || 0.5;
            document.getElementById('autoLearningEnabled').value = data.settings.auto_learning_enabled ? 'true' : 'false';
            document.getElementById('patternMinOccurrences').value = data.settings.pattern_min_occurrences || 3;

            // Load entity rules
            entityRules = data.settings.entity_rules || [];
            renderEntityRules();
        }
    } catch (error) {
        console.error('Error loading settings:', error);
    }
}

function renderEntityRules() {
    const container = document.getElementById('entityRulesContainer');

    if (entityRules.length === 0) {
        container.innerHTML = `
            <div style="padding: 1rem; background: #f8fafc; border-radius: 6px; color: #64748b; text-align: center;">
                No entity rules defined. Click "Add Entity Rule" to create one.
            </div>
        `;
        return;
    }

    container.innerHTML = entityRules.map((rule, index) => `
        <div class="pattern-card" style="padding: 1rem; margin-bottom: 0.75rem; border-left: 4px solid #10b981;">
            <div class="pattern-header" style="margin-bottom: 0;">
                <div style="flex: 1;">
                    <div style="font-weight: 600; font-size: 1rem; margin-bottom: 0.5rem;">
                        Entity: <span style="color: #7c3aed;">${escapeHtml(rule.entity)}</span>
                    </div>
                    <div style="font-size: 0.9rem; color: #64748b;">
                        → Category: <strong>${escapeHtml(rule.category)}</strong>
                        ${rule.subcategory ? ` | Subcategory: <strong>${escapeHtml(rule.subcategory)}</strong>` : ''}
                    </div>
                </div>
                <button class="btn btn-delete" onclick="removeEntityRule(${index})" style="padding: 0.4rem 0.8rem; font-size: 0.85rem;">
                    Remove
                </button>
            </div>
        </div>
    `).join('');
}

function addEntityRule() {
    const entity = prompt('Enter the entity name (e.g., Personal, Company):');
    if (!entity || !entity.trim()) return;

    const category = prompt('Enter the category (e.g., Personal_Expense, Operating_Expense):');
    if (!category || !category.trim()) return;

    const subcategory = prompt('Enter the subcategory (optional):');

    entityRules.push({
        entity: entity.trim(),
        category: category.trim(),
        subcategory: subcategory && subcategory.trim() ? subcategory.trim() : ''
    });

    renderEntityRules();
}

function removeEntityRule(index) {
    if (!confirm('Remove this entity rule?')) return;

    entityRules.splice(index, 1);
    renderEntityRules();
}

async function saveSettings() {
    const settings = {
        min_confidence_threshold: parseFloat(document.getElementById('minConfidenceThreshold').value),
        auto_learning_enabled: document.getElementById('autoLearningEnabled').value === 'true',
        pattern_min_occurrences: parseInt(document.getElementById('patternMinOccurrences').value),
        entity_rules: entityRules
    };

    try {
        const response = await fetch('/api/tenant-settings', {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(settings)
        });

        const data = await response.json();

        if (data.success) {
            alert('Settings saved successfully!');
        } else {
            alert('Error saving settings: ' + data.message);
        }
    } catch (error) {
        console.error('Error saving settings:', error);
        alert('Failed to save settings. Please try again.');
    }
}

// ===================================
// UTILITIES
// ===================================

function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Helper functions for SQL LIKE wildcards
function stripWildcards(pattern) {
    if (!pattern) return '';
    // Remove leading and trailing % wildcards
    return pattern.replace(/^%+|%+$/g, '').trim();
}

function addWildcards(pattern) {
    if (!pattern) return '';
    const clean = pattern.trim();
    if (!clean) return '';

    // Add % wildcards at start and end if not already present
    let result = clean;
    if (!result.startsWith('%')) {
        result = '%' + result;
    }
    if (!result.endsWith('%')) {
        result = result + '%';
    }
    return result;
}

// ===================================
// ACCOUNTS MANAGEMENT (Bank Accounts & Crypto Wallets)
// ===================================

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
        // Add buttons
        document.getElementById('addBankAccountBtn')?.addEventListener('click', () => this.openBankModal());
        document.getElementById('addWalletBtn')?.addEventListener('click', () => this.openWalletModal());

        // Form submissions
        document.getElementById('bankAccountForm')?.addEventListener('submit', (e) => this.saveBankAccount(e));
        document.getElementById('walletForm')?.addEventListener('submit', (e) => this.saveWallet(e));

        // Modal close on background click
        document.getElementById('bankAccountModal')?.addEventListener('click', (e) => {
            if (e.target.id === 'bankAccountModal') closeBankModal();
        });
        document.getElementById('walletModal')?.addEventListener('click', (e) => {
            if (e.target.id === 'walletModal') closeWalletModal();
        });
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
                            ${escapeHtml(account.account_name)}
                            ${account.is_primary ? '<span class="primary-badge">PRIMARY</span>' : ''}
                        </div>
                        <div style="color: #64748b; margin-top: 0.25rem;">
                            ${escapeHtml(account.institution_name)}
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
                            <div class="detail-value">${escapeHtml(account.account_number)}</div>
                        </div>
                    ` : ''}
                    ${account.routing_number ? `
                        <div class="detail-item">
                            <div class="detail-label">Routing Number</div>
                            <div class="detail-value">${escapeHtml(account.routing_number)}</div>
                        </div>
                    ` : ''}
                    <div class="detail-item">
                        <div class="detail-label">Currency</div>
                        <div class="detail-value">${escapeHtml(account.currency || 'USD')}</div>
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
                        <p style="margin: 0.5rem 0 0 0; color: #475569;">${escapeHtml(account.notes)}</p>
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
                            ${escapeHtml(wallet.entity_name)}
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
                            ${escapeHtml(wallet.wallet_address)}
                        </div>
                    </div>
                    ${wallet.purpose ? `
                        <div class="detail-item">
                            <div class="detail-label">Purpose</div>
                            <div class="detail-value">${escapeHtml(wallet.purpose)}</div>
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
                        <p style="margin: 0.5rem 0 0 0; color: #475569;">${escapeHtml(wallet.notes)}</p>
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

// ===================================
// PATTERN SUGGESTIONS (AUTO-LEARNING)
// ===================================

async function loadPatternSuggestions() {
    const suggestionsList = document.getElementById('suggestionsList');
    suggestionsList.innerHTML = '<div class="loading">Loading pattern suggestions...</div>';

    try {
        const response = await fetch('/api/pattern-suggestions');
        const data = await response.json();

        if (data.success) {
            renderPatternSuggestions(data.suggestions || []);
        } else {
            suggestionsList.innerHTML = `<div class="empty-state">
                <div class="empty-state-icon">⚠️</div>
                <p>Error loading suggestions: ${data.message}</p>
            </div>`;
        }
    } catch (error) {
        console.error('Error loading pattern suggestions:', error);
        suggestionsList.innerHTML = `<div class="empty-state">
            <div class="empty-state-icon">❌</div>
            <p>Failed to load pattern suggestions. Please try again.</p>
        </div>`;
    }
}

function renderPatternSuggestions(suggestions) {
    const suggestionsList = document.getElementById('suggestionsList');

    if (suggestions.length === 0) {
        suggestionsList.innerHTML = `<div class="empty-state">
            <div class="empty-state-icon">✅</div>
            <h3>No Pending Suggestions</h3>
            <p>When the system detects a pattern after 50 manual classifications, suggestions will appear here for your approval.</p>
        </div>`;
        return;
    }

    suggestionsList.innerHTML = suggestions.map(suggestion => {
        const confBadge = suggestion.confidence_score >= 0.8 ? 'high' :
                         suggestion.confidence_score >= 0.5 ? 'medium' : 'low';

        const displayPattern = stripWildcards(suggestion.description_pattern);

        return `
            <div class="suggestion-card">
                <div class="suggestion-header">
                    <div>
                        <div style="font-weight: 600; font-size: 1.1rem; color: #1e293b; margin-bottom: 0.5rem;">
                            ${escapeHtml(displayPattern)}
                        </div>
                        <div style="display: flex; gap: 0.5rem; align-items: center;">
                            <span class="badge badge-${confBadge}">
                                ${(suggestion.confidence_score * 100).toFixed(0)}% Confidence
                            </span>
                            <span class="badge" style="background: #f59e0b; color: white;">
                                ${suggestion.occurrence_count} Occurrences
                            </span>
                        </div>
                    </div>
                </div>

                <div class="pattern-details" style="margin-top: 1rem;">
                    ${suggestion.entity ? `
                    <div class="detail-item">
                        <div class="detail-label">Entity</div>
                        <div class="detail-value">${escapeHtml(suggestion.entity)}</div>
                    </div>
                    ` : ''}
                    ${suggestion.pattern_type ? `
                    <div class="detail-item">
                        <div class="detail-label">Type</div>
                        <div class="detail-value">${escapeHtml(suggestion.pattern_type)}</div>
                    </div>
                    ` : ''}
                    ${suggestion.accounting_category ? `
                    <div class="detail-item">
                        <div class="detail-label">Category</div>
                        <div class="detail-value">${escapeHtml(suggestion.accounting_category)}</div>
                    </div>
                    ` : ''}
                    ${suggestion.accounting_subcategory ? `
                    <div class="detail-item">
                        <div class="detail-label">Subcategory</div>
                        <div class="detail-value">${escapeHtml(suggestion.accounting_subcategory)}</div>
                    </div>
                    ` : ''}
                    ${suggestion.justification ? `
                    <div class="detail-item" style="grid-column: 1 / -1;">
                        <div class="detail-label">Justification</div>
                        <div class="detail-value">${escapeHtml(suggestion.justification)}</div>
                    </div>
                    ` : ''}
                </div>

                <div style="margin-top: 1.5rem; display: flex; gap: 1rem; justify-content: flex-end;">
                    <button class="btn btn-delete" onclick="rejectSuggestion(${suggestion.id})" style="background: #ef4444;">
                        ❌ Reject
                    </button>
                    <button class="btn btn-edit" onclick="approveSuggestion(${suggestion.id})" style="background: #10b981;">
                        ✅ Approve & Create Pattern
                    </button>
                </div>
            </div>
        `;
    }).join('');
}

async function approveSuggestion(suggestionId) {
    if (!confirm('Approve this pattern suggestion?\n\nThis will create a new classification pattern that will be applied automatically to matching transactions.')) {
        return;
    }

    try {
        const response = await fetch(`/api/pattern-suggestions/${suggestionId}/approve`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });

        const data = await response.json();

        if (data.success) {
            alert('Pattern approved and created successfully!');
            await loadPatternSuggestions();
            await updateSuggestionsBadge();
            await loadPatterns();
        } else {
            alert('Error approving pattern: ' + data.message);
        }
    } catch (error) {
        console.error('Error approving suggestion:', error);
        alert('Failed to approve suggestion. Please try again.');
    }
}

async function rejectSuggestion(suggestionId) {
    if (!confirm('Reject this pattern suggestion?\n\nThis will mark the suggestion as rejected and it will not be shown again.')) {
        return;
    }

    try {
        const response = await fetch(`/api/pattern-suggestions/${suggestionId}/reject`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });

        const data = await response.json();

        if (data.success) {
            alert('Pattern suggestion rejected.');
            await loadPatternSuggestions();
            await updateSuggestionsBadge();
        } else {
            alert('Error rejecting pattern: ' + data.message);
        }
    } catch (error) {
        console.error('Error rejecting suggestion:', error);
        alert('Failed to reject suggestion. Please try again.');
    }
}

function openSuggestionsModal() {
    const modal = document.getElementById('suggestionsModal');
    modal.classList.add('active');
    loadPatternSuggestions();
}

function closeSuggestionsModal() {
    document.getElementById('suggestionsModal').classList.remove('active');
}

async function updateSuggestionsBadge() {
    try {
        const response = await fetch('/api/pattern-suggestions');
        const data = await response.json();

        if (data.success) {
            const count = data.suggestions?.length || 0;
            const badge = document.getElementById('suggestionsBadge');

            // Check if badge element exists before accessing it
            if (badge) {
                if (count > 0) {
                    badge.textContent = count;
                    badge.style.display = 'flex';
                } else {
                    badge.style.display = 'none';
                }
            }
        }
    } catch (error) {
        console.error('Error updating suggestions badge:', error);
    }
}

// ===================================
// PATTERN NOTIFICATIONS TAB
// ===================================

let currentNotificationsFilter = false; // false = all, true = unread only

async function loadPageNotifications(unreadOnly = false) {
    currentNotificationsFilter = unreadOnly;
    const container = document.getElementById('notificationsListPage');
    container.innerHTML = '<div style="padding: 2rem; text-align: center; color: #64748b;">Loading notifications...</div>';

    try {
        const url = `/api/pattern-notifications?unread_only=${unreadOnly}&limit=50`;
        const response = await fetch(url);
        const data = await response.json();

        if (data.success) {
            renderPageNotifications(data.notifications || []);
            updateNotificationStats(data.unread_count, data.notifications.length);
        } else {
            container.innerHTML = `<div class="empty-state">
                <div class="empty-state-icon">⚠️</div>
                <p>Error loading notifications: ${data.message || 'Unknown error'}</p>
            </div>`;
        }
    } catch (error) {
        console.error('Error loading notifications:', error);
        container.innerHTML = `<div class="empty-state">
            <div class="empty-state-icon">❌</div>
            <p>Failed to load notifications. Please try again.</p>
        </div>`;
    }
}

function renderPageNotifications(notifications) {
    const container = document.getElementById('notificationsListPage');

    if (notifications.length === 0) {
        container.innerHTML = `<div class="empty-state">
            <div class="empty-state-icon">🔔</div>
            <h3>No Notifications</h3>
            <p>${currentNotificationsFilter ? 'All caught up! No unread notifications.' : 'No notifications to display.'}</p>
        </div>`;
        return;
    }

    const html = notifications.map(notif => {
        const isUnread = !notif.is_read;
        const bgColor = isUnread ? '#f0f9ff' : 'white';
        const borderLeft = isUnread ? '4px solid #3b82f6' : '4px solid #e2e8f0';

        const typeIcons = {
            'pattern_created': '✨',
            'pattern_activated': '✅',
            'pattern_deactivated': '❌',
            'pattern_low_confidence': '⚠️',
            'pattern_rejected': '🚫'
        };

        const icon = typeIcons[notif.notification_type] || '📋';
        const timeAgo = getTimeAgo(new Date(notif.created_at));

        return `
            <div class="pattern-card" style="background: ${bgColor}; border-left: ${borderLeft}; cursor: pointer;" onclick="markPageNotificationRead('${notif.id}')">
                <div class="pattern-header">
                    <div style="display: flex; align-items: start; gap: 1rem;">
                        <div style="font-size: 2rem;">${icon}</div>
                        <div style="flex: 1;">
                            <div style="font-weight: 700; font-size: 1.1rem; color: #1e293b; margin-bottom: 0.5rem;">
                                ${escapeHtml(notif.title)}
                            </div>
                            ${notif.message ? `
                                <div style="color: #475569; margin-bottom: 0.75rem;">
                                    ${escapeHtml(notif.message)}
                                </div>
                            ` : ''}
                            ${notif.pattern ? `
                                <div style="background: #f8fafc; padding: 0.75rem; border-radius: 6px; font-size: 0.9rem;">
                                    <div><strong>Pattern:</strong> ${escapeHtml(stripWildcards(notif.pattern.description))}</div>
                                    ${notif.pattern.category ? `<div style="margin-top: 0.25rem;"><strong>Category:</strong> ${escapeHtml(notif.pattern.category)}</div>` : ''}
                                    ${notif.pattern.entity ? `<div style="margin-top: 0.25rem;"><strong>Entity:</strong> ${escapeHtml(notif.pattern.entity)}</div>` : ''}
                                    ${notif.pattern.confidence ? `<div style="margin-top: 0.25rem;"><strong>Confidence:</strong> ${(notif.pattern.confidence * 100).toFixed(0)}%</div>` : ''}
                                </div>
                            ` : ''}
                            <div style="color: #94a3b8; font-size: 0.85rem; margin-top: 0.75rem;">
                                ${timeAgo}
                            </div>
                        </div>
                    </div>
                    ${isUnread ? '<div class="badge" style="background: #3b82f6; color: white;">NEW</div>' : ''}
                </div>
            </div>
        `;
    }).join('');

    container.innerHTML = html;
}

function updateNotificationStats(unreadCount, totalCount) {
    document.getElementById('unreadNotificationsCount').textContent = unreadCount;
    document.getElementById('totalNotificationsCount').textContent = totalCount;
}

async function markPageNotificationRead(notificationId) {
    try {
        const response = await fetch(`/api/pattern-notifications/${notificationId}/mark-read`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });

        const data = await response.json();

        if (data.success) {
            // Reload notifications to reflect the change
            loadPageNotifications(currentNotificationsFilter);
        }
    } catch (error) {
        console.error('Error marking notification as read:', error);
    }
}

async function markAllNotificationsAsRead() {
    if (!confirm('Mark all notifications as read?')) {
        return;
    }

    try {
        const response = await fetch('/api/pattern-notifications/mark-all-read', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });

        const data = await response.json();

        if (data.success) {
            alert(`Marked ${data.updated_count || 0} notification(s) as read.`);
            loadPageNotifications(currentNotificationsFilter);
        } else {
            alert('Error marking notifications as read: ' + (data.message || 'Unknown error'));
        }
    } catch (error) {
        console.error('Error marking all notifications as read:', error);
        alert('Failed to mark notifications as read. Please try again.');
    }
}

function getTimeAgo(date) {
    const seconds = Math.floor((new Date() - date) / 1000);

    if (seconds < 60) return 'just now';
    const minutes = Math.floor(seconds / 60);
    if (minutes < 60) return `${minutes}m ago`;
    const hours = Math.floor(minutes / 60);
    if (hours < 24) return `${hours}h ago`;
    const days = Math.floor(hours / 24);
    if (days < 7) return `${days}d ago`;
    const weeks = Math.floor(days / 7);
    if (weeks < 4) return `${weeks}w ago`;
    const months = Math.floor(days / 30);
    return `${months}mo ago`;
}

// Run Knowledge Generator to analyze transaction history and discover patterns
async function runKnowledgeGenerator() {
    const btn = document.getElementById('runKnowledgeGenBtn');
    const originalText = btn.innerHTML;

    if (confirm('Run Knowledge Generator to analyze your transaction history and discover new patterns?\n\nThis may take 30-60 seconds.')) {
        btn.disabled = true;
        btn.innerHTML = '⏳ Analyzing...';

        try {
            const response = await fetch('/api/knowledge-generator/run', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-Tenant-ID': 'delta'  // Will be replaced with session tenant_id in production
                }
            });

            const data = await response.json();

            if (data.success) {
                alert(`Knowledge Generator Complete!\n\n` +
                      `Accounts analyzed: ${data.results.accounts_analyzed}\n` +
                      `Vendors analyzed: ${data.results.vendors_analyzed}\n` +
                      `Patterns created: ${data.results.patterns_created}\n` +
                      `Insights generated: ${data.results.insights_generated}`);

                // Reload patterns to show new AI-generated ones
                await loadPatterns();
            } else {
                alert(`Error: ${data.message}`);
            }
        } catch (error) {
            console.error('Knowledge Generator error:', error);
            alert('Error running Knowledge Generator. Check console for details.');
        } finally {
            btn.disabled = false;
            btn.innerHTML = originalText;
        }
    }
}

// =============================================
// BUSINESS SUMMARY FUNCTIONS
// =============================================

// Load Business Summary when tab is clicked
async function loadBusinessSummary() {
    try {
        const response = await fetch('/api/business-summary', {
            headers: {
                'Content-Type': 'application/json',
                'X-Tenant-ID': 'delta'
            }
        });

        const data = await response.json();

        if (data.success && data.summary) {
            displayBusinessSummary(data.summary);
        } else {
            document.getElementById('businessSummaryContent').innerHTML = `
                <div style="text-align: center; color: #94a3b8; padding: 2rem;">
                    No business summary generated yet.<br><br>
                    Upload a file or click "Regenerate Summary" to create one.
                </div>
            `;
            document.getElementById('summaryMetadata').style.display = 'none';
        }
    } catch (error) {
        console.error('Error loading business summary:', error);
    }
}

function displayBusinessSummary(summary) {
    // Update metadata
    const metadataDiv = document.getElementById('summaryMetadata');
    metadataDiv.style.display = 'block';

    document.getElementById('summaryGeneratedAt').textContent =
        summary.generated_at ? new Date(summary.generated_at).toLocaleString() : '-';
    document.getElementById('summaryTriggeredBy').textContent =
        summary.triggered_by || 'manual';
    document.getElementById('summaryPatternCount').textContent =
        summary.stats?.pattern_count || 0;
    document.getElementById('summaryEntityCount').textContent =
        summary.stats?.entity_count || 0;
    document.getElementById('summaryWorkforceCount').textContent =
        summary.stats?.workforce_count || 0;

    // Update content - render markdown as formatted text
    const contentDiv = document.getElementById('businessSummaryContent');
    contentDiv.textContent = summary.markdown || 'No content available';
}

async function regenerateBusinessSummary() {
    const btn = document.getElementById('regenerateSummaryBtn');
    const originalText = btn.innerHTML;

    if (confirm('Regenerate the business summary from current tenant knowledge?')) {
        btn.disabled = true;
        btn.innerHTML = 'Generating...';

        try {
            const response = await fetch('/api/business-summary/regenerate', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-Tenant-ID': 'delta'
                }
            });

            const data = await response.json();

            if (data.success) {
                displayBusinessSummary(data.summary);
                alert('Business summary regenerated successfully!');
            } else {
                alert(`Error: ${data.message}`);
            }
        } catch (error) {
            console.error('Error regenerating summary:', error);
            alert('Error regenerating summary. Check console for details.');
        } finally {
            btn.disabled = false;
            btn.innerHTML = originalText;
        }
    }
}

// Add tab click handler for business-summary
document.addEventListener('DOMContentLoaded', function() {
    const tabs = document.querySelectorAll('.tab-button');
    tabs.forEach(tab => {
        tab.addEventListener('click', function() {
            if (this.dataset.tab === 'business-summary') {
                loadBusinessSummary();
            }
        });
    });
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
