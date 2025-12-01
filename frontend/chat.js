// Chat functionality
let chatHistory = [];
let savedChats = [];
let currentChatId = null;
let isDarkMode = false;
let lastQuestion = '';
let lastAnswer = '';

function escapeHTML(text) {
    return text
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;');
}

function formatAIMessageHTML(text) {
    const escaped = escapeHTML(text);
    const lines = escaped.split(/\n/);
    return lines.map(line => {
        const trimmed = line.trim().toLowerCase();
        if (trimmed.startsWith('tổng thời gian')) {
            return `<span class="stats-line">${line}</span>`;
        }
        return line;
    }).join('<br>');
}

function renderMessageText(element, sender, text) {
    if (sender === 'ai') {
        element.innerHTML = formatAIMessageHTML(text);
    } else {
        element.textContent = text;
    }
}

// DOM elements
const chatMessages = document.getElementById('chat-messages');
const chatInput = document.getElementById('chat-input');
const sendButton = document.getElementById('send-button');
const maxTokensInput = document.getElementById('max-tokens');
const newChatBtn = document.getElementById('new-chat-btn');
const clearHistoryBtn = document.getElementById('clear-history-btn');
const exportChatBtn = document.getElementById('export-chat-btn');
const chatList = document.getElementById('chat-list');
const welcomeContainer = document.getElementById('welcome-container');
const sidebarToggle = document.getElementById('sidebar-toggle');
const sidebar = document.querySelector('.sidebar');

// Modal elements
const renameModal = document.getElementById('rename-modal');
const renameInput = document.getElementById('rename-input');
const cancelRename = document.getElementById('cancel-rename');
const saveRename = document.getElementById('save-rename');

// Feedback elements

// Initialize
const MAX_TOKENS_STORAGE_KEY = 'legal-ai-max-tokens';
const MAX_TOKEN_OPTIONS = [64, 128, 256, 512, 1024, 2048];
const DEFAULT_MAX_TOKENS = 256;

document.addEventListener('DOMContentLoaded', function() {
    loadSavedChats();
    loadMaxTokensPreference();
    handleResponsiveSidebar();
    setupEventListeners();
    createWelcomeContainer();
    window.addEventListener('resize', handleResponsiveSidebar);
});

function setupEventListeners() {
    // Send message
    sendButton.addEventListener('click', sendMessage);
    chatInput.addEventListener('keydown', handleKeyDown);
    chatInput.addEventListener('input', handleInputChange);

    // Chat management
    newChatBtn.addEventListener('click', startNewChat);
    clearHistoryBtn.addEventListener('click', clearChatHistory);
    exportChatBtn.addEventListener('click', exportChat);

    // Sidebar toggle
    sidebarToggle.addEventListener('click', toggleSidebar);

    if (maxTokensInput) {
        maxTokensInput.addEventListener('change', handleMaxTokensChange);
    }

    // Suggestion buttons
    document.addEventListener('click', function(e) {
        if (e.target.closest('.suggestion-card')) {
            const suggestion = e.target.closest('.suggestion-card').getAttribute('data-suggestion');
            chatInput.value = suggestion;
            sendMessage();
        }
    });

    // Modal events
    cancelRename.addEventListener('click', closeRenameModal);
    saveRename.addEventListener('click', saveRenameChat);
    renameInput.addEventListener('keydown', function(e) {
        if (e.key === 'Enter') {
            saveRenameChat();
        } else if (e.key === 'Escape') {
            closeRenameModal();
        }
    });

    // Rating stars
    document.addEventListener('click', function(e) {
        if (e.target.classList.contains('star')) {
            const rating = e.target.getAttribute('data-rating');
            rateResponse(rating);
        }
    });

    // Feedback button

}

function handleKeyDown(e) {
    if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        sendMessage();
    }
}

function handleInputChange() {
    const hasText = chatInput.value.trim().length > 0;
    sendButton.disabled = !hasText;
    
    // Auto-resize textarea
    chatInput.style.height = 'auto';
    chatInput.style.height = Math.min(chatInput.scrollHeight, 200) + 'px';
}

