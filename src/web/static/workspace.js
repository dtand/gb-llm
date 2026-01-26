/**
 * GB Game Studio - Workspace Application
 * 
 * A chat-based interface for iterative game development.
 */

const API_BASE = '';

// State
let currentProjectId = null;
let currentProject = null;
let websocket = null;
let templates = [];
let projects = [];

// Initialize
document.addEventListener('DOMContentLoaded', async () => {
    await loadTemplates();
    await loadProjects();
    setupEventListeners();
    
    // Check URL for project ID
    const urlParams = new URLSearchParams(window.location.search);
    const projectId = urlParams.get('project');
    if (projectId) {
        await selectProject(projectId);
    }
});

// === Event Listeners ===

function setupEventListeners() {
    // New project buttons
    document.getElementById('new-project-btn').addEventListener('click', showNewProjectModal);
    document.getElementById('create-first-project').addEventListener('click', showNewProjectModal);
    
    // Modal
    document.querySelector('.modal-close').addEventListener('click', hideNewProjectModal);
    document.querySelector('.modal-backdrop').addEventListener('click', hideNewProjectModal);
    document.getElementById('cancel-create').addEventListener('click', hideNewProjectModal);
    document.getElementById('new-project-form').addEventListener('submit', handleCreateProject);
    
    // Project actions
    document.getElementById('refresh-projects').addEventListener('click', loadProjects);
    document.getElementById('build-btn').addEventListener('click', handleBuild);
    document.getElementById('play-btn').addEventListener('click', handlePlay);
    document.getElementById('download-btn').addEventListener('click', handleDownload);
    document.getElementById('rollback-btn').addEventListener('click', showRollbackModal);
    document.getElementById('delete-btn').addEventListener('click', showDeleteModal);
    document.getElementById('confirm-delete-btn').addEventListener('click', handleDeleteProject);
    
    // Chat
    document.getElementById('send-btn').addEventListener('click', handleSendMessage);
    document.getElementById('build-feature-btn').addEventListener('click', handleBuildFeature);
    document.getElementById('retry-btn').addEventListener('click', handleRetry);
    document.getElementById('new-chat-btn').addEventListener('click', handleNewChat);
    document.getElementById('chat-input').addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            handleSendMessage();
        }
        // Ctrl/Cmd + Enter triggers build feature
        if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) {
            e.preventDefault();
            handleBuildFeature();
        }
    });
    
    // Log toggle
    document.getElementById('toggle-log').addEventListener('click', toggleLog);
    
    // Panel tabs (Files / Emulator)
    document.querySelectorAll('.panel-tab').forEach(tab => {
        tab.addEventListener('click', () => switchPanelTab(tab.dataset.tab));
    });
    
    // Emulator controls
    document.getElementById('emu-play-btn').addEventListener('click', handleEmulatorPlay);
    document.getElementById('emu-pause-btn').addEventListener('click', handleEmulatorPause);
    document.getElementById('emu-reload-btn').addEventListener('click', handleEmulatorReload);
    document.getElementById('emu-volume').addEventListener('input', handleEmulatorVolume);
    
    // Keyboard shortcuts
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') hideNewProjectModal();
    });
}

// === API Functions ===

async function apiRequest(endpoint, options = {}) {
    const response = await fetch(`${API_BASE}${endpoint}`, {
        headers: {
            'Content-Type': 'application/json',
            ...options.headers,
        },
        ...options,
    });
    
    if (!response.ok) {
        const error = await response.json().catch(() => ({ detail: 'Request failed' }));
        throw new Error(error.detail || 'Request failed');
    }
    
    return response.json();
}

async function loadTemplates() {
    try {
        templates = await apiRequest('/api/v2/templates');
        renderTemplates();
        populateTemplateSelect();
    } catch (error) {
        console.error('Failed to load templates:', error);
    }
}

async function loadProjects() {
    try {
        projects = await apiRequest('/api/v2/projects');
        renderProjects();
    } catch (error) {
        console.error('Failed to load projects:', error);
    }
}

async function selectProject(projectId) {
    try {
        const project = await apiRequest(`/api/v2/projects/${projectId}`);
        currentProjectId = projectId;
        currentProject = project;
        
        // Update URL
        window.history.pushState({}, '', `/workspace?project=${projectId}`);
        
        // Connect WebSocket
        connectWebSocket(projectId);
        
        // Load conversation
        const conversation = await apiRequest(`/api/v2/projects/${projectId}/conversation`);
        
        // Show project view
        showProjectView(project, conversation);
        
        // Highlight in sidebar
        document.querySelectorAll('.project-item').forEach(el => {
            el.classList.toggle('active', el.dataset.id === projectId);
        });
        
        // Reset emulator when switching projects
        if (window.GBEmulator) {
            window.GBEmulator.stop();
            emulatorLoaded = false;
            const overlay = document.getElementById('emulator-overlay');
            if (overlay) overlay.classList.remove('hidden');
        }
        
        // Default to emulator tab and update its state
        switchPanelTab('emulator');
        updateEmulatorState();
        
    } catch (error) {
        console.error('Failed to load project:', error);
        addLogEntry('error', `Failed to load project: ${error.message}`);
    }
}

// === WebSocket ===

