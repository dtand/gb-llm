/**
 * GB Game Studio - Frontend Application
 */

const API_BASE = '';  // Same origin

// State
let currentProjectId = null;
let websocket = null;
let emulatorInstance = null;

// DOM Elements
const generateForm = document.getElementById('generate-form');
const generateBtn = document.getElementById('generate-btn');
const progressSection = document.getElementById('progress-section');
const progressPhase = document.getElementById('progress-phase');
const progressStep = document.getElementById('progress-step');
const progressFill = document.getElementById('progress-fill');
const progressLog = document.getElementById('progress-log');
const projectsGrid = document.getElementById('projects-grid');
const refreshBtn = document.getElementById('refresh-btn');
const projectModal = document.getElementById('project-modal');
const modalBody = document.getElementById('modal-body');
const modalClose = document.getElementById('modal-close');
const emulatorModal = document.getElementById('emulator-modal');

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    loadProjects();
    setupEventListeners();
});

function setupEventListeners() {
    // Generate form submission
    generateForm.addEventListener('submit', handleGenerate);
    
    // Refresh button
    refreshBtn.addEventListener('click', loadProjects);
    
    // Modal close
    modalClose.addEventListener('click', closeModal);
    document.querySelector('.modal-backdrop')?.addEventListener('click', closeModal);
    
    // Escape key to close modal
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') closeModal();
    });
}

// API Functions

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

async function loadProjects() {
    projectsGrid.innerHTML = '<div class="loading">Loading projects...</div>';
    
    try {
        const projects = await apiRequest('/api/v2/projects');
        renderProjects(projects);
    } catch (error) {
        projectsGrid.innerHTML = `<div class="loading">Error loading projects: ${error.message}</div>`;
    }
}

async function handleGenerate(e) {
    e.preventDefault();
    
    const description = document.getElementById('description').value.trim();
    
    if (!description) return;
    
    // Update UI
    setGenerateLoading(true);
    showProgress();
    clearProgressLog();
    addProgressLog('Starting generation...', 'info');
    
    try {
        // Start generation via new pipeline endpoint
        const response = await apiRequest('/api/v2/generate', {
            method: 'POST',
            body: JSON.stringify({
                prompt: description,
            }),
        });
        
        currentProjectId = response.project_id;
        addProgressLog(`Project ID: ${currentProjectId}`, 'info');
        
        // Connect to WebSocket for progress updates
        connectWebSocket(currentProjectId);
        
    } catch (error) {
        addProgressLog(`Error: ${error.message}`, 'error');
        setGenerateLoading(false);
    }
}

// WebSocket