function sendMessage() {
    const message = chatInput.value.trim();
    if (!message) return;

    // Lưu câu hỏi để có thể gửi feedback
    lastQuestion = message;

    // Add user message
    addMessage('user', message);
    chatInput.value = '';
    handleInputChange();

    // Hide welcome container
    welcomeContainer.style.display = 'none';

    // Show typing indicator
    addTypingIndicator();

    // Send to backend - use API URL from config
    const apiUrl = typeof getAPIUrl !== 'undefined' ? getAPIUrl('/chat') : '/chat';
    const payload = {
        question: message,
        chat_history: chatHistory
    };
    const maxTokens = getMaxTokens();
    if (maxTokens !== null) {
        payload.max_tokens = maxTokens;
    }
    fetch(apiUrl, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'ngrok-skip-browser-warning': '1',
        },
        body: JSON.stringify(payload)
    })
    .then(response => {
        if (!response.ok) {
            throw new Error('Network response was not ok');
        }
        return response.body.getReader();
    })
    .then(reader => {
        const decoder = new TextDecoder();
        let aiMessage = '';
        let aiMessageElement = null;

        function readStream() {
            return reader.read().then(({ done, value }) => {
                if (done) {
                    removeTypingIndicator();
                    if (aiMessageElement) {
                        renderMessageText(aiMessageElement, 'ai', aiMessage);
                    }
                    saveCurrentChat();
                    showRatingPanel();
                    return;
                }

                const chunk = decoder.decode(value, { stream: true });
                aiMessage += chunk;

                if (!aiMessageElement) {
                    removeTypingIndicator();
                    aiMessageElement = addMessage('ai', aiMessage);
                } else {
                    renderMessageText(aiMessageElement, 'ai', aiMessage);
                }
                
                // Update chat history with the complete AI response
                if (chatHistory.length > 0) {
                    chatHistory[chatHistory.length - 1][1] = aiMessage;
                    // Lưu để có thể gửi feedback
                    lastAnswer = aiMessage;
                }

                // Scroll to bottom
                chatMessages.scrollTop = chatMessages.scrollHeight;

                return readStream();
            });
        }

        return readStream();
    })
    .catch(error => {
        console.error('Error:', error);
        removeTypingIndicator();
        addMessage('ai', 'Lỗi khi nhận phản hồi từ máy chủ.');
    });
}

