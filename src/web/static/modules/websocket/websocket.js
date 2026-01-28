/**
 * GB Game Studio - WebSocket Module
 * 
 * WebSocket connection and message handling.
 */

function connectWebSocket(projectId) {
    if (window.gbStudio.websocket) {
        window.gbStudio.websocket.close();
    }
    
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/ws/projects/${projectId}`;
    
    window.gbStudio.websocket = new WebSocket(wsUrl);
    
    window.gbStudio.websocket.onopen = () => {
        addLogEntry('info', 'Connected to project');
    };
    
    window.gbStudio.websocket.onmessage = (event) => {
        const data = JSON.parse(event.data);
        handleWebSocketMessage(data);
    };
    
    window.gbStudio.websocket.onerror = (error) => {
        console.error('WebSocket error:', error);
        addLogEntry('error', 'Connection error');
    };
    
    window.gbStudio.websocket.onclose = () => {
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
        // Dev mode messages
        case 'dev_mode_start':
            addLogEntry('agent', '🔧 ' + data.message);
            setChatStatus('Implementing...');
            break;
        case 'dev_mode_complete':
            setChatStatus('Ready');
            if (data.success && data.files && data.files.length > 0) {
                refreshProjectState();
            }
            break;
        case 'dev_mode_error':
            addLogEntry('error', `Dev mode error: ${data.error}`);
            setChatStatus('Ready');
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

// Export functions
window.connectWebSocket = connectWebSocket;
