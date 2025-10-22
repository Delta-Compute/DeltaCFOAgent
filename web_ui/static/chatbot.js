/**
 * AI CFO Assistant Chatbot
 * Handles chat interface interactions and API communication
 */

class CFOChatbot {
    constructor() {
        this.isOpen = false;
        this.conversationHistory = [];
        this.isLoading = false;

        // DOM elements
        this.toggle = document.getElementById('chatbotToggle');
        this.window = document.getElementById('chatbotWindow');
        this.closeBtn = document.getElementById('chatbotClose');
        this.messagesContainer = document.getElementById('chatbotMessages');
        this.input = document.getElementById('chatbotInput');
        this.sendBtn = document.getElementById('chatbotSend');
        this.loadingIndicator = document.getElementById('chatbotLoading');
        this.suggestionsContainer = document.getElementById('chatbotSuggestions');

        this.init();
    }

    init() {
        // Event listeners
        this.toggle.addEventListener('click', () => this.open());
        this.closeBtn.addEventListener('click', () => this.close());
        this.sendBtn.addEventListener('click', () => this.sendMessage());
        this.input.addEventListener('keydown', (e) => this.handleKeydown(e));
        this.input.addEventListener('input', () => this.handleInputChange());

        // Suggestion chips
        const suggestionChips = this.suggestionsContainer.querySelectorAll('.suggestion-chip');
        suggestionChips.forEach(chip => {
            chip.addEventListener('click', () => {
                const message = chip.dataset.message;
                this.input.value = message;
                this.sendMessage();
            });
        });

        // Auto-resize textarea
        this.input.addEventListener('input', () => this.autoResizeTextarea());

        // Load conversation history from localStorage
        this.loadHistory();

        console.log('CFO Chatbot initialized');
    }

    open() {
        this.isOpen = true;
        this.toggle.style.display = 'none';
        this.window.style.display = 'flex';
        this.input.focus();

        // Hide suggestions after first message
        if (this.conversationHistory.length > 0) {
            this.suggestionsContainer.style.display = 'none';
        }
    }

    close() {
        this.isOpen = false;
        this.window.style.display = 'none';
        this.toggle.style.display = 'flex';
    }

    handleKeydown(e) {
        // Send on Enter, new line on Shift+Enter
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            this.sendMessage();
        }
    }

    handleInputChange() {
        const hasText = this.input.value.trim().length > 0;
        this.sendBtn.disabled = !hasText || this.isLoading;
    }

    autoResizeTextarea() {
        this.input.style.height = 'auto';
        this.input.style.height = Math.min(this.input.scrollHeight, 100) + 'px';
    }

    async sendMessage() {
        const message = this.input.value.trim();

        if (!message || this.isLoading) {
            return;
        }

        // Hide suggestions after first message
        this.suggestionsContainer.style.display = 'none';

        // Add user message to UI
        this.addMessage(message, 'user');

        // Clear input
        this.input.value = '';
        this.input.style.height = 'auto';
        this.handleInputChange();

        // Add to conversation history
        this.conversationHistory.push({
            role: 'user',
            content: message
        });

        // Show loading indicator
        this.setLoading(true);

        try {
            // Call backend API
            const response = await fetch('/api/chatbot', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    message: message,
                    history: this.conversationHistory
                })
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const data = await response.json();

            // Add assistant response to UI
            this.addMessage(data.response, 'bot');

            // Add to conversation history
            this.conversationHistory.push({
                role: 'assistant',
                content: data.response
            });

            // Save history
            this.saveHistory();

        } catch (error) {
            console.error('Chatbot error:', error);
            this.addMessage(
                'I apologize, but I encountered an error processing your request. Please try again.',
                'bot',
                true
            );
        } finally {
            this.setLoading(false);
        }
    }

    addMessage(content, sender, isError = false) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `chat-message ${sender}-message ${isError ? 'error-message' : ''}`;

        const contentDiv = document.createElement('div');
        contentDiv.className = 'message-content';

        // Format content with paragraph breaks
        const paragraphs = content.split('\n\n');
        paragraphs.forEach((para, index) => {
            if (para.trim()) {
                const p = document.createElement('p');
                p.textContent = para.trim();
                contentDiv.appendChild(p);
            }
        });

        const timeDiv = document.createElement('div');
        timeDiv.className = 'message-time';
        timeDiv.textContent = this.formatTime(new Date());

        messageDiv.appendChild(contentDiv);
        messageDiv.appendChild(timeDiv);

        // Remove loading indicator if visible
        if (this.loadingIndicator.style.display !== 'none') {
            this.messagesContainer.appendChild(messageDiv);
        } else {
            this.messagesContainer.appendChild(messageDiv);
        }

        // Scroll to bottom
        this.scrollToBottom();
    }

    setLoading(loading) {
        this.isLoading = loading;

        if (loading) {
            this.loadingIndicator.style.display = 'block';
            this.sendBtn.disabled = true;
            this.input.disabled = true;
        } else {
            this.loadingIndicator.style.display = 'none';
            this.input.disabled = false;
            this.handleInputChange();
        }

        this.scrollToBottom();
    }

    scrollToBottom() {
        setTimeout(() => {
            this.messagesContainer.scrollTop = this.messagesContainer.scrollHeight;
        }, 100);
    }

    formatTime(date) {
        const now = new Date();
        const diff = Math.floor((now - date) / 1000); // seconds

        if (diff < 60) {
            return 'Just now';
        } else if (diff < 3600) {
            const minutes = Math.floor(diff / 60);
            return `${minutes} min${minutes > 1 ? 's' : ''} ago`;
        } else if (diff < 86400) {
            const hours = Math.floor(diff / 3600);
            return `${hours} hour${hours > 1 ? 's' : ''} ago`;
        } else {
            return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
        }
    }

    saveHistory() {
        try {
            // Save to localStorage (limit to last 50 messages)
            const limitedHistory = this.conversationHistory.slice(-50);
            localStorage.setItem('cfo_chatbot_history', JSON.stringify(limitedHistory));
        } catch (error) {
            console.error('Error saving chat history:', error);
        }
    }

    loadHistory() {
        try {
            const saved = localStorage.getItem('cfo_chatbot_history');
            if (saved) {
                this.conversationHistory = JSON.parse(saved);

                // Restore messages to UI (skip welcome message)
                const messagesToShow = this.conversationHistory.slice(-10); // Last 10 messages
                messagesToShow.forEach(msg => {
                    if (msg.role === 'user') {
                        this.addMessage(msg.content, 'user');
                    } else if (msg.role === 'assistant') {
                        this.addMessage(msg.content, 'bot');
                    }
                });

                // If there's history, hide suggestions
                if (this.conversationHistory.length > 0) {
                    this.suggestionsContainer.style.display = 'none';
                }
            }
        } catch (error) {
            console.error('Error loading chat history:', error);
        }
    }

    clearHistory() {
        this.conversationHistory = [];
        localStorage.removeItem('cfo_chatbot_history');

        // Clear messages except welcome
        const messages = this.messagesContainer.querySelectorAll('.chat-message');
        messages.forEach((msg, index) => {
            if (index > 0) { // Keep first welcome message
                msg.remove();
            }
        });

        // Show suggestions again
        this.suggestionsContainer.style.display = 'flex';
    }
}

// Initialize chatbot when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    window.cfoChatbot = new CFOChatbot();
});
