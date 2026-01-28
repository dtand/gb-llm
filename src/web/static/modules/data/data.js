/**
 * GB Game Studio - Data Module
 * 
 * Spreadsheet-style data management for game tables.
 */

let dataSchema = null;
let currentTableName = null;
let currentTableData = null;
let dataSortColumn = null;
let dataSortDesc = false;
let dataSearchQuery = '';

async function loadDataSchema() {
    const { currentProjectId } = window.gbStudio;
    if (!currentProjectId) return;
    
    const emptyEl = document.getElementById('data-empty');
    const containerEl = document.getElementById('data-container');
    
    try {
        dataSchema = await apiRequest(`/api/v2/projects/${currentProjectId}/schema`);
        
        if (!dataSchema.exists || dataSchema.tables.length === 0) {
            emptyEl.style.display = 'flex';
            containerEl.style.display = 'none';
            return;
        }
        
        emptyEl.style.display = 'none';
        containerEl.style.display = 'flex';
        
        renderDataTablesList();
        loadRomBudget();
        
        // Auto-select first table
        if (dataSchema.tables.length > 0) {
            selectDataTable(dataSchema.tables[0]);
        }
    } catch (error) {
        console.error('Failed to load data schema:', error);
        emptyEl.style.display = 'flex';
        containerEl.style.display = 'none';
    }
}

function renderDataTablesList() {
    const listEl = document.getElementById('data-tables-list');
    
    listEl.innerHTML = dataSchema.tables.map(tableName => {
        const stats = dataSchema.stats[tableName] || { row_count: 0 };
        const isActive = tableName === currentTableName;
        
        return `
            <div class="data-table-item ${isActive ? 'active' : ''}" 
                 data-table="${tableName}"
                 onclick="selectDataTable('${tableName}')">
                <span class="data-table-item-name">${capitalize(tableName)}</span>
                <span class="data-table-item-count">${stats.row_count}</span>
            </div>
        `;
    }).join('');
}

async function loadRomBudget() {
    const { currentProjectId } = window.gbStudio;
    const budgetEl = document.getElementById('data-budget');
    
    try {
        const budget = await apiRequest(`/api/v2/projects/${currentProjectId}/budget`);
        
        if (!budget.exists && budget.error) {
            budgetEl.innerHTML = '';
            return;
        }
        
        const percent = budget.usage_percent || 0;
        let statusClass = '';
        if (percent >= 100) statusClass = 'danger';
        else if (percent >= 80) statusClass = 'warning';
        
        budgetEl.innerHTML = `
            <span>ROM:</span>
            <div class="data-budget-bar">
                <div class="data-budget-fill ${statusClass}" style="width: ${Math.min(percent, 100)}%"></div>
            </div>
            <span>${percent.toFixed(1)}%</span>
        `;
    } catch (error) {
        budgetEl.innerHTML = '';
    }
}

async function selectDataTable(tableName) {
    const { currentProjectId } = window.gbStudio;
    currentTableName = tableName;
    dataSortColumn = null;
    dataSortDesc = false;
    
    // Update sidebar selection
    document.querySelectorAll('.data-table-item').forEach(item => {
        item.classList.toggle('active', item.dataset.table === tableName);
    });
    
    // Update header
    document.getElementById('data-table-name').textContent = capitalize(tableName);
    
    // Load table data
    await loadTableData();
}

async function loadTableData() {
    const { currentProjectId } = window.gbStudio;
    if (!currentTableName) return;
    
    const params = new URLSearchParams();
    if (dataSearchQuery) params.set('search', dataSearchQuery);
    if (dataSortColumn) {
        params.set('sort_by', dataSortColumn);
        params.set('sort_desc', dataSortDesc);
    }
    params.set('limit', '500');
    
    try {
        currentTableData = await apiRequest(
            `/api/v2/projects/${currentProjectId}/data/${currentTableName}?${params}`
        );
        
        document.getElementById('data-table-count').textContent = 
            `${currentTableData.filtered_count} row${currentTableData.filtered_count !== 1 ? 's' : ''}`;
        
        renderDataSpreadsheet();
    } catch (error) {
        console.error('Failed to load table data:', error);
    }
}

