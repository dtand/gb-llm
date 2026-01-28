/**
 * GB Game Studio - Projects Module
 * 
 * Project loading, selection, and rendering functions.
 */

// === Template Functions ===

async function loadTemplates() {
    try {
        window.gbStudio.templates = await apiRequest('/api/v2/templates');
        renderTemplates();
        populateTemplateSelect();
    } catch (error) {
        console.error('Failed to load templates:', error);
    }
}

function renderTemplates() {
    const container = document.getElementById('templates-list');
    container.innerHTML = window.gbStudio.templates.map(t => `
        <div class="project-item template-item" data-id="${t.id}" onclick="forkTemplate('${t.id}')">
            <span class="project-icon">📦</span>
            <span class="project-name">${t.name}</span>
        </div>
    `).join('');
}

function populateTemplateSelect() {
    const select = document.getElementById('template-select');
    if (!select) return; // Guard against missing element
    
    // Clear existing options except the first "Blank Project" option
    while (select.options.length > 1) {
        select.remove(1);
    }
    
    window.gbStudio.templates.forEach(t => {
        const option = document.createElement('option');
        option.value = t.id;
        option.textContent = t.name;
        select.appendChild(option);
    });
}

// === Project Functions ===

async function loadProjects() {
    try {
        window.gbStudio.projects = await apiRequest('/api/v2/projects');
        renderProjects();
    } catch (error) {
        console.error('Failed to load projects:', error);
    }
}

function renderProjects() {
    const container = document.getElementById('projects-list');
    const { projects, currentProjectId } = window.gbStudio;
    
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

async function selectProject(projectId) {
    try {
        const project = await apiRequest(`/api/v2/projects/${projectId}`);
        window.gbStudio.currentProjectId = projectId;
        window.gbStudio.currentProject = project;
        
        // Update URL
        window.history.pushState({}, '', `/?project=${projectId}`);
        
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
            window.emulatorLoaded = false;
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

// Light refresh - updates project data without reconnecting WebSocket
async function refreshProjectState() {
    const { currentProjectId } = window.gbStudio;
    if (!currentProjectId) return;
    
    try {
        const project = await apiRequest(`/api/v2/projects/${currentProjectId}`);
        window.gbStudio.currentProject = project;
        
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

async function forkTemplate(templateId) {
    const select = document.getElementById('template-select');
    if (select) {
        select.value = templateId;
    }
    showNewProjectModal();
}

// Export functions
window.loadTemplates = loadTemplates;
window.loadProjects = loadProjects;
window.selectProject = selectProject;
window.refreshProjectState = refreshProjectState;
window.forkTemplate = forkTemplate;
window.renderProjects = renderProjects;
window.getStatusIcon = getStatusIcon;