function connectWebSocket(projectId) {
    if (websocket) {
        websocket.close();
    }
    
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/ws/projects/${projectId}`;
    
    websocket = new WebSocket(wsUrl);
    
    websocket.onopen = () => {
        addLogEntry('info', 'Connected to project');
    };
    
    websocket.onmessage = (event) => {
        const data = JSON.parse(event.data);
        handleWebSocketMessage(data);
    };
    
    websocket.onerror = (error) => {
        console.error('WebSocket error:', error);
        addLogEntry('error', 'Connection error');
    };
    
    websocket.onclose = () => {
        addLogEntry('info', 'Disconnected');
    };
}

function handleWebSocketMessage(data) {
    switch (data.type) {
        case 'status':
            updateProjectStatus(data.status);
            break;
        // Dialogue mode messages
        case 'dialogue_start':
            addLogEntry('info', 'Chatting with Designer...');
            setChatStatus('Thinking...');
            break;
        case 'dialogue_complete':
            setChatStatus('Ready');
            break;
        case 'dialogue_error':
            addLogEntry('error', `Dialogue error: ${data.error}`);
            setChatStatus('Ready');
            break;
        // Build feature messages
        case 'build_feature_start':
            addLogEntry('agent', '🚀 ' + data.message);
            setChatStatus('Building...');
            break;
        case 'build_feature_complete':
            setChatStatus('Ready');
            hideProgressBar();
            if (data.success && data.files && data.files.length > 0) {
                refreshProjectState();
                hideRetryButton();
            }
            if (data.can_retry) {
                showRetryButton();
            }
            break;
        case 'build_feature_error':
            addLogEntry('error', `Build error: ${data.error}`);
            setChatStatus('Ready');
            hideProgressBar();
            break;
        // Retry messages
        case 'retry_start':
            addLogEntry('agent', '🔄 Retrying failed build...');
            setChatStatus('Retrying...');
            break;
        case 'retry_complete':
            setChatStatus('Ready');
            hideProgressBar();
            if (data.success && data.files && data.files.length > 0) {
                refreshProjectState();
                hideRetryButton();
            }
            if (data.can_retry) {
                showRetryButton();
            } else {
                hideRetryButton();
            }
            break;
        case 'retry_error':
            addLogEntry('error', `Retry error: ${data.error}`);
            setChatStatus('Ready');
            hideProgressBar();
            break;
        // Pipeline log messages (used during build)
        case 'pipeline_log':
            // Handle progress updates specially
            if (data.level === 'progress') {
                updateProgressBar(data.message);
            } else if (data.level === 'step') {
                addLogEntry('agent', `📍 ${data.message}`);
                updateTypingStatus(data.message);
            } else {
                addLogEntry(data.level, data.message);
                updateTypingStatus(data.message);
            }
            break;
        // Legacy pipeline messages (for backwards compatibility)
        case 'pipeline_start':
            addLogEntry('info', `Processing: ${data.message.substring(0, 50)}...`);
            setChatStatus('Processing...');
            break;
        case 'pipeline_complete':
            setChatStatus('Ready');
            if (data.implemented && data.files && data.files.length > 0) {
                refreshProjectState();
            }
            break;
        case 'pipeline_error':
            addLogEntry('error', `Error: ${data.error}`);
            setChatStatus('Ready');
            break;
        case 'build_result':
            if (data.success) {
                addLogEntry('success', 'Build successful!');
                updateProjectStatus('compiled');
            } else {
                addLogEntry('error', 'Build failed');
            }
            break;
        case 'conversation_cleared':
            // Conversation was cleared (e.g., from another tab or endpoint)
            if (data.conversation) {
                renderConversation(data.conversation);
            }
            addLogEntry('info', 'Conversation cleared');
            break;
    }
}

// === Render Functions ===

function renderTemplates() {
    const container = document.getElementById('templates-list');
    container.innerHTML = templates.map(t => `
        <div class="project-item template-item" data-id="${t.id}" onclick="forkTemplate('${t.id}')">
            <span class="project-icon">📦</span>
            <span class="project-name">${t.name}</span>
        </div>
    `).join('');
}

function populateTemplateSelect() {
    const select = document.getElementById('template-select');
    templates.forEach(t => {
        const option = document.createElement('option');
        option.value = t.id;
        option.textContent = t.name;
        select.appendChild(option);
    });
}

function renderProjects() {
    const container = document.getElementById('projects-list');
    
    if (projects.length === 0) {
        container.innerHTML = '<div class="empty-list">No projects yet</div>';
        return;
    }
    
    container.innerHTML = projects.map(p => `
        <div class="project-item ${p.id === currentProjectId ? 'active' : ''}" 
             data-id="${p.id}" 
             onclick="selectProject('${p.id}')">
            <span class="project-icon">${getStatusIcon(p.status)}</span>
            <span class="project-name">${p.name}</span>
            <span class="project-status-dot ${p.status}"></span>
        </div>
    `).join('');
}

function getStatusIcon(status) {
    const icons = {
        'created': '📝',
        'scaffolded': '📝',
        'compiled': '✅',
        'build_failed': '❌',
        'error': '⚠️'
    };
    return icons[status] || '📁';
}

function showProjectView(project, conversation) {
    document.getElementById('empty-state').style.display = 'none';
    document.getElementById('project-view').style.display = 'flex';
    
    // Update header
    document.getElementById('project-name').textContent = project.name;
    document.getElementById('project-status').textContent = project.status;
    document.getElementById('project-status').className = `status-badge ${project.status}`;
    
    const templateName = project.forked_from || project.template_source || 'scratch';
    document.getElementById('project-template').textContent = `From: ${templateName}`;
    
    // Update buttons
    const hasRom = project.status === 'compiled' || project.status === 'verified';
    document.getElementById('play-btn').disabled = !hasRom;
    document.getElementById('download-btn').disabled = !hasRom;
    
    // Render files
    renderFileBrowser(project);
    
    // Reset code editor - auto-load first file if available
    const files = project.summary?.files || [];
    if (files.length > 0) {
        viewFile(files[0].path);
    } else {
        // Show empty editor state
        document.getElementById('code-editor').innerHTML = `
            <div class="editor-empty">
                <p>No source files yet</p>
                <p class="text-muted">Use the chat to add features to your game</p>
            </div>
        `;
    }
    
    // Render conversation
    renderConversation(conversation);
}

function renderFileBrowser(project) {
    const container = document.getElementById('file-browser');
    
    // Get files from summary if available
    const files = project.summary?.files || [];
    
    if (files.length === 0) {
        container.innerHTML = '<div class="empty-list">No files yet</div>';
        return;
    }
    
    container.innerHTML = files.map(f => `
        <div class="file-item" data-path="${f.path}" onclick="viewFile('${f.path}')">
            <span class="file-icon">📄</span>
            <span class="file-name">${f.path}</span>
        </div>
    `).join('');
}

function renderConversation(conversation) {
    const container = document.getElementById('chat-messages');
    
    // Filter to only show user and assistant messages (hide system messages)
    const visibleTurns = (conversation.turns || []).filter(turn => 
        turn.role === 'user' || turn.role === 'assistant'
    );
    
    if (visibleTurns.length === 0) {
        container.innerHTML = `
            <div class="chat-welcome">
                <p>👋 Hi! I'm your AI game developer.</p>
                <p>Tell me what features you'd like to add to your game!</p>
            </div>
        `;
        return;
    }
    
    container.innerHTML = visibleTurns.map(turn => `
        <div class="chat-message ${turn.role}">
            <div class="message-avatar">${turn.role === 'user' ? '👤' : '🤖'}</div>
            <div class="message-content">
                <div class="message-text">${formatMessage(turn.content)}</div>
                <div class="message-time">${formatTime(turn.timestamp)}</div>
            </div>
        </div>
    `).join('');
    
    // Scroll to bottom
    container.scrollTop = container.scrollHeight;
}

function formatMessage(content) {
    // Handle code blocks first (before line break conversion)
    let result = content.replace(/```([^`]*)```/g, (match, code) => {
        const escaped = code
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;');
        return `<pre><code>${escaped.trim()}</code></pre>`;
    });
    
    // Handle inline code
    result = result.replace(/`([^`]+)`/g, '<code>$1</code>');
    
    // Handle headers (## Header -> bold, ### Header -> bold smaller)
    result = result.replace(/^### (.+)$/gm, '<strong class="md-h3">$1</strong>');
    result = result.replace(/^## (.+)$/gm, '<strong class="md-h2">$1</strong>');
    result = result.replace(/^# (.+)$/gm, '<strong class="md-h1">$1</strong>');
    
    // Handle bold
    result = result.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
    
    // Handle italic
    result = result.replace(/\*([^*]+)\*/g, '<em>$1</em>');
    
    // Handle bullet points
    result = result.replace(/^- (.+)$/gm, '• $1');
    
    // Handle numbered lists
    result = result.replace(/^(\d+)\. (.+)$/gm, '$1. $2');
    
    // Handle line breaks (but not inside pre tags)
    const parts = result.split(/(<pre>[\s\S]*?<\/pre>)/);
    result = parts.map(part => {
        if (part.startsWith('<pre>')) return part;
        return part.replace(/\n/g, '<br>');
    }).join('');
    
    return result;
}

function formatTime(timestamp) {
    if (!timestamp) return '';
    const date = new Date(timestamp);
    return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}

// === Handlers ===

function showNewProjectModal() {
    document.getElementById('new-project-modal').style.display = 'block';
    document.getElementById('project-name-input').focus();
}

function hideNewProjectModal() {
    document.getElementById('new-project-modal').style.display = 'none';
    document.getElementById('new-project-form').reset();
}

async function handleCreateProject(e) {
    e.preventDefault();
    
    const name = document.getElementById('project-name-input').value.trim();
    const templateId = document.getElementById('template-select').value;
    const description = document.getElementById('project-description').value.trim();
    
    try {
        const response = await apiRequest('/api/v2/projects', {
            method: 'POST',
            body: JSON.stringify({
                name: name,
                template_id: templateId || null,
                prompt: description || `New project: ${name}`
            })
        });
        
        hideNewProjectModal();
        await loadProjects();
        await selectProject(response.project_id);
        
        addLogEntry('success', `Created project: ${name}`);
        
    } catch (error) {
        addLogEntry('error', `Failed to create project: ${error.message}`);
    }
}

async function forkTemplate(templateId) {
    document.getElementById('template-select').value = templateId;
    showNewProjectModal();
}

async function handleNewChat() {
    if (!currentProjectId) return;
    
    // Confirm with user
    if (!confirm('Start a new chat? This will clear the conversation history for this project.')) {
        return;
    }
    
    try {
        setChatStatus('Clearing...');
        
        const response = await apiRequest(`/api/v2/projects/${currentProjectId}/new-chat`, {
            method: 'POST'
        });
        
        // Render the cleared conversation
        if (response && response.conversation) {
            renderConversation(response.conversation);
        }
        
        addLogEntry('info', 'Started new chat');
        setChatStatus('Ready');
        
    } catch (error) {
        addLogEntry('error', `Failed to start new chat: ${error.message}`);
        setChatStatus('Ready');
    }
}

async function handleSendMessage() {
    const input = document.getElementById('chat-input');
    const sendBtn = document.getElementById('send-btn');
    const message = input.value.trim();
    
    if (!message || !currentProjectId) return;
    
    // Clear input and set loading state
    input.value = '';
    setLoadingState(true);
    
    // Add user message to UI immediately
    addChatMessage('user', message);
    
    // Show typing indicator
    const typingIndicator = showTypingIndicator();
    
    // Show loading state
    setChatStatus('Thinking...');
    addLogEntry('info', 'Chatting with Designer...');
    
    try {
        // Use dialogue endpoint (no implementation)
        const response = await apiRequest(`/api/v2/projects/${currentProjectId}/chat`, {
            method: 'POST',
            body: JSON.stringify({ message })
        });
        
        // Remove typing indicator
        typingIndicator.remove();
        
        // Add assistant response
        if (response && response.response) {
            addChatMessage('assistant', response.response);
            addLogEntry('info', 'Dialogue complete');
        } else {
            addChatMessage('assistant', 'Received an empty response. Please try again.');
            addLogEntry('warning', 'Empty response from server');
        }
        
    } catch (error) {
        typingIndicator.remove();
        const errorMsg = error?.message || error?.toString() || 'Unknown error occurred';
        addChatMessage('assistant', `Error: ${errorMsg}`);
        addLogEntry('error', errorMsg);
    }
    
    setLoadingState(false);
    setChatStatus('Ready');
}

// Build Feature - synthesizes conversation and implements
async function handleBuildFeature() {
    const buildBtn = document.getElementById('build-feature-btn');
    const input = document.getElementById('chat-input');
    const message = input.value.trim();
    
    if (!currentProjectId) return;
    
    // Check if there's any conversation or a message to build from
    const project = currentProject;
    const hasConversation = (project?.conversation?.length > 0) || message;
    
    if (!hasConversation) {
        addChatMessage('assistant', "💡 **Tip:** Start by describing what you want to build! Tell me about the game mechanics, features, or changes you'd like to make, then click **Build Feature** when you're ready.");
        return;
    }
    
    // If there's a message typed, show it in chat immediately
    if (message) {
        addChatMessage('user', message);
        input.value = '';
    }
    
    // Set loading state
    setLoadingState(true);
    buildBtn.disabled = true;
    buildBtn.textContent = '⏳ Building...';
    
    setChatStatus('Building features...');
    addLogEntry('agent', '🚀 Building features from conversation...');
    addChatMessage('system', '⚡ **Building features from our conversation...**');
    
    try {
        // Pass the message to build-feature endpoint - it will be added as a feature_request
        const requestBody = message ? { message } : {};
        const response = await apiRequest(`/api/v2/projects/${currentProjectId}/build-feature`, {
            method: 'POST',
            body: JSON.stringify(requestBody)
        });
        
        // Add the response to chat
        addChatMessage('assistant', response.response);
        
        if (response.success && response.features_implemented?.length > 0) {
            addLogEntry('success', `Implemented: ${response.features_implemented.join(', ')}`);
            // Refresh project state since files changed
            await refreshProjectState();
            hideRetryButton();
        } else if (response.success) {
            addLogEntry('info', 'No features identified to implement');
            hideRetryButton();
        } else {
            addLogEntry('error', response.error || 'Build failed');
            // Show retry button if available
            if (response.can_retry) {
                showRetryButton();
            }
        }
        
    } catch (error) {
        addChatMessage('assistant', `❌ Build error: ${error.message}`);
        addLogEntry('error', error.message);
    }
    
    setLoadingState(false);
    buildBtn.disabled = false;
    buildBtn.textContent = '⚡ Build Feature';
    setChatStatus('Ready');
    // Hide progress bar when build finishes (success or failure handled by response)
}

// Light refresh - updates project data without reconnecting WebSocket
async function refreshProjectState() {
    if (!currentProjectId) return;
    
    try {
        const project = await apiRequest(`/api/v2/projects/${currentProjectId}`);
        currentProject = project;
        
        // Update status badge
        document.getElementById('project-status').textContent = project.status;
        document.getElementById('project-status').className = `status-badge ${project.status}`;
        
        // Update buttons
        const hasRom = project.status === 'compiled' || project.status === 'verified';
        document.getElementById('play-btn').disabled = !hasRom;
        document.getElementById('download-btn').disabled = !hasRom;
        
        // Refresh file browser
        renderFileBrowser(project);
        
        // Refresh current file if one is selected
        const activeFile = document.querySelector('.file-item.active');
        if (activeFile) {
            await viewFile(activeFile.dataset.path);
        }
        
        addLogEntry('info', 'Files refreshed');
    } catch (error) {
        console.error('Failed to refresh project:', error);
    }
}

// Retry button management
function showRetryButton() {
    const retryBtn = document.getElementById('retry-btn');
    if (retryBtn) {
        retryBtn.style.display = 'inline-flex';
    }
}

function hideRetryButton() {
    const retryBtn = document.getElementById('retry-btn');
    if (retryBtn) {
        retryBtn.style.display = 'none';
    }
}

async function handleRetry() {
    if (!currentProjectId) return;
    
    const retryBtn = document.getElementById('retry-btn');
    const input = document.getElementById('chat-input');
    const additionalGuidance = input.value.trim();
    
    // Clear input if used as guidance
    if (additionalGuidance) {
        input.value = '';
        addChatMessage('user', `[Retry guidance] ${additionalGuidance}`);
    }
    
    // Set loading state
    setLoadingState(true);
    retryBtn.disabled = true;
    retryBtn.textContent = '⏳ Retrying...';
    
    setChatStatus('Retrying build...');
    addLogEntry('agent', '🔄 Retrying from last failure...');
    addChatMessage('system', '🔄 **Retrying the failed build...**');
    
    try {
        const requestBody = additionalGuidance ? { additional_guidance: additionalGuidance } : {};
        const response = await apiRequest(`/api/v2/projects/${currentProjectId}/retry`, {
            method: 'POST',
            body: JSON.stringify(requestBody)
        });
        
        // Add the response to chat
        addChatMessage('assistant', response.response);
        
        if (response.success && response.features_implemented?.length > 0) {
            addLogEntry('success', `Retry succeeded: ${response.features_implemented.join(', ')}`);
            await refreshProjectState();
            hideRetryButton();
        } else if (response.success) {
            addLogEntry('info', 'Retry completed');
            hideRetryButton();
        } else {
            addLogEntry('error', response.error || 'Retry failed');
            // Keep retry button visible if still retryable
            if (!response.can_retry) {
                hideRetryButton();
            }
        }
        
    } catch (error) {
        addChatMessage('assistant', `❌ Retry error: ${error.message}`);
        addLogEntry('error', error.message);
    }
    
    setLoadingState(false);
    retryBtn.disabled = false;
    retryBtn.textContent = '🔄 Retry';
    setChatStatus('Ready');
}

// Progress bar management
function updateProgressBar(progressStr) {
    // Parse "X/Y" format
    const match = progressStr.match(/(\d+)\/(\d+)/);
    if (!match) return;
    
    const current = parseInt(match[1]);
    const total = parseInt(match[2]);
    const percent = total > 0 ? (current / total) * 100 : 0;
    
    // Get or create progress container
    let progressContainer = document.getElementById('build-progress');
    if (!progressContainer) {
        progressContainer = document.createElement('div');
        progressContainer.id = 'build-progress';
        progressContainer.className = 'build-progress';
        progressContainer.innerHTML = `
            <div class="progress-bar-container">
                <div class="progress-bar" id="progress-bar-fill"></div>
            </div>
            <div class="progress-text" id="progress-text">0/0 steps</div>
        `;
        
        // Insert before chat buttons
        const chatButtons = document.querySelector('.chat-buttons');
        if (chatButtons && chatButtons.parentNode) {
            chatButtons.parentNode.insertBefore(progressContainer, chatButtons);
        }
    }
    
    // Show the progress bar
    progressContainer.style.display = 'flex';
    
    // Update progress
    const fill = document.getElementById('progress-bar-fill');
    const text = document.getElementById('progress-text');
    
    if (fill) {
        fill.style.width = `${percent}%`;
    }
    if (text) {
        text.textContent = `${current}/${total} steps`;
    }
}

function hideProgressBar() {
    const progressContainer = document.getElementById('build-progress');
    if (progressContainer) {
        progressContainer.style.display = 'none';
    }
}

// Set chat loading state
function setLoadingState(loading) {
    const input = document.getElementById('chat-input');
    const sendBtn = document.getElementById('send-btn');
    
    input.disabled = loading;
    sendBtn.disabled = loading;
    
    if (loading) {
        sendBtn.innerHTML = '<span class="spinner"></span>';
        sendBtn.classList.add('loading');
    } else {
        sendBtn.innerHTML = 'Send →';
        sendBtn.classList.remove('loading');
    }
}

// Show typing indicator in chat
function showTypingIndicator() {
    const container = document.getElementById('chat-messages');
    const indicator = document.createElement('div');
    indicator.className = 'chat-message assistant typing-indicator';
    indicator.id = 'typing-indicator';
    indicator.innerHTML = `
        <div class="message-avatar">🤖</div>
        <div class="message-content">
            <div class="typing-status">Thinking...</div>
            <div class="typing-dots">
                <span></span>
                <span></span>
                <span></span>
            </div>
        </div>
    `;
    container.appendChild(indicator);
    container.scrollTop = container.scrollHeight;
    return indicator;
}

// Update typing indicator status text
function updateTypingStatus(message) {
    const indicator = document.getElementById('typing-indicator');
    if (indicator) {
        const statusEl = indicator.querySelector('.typing-status');
        if (statusEl) {
            statusEl.textContent = message;
        }
        // Scroll to bottom to show new status
        const container = document.getElementById('chat-messages');
        container.scrollTop = container.scrollHeight;
    }
}

function addChatMessage(role, content) {
    const container = document.getElementById('chat-messages');
    const messageEl = document.createElement('div');
    
    // Handle system messages (like build notifications) differently
    if (role === 'system') {
        messageEl.className = 'chat-message system';
        messageEl.innerHTML = `
            <div class="message-content system-message">
                <div class="message-text">${formatMessage(content)}</div>
            </div>
        `;
    } else {
        messageEl.className = `chat-message ${role}`;
        messageEl.innerHTML = `
            <div class="message-avatar">${role === 'user' ? '👤' : '🤖'}</div>
            <div class="message-content">
                <div class="message-text">${formatMessage(content)}</div>
                <div class="message-time">${new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</div>
            </div>
        `;
    }
    
    container.appendChild(messageEl);
    container.scrollTop = container.scrollHeight;
}

async function handleBuild() {
    if (!currentProjectId) return;
    
    addLogEntry('info', 'Starting build...');
    setChatStatus('Building...');
    
    try {
        const response = await apiRequest(`/api/v2/projects/${currentProjectId}/build`, {
            method: 'POST'
        });
        
        if (response.success) {
            addLogEntry('success', 'Build successful!');
            addChatMessage('assistant', '✅ **Build successful!** Your ROM is ready to play. Switch to the Emulator tab to test it!');
            updateProjectStatus('compiled');
            document.getElementById('play-btn').disabled = false;
            document.getElementById('download-btn').disabled = false;
            
            // Update emulator state
            await refreshProjectState();
            updateEmulatorState();
        } else {
            addLogEntry('error', 'Build failed');
            updateProjectStatus('build_failed');
            
            // Format error message nicely for chat
            const errorMsg = response.error || 'Unknown build error';
            const formattedError = formatBuildError(errorMsg);
            addChatMessage('assistant', `❌ **Build failed!**\n\n${formattedError}\n\nTry describing what you want to fix, or check the error details above.`);
        }
        
    } catch (error) {
        addLogEntry('error', `Build error: ${error.message}`);
        addChatMessage('assistant', `⚠️ Error triggering build: ${error.message}`);
    }
    
    setChatStatus('Ready');
}

function formatBuildError(error) {
    // Extract key error lines from compiler output
    const lines = error.split('\n');
    const errorLines = lines.filter(line => 
        line.includes('error:') || 
        line.includes('Error:') ||
        line.includes('undefined reference') ||
        line.includes('undeclared') ||
        line.includes('syntax error')
    );
    
    if (errorLines.length > 0) {
        // Show up to 5 key errors
        return '```\n' + errorLines.slice(0, 5).join('\n') + '\n```';
    }
    
    // If no specific errors found, show last 10 lines of output
    const lastLines = lines.slice(-10).filter(l => l.trim());
    return '```\n' + lastLines.join('\n') + '\n```';
}

async function handlePlay() {
    if (!currentProjectId) return;
    
    const playBtn = document.getElementById('play-btn');
    const originalText = playBtn.textContent;
    playBtn.disabled = true;
    playBtn.textContent = '🚀 Launching...';
    
    try {
        const response = await fetch(`/api/v2/projects/${currentProjectId}/play`, {
            method: 'POST'
        });
        
        if (!response.ok) {
            const data = await response.json();
            throw new Error(data.detail || 'Failed to launch emulator');
        }
        
        const data = await response.json();
        addChatMessage('assistant', `🎮 **Launched SameBoy!** Playing: \`${data.rom_path.split('/').pop()}\``);
    } catch (error) {
        console.error('Play error:', error);
        addChatMessage('assistant', `❌ **Play failed:** ${error.message}`);
    } finally {
        playBtn.disabled = false;
        playBtn.textContent = originalText;
    }
}