function renderDataSpreadsheet() {
    const spreadsheetEl = document.getElementById('data-spreadsheet');
    
    if (!currentTableData || currentTableData.rows.length === 0) {
        spreadsheetEl.innerHTML = `
            <div class="data-no-results">
                ${dataSearchQuery ? 'No matching rows found' : 'No data yet. Click "+ Add Row" to create one.'}
            </div>
        `;
        return;
    }
    
    const fields = currentTableData.fields;
    const fieldNames = Object.keys(fields);
    
    // Build table HTML
    const html = `
        <table class="data-table">
            <thead>
                <tr>
                    ${fieldNames.map(name => {
                        const isSorted = dataSortColumn === name;
                        const sortClass = isSorted ? 'sorted' : '';
                        const indicator = isSorted ? (dataSortDesc ? '↓' : '↑') : '↕';
                        return `
                            <th class="${sortClass}" onclick="sortDataTable('${name}')">
                                ${name}
                                <span class="sort-indicator">${indicator}</span>
                            </th>
                        `;
                    }).join('')}
                    <th style="width: 80px;">Actions</th>
                </tr>
            </thead>
            <tbody>
                ${currentTableData.rows.map(row => renderDataRow(row, fields)).join('')}
            </tbody>
        </table>
    `;
    
    spreadsheetEl.innerHTML = html;
    
    // Attach event listeners to inputs
    spreadsheetEl.querySelectorAll('.data-cell-input, .data-cell-select').forEach(input => {
        input.addEventListener('change', handleDataCellChange);
    });
    
    spreadsheetEl.querySelectorAll('.data-cell-checkbox').forEach(checkbox => {
        checkbox.addEventListener('change', handleDataCellChange);
    });
}

function renderDataRow(row, fields) {
    const fieldNames = Object.keys(fields);
    const rowId = row.id;
    
    return `
        <tr data-row-id="${rowId}">
            ${fieldNames.map(name => {
                const field = fields[name];
                const value = row[name];
                return `<td>${renderDataCell(name, field, value, rowId)}</td>`;
            }).join('')}
            <td>
                <div class="data-cell-actions">
                    <button class="data-cell-btn" onclick="duplicateDataRow(${rowId})" title="Duplicate">📋</button>
                    <button class="data-cell-btn delete" onclick="deleteDataRow(${rowId})" title="Delete">🗑️</button>
                </div>
            </td>
        </tr>
    `;
}

function renderDataCell(fieldName, field, value, rowId) {
    const type = field.type;
    
    // Read-only for auto ID fields
    if (field.auto && fieldName === 'id') {
        return `<span style="color: var(--text-muted); font-family: var(--font-mono);">${value}</span>`;
    }
    
    switch (type) {
        case 'string':
            return `
                <input type="text" 
                       class="data-cell-input" 
                       data-row-id="${rowId}" 
                       data-field="${fieldName}"
                       value="${escapeHtml(value || '')}"
                       maxlength="${field.length || 255}">
            `;
        
        case 'uint8':
        case 'int8':
        case 'uint16':
        case 'int16':
            const min = field.min ?? (type.startsWith('u') ? 0 : -128);
            const max = field.max ?? 255;
            return `
                <input type="number" 
                       class="data-cell-input" 
                       data-row-id="${rowId}" 
                       data-field="${fieldName}"
                       value="${value ?? field.default ?? 0}"
                       min="${min}" 
                       max="${max}">
            `;
        
        case 'bool':
            return `
                <input type="checkbox" 
                       class="data-cell-checkbox" 
                       data-row-id="${rowId}" 
                       data-field="${fieldName}"
                       ${value ? 'checked' : ''}>
            `;
        
        case 'enum':
            const options = field.values || [];
            return `
                <select class="data-cell-select" 
                        data-row-id="${rowId}" 
                        data-field="${fieldName}">
                    ${options.map(opt => `
                        <option value="${opt}" ${value === opt ? 'selected' : ''}>
                            ${capitalize(opt)}
                        </option>
                    `).join('')}
                </select>
            `;
        
        case 'ref':
            // For ref fields, we'd ideally show a dropdown of target table rows
            // For now, show number input with indication it's a reference
            if (value === null || value === undefined) {
                return `
                    <input type="number" 
                           class="data-cell-input" 
                           data-row-id="${rowId}" 
                           data-field="${fieldName}"
                           value=""
                           placeholder="null"
                           min="0">
                `;
            }
            return `
                <input type="number" 
                       class="data-cell-input" 
                       data-row-id="${rowId}" 
                       data-field="${fieldName}"
                       value="${value}"
                       min="0">
            `;
        
        default:
            return `<span>${value}</span>`;
    }
}

