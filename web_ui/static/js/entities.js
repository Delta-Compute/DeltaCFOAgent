/**
 * Entity & Business Line Management
 * Handles CRUD operations for legal entities and their business lines
 */

class EntitiesManager {
    constructor() {
        this.entities = [];
        this.businessLines = [];
        this.editingEntity = null;
        this.editingBusinessLine = null;
    }

    async init() {
        console.log('Initializing entities manager...');
        this.attachEventListeners();
        await this.loadEntities();
        await this.loadBusinessLines();
        this.updateStats();
    }

    attachEventListeners() {
        // Tab switching
        document.querySelectorAll('.tab-button').forEach(button => {
            button.addEventListener('click', (e) => this.switchTab(e.target.dataset.tab));
        });

        // Add buttons
        document.getElementById('addEntityBtn').addEventListener('click', () => this.openEntityModal());
        document.getElementById('addBusinessLineBtn').addEventListener('click', () => this.openBusinessLineModal());

        // Form submissions
        document.getElementById('entityForm').addEventListener('submit', (e) => this.saveEntity(e));
        document.getElementById('businessLineForm').addEventListener('submit', (e) => this.saveBusinessLine(e));

        // Modal close on background click
        document.getElementById('entityModal').addEventListener('click', (e) => {
            if (e.target.id === 'entityModal') closeEntityModal();
        });
        document.getElementById('businessLineModal').addEventListener('click', (e) => {
            if (e.target.id === 'businessLineModal') closeBusinessLineModal();
        });

        // Entity filter for business lines
        document.getElementById('entityFilter').addEventListener('change', (e) => {
            this.renderBusinessLines(e.target.value);
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
    // ENTITIES CRUD
    // ========================================

    async loadEntities() {
        try {
            const response = await fetch('/api/entities');
            const result = await response.json();

            if (result.success && result.entities) {
                this.entities = result.entities;
                this.renderEntities();
                this.populateEntitySelectors();
            } else {
                throw new Error(result.error || 'Failed to load entities');
            }
        } catch (error) {
            console.error('Error loading entities:', error);
            this.showError('entitiesList', 'Error loading entities: ' + error.message);
        }
    }

    renderEntities() {
        const container = document.getElementById('entitiesList');

        if (this.entities.length === 0) {
            container.innerHTML = `
                <div class="empty-state">
                    <div class="empty-state-icon">🏢</div>
                    <h3>No Entities Yet</h3>
                    <p>Click "Add Entity" to create your first legal entity</p>
                </div>
            `;
            return;
        }

        container.innerHTML = this.entities.map(entity => `
            <div class="entity-card">
                <div class="entity-header">
                    <div class="entity-name-section">
                        <div class="entity-name">
                            ${this.escapeHtml(entity.name)}
                            <span class="entity-code">${this.escapeHtml(entity.code)}</span>
                        </div>
                        <div style="margin-top: 0.25rem;">
                            <span class="status-badge ${entity.is_active ? 'status-active' : 'status-inactive'}">
                                ${entity.is_active ? 'Active' : 'Inactive'}
                            </span>
                        </div>
                    </div>
                    <div class="button-group">
                        <button class="btn btn-view" onclick="entitiesManager.viewEntityDetails('${entity.id}')">
                            View Details
                        </button>
                        <button class="btn btn-edit" onclick="entitiesManager.editEntity('${entity.id}')">
                            Edit
                        </button>
                        <button class="btn btn-delete" onclick="entitiesManager.deleteEntity('${entity.id}', '${this.escapeHtml(entity.name)}')">
                            Delete
                        </button>
                    </div>
                </div>

                <div class="entity-details">
                    ${entity.legal_name ? `
                    <div class="detail-item">
                        <div class="detail-label">Legal Name</div>
                        <div class="detail-value">${this.escapeHtml(entity.legal_name)}</div>
                    </div>
                    ` : ''}
                    ${entity.tax_id ? `
                    <div class="detail-item">
                        <div class="detail-label">Tax ID</div>
                        <div class="detail-value">${this.escapeHtml(entity.tax_id)}</div>
                    </div>
                    ` : ''}
                    ${entity.entity_type ? `
                    <div class="detail-item">
                        <div class="detail-label">Entity Type</div>
                        <div class="detail-value">${this.escapeHtml(entity.entity_type)}</div>
                    </div>
                    ` : ''}
                    ${entity.tax_jurisdiction ? `
                    <div class="detail-item">
                        <div class="detail-label">Jurisdiction</div>
                        <div class="detail-value">${this.escapeHtml(entity.tax_jurisdiction)}</div>
                    </div>
                    ` : ''}
                    <div class="detail-item">
                        <div class="detail-label">Base Currency</div>
                        <div class="detail-value">${this.escapeHtml(entity.base_currency || 'USD')}</div>
                    </div>
                    <div class="detail-item">
                        <div class="detail-label">Business Lines</div>
                        <div class="detail-value">${entity.business_lines_count || 0}</div>
                    </div>
                    <div class="detail-item">
                        <div class="detail-label">Transactions</div>
                        <div class="detail-value">${(entity.transactions_count || 0).toLocaleString()}</div>
                    </div>
                </div>
            </div>
        `).join('');
    }

    openEntityModal(entity = null) {
        this.editingEntity = entity;
        const modal = document.getElementById('entityModal');
        const form = document.getElementById('entityForm');

        // Reset form
        form.reset();

        if (entity) {
            // Editing mode
            document.getElementById('entityModalTitle').textContent = 'Edit Entity';
            document.getElementById('entityCode').value = entity.code || '';
            document.getElementById('entityName').value = entity.name || '';
            document.getElementById('legalName').value = entity.legal_name || '';
            document.getElementById('taxId').value = entity.tax_id || '';
            document.getElementById('entityType').value = entity.entity_type || '';
            document.getElementById('taxJurisdiction').value = entity.tax_jurisdiction || '';
            document.getElementById('baseCurrency').value = entity.base_currency || 'USD';
            document.getElementById('incorporationDate').value = entity.incorporation_date || '';
            document.getElementById('fiscalYearEnd').value = entity.fiscal_year_end || '12-31';
            document.getElementById('address').value = entity.address || '';
            document.getElementById('countryCode').value = entity.country_code || '';
            document.getElementById('isActive').checked = entity.is_active !== false;
        } else {
            // Creating mode
            document.getElementById('entityModalTitle').textContent = 'Add Entity';
            document.getElementById('isActive').checked = true;
            document.getElementById('baseCurrency').value = 'USD';
            document.getElementById('fiscalYearEnd').value = '12-31';
        }

        modal.classList.add('active');
    }

    editEntity(entityId) {
        const entity = this.entities.find(e => e.id === entityId);
        if (entity) {
            this.openEntityModal(entity);
        }
    }

    async saveEntity(e) {
        e.preventDefault();

        const entityData = {
            code: document.getElementById('entityCode').value.trim().toUpperCase(),
            name: document.getElementById('entityName').value.trim(),
            legal_name: document.getElementById('legalName').value.trim() || null,
            tax_id: document.getElementById('taxId').value.trim() || null,
            entity_type: document.getElementById('entityType').value || null,
            tax_jurisdiction: document.getElementById('taxJurisdiction').value.trim() || null,
            base_currency: document.getElementById('baseCurrency').value,
            incorporation_date: document.getElementById('incorporationDate').value || null,
            fiscal_year_end: document.getElementById('fiscalYearEnd').value || '12-31',
            address: document.getElementById('address').value.trim() || null,
            country_code: document.getElementById('countryCode').value.trim().toUpperCase() || null,
            is_active: document.getElementById('isActive').checked
        };

        try {
            let response;
            if (this.editingEntity) {
                // Update existing entity
                response = await fetch(`/api/entities/${this.editingEntity.id}`, {
                    method: 'PUT',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(entityData)
                });
            } else {
                // Create new entity
                response = await fetch('/api/entities', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(entityData)
                });
            }

            const result = await response.json();

            if (result.success) {
                closeEntityModal();
                await this.loadEntities();
                this.updateStats();
                this.showSuccessMessage(this.editingEntity ? 'Entity updated successfully' : 'Entity created successfully');
            } else {
                throw new Error(result.error || 'Failed to save entity');
            }
        } catch (error) {
            console.error('Error saving entity:', error);
            alert('Error saving entity: ' + error.message);
        }
    }

    async deleteEntity(entityId, entityName) {
        if (!confirm(`Are you sure you want to delete entity "${entityName}"?\n\nThis will deactivate the entity but preserve historical data.`)) {
            return;
        }

        try {
            const response = await fetch(`/api/entities/${entityId}`, {
                method: 'DELETE'
            });

            const result = await response.json();

            if (result.success) {
                await this.loadEntities();
                this.updateStats();
                this.showSuccessMessage('Entity deleted successfully');
            } else {
                throw new Error(result.error || 'Failed to delete entity');
            }
        } catch (error) {
            console.error('Error deleting entity:', error);
            alert('Error deleting entity: ' + error.message);
        }
    }

    async viewEntityDetails(entityId) {
        const entity = this.entities.find(e => e.id === entityId);
        if (!entity) return;

        // Switch to business lines tab and filter by this entity
        this.switchTab('businessLinesTab');
        document.getElementById('entityFilter').value = entityId;
        this.renderBusinessLines(entityId);
    }

    // ========================================
    // BUSINESS LINES CRUD
    // ========================================

    async loadBusinessLines() {
        try {
            const response = await fetch('/api/business-lines');
            const result = await response.json();

            if (result.success && result.business_lines) {
                this.businessLines = result.business_lines;
                this.renderBusinessLines();
            } else {
                throw new Error(result.error || 'Failed to load business lines');
            }
        } catch (error) {
            console.error('Error loading business lines:', error);
            this.showError('businessLinesList', 'Error loading business lines: ' + error.message);
        }
    }

    renderBusinessLines(entityFilter = '') {
        const container = document.getElementById('businessLinesList');

        let filteredLines = this.businessLines;
        if (entityFilter) {
            filteredLines = this.businessLines.filter(bl => bl.entity_id === entityFilter);
        }

        if (filteredLines.length === 0) {
            container.innerHTML = `
                <div class="empty-state">
                    <div class="empty-state-icon">📊</div>
                    <h3>No Business Lines Yet</h3>
                    <p>Click "Add Business Line" to create a profit center within an entity</p>
                </div>
            `;
            return;
        }

        // Group by entity
        const grouped = {};
        filteredLines.forEach(bl => {
            if (!grouped[bl.entity_id]) {
                grouped[bl.entity_id] = [];
            }
            grouped[bl.entity_id].push(bl);
        });

        let html = '';
        for (const entityId in grouped) {
            const entity = this.entities.find(e => e.id === entityId);
            const lines = grouped[entityId];

            html += `
                <div style="margin-bottom: 2rem;">
                    <h3 style="margin-bottom: 1rem; color: #1e293b;">
                        ${entity ? this.escapeHtml(entity.name) : 'Unknown Entity'}
                        <span class="entity-code">${entity ? this.escapeHtml(entity.code) : ''}</span>
                    </h3>
                    ${lines.map(bl => this.renderBusinessLineCard(bl)).join('')}
                </div>
            `;
        }

        container.innerHTML = html;
    }

    renderBusinessLineCard(bl) {
        return `
            <div class="business-line-card" style="border-left-color: ${bl.color_hex || '#3b82f6'};">
                <div class="business-line-header">
                    <div>
                        <div class="business-line-name">
                            ${this.escapeHtml(bl.name)}
                            <span class="entity-code">${this.escapeHtml(bl.code)}</span>
                            ${bl.is_default ? '<span class="default-badge">DEFAULT</span>' : ''}
                        </div>
                        <div style="margin-top: 0.25rem;">
                            <span class="status-badge ${bl.is_active ? 'status-active' : 'status-inactive'}">
                                ${bl.is_active ? 'Active' : 'Inactive'}
                            </span>
                        </div>
                    </div>
                    <div class="button-group">
                        ${!bl.is_default ? `
                        <button class="btn btn-view" onclick="entitiesManager.setDefaultBusinessLine('${bl.id}', '${bl.entity_id}')">
                            Set as Default
                        </button>
                        ` : ''}
                        <button class="btn btn-edit" onclick="entitiesManager.editBusinessLine('${bl.id}')">
                            Edit
                        </button>
                        <button class="btn btn-delete" onclick="entitiesManager.deleteBusinessLine('${bl.id}', '${this.escapeHtml(bl.name)}')">
                            Delete
                        </button>
                    </div>
                </div>

                ${bl.description ? `
                <div style="margin: 1rem 0; color: #64748b;">
                    ${this.escapeHtml(bl.description)}
                </div>
                ` : ''}

                <div class="entity-details">
                    ${bl.start_date ? `
                    <div class="detail-item">
                        <div class="detail-label">Start Date</div>
                        <div class="detail-value">${bl.start_date}</div>
                    </div>
                    ` : ''}
                    ${bl.end_date ? `
                    <div class="detail-item">
                        <div class="detail-label">End Date</div>
                        <div class="detail-value">${bl.end_date}</div>
                    </div>
                    ` : ''}
                    <div class="detail-item">
                        <div class="detail-label">Transactions</div>
                        <div class="detail-value">${(bl.transactions_count || 0).toLocaleString()}</div>
                    </div>
                </div>
            </div>
        `;
    }

    openBusinessLineModal(businessLine = null) {
        this.editingBusinessLine = businessLine;
        const modal = document.getElementById('businessLineModal');
        const form = document.getElementById('businessLineForm');

        // Reset form
        form.reset();

        if (businessLine) {
            // Editing mode
            document.getElementById('businessLineModalTitle').textContent = 'Edit Business Line';
            document.getElementById('blEntityId').value = businessLine.entity_id || '';
            document.getElementById('blCode').value = businessLine.code || '';
            document.getElementById('blName').value = businessLine.name || '';
            document.getElementById('blDescription').value = businessLine.description || '';
            document.getElementById('blColorHex').value = businessLine.color_hex || '#3B82F6';
            document.getElementById('blStartDate').value = businessLine.start_date || '';
            document.getElementById('blIsActive').checked = businessLine.is_active !== false;
            document.getElementById('blIsDefault').checked = businessLine.is_default || false;
        } else {
            // Creating mode
            document.getElementById('businessLineModalTitle').textContent = 'Add Business Line';
            document.getElementById('blIsActive').checked = true;
            document.getElementById('blIsDefault').checked = false;
            document.getElementById('blColorHex').value = '#3B82F6';
        }

        modal.classList.add('active');
    }

    editBusinessLine(businessLineId) {
        const bl = this.businessLines.find(b => b.id === businessLineId);
        if (bl) {
            this.openBusinessLineModal(bl);
        }
    }

    async saveBusinessLine(e) {
        e.preventDefault();

        const blData = {
            entity_id: document.getElementById('blEntityId').value,
            code: document.getElementById('blCode').value.trim().toUpperCase(),
            name: document.getElementById('blName').value.trim(),
            description: document.getElementById('blDescription').value.trim() || null,
            color_hex: document.getElementById('blColorHex').value,
            start_date: document.getElementById('blStartDate').value || null,
            is_active: document.getElementById('blIsActive').checked,
            is_default: document.getElementById('blIsDefault').checked
        };

        try {
            let response;
            if (this.editingBusinessLine) {
                // Update existing business line
                response = await fetch(`/api/business-lines/${this.editingBusinessLine.id}`, {
                    method: 'PUT',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(blData)
                });
            } else {
                // Create new business line
                response = await fetch('/api/business-lines', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(blData)
                });
            }

            const result = await response.json();

            if (result.success) {
                closeBusinessLineModal();
                await this.loadBusinessLines();
                await this.loadEntities(); // Reload to update business line counts
                this.updateStats();
                this.showSuccessMessage(this.editingBusinessLine ? 'Business line updated successfully' : 'Business line created successfully');
            } else {
                throw new Error(result.error || 'Failed to save business line');
            }
        } catch (error) {
            console.error('Error saving business line:', error);
            alert('Error saving business line: ' + error.message);
        }
    }

    async deleteBusinessLine(businessLineId, businessLineName) {
        if (!confirm(`Are you sure you want to delete business line "${businessLineName}"?\n\nThis will deactivate the business line but preserve historical data.`)) {
            return;
        }

        try {
            const response = await fetch(`/api/business-lines/${businessLineId}`, {
                method: 'DELETE'
            });

            const result = await response.json();

            if (result.success) {
                await this.loadBusinessLines();
                await this.loadEntities();
                this.updateStats();
                this.showSuccessMessage('Business line deleted successfully');
            } else {
                throw new Error(result.error || 'Failed to delete business line');
            }
        } catch (error) {
            console.error('Error deleting business line:', error);
            alert('Error deleting business line: ' + error.message);
        }
    }

    async setDefaultBusinessLine(businessLineId, entityId) {
        try {
            const response = await fetch(`/api/business-lines/${businessLineId}/set-default`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' }
            });

            const result = await response.json();

            if (result.success) {
                await this.loadBusinessLines();
                this.showSuccessMessage('Default business line updated');
            } else {
                throw new Error(result.error || 'Failed to set default business line');
            }
        } catch (error) {
            console.error('Error setting default business line:', error);
            alert('Error setting default business line: ' + error.message);
        }
    }

