/**
 * GB Game Studio - Files Module
 * 
 * File browser and code viewer with syntax highlighting.
 */

// === Panel Tab Switching ===

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
    if (tabName === 'emulator' && window.gbStudio.currentProject) {
        updateEmulatorState();
    }
    
    // If switching to agents, load agent config
    if (tabName === 'agents' && window.gbStudio.currentProjectId) {
        loadAgentConfig();
    }
    
    // If switching to sprites, load sprites
    if (tabName === 'sprites' && window.gbStudio.currentProjectId) {
        loadSprites();
    }
    
    // If switching to tuning, load tunables
    if (tabName === 'tuning' && window.gbStudio.currentProjectId) {
        loadTunables();
    }
    
    // If switching to data, load data schema
    if (tabName === 'data' && window.gbStudio.currentProjectId) {
        loadDataSchema();
    }
}

// === File Browser ===

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

// === File Viewer ===

async function viewFile(filePath) {
    const { currentProjectId } = window.gbStudio;
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

// === Syntax Highlighting ===

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

// Export functions
window.switchPanelTab = switchPanelTab;
window.renderFileBrowser = renderFileBrowser;
window.viewFile = viewFile;
window.highlightC = highlightC;