async function handleDownload() {
    if (!currentProjectId) return;
    
    window.location.href = `/api/v2/projects/${currentProjectId}/files/rom`;
}

// === Panel Tabs (Files / Emulator) ===

function switchPanelTab(tabName) {
    // Update tab buttons
    document.querySelectorAll('.panel-tab').forEach(tab => {
        tab.classList.toggle('active', tab.dataset.tab === tabName);
    });
    
    // Update tab content
    document.querySelectorAll('.tab-content').forEach(content => {
        content.classList.remove('active');
    });
    document.getElementById(`${tabName}-content`).classList.add('active');
    
    // If switching to emulator, check if we should auto-load ROM
    if (tabName === 'emulator' && currentProject) {
        updateEmulatorState();
    }
    
    // If switching to agents, load agent config
    if (tabName === 'agents' && currentProjectId) {
        loadAgentConfig();
    }
    
    // If switching to sprites, load sprites
    if (tabName === 'sprites' && currentProjectId) {
        loadSprites();
    }
    
    // If switching to tuning, load tunables
    if (tabName === 'tuning' && currentProjectId) {
        loadTunables();
    }
    
    // If switching to data, load data schema
    if (tabName === 'data' && currentProjectId) {
        loadDataSchema();
    }
}

// === Tunable Parameters ===