    // ========================================
    // HELPER FUNCTIONS
    // ========================================

    populateEntitySelectors() {
        const entityFilter = document.getElementById('entityFilter');
        const blEntityId = document.getElementById('blEntityId');

        // Populate entity filter
        entityFilter.innerHTML = '<option value="">All Entities</option>' +
            this.entities.map(e => `
                <option value="${e.id}">${this.escapeHtml(e.name)} (${this.escapeHtml(e.code)})</option>
            `).join('');

        // Populate business line entity selector
        blEntityId.innerHTML = '<option value="">Select Entity</option>' +
            this.entities.filter(e => e.is_active).map(e => `
                <option value="${e.id}">${this.escapeHtml(e.name)} (${this.escapeHtml(e.code)})</option>
            `).join('');
    }

    updateStats() {
        const totalEntities = this.entities.length;
        const activeEntities = this.entities.filter(e => e.is_active).length;
        const totalBusinessLines = this.businessLines.filter(bl => bl.is_active).length;

        document.getElementById('totalEntities').textContent = totalEntities;
        document.getElementById('activeEntities').textContent = activeEntities;
        document.getElementById('totalBusinessLines').textContent = totalBusinessLines;
    }

    showError(containerId, message) {
        const container = document.getElementById(containerId);
        container.innerHTML = `
            <div class="empty-state">
                <div class="empty-state-icon">⚠️</div>
                <p>${this.escapeHtml(message)}</p>
            </div>
        `;
    }

    showSuccessMessage(message) {
        // Simple alert for now - can be enhanced with toast notifications
        alert(message);
    }

    escapeHtml(unsafe) {
        if (!unsafe) return '';
        return unsafe
            .toString()
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#039;");
    }
}
