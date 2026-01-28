/**
 * GB Game Studio - Tuning Module
 * 
 * Tunable game parameters with sliders.
 */

let tunableData = null;
let tunableChanges = {};  // Track pending changes: { name: newValue }
let originalTunables = {};  // Store original values for reset

async function loadTunables() {
    const { currentProjectId } = window.gbStudio;
    if (!currentProjectId) return;
    
    const emptyEl = document.getElementById('tuning-empty');
    const categoriesEl = document.getElementById('tuning-categories');
    
    try {
        tunableData = await apiRequest(`/api/v2/projects/${currentProjectId}/tuning`);
        tunableChanges = {};
        
        // Store original values
        originalTunables = {};
        for (const t of tunableData.tunables) {
            originalTunables[t.name] = t.value;
        }
        
        renderTunables();
    } catch (error) {
        console.error('Failed to load tunables:', error);
        emptyEl.style.display = 'flex';
        categoriesEl.innerHTML = '';
    }
}

function renderTunables() {
    const emptyEl = document.getElementById('tuning-empty');
    const categoriesEl = document.getElementById('tuning-categories');
    
    if (!tunableData || tunableData.tunables.length === 0) {
        emptyEl.style.display = 'flex';
        categoriesEl.innerHTML = '';
        return;
    }
    
    emptyEl.style.display = 'none';
    
    // Render by category
    const categoryIcons = {
        player: '🏃',
        physics: '🔵',
        difficulty: '🎯',
        timing: '⏱️',
        scoring: '🏆',
        enemies: '👾',
        default: '⚙️'
    };
    
    const categoryLabels = {
        player: 'Player',
        physics: 'Physics',
        difficulty: 'Difficulty',
        timing: 'Timing',
        scoring: 'Scoring',
        enemies: 'Enemies'
    };
    
    categoriesEl.innerHTML = tunableData.categories.map(category => {
        const tunables = tunableData.by_category[category];
        const icon = categoryIcons[category] || categoryIcons.default;
        const label = categoryLabels[category] || capitalize(category);
        
        return `
            <div class="tuning-category" data-category="${category}">
                <div class="category-header">
                    <span class="category-icon">${icon}</span>
                    <span class="category-label">${label}</span>
                </div>
                <div class="category-tunables">
                    ${tunables.map(t => renderTunableSlider(t)).join('')}
                </div>
            </div>
        `;
    }).join('');
    
    // Attach event listeners to sliders
    categoriesEl.querySelectorAll('.tunable-slider').forEach(slider => {
        slider.addEventListener('input', handleTunableChange);
    });
    
    // Attach event listeners to number inputs
    categoriesEl.querySelectorAll('.tunable-value-input').forEach(input => {
        input.addEventListener('change', handleTunableInputChange);
    });
    
    updateApplyButtonState();
}

function renderTunableSlider(tunable) {
    const currentValue = tunableChanges[tunable.name] ?? tunable.value;
    const hasChanged = tunableChanges[tunable.name] !== undefined;
    
    return `
        <div class="tunable-item ${hasChanged ? 'changed' : ''}" data-name="${tunable.name}">
            <div class="tunable-header">
                <span class="tunable-name">${formatTunableName(tunable.name)}</span>
                <span class="tunable-description">${tunable.description}</span>
            </div>
            <div class="tunable-control">
                <input type="range" 
                       class="tunable-slider" 
                       data-name="${tunable.name}"
                       data-file="${tunable.file}"
                       min="${tunable.min}" 
                       max="${tunable.max}" 
                       value="${currentValue}">
                <input type="number" 
                       class="tunable-value-input" 
                       data-name="${tunable.name}"
                       data-file="${tunable.file}"
                       min="${tunable.min}" 
                       max="${tunable.max}" 
                       value="${currentValue}">
                <span class="tunable-range">${tunable.min}-${tunable.max}</span>
            </div>
        </div>
    `;
}

function formatTunableName(name) {
    return name
        .replace(/^(PLAYER_|ENEMY_|BALL_|SPAWN_|MAX_|MIN_)/, '')
        .replace(/_/g, ' ')
        .toLowerCase()
        .replace(/\b\w/g, c => c.toUpperCase());
}

function handleTunableChange(e) {
    const name = e.target.dataset.name;
    const value = parseInt(e.target.value);
    const original = originalTunables[name];
    
    // Update the number input to match
    const input = document.querySelector(`.tunable-value-input[data-name="${name}"]`);
    if (input) input.value = value;
    
    // Track change (or remove if back to original)
    if (value !== original) {
        tunableChanges[name] = value;
    } else {
        delete tunableChanges[name];
    }
    
    // Update visual state
    const item = document.querySelector(`.tunable-item[data-name="${name}"]`);
    if (item) {
        item.classList.toggle('changed', value !== original);
    }
    
    updateApplyButtonState();
}