let tunableData = null;
let tunableChanges = {};  // Track pending changes: { name: newValue }
let originalTunables = {};  // Store original values for reset

async function loadTunables() {
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

// === Data Management ===

let dataSchema = null;
let currentTableName = null;
let currentTableData = null;
let dataSortColumn = null;
let dataSortDesc = false;
let dataSearchQuery = '';

async function loadDataSchema() {
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

// Debounce helper for search
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

// === Sprite Viewer ===

// Game Boy 4-color palette (classic green shades)
const GB_PALETTE = [
    '#9bbc0f', // Lightest (color 0)
    '#8bac0f', // Light (color 1)
    '#306230', // Dark (color 2)
    '#0f380f'  // Darkest (color 3)
];

// Alternative DMG palette (more authentic)
const DMG_PALETTE = [
    '#e0f8d0', // Lightest
    '#88c070', // Light
    '#346856', // Dark
    '#081820'  // Darkest
];

let spriteData = null;

async function loadSprites() {
    if (!currentProjectId) return;
    
    const emptyEl = document.getElementById('sprites-empty');
    const gridEl = document.getElementById('sprites-grid');
    
    try {
        spriteData = await apiRequest(`/api/v2/projects/${currentProjectId}/sprites`);
        renderSprites();
    } catch (error) {
        console.error('Failed to load sprites:', error);
        emptyEl.style.display = 'flex';
        gridEl.innerHTML = '';
    }
}

function renderSprites() {
    const emptyEl = document.getElementById('sprites-empty');
    const gridEl = document.getElementById('sprites-grid');
    
    if (!spriteData || spriteData.sprites.length === 0) {
        emptyEl.style.display = 'flex';
        gridEl.innerHTML = '';
        return;
    }
    
    emptyEl.style.display = 'none';
    
    gridEl.innerHTML = spriteData.sprites.map((sprite, idx) => `
        <div class="sprite-card" data-index="${idx}">
            <canvas class="sprite-canvas" 
                    id="sprite-canvas-${idx}" 
                    width="${sprite.width}" 
                    height="${sprite.height}"
                    title="${sprite.name}">
            </canvas>
            <div class="sprite-info">
                <span class="sprite-name">${formatSpriteName(sprite.name)}</span>
                <span class="sprite-size">${sprite.width}×${sprite.height}</span>
            </div>
            <button class="sprite-edit-btn" onclick="editSprite(${idx})" title="Edit sprite">
                ✏️ Edit
            </button>
        </div>
    `).join('');
    
    // Render each sprite to its canvas
    spriteData.sprites.forEach((sprite, idx) => {
        const canvas = document.getElementById(`sprite-canvas-${idx}`);
        if (canvas) {
            renderSpriteToCanvas(canvas, sprite);
        }
    });
}

function formatSpriteName(name) {
    // Convert snake_case to Title Case
    return name
        .replace(/_tile$|_tiles$|_sprite$|_data$/, '') // Remove common suffixes
        .replace(/_/g, ' ')
        .replace(/\b\w/g, c => c.toUpperCase());
}

/**
 * Render Game Boy 2bpp tile data to a canvas.
 * 
 * GB tiles use 2 bits per pixel, stored as 2 bytes per row.
 * Byte 0 = low bit of each pixel, Byte 1 = high bit.
 * Color = (highBit << 1) | lowBit
 */
function renderSpriteToCanvas(canvas, sprite) {
    const ctx = canvas.getContext('2d');
    const { width, height, data } = sprite;
    const palette = DMG_PALETTE;
    
    // Scale factor for display (make small sprites visible)
    const scale = width <= 8 ? 6 : (width <= 16 ? 4 : 2);
    canvas.style.width = `${width * scale}px`;
    canvas.style.height = `${height * scale}px`;
    canvas.style.imageRendering = 'pixelated';
    
    // Clear canvas
    ctx.clearRect(0, 0, width, height);
    
    // Process tile data (2 bytes per row, 8 pixels per row)
    let byteIndex = 0;
    
    for (let tileY = 0; tileY < height; tileY += 8) {
        for (let tileX = 0; tileX < width; tileX += 8) {
            // Each 8x8 tile is 16 bytes
            for (let row = 0; row < 8 && (tileY + row) < height; row++) {
                if (byteIndex + 1 >= data.length) break;
                
                const lowByte = data[byteIndex];
                const highByte = data[byteIndex + 1];
                byteIndex += 2;
                
                // Decode 8 pixels from this row
                for (let bit = 7; bit >= 0 && (tileX + (7 - bit)) < width; bit--) {
                    const lowBit = (lowByte >> bit) & 1;
                    const highBit = (highByte >> bit) & 1;
                    const colorIndex = (highBit << 1) | lowBit;
                    
                    const x = tileX + (7 - bit);
                    const y = tileY + row;
                    
                    ctx.fillStyle = palette[colorIndex];
                    ctx.fillRect(x, y, 1, 1);
                }
            }
        }
    }
}

// === Sprite Editor ===

const spriteEditor = {
    canvas: null,
    ctx: null,
    previewCanvas: null,
    previewCtx: null,
    width: 8,
    height: 8,
    pixels: null,  // 2D array of color indices (0-3)
    currentColor: 0,
    currentTool: 'pencil',
    isDrawing: false,
    editingSprite: null,  // Name of sprite being edited, null for new
    scale: 24,  // Pixels per GB pixel in editor
};

function initSpriteEditor() {
    spriteEditor.canvas = document.getElementById('sprite-editor-canvas');
    spriteEditor.ctx = spriteEditor.canvas.getContext('2d');
    spriteEditor.previewCanvas = document.getElementById('sprite-preview-canvas');
    spriteEditor.previewCtx = spriteEditor.previewCanvas.getContext('2d');
    
    // Mouse events for drawing
    spriteEditor.canvas.addEventListener('mousedown', handleEditorMouseDown);
    spriteEditor.canvas.addEventListener('mousemove', handleEditorMouseMove);
    spriteEditor.canvas.addEventListener('mouseup', handleEditorMouseUp);
    spriteEditor.canvas.addEventListener('mouseleave', handleEditorMouseUp);
    
    // Touch support
    spriteEditor.canvas.addEventListener('touchstart', handleEditorTouchStart);
    spriteEditor.canvas.addEventListener('touchmove', handleEditorTouchMove);
    spriteEditor.canvas.addEventListener('touchend', handleEditorMouseUp);
    
    // Tool buttons
    document.querySelectorAll('.tool-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            document.querySelectorAll('.tool-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            spriteEditor.currentTool = btn.dataset.tool;
        });
    });
    
    // Palette buttons
    document.querySelectorAll('.palette-color').forEach(btn => {
        btn.addEventListener('click', () => {
            document.querySelectorAll('.palette-color').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            spriteEditor.currentColor = parseInt(btn.dataset.color);
        });
    });
    
    // Size buttons
    document.querySelectorAll('.size-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            document.querySelectorAll('.size-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            const [w, h] = btn.dataset.size.split('x').map(Number);
            resizeSpriteCanvas(w, h);
        });
    });
    
    // Create sprite button
    document.getElementById('create-sprite-btn').addEventListener('click', () => {
        showSpriteEditor(null);
    });
    
    // Save button
    document.getElementById('save-sprite-btn').addEventListener('click', saveSprite);
}