function connectWebSocket(projectId) {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/ws/projects/${projectId}`;
    
    websocket = new WebSocket(wsUrl);
    
    websocket.onopen = () => {
        addProgressLog('Connected to progress stream', 'info');
    };
    
    websocket.onmessage = (event) => {
        const data = JSON.parse(event.data);
        handleProgressUpdate(data);
    };
    
    websocket.onerror = (error) => {
        console.error('WebSocket error:', error);
        addProgressLog('Connection error', 'error');
    };
    
    websocket.onclose = () => {
        console.log('WebSocket closed');
    };
    
    // Keep alive
    const pingInterval = setInterval(() => {
        if (websocket && websocket.readyState === WebSocket.OPEN) {
            websocket.send('ping');
        } else {
            clearInterval(pingInterval);
        }
    }, 25000);
}

function handleProgressUpdate(data) {
    switch (data.type) {
        case 'status':
            progressPhase.textContent = `Status: ${data.status}`;
            if (data.total_steps > 0) {
                const percent = (data.current_step / data.total_steps) * 100;
                progressFill.style.width = `${percent}%`;
                progressStep.textContent = `Step ${data.current_step}/${data.total_steps}`;
            }
            break;
            
        case 'phase':
            progressPhase.textContent = data.phase.charAt(0).toUpperCase() + data.phase.slice(1);
            addProgressLog(`📋 ${data.message}`, 'info');
            break;
            
        case 'step':
            progressStep.textContent = `Step ${data.step}/${data.total}`;
            const percent = ((data.step - 1) / data.total) * 100;
            progressFill.style.width = `${percent}%`;
            addProgressLog(`🔨 Step ${data.step}/${data.total}: ${data.title}`, 'info');
            break;
            
        case 'attempt':
            addProgressLog(`  ↻ Attempt ${data.attempt}/${data.max_attempts}`, 'warning');
            break;
            
        case 'log':
            // Regular log messages from orchestrator/coder
            const msg = data.message || '';
            // Color-code based on content
            if (msg.includes('FAILED') || msg.includes('Error')) {
                addProgressLog(`  ${msg}`, 'error');
            } else if (msg.includes('passed') || msg.includes('successful') || msg.includes('SUCCESS')) {
                addProgressLog(`  ✓ ${msg}`, 'success');
            } else {
                addProgressLog(`  ${msg}`);
            }
            break;
        
        case 'error':
            addProgressLog(`❌ ${data.message}`, 'error');
            break;
            
        case 'complete':
            progressFill.style.width = '100%';
            if (data.success) {
                progressPhase.textContent = '✅ Complete!';
                addProgressLog(data.message || 'Generation complete!', 'success');
                if (data.rom_path) {
                    addProgressLog('🎮 ROM generated successfully!', 'success');
                }
            } else {
                progressPhase.textContent = '❌ Failed';
                addProgressLog(data.message || 'Generation failed', 'error');
            }
            setGenerateLoading(false);
            loadProjects();
            
            // Close WebSocket
            if (websocket) {
                websocket.close();
                websocket = null;
            }
            break;
    }
}

// Progress UI

function showProgress() {
    progressSection.style.display = 'block';
    progressPhase.textContent = 'Initializing...';
    progressStep.textContent = '';
    progressFill.style.width = '0%';
}

function clearProgressLog() {
    progressLog.innerHTML = '';
}

function addProgressLog(message, type = '') {
    const entry = document.createElement('div');
    entry.className = `log-entry ${type ? `log-${type}` : ''}`;
    
    const timestamp = new Date().toLocaleTimeString();
    entry.innerHTML = `<span style="opacity: 0.5">[${timestamp}]</span> ${escapeHtml(message)}`;
    
    progressLog.appendChild(entry);
    progressLog.scrollTop = progressLog.scrollHeight;
}

function setGenerateLoading(loading) {
    generateBtn.disabled = loading;
    document.querySelector('.btn-text').style.display = loading ? 'none' : 'inline';
    document.querySelector('.btn-loading').style.display = loading ? 'inline-flex' : 'none';
}

// Projects Grid

function renderProjects(projects) {
    if (!projects || projects.length === 0) {
        projectsGrid.innerHTML = `
            <div class="empty-state">
                <div class="empty-state-icon">🎮</div>
                <p>No games yet. Create your first one above!</p>
            </div>
        `;
        return;
    }
    
    // Sort by created_at descending
    projects.sort((a, b) => new Date(b.created_at) - new Date(a.created_at));
    
    projectsGrid.innerHTML = projects.map(project => `
        <div class="project-card" data-id="${project.id}">
            <div class="project-card-header">
                <span class="project-name">${escapeHtml(project.name)}</span>
                <span class="project-status status-${project.status}">${project.status}</span>
            </div>
            <p class="project-description">${escapeHtml(project.description)}</p>
            <div class="project-footer">
                <div class="project-meta">
                    Created: ${formatDate(project.created_at)}
                </div>
                ${project.rom_path ? `
                    <button class="btn btn-play" onclick="event.stopPropagation(); playGame('${project.id}', '${escapeHtml(project.name).replace(/'/g, "\\'")}')">
                        🎮 Play
                    </button>
                ` : ''}
            </div>
        </div>
    `).join('');
    
    // Add click handlers
    projectsGrid.querySelectorAll('.project-card').forEach(card => {
        card.addEventListener('click', () => {
            openProjectModal(card.dataset.id);
        });
    });
}

// Modal

async function openProjectModal(projectId) {
    try {
        const project = await apiRequest(`/api/v2/projects/${projectId}`);
        renderProjectModal(project);
        projectModal.style.display = 'flex';
    } catch (error) {
        alert(`Error loading project: ${error.message}`);
    }
}

function renderProjectModal(project) {
    const statusClass = `status-${project.status}`;
    
    let errorHtml = '';
    if (project.error) {
        errorHtml = `
            <div class="modal-section">
                <h4>Error</h4>
                <p style="color: var(--error)">${escapeHtml(project.error)}</p>
            </div>
        `;
    }
    
    // Show summary if available
    let summaryHtml = '';
    if (project.summary && project.summary.current_state) {
        summaryHtml = `
            <div class="modal-section">
                <h4>Current State</h4>
                <p>${escapeHtml(project.summary.current_state)}</p>
            </div>
        `;
    }
    
    modalBody.innerHTML = `
        <div class="modal-header">
            <h3>${escapeHtml(project.name)}</h3>
            <span class="project-status ${statusClass}">${project.status}</span>
        </div>
        
        <div class="modal-section">
            <h4>Description</h4>
            <p>${escapeHtml(project.description)}</p>
        </div>
        
        ${summaryHtml}
        ${errorHtml}
        
        <div class="modal-section">
            <h4>Details</h4>
            <p><strong>ID:</strong> ${project.id}</p>
            <p><strong>Created:</strong> ${formatDate(project.created_at)}</p>
            <p><strong>Updated:</strong> ${formatDate(project.updated_at)}</p>
            ${project.template_source ? `<p><strong>Template:</strong> ${escapeHtml(project.template_source)}</p>` : ''}
        </div>
        
        <div class="modal-actions">
            ${project.rom_path ? `
                <button class="btn btn-play" onclick="playGame('${project.id}', '${escapeHtml(project.name)}')">
                    🎮 Play in Browser
                </button>
                <a href="/api/v2/projects/${project.id}/files/rom" class="btn btn-success" download>
                    ⬇️ Download ROM
                </a>
            ` : ''}
            <a href="/workspace.html?project=${project.id}" class="btn btn-secondary">
                📝 Open Workspace
            </a>
            <button class="btn btn-secondary" style="background: rgba(248, 113, 113, 0.2); color: var(--error);" onclick="deleteProject('${project.id}')">
                🗑️ Delete
            </button>
        </div>
    `;
}

function closeModal() {
    projectModal.style.display = 'none';
}

async function deleteProject(projectId) {
    if (!confirm('Are you sure you want to delete this project?')) return;
    
    try {
        await apiRequest(`/api/v2/projects/${projectId}`, { method: 'DELETE' });
        closeModal();
        loadProjects();
    } catch (error) {
        alert(`Error deleting project: ${error.message}`);
    }
}

// Utilities

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function formatDate(isoString) {
    if (!isoString) return 'Unknown';
    const date = new Date(isoString);
    return date.toLocaleDateString() + ' ' + date.toLocaleTimeString();
}

// Emulator Functions

async function playGame(projectId, gameName) {
    closeModal();
    
    document.getElementById('emulator-title').textContent = gameName;
    emulatorModal.style.display = 'flex';
    
    const gameContainer = document.getElementById('emulator-game');
    gameContainer.innerHTML = '<div style="display: flex; align-items: center; justify-content: center; height: 100%; color: #0f380f; font-family: \'Press Start 2P\', cursive; font-size: 10px;">Clearing cache...</div>';
    
    // Clean up any previous EmulatorJS instance AND WAIT for IndexedDB cleanup
    await cleanupEmulatorAsync();
    
    gameContainer.innerHTML = '<div style="display: flex; align-items: center; justify-content: center; height: 100%; color: #0f380f; font-family: \'Press Start 2P\', cursive; font-size: 10px;">Loading...</div>';
    
    // Use EmulatorJS via CDN - add cache-busting timestamp
    const romUrl = `/api/v2/projects/${projectId}/files/rom?t=${Date.now()}`;
    
    // Create container for EmulatorJS
    gameContainer.innerHTML = `
        <div id="ejs-container" style="width: 100%; height: 100%;"></div>
    `;
    
    // Set up EmulatorJS configuration - must be set BEFORE loading script
    window.EJS_player = '#ejs-container';
    window.EJS_gameUrl = romUrl;
    window.EJS_core = 'gambatte';  // GameBoy core
    window.EJS_pathtodata = 'https://cdn.emulatorjs.org/stable/data/';
    window.EJS_startOnLoaded = true;  // Auto-start when loaded
    window.EJS_color = '#9bbc0f';  // GameBoy green
    window.EJS_backgroundColor = '#0f380f';
    window.EJS_fullscreenOnLoaded = false;
    window.EJS_VirtualGamepadSettings = false; // Disable virtual gamepad
    
    // Callback when emulator is ready
    window.EJS_onGameStart = function() {
        console.log('Game started!');
    };
    
    // Load the emulator script
    const script = document.createElement('script');
    script.id = 'ejs-loader-script';
    script.src = 'https://cdn.emulatorjs.org/stable/data/loader.js';
    script.onload = () => {
        console.log('EmulatorJS script loaded');
    };
    script.onerror = () => {
        gameContainer.innerHTML = `
            <div style="display: flex; flex-direction: column; align-items: center; justify-content: center; height: 100%; color: #0f380f; padding: 1rem; text-align: center;">
                <p style="font-family: 'Press Start 2P', cursive; font-size: 8px; margin-bottom: 10px;">LOAD ERROR</p>
                <a href="${romUrl}" download style="color: #306230; font-size: 10px;">Download ROM</a>
            </div>
        `;
    };
    document.body.appendChild(script);
}

function cleanupEmulator() {
    // Remove EmulatorJS globals
    const ejsGlobals = [
        'EJS_player', 'EJS_gameUrl', 'EJS_core', 'EJS_pathtodata',
        'EJS_startOnLoaded', 'EJS_color', 'EJS_backgroundColor',
        'EJS_defaultControls', 'EJS_Buttons', 'EJS_ready',
        'EJS_onGameStart', 'EJS_fullscreenOnLoaded', 'EJS_VirtualGamepadSettings',
        'EJS_emulator', 'EJS_biosUrl', 'EJS_DEBUG_XX'
    ];
    ejsGlobals.forEach(g => delete window[g]);
    
    // Remove the loader script
    const oldScript = document.getElementById('ejs-loader-script');
    if (oldScript) {
        oldScript.remove();
    }
    
    // Remove any EmulatorJS created elements
    document.querySelectorAll('[id^="ejs-"], [id^="EJS_"], [class^="ejs_"], [class*=" ejs_"]').forEach(el => {
        if (el.id !== 'ejs-container') {
            el.remove();
        }
    });
    document.querySelectorAll('link[href*="emulatorjs"], style[data-ejs]').forEach(el => el.remove());
}

// Async version that waits for IndexedDB cleanup to complete
async function cleanupEmulatorAsync() {
    // First do sync cleanup
    cleanupEmulator();
    
    // ONLY delete ROM cache - NOT the core (emulator engine) or saves
    const ejsDatabases = [
        'EmulatorJS-roms'  // This is where cached ROMs live
    ];
    
    // Helper to delete a database with timeout
    const deleteDb = (name) => new Promise((resolve) => {
        const timeout = setTimeout(() => {
            console.log(`Timeout deleting: ${name}`);
            resolve();
        }, 500); // 500ms timeout per database
        
        try {
            const req = indexedDB.deleteDatabase(name);
            req.onsuccess = () => { clearTimeout(timeout); console.log(`Cleared: ${name}`); resolve(); };
            req.onerror = () => { clearTimeout(timeout); resolve(); };
            req.onblocked = () => { clearTimeout(timeout); console.log(`Blocked: ${name}`); resolve(); };
        } catch (e) {
            clearTimeout(timeout);
            resolve();
        }
    });
    
    // Delete ROM cache with overall timeout
    try {
        await Promise.race([
            Promise.all(ejsDatabases.map(deleteDb)),
            new Promise(r => setTimeout(r, 1000)) // 1 second max
        ]);
    } catch (e) {
        console.log('Cache cleanup error:', e);
    }
    
    console.log('EmulatorJS ROM cache cleanup complete');
}

function closeEmulator() {
    emulatorModal.style.display = 'none';
    
    // Clean up EmulatorJS
    const container = document.getElementById('emulator-game');
    if (container) {
        container.innerHTML = '';
    }
    
    cleanupEmulatorAsync(); // Fire and forget on close
}
