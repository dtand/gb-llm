/**
 * GB Game Studio - Modals Module
 * 
 * Modal dialogs for new project, rollback, delete, etc.
 */

// === New Project Modal ===

async function showNewProjectModal() {
    const modal = document.getElementById('new-project-modal');
    const nameInput = document.getElementById('project-name-input');
    const descInput = document.getElementById('project-description');
    const templateSelect = document.getElementById('template-select');
    
    if (modal) modal.style.display = 'block';
    if (nameInput) {
        nameInput.value = '';
        nameInput.focus();
    }
    if (descInput) descInput.value = '';
    if (templateSelect) templateSelect.selectedIndex = 0;
}

function hideNewProjectModal() {
    const modal = document.getElementById('new-project-modal');
    if (modal) modal.style.display = 'none';
}

async function handleCreateProject(e) {
    if (e) e.preventDefault();
    
    const name = document.getElementById('project-name-input')?.value.trim();
    const description = document.getElementById('project-description')?.value.trim();
    const templateId = document.getElementById('template-select')?.value;
    
    if (!name) {
        alert('Please enter a project name');
        return;
    }
    
    hideNewProjectModal();
    addLogEntry('info', `Creating project "${name}"...`);
    
    try {
        // API expects: prompt (required), template_id (optional), name (optional)
        const body = { 
            prompt: description || name,  // Use description as prompt, fallback to name
            name: name
        };
        if (templateId) body.template_id = templateId;
        
        const response = await apiRequest('/api/v2/projects', {
            method: 'POST',
            body: JSON.stringify(body)
        });
        
        addLogEntry('success', `Project "${name}" created`);
        
        // Update URL and select project
        window.history.pushState({}, '', `/?project=${response.project_id}`);
        window.gbStudio.currentProjectId = response.project_id;
        
        await loadProjects();
        await selectProject(response.project_id);
        
    } catch (error) {
        addLogEntry('error', `Failed to create project: ${error.message}`);
    }
}

// Alias for backwards compatibility
const createProject = handleCreateProject;

// === Rollback Modal ===

async function showRollbackModal() {
    const { currentProjectId } = window.gbStudio;
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
    const { currentProjectId } = window.gbStudio;
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

// === Delete Modal ===

function showDeleteModal() {
    const { currentProjectId, currentProject } = window.gbStudio;
    if (!currentProjectId || !currentProject) return;
    
    document.getElementById('delete-project-name').textContent = currentProject.name;
    document.getElementById('delete-modal').style.display = 'block';
}

function hideDeleteModal() {
    document.getElementById('delete-modal').style.display = 'none';
}

async function handleDeleteProject() {
    const { currentProjectId } = window.gbStudio;
    if (!currentProjectId) return;
    
    hideDeleteModal();
    addLogEntry('info', 'Deleting project...');
    
    try {
        await apiRequest(`/api/v2/projects/${currentProjectId}`, {
            method: 'DELETE'
        });
        
        addLogEntry('success', 'Project deleted');
        
        // Clear current project
        window.gbStudio.currentProjectId = null;
        window.gbStudio.currentProject = null;
        
        // Update URL
        window.history.pushState({}, '', '/');
        
        // Show empty state
        document.getElementById('project-view').style.display = 'none';
        document.getElementById('empty-state').style.display = 'flex';
        
        // Reload projects list
        await loadProjects();
        
    } catch (error) {
        addLogEntry('error', `Delete failed: ${error.message}`);
    }
}

// Close modals when clicking on modal backdrop
document.addEventListener('click', (e) => {
    if (e.target.classList.contains('modal-backdrop')) {
        e.target.closest('.modal').style.display = 'none';
    }
});

// Close modals on Escape
document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
        document.querySelectorAll('.modal').forEach(modal => {
            modal.style.display = 'none';
        });
    }
});

// Export functions
window.showNewProjectModal = showNewProjectModal;
window.hideNewProjectModal = hideNewProjectModal;
window.createProject = createProject;
window.handleCreateProject = handleCreateProject;
window.showRollbackModal = showRollbackModal;
window.hideRollbackModal = hideRollbackModal;
window.restoreSnapshot = restoreSnapshot;
window.showDeleteModal = showDeleteModal;
window.hideDeleteModal = hideDeleteModal;
window.handleDeleteProject = handleDeleteProject;