function showSpriteEditor(existingSprite = null) {
    const modal = document.getElementById('sprite-editor-modal');
    const title = document.getElementById('sprite-editor-title');
    const nameInput = document.getElementById('sprite-name-input');
    
    spriteEditor.editingSprite = existingSprite;
    
    if (existingSprite) {
        title.textContent = 'Edit Sprite';
        nameInput.value = existingSprite.name;
        resizeSpriteCanvas(existingSprite.width, existingSprite.height);
        loadSpriteIntoEditor(existingSprite);
        
        // Update size button
        const sizeStr = `${existingSprite.width}x${existingSprite.height}`;
        document.querySelectorAll('.size-btn').forEach(btn => {
            btn.classList.toggle('active', btn.dataset.size === sizeStr);
        });
    } else {
        title.textContent = 'Create Sprite';
        nameInput.value = '';
        resizeSpriteCanvas(8, 8);
        clearSpriteCanvas();
        
        // Reset to 8x8
        document.querySelectorAll('.size-btn').forEach(btn => {
            btn.classList.toggle('active', btn.dataset.size === '8x8');
        });
    }
    
    // Reset tools
    spriteEditor.currentColor = 0;
    spriteEditor.currentTool = 'pencil';
    document.querySelectorAll('.palette-color').forEach(b => b.classList.toggle('active', b.dataset.color === '0'));
    document.querySelectorAll('.tool-btn').forEach(b => b.classList.toggle('active', b.dataset.tool === 'pencil'));
    
    modal.style.display = 'flex';
}

function hideSpriteEditor() {
    document.getElementById('sprite-editor-modal').style.display = 'none';
}