function addMessage(sender, text) {
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${sender}`;
    
    const avatar = sender === 'user' ? 'U' : 'AI';
    const avatarBg = sender === 'user' ? 'linear-gradient(135deg, var(--primary-color), var(--secondary-color))' : 'linear-gradient(135deg, var(--success-color), #30D158)';
    
    messageDiv.innerHTML = `
        <div class="message-content">
            <div class="message-avatar" style="background: ${avatarBg}">${avatar}</div>
            <div class="message-text"></div>
        </div>
    `;
    
    chatMessages.appendChild(messageDiv);
    chatMessages.scrollTop = chatMessages.scrollHeight;
    
    // Add to chat history
    if (sender === 'user') {
        chatHistory.push([text, '']);
    } else {
        if (chatHistory.length > 0) {
            chatHistory[chatHistory.length - 1][1] = text;
        }
    }
    
    const messageTextElement = messageDiv.querySelector('.message-text');
    renderMessageText(messageTextElement, sender, text);
    
    return messageTextElement;
}

function addTypingIndicator() {
    const typingDiv = document.createElement('div');
    typingDiv.className = 'message ai';
    typingDiv.id = 'typing-indicator';
    
    typingDiv.innerHTML = `
        <div class="message-content">
            <div class="message-avatar" style="background: linear-gradient(135deg, var(--success-color), #30D158)">AI</div>
            <div class="message-text">
                <div class="typing-dots">
                    <span></span>
                    <span></span>
                    <span></span>
                </div>
            </div>
        </div>
    `;
    
    chatMessages.appendChild(typingDiv);
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

function removeTypingIndicator() {
    const typingIndicator = document.getElementById('typing-indicator');
    if (typingIndicator) {
        typingIndicator.remove();
    }
}

function startNewChat() {
    if (chatHistory.length > 0) {
        saveCurrentChat();
    }
    
    chatHistory = [];
    currentChatId = null;
    chatMessages.innerHTML = '';
    welcomeContainer.style.display = 'block';
    const ratingPanel = document.getElementById('rating-panel');
    if (ratingPanel) {
        ratingPanel.style.display = 'none';
    }
    
    // Update active state
    document.querySelectorAll('.chat-item').forEach(item => {
        item.classList.remove('active');
    });
}

function clearChatHistory() {
    if (confirm('Bạn có chắc chắn muốn xóa tất cả cuộc trò chuyện?')) {
        savedChats = [];
        localStorage.setItem('savedChats', JSON.stringify(savedChats));
        updateChatList();
        startNewChat();
    }
}

function exportChat() {
    if (chatHistory.length === 0) {
        alert('Không có cuộc trò chuyện nào để xuất.');
        return;
    }
    
    let exportText = 'AI Legal Assistant - Chat Export\n';
    exportText += '='.repeat(50) + '\n\n';
    
    chatHistory.forEach(([userMsg, aiMsg]) => {
        exportText += `User: ${userMsg}\n`;
        exportText += `AI: ${aiMsg}\n\n`;
    });
    
    const blob = new Blob([exportText], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `chat-export-${new Date().toISOString().split('T')[0]}.txt`;
    a.click();
    URL.revokeObjectURL(url);
}

function toggleDarkMode() {
    isDarkMode = !isDarkMode;
    document.body.setAttribute('data-theme', isDarkMode ? 'dark' : 'light');
    localStorage.setItem('darkMode', isDarkMode);
    
    // Update button text
    const buttonText = darkModeToggle.querySelector('span') || document.createElement('span');
    buttonText.textContent = isDarkMode ? 'Light Mode' : 'Dark Mode';
    if (!darkModeToggle.querySelector('span')) {
        darkModeToggle.appendChild(buttonText);
    }
    
    // Update icon
    const icon = darkModeToggle.querySelector('svg');
    if (isDarkMode) {
        icon.innerHTML = '<path d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364 6.364l-.707-.707M6.343 6.343l-.707-.707m12.728 0l-.707.707M6.343 17.657l-.707.707M16 12a4 4 0 11-8 0 4 4 0 018 0z" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>';
    } else {
        icon.innerHTML = '<path d="M12 3a6 6 0 0 0 9 9 9 9 0 1 1-9-9Z" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>';
    }
}

function toggleSidebar() {
    sidebar.classList.toggle('closed');
}

function handleResponsiveSidebar() {
    if (!sidebar) return;
    if (window.innerWidth <= 768) {
        sidebar.classList.add('closed');
    } else {
        sidebar.classList.remove('closed');
    }
}

function loadSavedChats() {
    const saved = localStorage.getItem('savedChats');
    if (saved) {
        savedChats = JSON.parse(saved);
        updateChatList();
    }
}

function loadMaxTokensPreference() {
    if (!maxTokensInput) return;
    const saved = localStorage.getItem(MAX_TOKENS_STORAGE_KEY);
    let value = DEFAULT_MAX_TOKENS;
    if (saved) {
        const numeric = parseInt(saved, 10);
        if (!Number.isNaN(numeric) && MAX_TOKEN_OPTIONS.includes(numeric)) {
            value = numeric;
        }
    }
    maxTokensInput.value = value;
    localStorage.setItem(MAX_TOKENS_STORAGE_KEY, value);
}

function handleMaxTokensChange() {
    if (!maxTokensInput) return;
    const value = parseInt(maxTokensInput.value, 10);
    if (Number.isNaN(value) || !MAX_TOKEN_OPTIONS.includes(value)) {
        maxTokensInput.value = DEFAULT_MAX_TOKENS;
        localStorage.setItem(MAX_TOKENS_STORAGE_KEY, DEFAULT_MAX_TOKENS);
        return;
    }
    localStorage.setItem(MAX_TOKENS_STORAGE_KEY, value);
}

function getMaxTokens() {
    if (!maxTokensInput) return null;
    const value = parseInt(maxTokensInput.value, 10);
    if (Number.isNaN(value) || !MAX_TOKEN_OPTIONS.includes(value)) {
        return null;
    }
    return value;
}

function saveCurrentChat() {
    if (chatHistory.length === 0) return;
    
    const title = chatHistory[0][0].substring(0, 50) + (chatHistory[0][0].length > 50 ? '...' : '');
    const timestamp = new Date().toISOString();
    
    const chatData = {
        id: currentChatId || Date.now().toString(),
        title: title,
        timestamp: timestamp,
        history: [...chatHistory]
    };
    
    if (currentChatId) {
        // Update existing chat
        const index = savedChats.findIndex(chat => chat.id === currentChatId);
        if (index !== -1) {
            savedChats[index] = chatData;
        }
    } else {
        // Add new chat
        currentChatId = chatData.id;
        savedChats.unshift(chatData);
        
        // Keep only last 20 chats
        if (savedChats.length > 20) {
            savedChats = savedChats.slice(0, 20);
        }
    }
    
    localStorage.setItem('savedChats', JSON.stringify(savedChats));
    updateChatList();
}

function updateChatList() {
    chatList.innerHTML = '';
    
    savedChats.forEach(chat => {
        const chatItem = document.createElement('div');
        chatItem.className = 'chat-item';
        chatItem.setAttribute('data-chat-id', chat.id);
        
        const time = new Date(chat.timestamp).toLocaleString('vi-VN', {
            month: 'short',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
        });
        
        chatItem.innerHTML = `
            <div class="chat-item-content">
                <div class="chat-item-title">${chat.title}</div>
                <div class="chat-item-time">${time}</div>
            </div>
            <div class="chat-item-actions">
                <div class="chat-item-action" onclick="showRenameModal('${chat.id}')">
                    <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                        <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                        <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                    </svg>
                </div>
                <div class="chat-item-action" onclick="deleteChat('${chat.id}')">
                    <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                        <path d="M3 6h18M8 6V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2m3 0v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6h14Z" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                    </svg>
                </div>
            </div>
        `;
        
        chatItem.addEventListener('click', (e) => {
            if (!e.target.closest('.chat-item-action')) {
                loadChat(chat.id);
            }
        });
        
        chatList.appendChild(chatItem);
    });
}

function loadChat(chatId) {
    const chat = savedChats.find(c => c.id === chatId);
    if (!chat) return;
    
    currentChatId = chatId;
    chatHistory = [...chat.history];
    
    // Clear current display
    chatMessages.innerHTML = '';
    welcomeContainer.style.display = 'none';
    const ratingPanel = document.getElementById('rating-panel');
    if (ratingPanel) {
        ratingPanel.style.display = 'none';
    }
    
    // Display chat history
    chatHistory.forEach(([userMsg, aiMsg]) => {
        addMessage('user', userMsg);
        if (aiMsg) {
            addMessage('ai', aiMsg);
        }
    });
    
    // Update active state
    document.querySelectorAll('.chat-item').forEach(item => {
        item.classList.remove('active');
    });
    document.querySelector(`[data-chat-id="${chatId}"]`).classList.add('active');
}

function showRenameModal(chatId) {
    const chat = savedChats.find(c => c.id === chatId);
    if (!chat) return;
    
    renameInput.value = chat.title;
    renameInput.setAttribute('data-chat-id', chatId);
    renameModal.style.display = 'flex';
    renameInput.focus();
    renameInput.select();
}

function closeRenameModal() {
    renameModal.style.display = 'none';
    renameInput.value = '';
    renameInput.removeAttribute('data-chat-id');
}

function saveRenameChat() {
    const chatId = renameInput.getAttribute('data-chat-id');
    const newTitle = renameInput.value.trim();
    
    if (!chatId || !newTitle) {
        closeRenameModal();
        return;
    }
    
    const chat = savedChats.find(c => c.id === chatId);
    if (chat) {
        chat.title = newTitle;
        localStorage.setItem('savedChats', JSON.stringify(savedChats));
        updateChatList();
    }
    
    closeRenameModal();
}

function deleteChat(chatId) {
    if (!confirm('Bạn có chắc chắn muốn xóa cuộc trò chuyện này?')) return;
    
    savedChats = savedChats.filter(chat => chat.id !== chatId);
    localStorage.setItem('savedChats', JSON.stringify(savedChats));
    updateChatList();
    
    if (currentChatId === chatId) {
        startNewChat();
    }
}

function createWelcomeContainer() {
    if (!welcomeContainer.querySelector('.welcome-content')) {
        welcomeContainer.innerHTML = `
            <div class="welcome-content">
                <div class="welcome-hero">
                    <div class="welcome-pill">Trợ lý pháp luật giao thông</div>
                    <h1>Chào mừng bạn đến với Legal AI</h1>
                    <p class="welcome-subtitle">
                        Đặt câu hỏi về luật giao thông đường bộ – tôi sẽ tra cứu điều khoản, mức phạt, điểm trừ và đưa ra câu trả lời đầy đủ.
                        Chọn một tình huống phổ biến dưới đây hoặc nhập câu hỏi cụ thể của bạn.
                    </p>
                </div>

                <div class="suggestions-grid traffic">
                    <button class="suggestion-card" data-suggestion="An toàn giao thông được hiểu như thế nào theo Luật?">
                        <div class="suggestion-icon">🚦</div>
                        <div class="suggestion-content">
                            <h3>Khái niệm ATGT</h3>
                            <p>Hiểu an toàn giao thông theo luật hiện hành</p>
                        </div>
                    </button>

                    <button class="suggestion-card" data-suggestion="Không thắt dây an toàn khi ngồi ô tô bị phạt bao nhiêu?">
                        <div class="suggestion-icon">🪢</div>
                        <div class="suggestion-content">
                            <h3>Dây an toàn ô tô</h3>
                            <p>Mức phạt khi không cài dây đúng quy định</p>
                        </div>
                    </button>

                    <button class="suggestion-card" data-suggestion="Đi xe máy không đội mũ bảo hiểm thì bị xử phạt ra sao?">
                        <div class="suggestion-icon">🪖</div>
                        <div class="suggestion-content">
                            <h3>Mũ bảo hiểm</h3>
                            <p>Trách nhiệm của người điều khiển và người ngồi sau</p>
                        </div>
                    </button>

                    <button class="suggestion-card" data-suggestion="Vượt đèn đỏ bằng xe máy sẽ bị phạt thế nào?">
                        <div class="suggestion-icon">🚨</div>
                        <div class="suggestion-content">
                            <h3>Vượt đèn đỏ</h3>
                            <p>Mức phạt và tước GPLX khi vượt tín hiệu</p>
                        </div>
                    </button>

                    <button class="suggestion-card" data-suggestion="Xe ô tô chạy quá tốc độ 20km/h bị phạt bao nhiêu?">
                        <div class="suggestion-icon">⚡</div>
                        <div class="suggestion-content">
                            <h3>Quá tốc độ</h3>
                            <p>Khung xử phạt cho ô tô khi vượt tốc độ</p>
                        </div>
                    </button>

                    <button class="suggestion-card" data-suggestion="Xe máy chở ba người có bị xử phạt không?">
                        <div class="suggestion-icon">🛵</div>
                        <div class="suggestion-content">
                            <h3>Chở quá người</h3>
                            <p>Giới hạn số người và các trường hợp ngoại lệ</p>
                        </div>
                    </button>
                </div>
            </div>
        `;
    }
}

function showRatingPanel() {}