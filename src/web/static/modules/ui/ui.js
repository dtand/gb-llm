/**
 * GB Game Studio - UI Module
 * 
 * UI helpers, resizers, log functions, and status updates.
 */

// === Status Functions ===

function setChatStatus(status) {
    const statusEl = document.getElementById('chat-status');
    if (statusEl) {
        statusEl.textContent = status;
    }
}

function updateProjectStatus(status) {
    const badge = document.getElementById('project-status');
    if (badge) {
        badge.textContent = status;
        badge.className = `status-badge ${status}`;
    }
    
    if (window.gbStudio.currentProject) {
        window.gbStudio.currentProject.status = status;
    }
}

// === Log Panel ===

function toggleLog() {
    const log = document.getElementById('agent-log');
    const toggleBtn = document.getElementById('toggle-log');
    
    if (log) {
        log.classList.toggle('collapsed');
        if (toggleBtn) {
            toggleBtn.textContent = log.classList.contains('collapsed') ? '▲' : '▼';
        }
    }
}

function addLogEntry(type, message) {
    const container = document.getElementById('log-content');
    if (!container) return;
    
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

// === Loading States ===

function showLoading(elementId, message = 'Loading...') {
    const el = document.getElementById(elementId);
    if (el) {
        el.innerHTML = `<div class="loading">${message}</div>`;
    }
}

function hideLoading(elementId) {
    const el = document.getElementById(elementId);
    if (el) {
        el.innerHTML = '';
    }
}

// === Tab Switching ===

function initPanelTabs() {
    document.querySelectorAll('.panel-tabs .tab').forEach(tab => {
        tab.addEventListener('click', () => {
            const panelId = tab.dataset.panel;
            const tabContainer = tab.closest('.panel-tabs');
            const panelContainer = tab.closest('[data-panel-container]') || 
                                   document.querySelector(`[data-panels="${tabContainer.dataset.for}"]`);
            
            // Update tab states
            tabContainer.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
            tab.classList.add('active');
            
            // Show corresponding panel
            if (panelContainer) {
                panelContainer.querySelectorAll('.panel-content').forEach(p => p.classList.remove('active'));
                const targetPanel = panelContainer.querySelector(`[data-panel="${panelId}"]`);
                if (targetPanel) {
                    targetPanel.classList.add('active');
                }
            }
        });
    });
}

// === Keyboard Shortcuts ===

function initKeyboardShortcuts() {
    document.addEventListener('keydown', (e) => {
        // Cmd/Ctrl + Enter to send message
        if ((e.metaKey || e.ctrlKey) && e.key === 'Enter') {
            const chatInput = document.getElementById('chat-input');
            if (document.activeElement === chatInput) {
                handleSendMessage();
                e.preventDefault();
            }
        }
        
        // Cmd/Ctrl + B to build
        if ((e.metaKey || e.ctrlKey) && e.key === 'b') {
            if (window.gbStudio.currentProjectId) {
                handleBuild();
                e.preventDefault();
            }
        }
    });
}

// === Tooltip Helpers ===

function showTooltip(element, message) {
    const tooltip = document.createElement('div');
    tooltip.className = 'tooltip';
    tooltip.textContent = message;
    
    const rect = element.getBoundingClientRect();
    tooltip.style.top = `${rect.bottom + 8}px`;
    tooltip.style.left = `${rect.left + rect.width / 2}px`;
    
    document.body.appendChild(tooltip);
    
    // Auto-remove
    setTimeout(() => tooltip.remove(), 2000);
    
    return tooltip;
}

// === Initialize ===

document.addEventListener('DOMContentLoaded', () => {
    initResizers();
    initPanelTabs();
    initKeyboardShortcuts();
    
    // Toggle log button
    const toggleLogBtn = document.getElementById('toggle-log');
    if (toggleLogBtn) {
        toggleLogBtn.addEventListener('click', toggleLog);
    }
});

// Export functions
window.setChatStatus = setChatStatus;
window.updateProjectStatus = updateProjectStatus;
window.toggleLog = toggleLog;
window.addLogEntry = addLogEntry;
window.showLoading = showLoading;
window.hideLoading = hideLoading;
window.showTooltip = showTooltip;
