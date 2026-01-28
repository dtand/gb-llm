/**
 * GB Game Studio - Agents Module
 * 
 * Agent configuration and model selection panel.
 */

let agentConfig = null;

async function loadAgentConfig() {
    const { currentProjectId } = window.gbStudio;
    if (!currentProjectId) return;
    
    try {
        agentConfig = await apiRequest(`/api/v2/projects/${currentProjectId}/agents`);
        renderAgentCards();
    } catch (error) {
        console.error('Failed to load agent config:', error);
        document.getElementById('agents-grid').innerHTML = `
            <div class="agent-error">Failed to load agent configuration</div>
        `;
    }
}

function renderAgentCards() {
    const container = document.getElementById('agents-grid');
    if (!agentConfig) {
        container.innerHTML = '<div class="loading">Loading...</div>';
        return;
    }
    
    const agentIcons = {
        designer: '🎨',
        coder: '👨‍💻',
        reviewer: '🔍',
        cleanup: '🧹'
    };
    
    const agentOrder = ['designer', 'coder', 'reviewer', 'cleanup'];
    
    container.innerHTML = agentOrder.map(agentName => {
        const agent = agentConfig.agents[agentName];
        const icon = agentIcons[agentName];
        const canDisable = ['reviewer', 'cleanup'].includes(agentName); // These agents can be toggled
        
        return `
            <div class="agent-card ${!agent.enabled ? 'disabled' : ''}" data-agent="${agentName}">
                <div class="agent-header">
                    <span class="agent-icon">${icon}</span>
                    <span class="agent-name">${capitalize(agentName)}</span>
                    ${canDisable ? `
                        <label class="agent-toggle">
                            <input type="checkbox" 
                                   ${agent.enabled ? 'checked' : ''} 
                                   onchange="toggleAgent('${agentName}', this.checked)">
                            <span class="toggle-slider"></span>
                        </label>
                    ` : '<span class="agent-required" title="Required">Required</span>'}
                </div>
                <p class="agent-description">${agent.description}</p>
                <div class="agent-model">
                    <label>Model:</label>
                    <select onchange="updateAgentModel('${agentName}', this.value)" ${!agent.enabled ? 'disabled' : ''}>
                        ${agentConfig.available_models.map(m => `
                            <option value="${m.id}" ${agent.model === m.id ? 'selected' : ''}>
                                ${m.name} ${m.tier === 'premium' ? '⭐' : m.tier === 'fast' ? '⚡' : ''}
                            </option>
                        `).join('')}
                    </select>
                </div>
                <div class="agent-model-tier">
                    ${getModelTierBadge(agent.model)}
                </div>
            </div>
        `;
    }).join('');
}

function getModelTierBadge(modelId) {
    if (!agentConfig) return '';
    const model = agentConfig.available_models.find(m => m.id === modelId);
    if (!model) return '';
    
    const tierColors = {
        premium: 'tier-premium',
        standard: 'tier-standard', 
        fast: 'tier-fast'
    };
    
    return `<span class="model-tier ${tierColors[model.tier]}">${model.tier}</span>`;
}

async function toggleAgent(agentName, enabled) {
    const { currentProjectId } = window.gbStudio;
    if (!currentProjectId) return;
    
    try {
        agentConfig = await apiRequest(`/api/v2/projects/${currentProjectId}/agents/${agentName}`, {
            method: 'PUT',
            body: JSON.stringify({ enabled })
        });
        renderAgentCards();
        addLogEntry('info', `${capitalize(agentName)} agent ${enabled ? 'enabled' : 'disabled'}`);
    } catch (error) {
        console.error('Failed to update agent:', error);
        addLogEntry('error', `Failed to update ${agentName}: ${error.message}`);
        // Reload to get correct state
        loadAgentConfig();
    }
}

async function updateAgentModel(agentName, model) {
    const { currentProjectId } = window.gbStudio;
    if (!currentProjectId) return;
    
    try {
        agentConfig = await apiRequest(`/api/v2/projects/${currentProjectId}/agents/${agentName}`, {
            method: 'PUT',
            body: JSON.stringify({ model })
        });
        renderAgentCards();
        
        const modelInfo = agentConfig.available_models.find(m => m.id === model);
        addLogEntry('info', `${capitalize(agentName)} now using ${modelInfo?.name || model}`);
    } catch (error) {
        console.error('Failed to update agent model:', error);
        addLogEntry('error', `Failed to update ${agentName}: ${error.message}`);
        // Reload to get correct state
        loadAgentConfig();
    }
}

// Export functions
window.loadAgentConfig = loadAgentConfig;
window.toggleAgent = toggleAgent;
window.updateAgentModel = updateAgentModel;