async function handleDataCellChange(e) {
    const { currentProjectId } = window.gbStudio;
    const input = e.target;
    const rowId = parseInt(input.dataset.rowId);
    const fieldName = input.dataset.field;
    
    // Get the full row data
    const row = currentTableData.rows.find(r => r.id === rowId);
    if (!row) return;
    
    // Update the value
    let newValue;
    if (input.type === 'checkbox') {
        newValue = input.checked;
    } else if (input.type === 'number') {
        newValue = input.value === '' ? null : parseInt(input.value);
    } else {
        newValue = input.value;
    }
    
    // Create updated row
    const updatedRow = { ...row, [fieldName]: newValue };
    
    try {
        await apiRequest(`/api/v2/projects/${currentProjectId}/data/${currentTableName}/${rowId}`, {
            method: 'PUT',
            body: JSON.stringify({ row: updatedRow })
        });
        
        // Update local data
        const idx = currentTableData.rows.findIndex(r => r.id === rowId);
        if (idx >= 0) {
            currentTableData.rows[idx] = updatedRow;
        }
        
        // Brief visual feedback
        input.style.borderColor = 'var(--success)';
        setTimeout(() => {
            input.style.borderColor = '';
        }, 500);
        
    } catch (error) {
        console.error('Failed to update row:', error);
        input.style.borderColor = 'var(--error)';
    }
}

function sortDataTable(column) {
    if (dataSortColumn === column) {
        dataSortDesc = !dataSortDesc;
    } else {
        dataSortColumn = column;
        dataSortDesc = false;
    }
    loadTableData();
}

function handleDataSearch(e) {
    dataSearchQuery = e.target.value;
    loadTableData();
}

async function addDataRow() {
    const { currentProjectId } = window.gbStudio;
    if (!currentTableName || !dataSchema) return;
    
    const tableSchema = dataSchema.schema.tables[currentTableName];
    const fields = tableSchema.fields;
    
    // Create new row with defaults
    const newRow = {};
    for (const [name, field] of Object.entries(fields)) {
        if (field.auto) continue;  // Skip auto fields
        if (field.default !== undefined) {
            newRow[name] = field.default;
        } else if (field.type === 'string') {
            newRow[name] = '';
        } else if (field.type === 'bool') {
            newRow[name] = false;
        } else if (field.type === 'ref') {
            newRow[name] = null;
        } else {
            newRow[name] = 0;
        }
    }
    
    try {
        const result = await apiRequest(`/api/v2/projects/${currentProjectId}/data/${currentTableName}`, {
            method: 'POST',
            body: JSON.stringify({ row: newRow })
        });
        
        // Refresh data
        await loadTableData();
        
        // Update table count in sidebar
        const countEl = document.querySelector(`.data-table-item[data-table="${currentTableName}"] .data-table-item-count`);
        if (countEl) {
            countEl.textContent = currentTableData.filtered_count;
        }
        
        addLogEntry('success', `Added new ${currentTableName.slice(0, -1)} with ID ${result.id}`);
        
    } catch (error) {
        console.error('Failed to add row:', error);
        addLogEntry('error', `Failed to add row: ${error.message}`);
    }
}

async function duplicateDataRow(rowId) {
    const { currentProjectId } = window.gbStudio;
    const row = currentTableData.rows.find(r => r.id === rowId);
    if (!row) return;
    
    // Create copy without ID (will be auto-assigned)
    const { id, ...rowCopy } = row;
    
    try {
        const result = await apiRequest(`/api/v2/projects/${currentProjectId}/data/${currentTableName}`, {
            method: 'POST',
            body: JSON.stringify({ row: rowCopy })
        });
        
        await loadTableData();
        addLogEntry('success', `Duplicated row ${rowId} → ${result.id}`);
        
    } catch (error) {
        console.error('Failed to duplicate row:', error);
    }
}

async function deleteDataRow(rowId) {
    const { currentProjectId } = window.gbStudio;
    if (!confirm(`Delete row ${rowId}? This cannot be undone.`)) return;
    
    try {
        await apiRequest(`/api/v2/projects/${currentProjectId}/data/${currentTableName}/${rowId}`, {
            method: 'DELETE'
        });
        
        await loadTableData();
        
        // Update table count in sidebar
        const countEl = document.querySelector(`.data-table-item[data-table="${currentTableName}"] .data-table-item-count`);
        if (countEl) {
            countEl.textContent = currentTableData.filtered_count;
        }
        
        addLogEntry('success', `Deleted row ${rowId}`);
        
    } catch (error) {
        console.error('Failed to delete row:', error);
    }
}

// Initialize data panel buttons
document.addEventListener('DOMContentLoaded', () => {
    setTimeout(() => {
        const addRowBtn = document.getElementById('add-row-btn');
        const searchInput = document.getElementById('data-search');
        
        if (addRowBtn) addRowBtn.addEventListener('click', addDataRow);
        if (searchInput) {
            searchInput.addEventListener('input', debounce(handleDataSearch, 300));
        }
    }, 100);
});

// Export functions
window.loadDataSchema = loadDataSchema;
window.selectDataTable = selectDataTable;
window.sortDataTable = sortDataTable;
window.addDataRow = addDataRow;
window.duplicateDataRow = duplicateDataRow;
window.deleteDataRow = deleteDataRow;