function resizeSpriteCanvas(width, height) {
    spriteEditor.width = width;
    spriteEditor.height = height;
    
    // Update canvas size
    spriteEditor.canvas.width = width;
    spriteEditor.canvas.height = height;
    spriteEditor.previewCanvas.width = width;
    spriteEditor.previewCanvas.height = height;
    
    // Scale for display
    const scale = width <= 8 ? 24 : (width <= 16 ? 16 : 12);
    spriteEditor.scale = scale;
    spriteEditor.canvas.style.width = `${width * scale}px`;
    spriteEditor.canvas.style.height = `${height * scale}px`;
    spriteEditor.previewCanvas.style.width = `${width * 4}px`;
    spriteEditor.previewCanvas.style.height = `${height * 4}px`;
    
    // Initialize pixel array
    spriteEditor.pixels = Array(height).fill(null).map(() => Array(width).fill(0));
    
    // Update grid overlay
    updateGridOverlay();
    
    renderEditorCanvas();
    updatePreview();
}

function updateGridOverlay() {
    const overlay = document.getElementById('sprite-grid-overlay');
    const { width, height, scale } = spriteEditor;
    
    overlay.style.width = `${width * scale}px`;
    overlay.style.height = `${height * scale}px`;
    overlay.style.backgroundSize = `${scale}px ${scale}px`;
}

function loadSpriteIntoEditor(sprite) {
    const { width, height, data } = sprite;
    spriteEditor.pixels = Array(height).fill(null).map(() => Array(width).fill(0));
    
    // Decode 2bpp data into pixels array
    let byteIndex = 0;
    
    for (let tileY = 0; tileY < height; tileY += 8) {
        for (let tileX = 0; tileX < width; tileX += 8) {
            for (let row = 0; row < 8 && (tileY + row) < height; row++) {
                if (byteIndex + 1 >= data.length) break;
                
                const lowByte = data[byteIndex];
                const highByte = data[byteIndex + 1];
                byteIndex += 2;
                
                for (let bit = 7; bit >= 0 && (tileX + (7 - bit)) < width; bit--) {
                    const lowBit = (lowByte >> bit) & 1;
                    const highBit = (highByte >> bit) & 1;
                    const colorIndex = (highBit << 1) | lowBit;
                    
                    const x = tileX + (7 - bit);
                    const y = tileY + row;
                    spriteEditor.pixels[y][x] = colorIndex;
                }
            }
        }
    }
    
    renderEditorCanvas();
    updatePreview();
}

function renderEditorCanvas() {
    const { ctx, width, height, pixels } = spriteEditor;
    
    ctx.clearRect(0, 0, width, height);
    
    for (let y = 0; y < height; y++) {
        for (let x = 0; x < width; x++) {
            const colorIndex = pixels[y][x];
            ctx.fillStyle = DMG_PALETTE[colorIndex];
            ctx.fillRect(x, y, 1, 1);
        }
    }
}

function updatePreview() {
    const { previewCtx, width, height, pixels } = spriteEditor;
    
    previewCtx.clearRect(0, 0, width, height);
    
    for (let y = 0; y < height; y++) {
        for (let x = 0; x < width; x++) {
            const colorIndex = pixels[y][x];
            previewCtx.fillStyle = DMG_PALETTE[colorIndex];
            previewCtx.fillRect(x, y, 1, 1);
        }
    }
}

function getEditorPixelCoords(e) {
    const rect = spriteEditor.canvas.getBoundingClientRect();
    const scaleX = spriteEditor.width / rect.width;
    const scaleY = spriteEditor.height / rect.height;
    
    const x = Math.floor((e.clientX - rect.left) * scaleX);
    const y = Math.floor((e.clientY - rect.top) * scaleY);
    
    return { x: Math.max(0, Math.min(x, spriteEditor.width - 1)), 
             y: Math.max(0, Math.min(y, spriteEditor.height - 1)) };
}

function handleEditorMouseDown(e) {
    spriteEditor.isDrawing = true;
    applyTool(e);
}

function handleEditorMouseMove(e) {
    if (!spriteEditor.isDrawing) return;
    applyTool(e);
}

function handleEditorMouseUp() {
    spriteEditor.isDrawing = false;
}

function handleEditorTouchStart(e) {
    e.preventDefault();
    spriteEditor.isDrawing = true;
    const touch = e.touches[0];
    applyTool({ clientX: touch.clientX, clientY: touch.clientY });
}

function handleEditorTouchMove(e) {
    e.preventDefault();
    if (!spriteEditor.isDrawing) return;
    const touch = e.touches[0];
    applyTool({ clientX: touch.clientX, clientY: touch.clientY });
}

function applyTool(e) {
    const { x, y } = getEditorPixelCoords(e);
    const { currentTool, currentColor, pixels, width, height } = spriteEditor;
    
    switch (currentTool) {
        case 'pencil':
            pixels[y][x] = currentColor;
            break;
        case 'eraser':
            pixels[y][x] = 0;  // Lightest color
            break;
        case 'fill':
            floodFill(x, y, pixels[y][x], currentColor);
            break;
    }
    
    renderEditorCanvas();
    updatePreview();
}

function floodFill(startX, startY, targetColor, fillColor) {
    if (targetColor === fillColor) return;
    
    const { pixels, width, height } = spriteEditor;
    const stack = [[startX, startY]];
    
    while (stack.length > 0) {
        const [x, y] = stack.pop();
        
        if (x < 0 || x >= width || y < 0 || y >= height) continue;
        if (pixels[y][x] !== targetColor) continue;
        
        pixels[y][x] = fillColor;
        
        stack.push([x + 1, y]);
        stack.push([x - 1, y]);
        stack.push([x, y + 1]);
        stack.push([x, y - 1]);
    }
}

function clearSpriteCanvas() {
    const { width, height } = spriteEditor;
    spriteEditor.pixels = Array(height).fill(null).map(() => Array(width).fill(0));
    renderEditorCanvas();
    updatePreview();
}

function flipSpriteH() {
    const { pixels, width, height } = spriteEditor;
    for (let y = 0; y < height; y++) {
        pixels[y].reverse();
    }
    renderEditorCanvas();
    updatePreview();
}

function flipSpriteV() {
    spriteEditor.pixels.reverse();
    renderEditorCanvas();
    updatePreview();
}

function pixelsTo2bpp() {
    const { pixels, width, height } = spriteEditor;
    const bytes = [];
    
    // Process in 8x8 tile chunks
    for (let tileY = 0; tileY < height; tileY += 8) {
        for (let tileX = 0; tileX < width; tileX += 8) {
            // Each tile row is 2 bytes
            for (let row = 0; row < 8 && (tileY + row) < height; row++) {
                let lowByte = 0;
                let highByte = 0;
                
                for (let bit = 7; bit >= 0; bit--) {
                    const x = tileX + (7 - bit);
                    const y = tileY + row;
                    const colorIndex = x < width ? pixels[y][x] : 0;
                    
                    if (colorIndex & 1) lowByte |= (1 << bit);
                    if (colorIndex & 2) highByte |= (1 << bit);
                }
                
                bytes.push(lowByte, highByte);
            }
        }
    }
    
    return bytes;
}

async function saveSprite() {
    const nameInput = document.getElementById('sprite-name-input');
    let name = nameInput.value.trim();
    
    // Validate name
    if (!name) {
        alert('Please enter a sprite name');
        nameInput.focus();
        return;
    }
    
    // Ensure valid C identifier
    name = name.toLowerCase().replace(/[^a-z0-9_]/g, '_');
    if (!/^[a-z_]/.test(name)) {
        name = 'sprite_' + name;
    }
    
    // Add suffix if not present
    if (!name.endsWith('_tile') && !name.endsWith('_tiles') && !name.endsWith('_sprite')) {
        name += '_tile';
    }
    
    const data = pixelsTo2bpp();
    
    try {
        await apiRequest(`/api/v2/projects/${currentProjectId}/sprites`, {
            method: 'POST',
            body: JSON.stringify({
                name: name,
                width: spriteEditor.width,
                height: spriteEditor.height,
                data: data,
                replace: spriteEditor.editingSprite?.name || null
            })
        });
        
        hideSpriteEditor();
        loadSprites();  // Refresh sprite list
        addLogEntry('success', `Sprite "${name}" saved`);
    } catch (error) {
        console.error('Failed to save sprite:', error);
        addLogEntry('error', `Failed to save sprite: ${error.message}`);
    }
}

