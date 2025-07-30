// Chat functionality
let chatHistory = [];
let savedChats = [];
let currentChatId = null;
let isDarkMode = false;

// DOM elements
const chatMessages = document.getElementById('chat-messages');
const chatInput = document.getElementById('chat-input');
const sendButton = document.getElementById('send-button');
const newChatBtn = document.getElementById('new-chat-btn');
const clearHistoryBtn = document.getElementById('clear-history-btn');
const exportChatBtn = document.getElementById('export-chat-btn');
const darkModeToggle = document.getElementById('dark-mode-toggle');
const chatList = document.getElementById('chat-list');
const welcomeContainer = document.getElementById('welcome-container');
const ratingPanel = document.getElementById('rating-panel');
const sidebarToggle = document.getElementById('sidebar-toggle');
const sidebar = document.querySelector('.sidebar');

// Modal elements
const renameModal = document.getElementById('rename-modal');
const renameInput = document.getElementById('rename-input');
const cancelRename = document.getElementById('cancel-rename');
const saveRename = document.getElementById('save-rename');

// Initialize
document.addEventListener('DOMContentLoaded', function() {
    loadSavedChats();
    loadDarkModePreference();
    setupEventListeners();
    createWelcomeContainer();
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
    darkModeToggle.addEventListener('click', toggleDarkMode);

    // Sidebar toggle
    sidebarToggle.addEventListener('click', toggleSidebar);

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

    // Add user message
    addMessage('user', message);
    chatInput.value = '';
    handleInputChange();

    // Hide welcome container
    welcomeContainer.style.display = 'none';

    // Show typing indicator
    addTypingIndicator();

    // Send to backend
    fetch('/chat', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            question: message,
            chat_history: chatHistory
        })
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
                        aiMessageElement.textContent = aiMessage;
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
                    aiMessageElement.textContent = aiMessage;
                }
                
                // Update chat history with the complete AI response
                if (chatHistory.length > 0) {
                    chatHistory[chatHistory.length - 1][1] = aiMessage;
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
            <div class="message-text">${text}</div>
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
    
    return messageDiv.querySelector('.message-text');
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
    ratingPanel.style.display = 'none';
    
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

function loadSavedChats() {
    const saved = localStorage.getItem('savedChats');
    if (saved) {
        savedChats = JSON.parse(saved);
        updateChatList();
    }
}

function loadDarkModePreference() {
    const saved = localStorage.getItem('darkMode');
    if (saved !== null) {
        isDarkMode = saved === 'true';
        document.body.setAttribute('data-theme', isDarkMode ? 'dark' : 'light');
        
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
        }
    }
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
    ratingPanel.style.display = 'none';
    
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
                <div class="welcome-icon">⚖️</div>
                <h1>Legal AI Assistant</h1>
                <p>Trợ lý pháp lý thông minh của bạn. Hỏi tôi bất cứ điều gì về luật pháp và quy định.</p>
                
                <div class="suggestions-grid">
                    <button class="suggestion-card" data-suggestion="Quyền lợi cơ bản của người lao động tại Việt Nam là gì?">
                        <div class="suggestion-icon">👥</div>
                        <div class="suggestion-content">
                            <h3>Quyền Lao Động</h3>
                            <p>Tìm hiểu về quyền lợi cơ bản của người lao động</p>
                        </div>
                    </button>
                    
                    <button class="suggestion-card" data-suggestion="Thủ tục đăng ký kinh doanh tại Việt Nam như thế nào?">
                        <div class="suggestion-icon">🏢</div>
                        <div class="suggestion-content">
                            <h3>Đăng Ký Kinh Doanh</h3>
                            <p>Các bước đăng ký doanh nghiệp hợp pháp</p>
                        </div>
                    </button>
                    
                    <button class="suggestion-card" data-suggestion="Những yêu cầu để có một hợp đồng hợp lệ là gì?">
                        <div class="suggestion-icon">📄</div>
                        <div class="suggestion-content">
                            <h3>Yêu Cầu Hợp Đồng</h3>
                            <p>Các yếu tố cần thiết của hợp đồng hợp lệ</p>
                        </div>
                    </button>
                    
                    <button class="suggestion-card" data-suggestion="Làm thế nào để bảo vệ quyền sở hữu trí tuệ?">
                        <div class="suggestion-icon">🔒</div>
                        <div class="suggestion-content">
                            <h3>Bảo Vệ Sở Hữu Trí Tuệ</h3>
                            <p>Bảo vệ tài sản trí tuệ của bạn</p>
                        </div>
                    </button>
                    
                    <button class="suggestion-card" data-suggestion="Nghĩa vụ thuế đối với doanh nghiệp nhỏ là gì?">
                        <div class="suggestion-icon">💰</div>
                        <div class="suggestion-content">
                            <h3>Nghĩa Vụ Thuế</h3>
                            <p>Hiểu về yêu cầu thuế</p>
                        </div>
                    </button>
                    
                    <button class="suggestion-card" data-suggestion="Cách xử lý tranh chấp lao động như thế nào?">
                        <div class="suggestion-icon">⚖️</div>
                        <div class="suggestion-content">
                            <h3>Tranh Chấp Lao Động</h3>
                            <p>Giải quyết xung đột tại nơi làm việc</p>
                        </div>
                    </button>
                    
                    <button class="suggestion-card" data-suggestion="Luật bảo vệ người tiêu dùng quy định như thế nào?">
                        <div class="suggestion-icon">🛡️</div>
                        <div class="suggestion-content">
                            <h3>Quyền Người Tiêu Dùng</h3>
                            <p>Quyền lợi của bạn với tư cách người tiêu dùng</p>
                        </div>
                    </button>
                    
                    <button class="suggestion-card" data-suggestion="Cách nộp đơn khiếu nại pháp lý như thế nào?">
                        <div class="suggestion-icon">📋</div>
                        <div class="suggestion-content">
                            <h3>Khiếu Nại Pháp Lý</h3>
                            <p>Nộp đơn khiếu nại chính thức</p>
                        </div>
                    </button>
                </div>
            </div>
        `;
    }
}

function showRatingPanel() {
    ratingPanel.style.display = 'block';
    
    // Reset stars
    document.querySelectorAll('.star').forEach(star => {
        star.classList.remove('active');
    });
}

function rateResponse(rating) {
    // Highlight stars up to the selected rating
    document.querySelectorAll('.star').forEach((star, index) => {
        if (index < rating) {
            star.classList.add('active');
        } else {
            star.classList.remove('active');
        }
    });
    
    // Hide rating panel after 2 seconds
    setTimeout(() => {
        ratingPanel.style.display = 'none';
    }, 2000);
} 