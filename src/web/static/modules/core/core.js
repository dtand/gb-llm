/**
 * GB Game Studio - Core Module
 * 
 * Application state, initialization, and API functions.
 */

const API_BASE = '';

// Global State
window.gbStudio = {
    currentProjectId: null,
    currentProject: null,
    websocket: null,
    templates: [],
    projects: []
};

// Initialize Application
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

// === Event Listeners Setup ===

function setupEventListeners() {
    // New project buttons
    const newProjectBtn = document.getElementById('new-project-btn');
    const createFirstBtn = document.getElementById('create-first-project');
    if (newProjectBtn) newProjectBtn.addEventListener('click', showNewProjectModal);
    if (createFirstBtn) createFirstBtn.addEventListener('click', showNewProjectModal);
    
    // Modal - use querySelectorAll for multiple close buttons
    document.querySelectorAll('.modal-close').forEach(btn => {
        btn.addEventListener('click', hideNewProjectModal);
    });
    document.querySelectorAll('.modal-backdrop').forEach(backdrop => {
        backdrop.addEventListener('click', hideNewProjectModal);
    });
    const cancelCreate = document.getElementById('cancel-create');
    if (cancelCreate) cancelCreate.addEventListener('click', hideNewProjectModal);
    const newProjectForm = document.getElementById('new-project-form');
    if (newProjectForm) newProjectForm.addEventListener('submit', handleCreateProject);
    
    // Project actions
    const refreshBtn = document.getElementById('refresh-projects');
    const buildBtn = document.getElementById('build-btn');
    const playBtn = document.getElementById('play-btn');
    const downloadBtn = document.getElementById('download-btn');
    const rollbackBtn = document.getElementById('rollback-btn');
    const deleteBtn = document.getElementById('delete-btn');
    const confirmDeleteBtn = document.getElementById('confirm-delete-btn');
    
    if (refreshBtn) refreshBtn.addEventListener('click', loadProjects);
    if (buildBtn) buildBtn.addEventListener('click', handleBuild);
    if (playBtn) playBtn.addEventListener('click', handlePlay);
    if (downloadBtn) downloadBtn.addEventListener('click', handleDownload);
    if (rollbackBtn) rollbackBtn.addEventListener('click', showRollbackModal);
    if (deleteBtn) deleteBtn.addEventListener('click', showDeleteModal);
    if (confirmDeleteBtn) confirmDeleteBtn.addEventListener('click', handleDeleteProject);
    
    // Chat
    const sendBtn = document.getElementById('send-btn');
    const buildFeatureBtn = document.getElementById('build-feature-btn');
    const retryBtn = document.getElementById('retry-btn');
    const newChatBtn = document.getElementById('new-chat-btn');
    const chatInput = document.getElementById('chat-input');
    const chatModeSelect = document.getElementById('chat-mode');
    const attachFileBtn = document.getElementById('attach-file-btn');
    
    if (sendBtn) sendBtn.addEventListener('click', handleSendMessage);
    if (buildFeatureBtn) buildFeatureBtn.addEventListener('click', handleBuildFeature);
    if (retryBtn) retryBtn.addEventListener('click', handleRetry);
    if (newChatBtn) newChatBtn.addEventListener('click', handleNewChat);
    if (chatModeSelect) chatModeSelect.addEventListener('change', handleModeChange);
    if (attachFileBtn) attachFileBtn.addEventListener('click', showAttachFileModal);
    if (chatInput) chatInput.addEventListener('keydown', (e) => {
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
    const toggleLogBtn = document.getElementById('toggle-log');
    if (toggleLogBtn) toggleLogBtn.addEventListener('click', toggleLog);
    
    // Panel tabs (Files / Emulator)
    document.querySelectorAll('.panel-tab').forEach(tab => {
        tab.addEventListener('click', () => switchPanelTab(tab.dataset.tab));
    });
    
    // Emulator controls
    const emuPlayBtn = document.getElementById('emu-play-btn');
    const emuPauseBtn = document.getElementById('emu-pause-btn');
    const emuReloadBtn = document.getElementById('emu-reload-btn');
    const emuVolume = document.getElementById('emu-volume');
    
    if (emuPlayBtn) emuPlayBtn.addEventListener('click', handleEmulatorPlay);
    if (emuPauseBtn) emuPauseBtn.addEventListener('click', handleEmulatorPause);
    if (emuReloadBtn) emuReloadBtn.addEventListener('click', handleEmulatorReload);
    if (emuVolume) emuVolume.addEventListener('input', handleEmulatorVolume);
    
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

// === Utility Functions ===

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

function formatTime(timestamp) {
    if (!timestamp) return '';
    const date = new Date(timestamp);
    return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}

// Export for module usage
window.apiRequest = apiRequest;
window.capitalize = capitalize;
window.escapeHtml = escapeHtml;
window.debounce = debounce;
window.formatTime = formatTime;
