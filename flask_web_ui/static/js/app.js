/**
 * Code Evolver Web UI - Main JavaScript
 * Handles WebSocket communication, UI updates, and animations
 */

// Initialize Socket.IO connection
const socket = io();

// DOM Elements
const chatMessages = document.getElementById('chatMessages');
const chatForm = document.getElementById('chatForm');
const messageInput = document.getElementById('messageInput');
const sendButton = document.getElementById('sendButton');
const connectionStatus = document.getElementById('connectionStatus');
const workflowProgress = document.getElementById('workflowProgress');
const progressFill = document.getElementById('progressFill');
const progressStatus = document.getElementById('progressStatus');
const toolsGrid = document.getElementById('toolsGrid');
const stepsContainer = document.getElementById('stepsContainer');
const resetVizBtn = document.getElementById('resetVizBtn');

// State
let isConnected = false;
let isProcessing = false;
let currentWorkflow = null;

// ===== Connection Handlers =====

socket.on('connect', () => {
    console.log('Connected to server');
    isConnected = true;
    updateConnectionStatus('connected');
});

socket.on('disconnect', () => {
    console.log('Disconnected from server');
    isConnected = false;
    updateConnectionStatus('disconnected');
});

socket.on('connected', (data) => {
    console.log('Server acknowledged connection:', data);
    addSystemMessage('Connected to Code Evolver!');
});

// ===== Message Handlers =====

socket.on('user_message', (data) => {
    // Message already added when sent, could update if needed
    console.log('User message acknowledged:', data);
});

socket.on('assistant_message', (data) => {
    addAssistantMessage(data.message);
    isProcessing = false;
    updateSendButton();
});

socket.on('error', (data) => {
    console.error('Error:', data);
    addSystemMessage(data.message, 'error');
    isProcessing = false;
    updateSendButton();
});

// ===== Workflow Visualization Handlers =====

socket.on('status', (data) => {
    console.log('Status update:', data);
    updateProgressStatus(data.message);
});

socket.on('workflow_step', (data) => {
    console.log('Workflow step:', data);
    updateProgress(data.progress, data.message);

    // Show progress bar if hidden
    if (workflowProgress.style.display === 'none') {
        workflowProgress.style.display = 'block';
        fadeIn(workflowProgress);
    }
});

socket.on('tool_discovered', (data) => {
    console.log('Tool discovered:', data);
    addDiscoveredTool(data);
});

socket.on('workflow_step_added', (data) => {
    console.log('Workflow step added:', data);
    addWorkflowStep(data.step, data.index);
});

socket.on('workflow_step_executing', (data) => {
    console.log('Workflow step executing:', data);
    updateStepStatus(data.index, 'executing');
});

socket.on('workflow_step_completed', (data) => {
    console.log('Workflow step completed:', data);
    updateStepStatus(data.index, 'completed');
});

// ===== UI Functions =====

function updateConnectionStatus(status) {
    connectionStatus.className = `status-indicator ${status}`;

    const statusText = connectionStatus.querySelector('.status-text');
    if (status === 'connected') {
        statusText.textContent = 'Connected';
    } else {
        statusText.textContent = 'Disconnected';
    }
}

function updateSendButton() {
    sendButton.disabled = !isConnected || isProcessing;
}

function updateProgress(percentage, message) {
    progressFill.style.width = `${percentage}%`;

    const progressPercentage = document.querySelector('.progress-percentage');
    if (progressPercentage) {
        progressPercentage.textContent = `${percentage}%`;
    }

    if (message) {
        updateProgressStatus(message);
    }
}

function updateProgressStatus(message) {
    if (progressStatus) {
        progressStatus.textContent = message;
    }
}

function addSystemMessage(message, type = 'info') {
    const messageDiv = document.createElement('div');
    messageDiv.className = 'message system-message';
    messageDiv.innerHTML = `
        <div class="message-content system-${type}">
            <div class="system-icon">${type === 'error' ? '⚠️' : 'ℹ️'}</div>
            <div>${message}</div>
        </div>
    `;

    chatMessages.appendChild(messageDiv);
    scrollToBottom();
}

function addUserMessage(message) {
    const messageDiv = document.createElement('div');
    messageDiv.className = 'message message-user';
    messageDiv.innerHTML = `
        <div class="message-content">
            <div>${escapeHtml(message)}</div>
            <div class="message-time">${formatTime(new Date())}</div>
        </div>
    `;

    chatMessages.appendChild(messageDiv);
    scrollToBottom();
}

function addAssistantMessage(message) {
    // Remove typing indicator if present
    removeTypingIndicator();

    const messageDiv = document.createElement('div');
    messageDiv.className = 'message message-assistant';

    // Parse markdown-like formatting
    const formattedMessage = formatMessage(message);

    messageDiv.innerHTML = `
        <div class="message-content">
            <div>${formattedMessage}</div>
            <div class="message-time">${formatTime(new Date())}</div>
        </div>
    `;

    chatMessages.appendChild(messageDiv);
    scrollToBottom();
}

function addTypingIndicator() {
    // Remove existing indicator
    removeTypingIndicator();

    const indicatorDiv = document.createElement('div');
    indicatorDiv.className = 'message message-assistant typing-indicator-wrapper';
    indicatorDiv.id = 'typingIndicator';
    indicatorDiv.innerHTML = `
        <div class="message-content">
            <div class="typing-indicator">
                <div class="typing-dot"></div>
                <div class="typing-dot"></div>
                <div class="typing-dot"></div>
            </div>
        </div>
    `;

    chatMessages.appendChild(indicatorDiv);
    scrollToBottom();
}