function handleTunableInputChange(e) {
    const name = e.target.dataset.name;
    let value = parseInt(e.target.value);
    const min = parseInt(e.target.min);
    const max = parseInt(e.target.max);
    
    // Clamp to range
    value = Math.max(min, Math.min(max, value));
    e.target.value = value;
    
    // Update the slider to match
    const slider = document.querySelector(`.tunable-slider[data-name="${name}"]`);
    if (slider) slider.value = value;
    
    // Track change
    const original = originalTunables[name];
    if (value !== original) {
        tunableChanges[name] = value;
    } else {
        delete tunableChanges[name];
    }
    
    // Update visual state
    const item = document.querySelector(`.tunable-item[data-name="${name}"]`);
    if (item) {
        item.classList.toggle('changed', value !== original);
    }
    
    updateApplyButtonState();
}

function updateApplyButtonState() {
    const applyBtn = document.getElementById('apply-tuning-btn');
    const resetBtn = document.getElementById('reset-tuning-btn');
    const hasChanges = Object.keys(tunableChanges).length > 0;
    
    applyBtn.disabled = !hasChanges;
    applyBtn.textContent = hasChanges 
        ? `✓ Apply ${Object.keys(tunableChanges).length} Change${Object.keys(tunableChanges).length > 1 ? 's' : ''}`
        : '✓ Apply & Rebuild';
    
    resetBtn.disabled = !hasChanges;
}

async function applyTunableChanges() {
    if (Object.keys(tunableChanges).length === 0) return;
    
    const { currentProjectId } = window.gbStudio;
    const applyBtn = document.getElementById('apply-tuning-btn');
    applyBtn.disabled = true;
    applyBtn.textContent = '⏳ Applying...';
    
    // Build updates array
    const updates = [];
    for (const [name, value] of Object.entries(tunableChanges)) {
        // Find the tunable to get its file
        const tunable = tunableData.tunables.find(t => t.name === name);
        if (tunable) {
            updates.push({
                name: name,
                value: value,
                file: tunable.file
            });
        }
    }
    
    try {
        // Apply changes
        await apiRequest(`/api/v2/projects/${currentProjectId}/tuning`, {
            method: 'PUT',
            body: JSON.stringify({ updates })
        });
        
        addLogEntry('success', `Applied ${updates.length} tuning change(s)`);
        
        // Trigger rebuild
        applyBtn.textContent = '⏳ Rebuilding...';
        
        const buildResponse = await apiRequest(`/api/v2/projects/${currentProjectId}/build`, {
            method: 'POST'
        });
        
        if (buildResponse.success) {
            addLogEntry('success', 'Rebuild successful!');
            addChatMessage('assistant', `✅ **Tuning applied!** Changed ${updates.length} parameter(s) and rebuilt. Try the new settings in the Emulator!`);
            
            // Refresh project state
            await refreshProjectState();
            updateEmulatorState();
        } else {
            addLogEntry('error', 'Rebuild failed');
            addChatMessage('assistant', `⚠️ Tuning applied but rebuild failed: ${buildResponse.error}`);
        }
        
        // Reset change tracking (reload fresh data)
        await loadTunables();
        
    } catch (error) {
        console.error('Failed to apply tunables:', error);
        addLogEntry('error', `Failed to apply: ${error.message}`);
    }
    
    updateApplyButtonState();
}

function resetTunableChanges() {
    if (Object.keys(tunableChanges).length === 0) return;
    
    // Reset all sliders and inputs to original values
    for (const [name, originalValue] of Object.entries(originalTunables)) {
        const slider = document.querySelector(`.tunable-slider[data-name="${name}"]`);
        const input = document.querySelector(`.tunable-value-input[data-name="${name}"]`);
        const item = document.querySelector(`.tunable-item[data-name="${name}"]`);
        
        if (slider) slider.value = originalValue;
        if (input) input.value = originalValue;
        if (item) item.classList.remove('changed');
    }
    
    tunableChanges = {};
    updateApplyButtonState();
}

// Initialize tuning buttons
document.addEventListener('DOMContentLoaded', () => {
    setTimeout(() => {
        const applyBtn = document.getElementById('apply-tuning-btn');
        const resetBtn = document.getElementById('reset-tuning-btn');
        
        if (applyBtn) applyBtn.addEventListener('click', applyTunableChanges);
        if (resetBtn) resetBtn.addEventListener('click', resetTunableChanges);
    }, 100);
});

// Export functions
window.loadTunables = loadTunables;