function editSprite(index) {
    if (!spriteData || !spriteData.sprites[index]) return;
    showSpriteEditor(spriteData.sprites[index]);
}

// Initialize editor when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    // Delay init until elements exist
    setTimeout(initSpriteEditor, 100);
});

// === Agent Configuration ===

let agentConfig = null;

async function loadAgentConfig() {
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

function capitalize(str) {
    return str.charAt(0).toUpperCase() + str.slice(1);
}

function escapeHtml(str) {
    if (str === null || str === undefined) return '';
    return String(str)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#039;');
}

// === Emulator Functions ===

let emulatorLoaded = false;

async function updateEmulatorState() {
    // Check if project has been compiled (status is 'compiled' or 'verified')
    const hasRom = currentProject && ['compiled', 'verified'].includes(currentProject.status);
    const overlay = document.getElementById('emulator-overlay');
    const playBtn = document.getElementById('emu-play-btn');
    const pauseBtn = document.getElementById('emu-pause-btn');
    const reloadBtn = document.getElementById('emu-reload-btn');
    
    if (!overlay) return; // Guard against missing elements
    
    if (hasRom) {
        playBtn.disabled = false;
        reloadBtn.disabled = false;
        
        // Update overlay message
        const message = overlay.querySelector('.emulator-message');
        if (!emulatorLoaded) {
            message.innerHTML = `
                <span class="emulator-icon">🎮</span>
                <p>Click Play to start the game</p>
            `;
        }
    } else {
        playBtn.disabled = true;
        pauseBtn.disabled = true;
        reloadBtn.disabled = true;
        overlay.classList.remove('hidden');
        
        const message = overlay.querySelector('.emulator-message');
        message.innerHTML = `
            <span class="emulator-icon">🔨</span>
            <p>Build the project first</p>
        `;
    }
}

async function handleEmulatorPlay() {
    if (!currentProjectId) return;
    
    const overlay = document.getElementById('emulator-overlay');
    const canvas = document.getElementById('emulator-canvas');
    const playBtn = document.getElementById('emu-play-btn');
    const pauseBtn = document.getElementById('emu-pause-btn');
    
    try {
        // Show loading state
        const message = overlay.querySelector('.emulator-message');
        message.innerHTML = `
            <span class="emulator-icon">⏳</span>
            <p>Loading ROM...</p>
        `;
        
        // Get ROM URL
        const romUrl = `/api/v2/projects/${currentProjectId}/files/rom`;
        
        // Load ROM into emulator
        await window.GBEmulator.loadRom(romUrl, canvas);
        
        // Hide overlay
        overlay.classList.add('hidden');
        emulatorLoaded = true;
        
        // Update button states
        playBtn.disabled = true;
        pauseBtn.disabled = false;
        
    } catch (error) {
        console.error('Emulator error:', error);
        const message = overlay.querySelector('.emulator-message');
        message.innerHTML = `
            <span class="emulator-icon">❌</span>
            <p>Failed to load ROM: ${error.message}</p>
        `;
    }
}

function handleEmulatorPause() {
    const emu = window.GBEmulator.get();
    if (!emu) return;
    
    const playBtn = document.getElementById('emu-play-btn');
    const pauseBtn = document.getElementById('emu-pause-btn');
    
    if (emu.isPaused) {
        emu.resume();
        pauseBtn.textContent = '⏸️ Pause';
    } else {
        emu.pause();
        pauseBtn.textContent = '▶️ Resume';
    }
}

async function handleEmulatorReload() {
    // Stop current emulator
    window.GBEmulator.stop();
    emulatorLoaded = false;
    
    const overlay = document.getElementById('emulator-overlay');
    overlay.classList.remove('hidden');
    
    const playBtn = document.getElementById('emu-play-btn');
    const pauseBtn = document.getElementById('emu-pause-btn');
    playBtn.disabled = false;
    pauseBtn.disabled = true;
    pauseBtn.textContent = '⏸️ Pause';
    
    // Auto-play after reload
    await handleEmulatorPlay();
}

function handleEmulatorVolume(e) {
    const emu = window.GBEmulator.get();
    if (emu) {
        emu.setVolume(e.target.value / 100);
    }
}

async function viewFile(filePath) {
    if (!currentProjectId) return;
    
    const editor = document.getElementById('code-editor');
    editor.innerHTML = `<div class="editor-content"><pre>Loading ${filePath}...</pre></div>`;
    
    addLogEntry('info', `Viewing: ${filePath}`);
    
    // Highlight selected file
    document.querySelectorAll('.file-item').forEach(el => {
        el.classList.toggle('active', el.dataset.path === filePath);
    });
    
    try {
        const response = await apiRequest(`/api/v2/projects/${currentProjectId}/files/${filePath}`);
        
        // Apply syntax highlighting for C files
        const highlighted = highlightC(response.content);
        editor.innerHTML = `
            <div class="editor-header">
                <span class="editor-filename">${filePath}</span>
                <span class="editor-info">${response.lines} lines</span>
            </div>
            <div class="editor-content">
                <pre><code>${highlighted}</code></pre>
            </div>
        `;
    } catch (error) {
        editor.innerHTML = `<div class="editor-error">Error loading file: ${error.message}</div>`;
        addLogEntry('error', `Failed to load ${filePath}: ${error.message}`);
    }
}

// Simple C syntax highlighting using token-based approach
function highlightC(code) {
    // Tokenize to avoid corrupting our own HTML
    const tokens = [];
    let i = 0;
    
    while (i < code.length) {
        // Multi-line comment
        if (code.slice(i, i+2) === '/*') {
            const end = code.indexOf('*/', i+2);
            const endPos = end === -1 ? code.length : end + 2;
            tokens.push({ type: 'comment', text: code.slice(i, endPos) });
            i = endPos;
        }
        // Single-line comment
        else if (code.slice(i, i+2) === '//') {
            const end = code.indexOf('\n', i);
            const endPos = end === -1 ? code.length : end;
            tokens.push({ type: 'comment', text: code.slice(i, endPos) });
            i = endPos;
        }
        // String
        else if (code[i] === '"') {
            let j = i + 1;
            while (j < code.length && code[j] !== '"') {
                if (code[j] === '\\') j++; // skip escaped char
                j++;
            }
            tokens.push({ type: 'string', text: code.slice(i, j+1) });
            i = j + 1;
        }
        // Char literal
        else if (code[i] === "'") {
            let j = i + 1;
            while (j < code.length && code[j] !== "'") {
                if (code[j] === '\\') j++;
                j++;
            }
            tokens.push({ type: 'string', text: code.slice(i, j+1) });
            i = j + 1;
        }
        // Preprocessor
        else if (code[i] === '#' && (i === 0 || code[i-1] === '\n')) {
            const end = code.indexOf('\n', i);
            const endPos = end === -1 ? code.length : end;
            tokens.push({ type: 'preproc', text: code.slice(i, endPos) });
            i = endPos;
        }
        // Word (identifier or keyword)
        else if (/[a-zA-Z_]/.test(code[i])) {
            let j = i;
            while (j < code.length && /[a-zA-Z0-9_]/.test(code[j])) j++;
            tokens.push({ type: 'word', text: code.slice(i, j) });
            i = j;
        }
        // Number
        else if (/[0-9]/.test(code[i])) {
            let j = i;
            if (code.slice(i, i+2).toLowerCase() === '0x') {
                j = i + 2;
                while (j < code.length && /[0-9a-fA-F]/.test(code[j])) j++;
            } else {
                while (j < code.length && /[0-9.]/.test(code[j])) j++;
            }
            tokens.push({ type: 'number', text: code.slice(i, j) });
            i = j;
        }
        // Other (operators, whitespace, etc)
        else {
            tokens.push({ type: 'other', text: code[i] });
            i++;
        }
    }
    
    // Keywords set
    const keywords = new Set(['if', 'else', 'while', 'for', 'return', 'switch', 'case', 'break', 
        'continue', 'default', 'do', 'typedef', 'struct', 'enum', 'union', 'sizeof', 'static', 
        'extern', 'const', 'volatile', 'register', 'inline', 'void', 'int', 'char', 'short', 
        'long', 'float', 'double', 'signed', 'unsigned', 'INT8', 'UINT8', 'INT16', 'UINT16', 
        'UBYTE', 'BYTE', 'TRUE', 'FALSE', 'NULL']);
    
    // Render tokens with highlighting
    return tokens.map(t => {
        const escaped = t.text
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;');
        
        switch (t.type) {
            case 'comment': return `<span class="hl-comment">${escaped}</span>`;
            case 'string': return `<span class="hl-string">${escaped}</span>`;
            case 'preproc': return `<span class="hl-preproc">${escaped}</span>`;
            case 'number': return `<span class="hl-number">${escaped}</span>`;
            case 'word': return keywords.has(t.text) 
                ? `<span class="hl-keyword">${escaped}</span>` 
                : escaped;
            default: return escaped;
        }
    }).join('');
}

// === UI Helpers ===

function setChatStatus(status) {
    document.getElementById('chat-status').textContent = status;
}

function updateProjectStatus(status) {
    const badge = document.getElementById('project-status');
    badge.textContent = status;
    badge.className = `status-badge ${status}`;
    
    if (currentProject) {
        currentProject.status = status;
    }
}

function toggleLog() {
    const log = document.getElementById('agent-log');
    log.classList.toggle('collapsed');
    document.getElementById('toggle-log').textContent = log.classList.contains('collapsed') ? '▲' : '▼';
}

function addLogEntry(type, message) {
    const container = document.getElementById('log-content');
    const entry = document.createElement('div');
    entry.className = `log-entry ${type}`;
    entry.innerHTML = `
        <span class="log-time">${new Date().toLocaleTimeString()}</span>
        <span class="log-type">[${type.toUpperCase()}]</span>
        <span class="log-message">${message}</span>
    `;
    container.appendChild(entry);
    container.scrollTop = container.scrollHeight;
    
    // Limit entries
    while (container.children.length > 100) {
        container.removeChild(container.firstChild);
    }
}

// Make functions available globally for onclick handlers
window.selectProject = selectProject;
window.forkTemplate = forkTemplate;
window.viewFile = viewFile;
window.hideRollbackModal = hideRollbackModal;
window.hideDeleteModal = hideDeleteModal;
window.restoreSnapshot = restoreSnapshot;

// === Rollback Functions ===

async function showRollbackModal() {
    if (!currentProjectId) return;
    
    document.getElementById('rollback-modal').style.display = 'block';
    const list = document.getElementById('snapshot-list');
    list.innerHTML = '<div class="loading">Loading snapshots...</div>';
    
    try {
        const snapshots = await apiRequest(`/api/v2/projects/${currentProjectId}/snapshots`);
        
        if (snapshots.length === 0) {
            list.innerHTML = '<div class="empty-snapshots">No snapshots available yet.<br>Snapshots are created automatically before each change.</div>';
            return;
        }
        
        // Sort by ID descending (newest first)
        snapshots.sort((a, b) => b.id - a.id);
        
        list.innerHTML = snapshots.map(s => `
            <div class="snapshot-item" onclick="restoreSnapshot(${s.id})">
                <div class="snapshot-info">
                    <div class="snapshot-id">Snapshot #${s.id}</div>
                    <div class="snapshot-desc">${s.description || 'No description'}</div>
                    <div class="snapshot-time">${formatTime(s.timestamp)} • ${s.file_count} files</div>
                </div>
                <button class="btn btn-secondary snapshot-restore">Restore</button>
            </div>
        `).join('');
        
    } catch (error) {
        list.innerHTML = `<div class="empty-snapshots">Error loading snapshots: ${error.message}</div>`;
    }
}

function hideRollbackModal() {
    document.getElementById('rollback-modal').style.display = 'none';
}

async function restoreSnapshot(snapshotId) {
    if (!currentProjectId || !confirm(`Restore to snapshot #${snapshotId}? Current state will be backed up first.`)) {
        return;
    }
    
    hideRollbackModal();
    addLogEntry('info', `Restoring to snapshot #${snapshotId}...`);
    
    try {
        const result = await apiRequest(`/api/v2/projects/${currentProjectId}/rollback`, {
            method: 'POST',
            body: JSON.stringify({ snapshot_id: snapshotId })
        });
        
        addLogEntry('success', result.message);
        addChatMessage('assistant', `🔄 Rolled back to snapshot #${snapshotId}. Your previous state was backed up.`);
        
        // Update status immediately (WebSocket will also send this)
        updateProjectStatus('scaffolded');
        
        // Refresh project files
        await refreshProjectState();
        
    } catch (error) {
        addLogEntry('error', `Rollback failed: ${error.message}`);
    }
}

// === Delete Functions ===

function showDeleteModal() {
    if (!currentProjectId || !currentProject) return;
    
    document.getElementById('delete-project-name').textContent = currentProject.name;
    document.getElementById('delete-modal').style.display = 'block';
}

function hideDeleteModal() {
    document.getElementById('delete-modal').style.display = 'none';
}

async function handleDeleteProject() {
    if (!currentProjectId) return;
    
    hideDeleteModal();
    addLogEntry('info', 'Deleting project...');
    
    try {
        await apiRequest(`/api/v2/projects/${currentProjectId}`, {
            method: 'DELETE'
        });
        
        addLogEntry('success', 'Project deleted');
        
        // Clear current project
        currentProjectId = null;
        currentProject = null;
        
        // Update URL
        window.history.pushState({}, '', '/workspace');
        
        // Show empty state
        document.getElementById('project-view').style.display = 'none';
        document.getElementById('empty-state').style.display = 'flex';
        
        // Reload projects list
        await loadProjects();
        
    } catch (error) {
        addLogEntry('error', `Delete failed: ${error.message}`);
    }
}

// === Resizable Panels ===

function initResizers() {
    // Sidebar resizer
    initResizer('sidebar-resizer', 'sidebar', 'width', 180, 400);
    
    // Split view resizer (between code and chat)
    initResizer('split-resizer', 'chat-panel', 'width', 280, 600, true);
    
    // Log resizer
    initResizer('log-resizer', 'agent-log', 'height', 36, 400, false, true);
}

function initResizer(resizerId, targetId, dimension, min, max, reverse = false, isHorizontal = false) {
    const resizer = document.getElementById(resizerId);
    const target = document.getElementById(targetId);
    
    if (!resizer || !target) return;
    
    let startPos = 0;
    let startSize = 0;
    
    function onMouseDown(e) {
        e.preventDefault();
        startPos = isHorizontal ? e.clientY : e.clientX;
        startSize = isHorizontal ? target.offsetHeight : target.offsetWidth;
        
        resizer.classList.add('dragging');
        document.body.classList.add(isHorizontal ? 'resizing-h' : 'resizing');
        
        document.addEventListener('mousemove', onMouseMove);
        document.addEventListener('mouseup', onMouseUp);
    }
    
    function onMouseMove(e) {
        const currentPos = isHorizontal ? e.clientY : e.clientX;
        let delta = currentPos - startPos;
        
        // Reverse direction for right-side or bottom panels
        if (reverse || isHorizontal) {
            delta = -delta;
        }
        
        let newSize = startSize + delta;
        newSize = Math.max(min, Math.min(max, newSize));
        
        target.style[dimension] = `${newSize}px`;
    }
    
    function onMouseUp() {
        resizer.classList.remove('dragging');
        document.body.classList.remove('resizing', 'resizing-h');
        
        document.removeEventListener('mousemove', onMouseMove);
        document.removeEventListener('mouseup', onMouseUp);
        
        // Save to localStorage
        localStorage.setItem(`resizer-${targetId}`, target.style[dimension]);
    }
    
    resizer.addEventListener('mousedown', onMouseDown);
    
    // Restore saved size
    const savedSize = localStorage.getItem(`resizer-${targetId}`);
    if (savedSize) {
        target.style[dimension] = savedSize;
    }
}

// Initialize resizers on load
document.addEventListener('DOMContentLoaded', initResizers);