function removeTypingIndicator() {
    const indicator = document.getElementById('typingIndicator');
    if (indicator) {
        indicator.remove();
    }
}

function addDiscoveredTool(tool) {
    // Clear empty state on first tool
    if (toolsGrid.querySelector('.empty-state')) {
        toolsGrid.innerHTML = '';
    }

    const toolCard = document.createElement('div');
    toolCard.className = 'tool-card';
    toolCard.style.animationDelay = `${tool.index * 0.1}s`;

    const toolIcon = getToolIcon(tool.type);

    toolCard.innerHTML = `
        <div class="tool-icon">${toolIcon}</div>
        <div class="tool-name">${escapeHtml(tool.name)}</div>
        <div class="tool-type">${escapeHtml(tool.type)}</div>
        <div class="tool-description">${escapeHtml(truncate(tool.description, 80))}</div>
    `;

    toolsGrid.appendChild(toolCard);
}

function addWorkflowStep(step, index) {
    // Clear empty state on first step
    if (stepsContainer.querySelector('.empty-state')) {
        stepsContainer.innerHTML = '';
    }

    const stepDiv = document.createElement('div');
    stepDiv.className = 'workflow-step';
    stepDiv.id = `step-${index}`;
    stepDiv.style.animationDelay = `${index * 0.1}s`;

    stepDiv.innerHTML = `
        <div class="step-number">${index + 1}</div>
        <div class="step-content">
            <div class="step-name">${escapeHtml(step.name)}</div>
            <div class="step-tool">Tool: ${escapeHtml(step.tool)}</div>
            <span class="step-status ${step.status}">${step.status}</span>
        </div>
    `;

    stepsContainer.appendChild(stepDiv);
}

function updateStepStatus(index, status) {
    const stepDiv = document.getElementById(`step-${index}`);
    if (!stepDiv) return;

    // Update step div class
    stepDiv.className = `workflow-step ${status}`;

    // Update status badge
    const statusBadge = stepDiv.querySelector('.step-status');
    if (statusBadge) {
        statusBadge.className = `step-status ${status}`;
        statusBadge.textContent = status;
    }
}

function resetVisualization() {
    // Hide progress
    workflowProgress.style.display = 'none';
    updateProgress(0, '');

    // Clear tools
    toolsGrid.innerHTML = `
        <div class="empty-state">
            <div class="empty-icon">🔧</div>
            <p>Waiting for request...</p>
        </div>
    `;

    // Clear steps
    stepsContainer.innerHTML = `
        <div class="empty-state">
            <div class="empty-icon">⚙️</div>
            <p>No workflow steps yet</p>
        </div>
    `;

    currentWorkflow = null;
}

// ===== Event Handlers =====

chatForm.addEventListener('submit', (e) => {
    e.preventDefault();

    const message = messageInput.value.trim();
    if (!message || !isConnected || isProcessing) {
        return;
    }

    // Clear input
    messageInput.value = '';
    messageInput.style.height = 'auto';

    // Add user message to chat
    addUserMessage(message);

    // Show typing indicator
    addTypingIndicator();

    // Reset visualization
    resetVisualization();

    // Send message to server
    socket.emit('chat_message', { message });

    // Update state
    isProcessing = true;
    updateSendButton();
});

// Auto-resize textarea
messageInput.addEventListener('input', () => {
    messageInput.style.height = 'auto';
    messageInput.style.height = messageInput.scrollHeight + 'px';
});

// Reset visualization button
if (resetVizBtn) {
    resetVizBtn.addEventListener('click', resetVisualization);
}

// ===== Utility Functions =====

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function formatTime(date) {
    return date.toLocaleTimeString('en-US', {
        hour: '2-digit',
        minute: '2-digit'
    });
}

function formatMessage(message) {
    // Simple markdown-like formatting
    let formatted = escapeHtml(message);

    // Bold (**text**)
    formatted = formatted.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');

    // Italic (*text*)
    formatted = formatted.replace(/\*(.+?)\*/g, '<em>$1</em>');

    // Code (`code`)
    formatted = formatted.replace(/`(.+?)`/g, '<code>$1</code>');

    // Line breaks
    formatted = formatted.replace(/\n/g, '<br>');

    return formatted;
}

function truncate(text, length) {
    if (text.length <= length) return text;
    return text.substring(0, length) + '...';
}

function scrollToBottom() {
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

function fadeIn(element) {
    element.classList.add('fade-in');
    setTimeout(() => {
        element.classList.remove('fade-in');
    }, 300);
}

function getToolIcon(type) {
    const icons = {
        'executable': '⚙️',
        'llm': '🤖',
        'workflow': '🔄',
        'function': '📦',
        'validator': '✅',
        'custom': '🔧',
        'openapi': '🌐'
    };
    return icons[type] || '🔨';
}

// ===== Example Prompts =====

window.sendExample = function(text) {
    if (!isConnected || isProcessing) {
        return;
    }

    messageInput.value = text;
    chatForm.dispatchEvent(new Event('submit'));
};

// ===== Initialize =====

console.log('Code Evolver Web UI initialized');
updateSendButton();

// Request chat history on load
socket.emit('get_history');
