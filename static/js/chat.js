// Add this to your extra_js block
document.addEventListener('DOMContentLoaded', function() {
    const chatContainer = document.getElementById('chatContainer');
    const chatForm = document.getElementById('chatForm');
    const sendMessageBtn = document.getElementById('sendMessageBtn');
    const imageUploadBtn = document.getElementById('imageUploadBtn');
    const fileUploadBtn = document.getElementById('fileUploadBtn');
    const imageInput = document.getElementById('{{ chat_form.image.id_for_label }}');
    const fileInput = document.getElementById('{{ chat_form.file.id_for_label }}');
    const uploadPreview = document.getElementById('uploadPreview');
    
    let lastMessageId = {{ chat_messages.last.id|default:0 }};
    let pollInterval;
    
    // Auto-scroll to bottom
    function scrollToBottom() {
        if (chatContainer) {
            chatContainer.scrollTop = chatContainer.scrollHeight;
        }
    }
    
    // Poll for new messages
    function pollMessages() {
        if (!chatContainer) return;
        
        fetch(`{% url 'get_chat_messages' event.id %}?last_message_id=${lastMessageId}`)
            .then(response => response.json())
            .then(data => {
                if (data.messages && data.messages.length > 0) {
                    data.messages.forEach(message => {
                        addMessageToChat(message);
                        lastMessageId = Math.max(lastMessageId, message.id);
                    });
                    scrollToBottom();
                }
            })
            .catch(error => console.error('Error polling messages:', error));
    }
    
    // Add message to chat
    function addMessageToChat(message) {
        const messageElement = createMessageElement(message);
        chatContainer.appendChild(messageElement);
    }
    
    // Create message element
    function createMessageElement(message) {
        const isSent = message.user.username === '{{ user.username }}';
        const messageDiv = document.createElement('div');
        messageDiv.className = `chat-message ${isSent ? 'sent' : 'received'}`;
        messageDiv.dataset.messageId = message.id;
        
        let contentHtml = '';
        if (message.message_type === 'text') {
            contentHtml = `<div class="message-text">${message.content.replace(/\n/g, '<br>')}</div>`;
        } else if (message.message_type === 'image') {
            contentHtml = `<div class="message-image"><img src="${message.image_url}" alt="Shared image" class="img-fluid rounded" style="max-height: 200px;"></div>`;
        } else if (message.message_type === 'file') {
            contentHtml = `<div class="message-file"><a href="${message.file_url}" target="_blank" class="file-link"><i class="fas fa-file me-2"></i>${message.file_name}</a></div>`;
        }
        
        messageDiv.innerHTML = `
            <div class="message-avatar">
                <img src="${message.user.avatar_url}" alt="${message.user.username}">
            </div>
            <div class="message-content">
                <div class="message-header">
                    <strong>${message.user.username}</strong>
                    <span class="message-time">${message.created_at}</span>
                </div>
                ${contentHtml}
                ${message.is_edited ? '<small class="text-muted">(edited)</small>' : ''}
                <div class="message-reactions">
                    ${message.reactions.map(reaction => 
                        `<span class="reaction-badge" data-emoji="${reaction.emoji}">
                            ${reaction.emoji} <small>${reaction.count}</small>
                        </span>`
                    ).join('')}
                </div>
            </div>
            <div class="message-actions">
                <div class="dropdown">
                    <button class="btn btn-sm btn-outline-secondary dropdown-toggle" type="button" data-bs-toggle="dropdown">
                        <i class="fas fa-ellipsis-h"></i>
                    </button>
                    <ul class="dropdown-menu">
                        <li>
                            <button class="dropdown-item reaction-picker" data-message-id="${message.id}">
                                <i class="far fa-smile me-2"></i>Add Reaction
                            </button>
                        </li>
                        ${isSent || '{{ user == event.host }}' ? `
                        <li>
                            <button class="dropdown-item text-danger delete-message" data-message-id="${message.id}">
                                <i class="fas fa-trash me-2"></i>Delete Message
                            </button>
                        </li>
                        ` : ''}
                    </ul>
                </div>
            </div>
        `;
        
        return messageDiv;
    }
    
    // Handle form submission
    if (chatForm) {
        chatForm.addEventListener('submit', function(e) {
            e.preventDefault();
            
            const formData = new FormData(this);
            sendMessageBtn.disabled = true;
            sendMessageBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i>';
            
            fetch(this.action, {
                method: 'POST',
                body: formData,
                headers: {
                    'X-Requested-With': 'XMLHttpRequest'
                }
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    this.reset();
                    uploadPreview.style.display = 'none';
                    addMessageToChat(data.message);
                    scrollToBottom();
                } else {
                    alert('Error sending message: ' + data.error);
                }
            })
            .catch(error => {
                console.error('Error:', error);
                alert('Error sending message');
            })
            .finally(() => {
                sendMessageBtn.disabled = false;
                sendMessageBtn.innerHTML = '<i class="fas fa-paper-plane"></i>';
            });
        });
    }
    
    // File upload handlers
    if (imageUploadBtn && imageInput) {
        imageUploadBtn.addEventListener('click', () => imageInput.click());
        imageInput.addEventListener('change', handleFileUpload);
    }
    
    if (fileUploadBtn && fileInput) {
        fileUploadBtn.addEventListener('click', () => fileInput.click());
        fileInput.addEventListener('change', handleFileUpload);
    }
    
    function handleFileUpload(e) {
        const file = e.target.files[0];
        if (file) {
            uploadPreview.innerHTML = `
                <div class="upload-preview-item">
                    <span><i class="fas fa-file me-2"></i>${file.name}</span>
                    <button type="button" class="btn btn-sm btn-outline-danger remove-upload">
                        <i class="fas fa-times"></i>
                    </button>
                </div>
            `;
            uploadPreview.style.display = 'block';
            
            // Add remove handler
            uploadPreview.querySelector('.remove-upload').addEventListener('click', function() {
                e.target.value = '';
                uploadPreview.style.display = 'none';
            });
        }
    }
    
    // Start polling for new messages
    if (chatContainer) {
        scrollToBottom();
        pollInterval = setInterval(pollMessages, 3000); // Poll every 3 seconds
    }
    
    // Cleanup on page leave
    window.addEventListener('beforeunload', function() {
        if (pollInterval) {
            clearInterval(pollInterval);
        }
    });
    
    // Reaction handlers
    document.addEventListener('click', function(e) {
        if (e.target.classList.contains('reaction-picker')) {
            const messageId = e.target.dataset.messageId;
            showReactionPicker(e.target, messageId);
        }
        
        if (e.target.classList.contains('delete-message')) {
            const messageId = e.target.dataset.messageId;
            deleteMessage(messageId);
        }
        
        if (e.target.classList.contains('reaction-badge')) {
            const messageId = e.target.closest('.chat-message').dataset.messageId;
            const emoji = e.target.dataset.emoji;
            addReaction(messageId, emoji);
        }
    });
    
    function showReactionPicker(button, messageId) {
        // Simple emoji picker - you can expand this
        const emojis = ['👍', '❤️', '😂', '😮', '😢', '😡'];
        const popup = document.createElement('div');
        popup.className = 'reaction-picker-popup';
        popup.style.left = `${button.offsetLeft}px`;
        popup.style.top = `${button.offsetTop - 50}px`;
        
        popup.innerHTML = emojis.map(emoji => 
            `<span class="reaction-emoji" data-emoji="${emoji}">${emoji}</span>`
        ).join('');
        
        document.body.appendChild(popup);
        
        // Add click handlers
        popup.querySelectorAll('.reaction-emoji').forEach(emojiSpan => {
            emojiSpan.addEventListener('click', function() {
                addReaction(messageId, this.dataset.emoji);
                popup.remove();
            });
        });
        
        // Remove popup on outside click
        setTimeout(() => {
            document.addEventListener('click', function removePopup() {
                popup.remove();
                document.removeEventListener('click', removePopup);
            });
        }, 100);
    }
    
    function addReaction(messageId, emoji) {
        fetch(`{% url 'add_chat_reaction' 0 %}`.replace('0', messageId), {
            method: 'POST',
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded',
                'X-CSRFToken': '{{ csrf_token }}',
                'X-Requested-With': 'XMLHttpRequest'
            },
            body: `emoji=${encodeURIComponent(emoji)}`
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                // Update reaction display
                updateReactionDisplay(messageId, data.reaction);
            }
        })
        .catch(error => console.error('Error adding reaction:', error));
    }
    
    function deleteMessage(messageId) {
        if (!confirm('Are you sure you want to delete this message?')) return;
        
        fetch(`{% url 'delete_chat_message' 0 %}`.replace('0', messageId), {
            method: 'POST',
            headers: {
                'X-CSRFToken': '{{ csrf_token }}',
                'X-Requested-With': 'XMLHttpRequest'
            }
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                document.querySelector(`.chat-message[data-message-id="${messageId}"]`).remove();
                
            }
        })
        .catch(error => console.error('Error deleting message:', error));
    }

    function updateReactionDisplay(messageId, reaction) {
        const messageElement = document.querySelector(`.chat-message[data-message-id="${messageId}"]`);
        if (!messageElement) return;

        const reactionsContainer = messageElement.querySelector('.message-reactions');
        let reactionBadge = reactionsContainer.querySelector(`[data-emoji="${reaction.emoji}"]`);

        if (reactionBadge) {
            // Update existing reaction
            reactionBadge.innerHTML = `${reaction.emoji} <small>${reaction.count}</small>`;
        } else {
            // Add new reaction
            reactionBadge = document.createElement('span');
            reactionBadge.className = 'reaction-badge';
            reactionBadge.dataset.emoji = reaction.emoji;
            reactionBadge.innerHTML = `${reaction.emoji} <small>${reaction.count}</small>`;
            reactionsContainer.appendChild(reactionBadge);
        }

        // Remove reaction if count is 0
        if (reaction.count === 0) {
            reactionBadge.remove();
        }
    }

    // Typing indicator (optional enhancement)
    let typingTimer;
    const messageInput = document.getElementById('{{ chat_form.content.id_for_label }}');
    
    if (messageInput) {
        messageInput.addEventListener('input', function() {
            // Clear existing timer
            clearTimeout(typingTimer);
            
            // Show typing indicator (you'd need to implement this on backend too)
            // For now, we'll just handle the frontend
            showTypingIndicator();
            
            // Set timer to hide typing indicator after 1 second of inactivity
            typingTimer = setTimeout(hideTypingIndicator, 1000);
        });
    }

    function showTypingIndicator() {
        // You would typically send a WebSocket message here
        // For now, we'll just demonstrate the concept
        let typingIndicator = document.getElementById('typing-indicator');
        if (!typingIndicator) {
            typingIndicator = document.createElement('div');
            typingIndicator.id = 'typing-indicator';
            typingIndicator.className = 'typing-indicator';
            typingIndicator.innerHTML = `
                <span>Someone is typing</span>
                <div class="typing-dots">
                    <div class="typing-dot"></div>
                    <div class="typing-dot"></div>
                    <div class="typing-dot"></div>
                </div>
            `;
            chatContainer.appendChild(typingIndicator);
        }
        scrollToBottom();
    }

    function hideTypingIndicator() {
        const typingIndicator = document.getElementById('typing-indicator');
        if (typingIndicator) {
            typingIndicator.remove();
        }
    }

    // Keyboard shortcuts
    document.addEventListener('keydown', function(e) {
        // Ctrl+Enter to send message
        if (e.ctrlKey && e.key === 'Enter' && chatForm) {
            chatForm.dispatchEvent(new Event('submit'));
        }
        
        // Escape to clear message
        if (e.key === 'Escape' && messageInput) {
            messageInput.value = '';
            uploadPreview.style.display = 'none';
        }
    });

    // Auto-resize textarea
    if (messageInput) {
        messageInput.addEventListener('input', function() {
            this.style.height = 'auto';
            this.style.height = (this.scrollHeight) + 'px';
        });
    }

    // Initialize
    scrollToBottom();
});