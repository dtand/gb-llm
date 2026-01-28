/**
 * GB Game Studio - Chat Module
 * 
 * Chat messaging, typing indicators, and conversation rendering.
 * Supports Designer mode (dialogue + build) and Dev mode (direct implementation).
 */

// Chat mode state
let chatMode = 'designer';  // 'designer' or 'dev'
let attachedFiles = [];     // Files attached in dev mode

// === Mode Toggle ===

function handleModeChange() {
    chatMode = document.getElementById('chat-mode').value;
    const attachedFilesEl = document.getElementById('attached-files');
    const sendBtn = document.getElementById('send-btn');
    const buildBtn = document.getElementById('build-feature-btn');
    const input = document.getElementById('chat-input');
    
    if (chatMode === 'dev') {
        // Dev mode: show attached files, change buttons
        if (attachedFilesEl) attachedFilesEl.style.display = 'flex';
        sendBtn.textContent = '🔧 Implement';
        sendBtn.title = 'Implement directly (bypasses Designer)';
        if (buildBtn) buildBtn.style.display = 'none';
        input.placeholder = 'Describe what you want to change... (direct to Coder)';
    } else {
        // Designer mode: hide attached files, restore buttons
        if (attachedFilesEl) attachedFilesEl.style.display = 'none';
        sendBtn.textContent = '💬 Send';
        sendBtn.title = 'Continue the conversation';
        if (buildBtn) buildBtn.style.display = 'inline-flex';
        input.placeholder = 'Discuss your game ideas... When ready, click Build Feature';
    }
    
    addLogEntry('info', `Switched to ${chatMode === 'dev' ? 'Dev' : 'Designer'} mode`);
}

// === Attached Files (Dev mode) ===

function showAttachFileModal() {
    const { currentProject } = window.gbStudio;
    // Get available files from current project
    const files = currentProject?.summary?.files || [];
    const cFiles = files.filter(f => f.path.endsWith('.c'));
    
    if (cFiles.length === 0) {
        addLogEntry('warning', 'No .c files available to attach');
        return;
    }
    
    // Simple prompt-based selection for now
    const fileList = cFiles.map(f => f.path).join('\n');
    const selected = prompt(`Select a file to attach:\n\n${fileList}\n\nEnter the file path:`);
    
    if (selected && cFiles.some(f => f.path === selected)) {
        if (!attachedFiles.includes(selected)) {
            attachedFiles.push(selected);
            renderAttachedFiles();
        }
    }
}

function renderAttachedFiles() {
    const container = document.getElementById('attached-list');
    if (!container) return;
    
    container.innerHTML = attachedFiles.map(f => `
        <span class="attached-chip">
            ${f.split('/').pop()}
            <span class="remove-chip" onclick="removeAttachedFile('${f}')">×</span>
        </span>
    `).join('');
}

function removeAttachedFile(filepath) {
    attachedFiles = attachedFiles.filter(f => f !== filepath);
    renderAttachedFiles();
}

// === Chat Functions ===

async function handleNewChat() {
    const { currentProjectId } = window.gbStudio;
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
    const { currentProjectId } = window.gbStudio;
    
    if (!message || !currentProjectId) return;
    
    // Route to appropriate handler based on mode
    if (chatMode === 'dev') {
        await handleDevModeImplement(message);
    } else {
        await handleDesignerChat(message);
    }
}

// Designer mode: chat with Designer (no implementation)
async function handleDesignerChat(message) {
    const input = document.getElementById('chat-input');
    const { currentProjectId } = window.gbStudio;
    
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

// Dev mode: implement directly without Designer
async function handleDevModeImplement(message) {
    const input = document.getElementById('chat-input');
    const sendBtn = document.getElementById('send-btn');
    const { currentProjectId } = window.gbStudio;
    
    // Clear input and set loading state
    input.value = '';
    setLoadingState(true);
    sendBtn.disabled = true;
    sendBtn.textContent = '⏳ Implementing...';
    
    // Add user message to UI
    addChatMessage('user', message);
    if (attachedFiles.length > 0) {
        addChatMessage('system', `📎 Attached files: ${attachedFiles.join(', ')}`);
    }
    
    setChatStatus('Implementing...');
    addLogEntry('agent', '🔧 Dev mode: implementing directly...');
    
    try {
        const response = await apiRequest(`/api/v2/projects/${currentProjectId}/dev`, {
            method: 'POST',
            body: JSON.stringify({ 
                message,
                attached_files: attachedFiles.length > 0 ? attachedFiles : null
            })
        });
        
        // Add response to chat
        addChatMessage('assistant', response.response);
        
        if (response.success && response.files_changed?.length > 0) {
            addLogEntry('success', `Changed: ${response.files_changed.join(', ')}`);
            // Refresh project state if function exists
            if (typeof refreshProjectState === 'function') {
                await refreshProjectState();
            }
        } else if (!response.success) {
            addLogEntry('error', response.error || 'Implementation failed');
        }
        
    } catch (error) {
        const errorMsg = error?.message || error?.toString() || 'Unknown error occurred';
        addChatMessage('assistant', `❌ Error: ${errorMsg}`);
        addLogEntry('error', errorMsg);
    }
    
    setLoadingState(false);
    sendBtn.disabled = false;
    sendBtn.textContent = '🔧 Implement';
    setChatStatus('Ready');
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

function setChatStatus(status) {
    document.getElementById('chat-status').textContent = status;
}

// Export functions
window.handleNewChat = handleNewChat;
window.handleSendMessage = handleSendMessage;
window.handleModeChange = handleModeChange;
window.showAttachFileModal = showAttachFileModal;
window.renderAttachedFiles = renderAttachedFiles;
window.removeAttachedFile = removeAttachedFile;
window.handleDesignerChat = handleDesignerChat;
window.handleDevModeImplement = handleDevModeImplement;
window.renderConversation = renderConversation;
window.formatMessage = formatMessage;
window.addChatMessage = addChatMessage;
window.setLoadingState = setLoadingState;
window.showTypingIndicator = showTypingIndicator;
window.updateTypingStatus = updateTypingStatus;
window.setChatStatus = setChatStatus;
