// static/js/chatbot.js

import { getUserId, getAbsoluteUrl, apiFetch } from './utils.js';

let currentChatName = null;
let currentUserId = null;

// --- Helper Functions ---

/**
 * Checks authentication and initializes the user ID.
 */
function checkAuthAndInit() {
    currentUserId = getUserId();
    if (!currentUserId) {
        alert('You must be logged in to use the chatbot.');
        window.location.href = getAbsoluteUrl('/login');
        return false;
    }
    return true;
}

/**
 * Scrolls the chat window to the bottom.
 */
function scrollToBottom() {
    const chatWindow = document.getElementById('chat-messages');
    chatWindow.scrollTop = chatWindow.scrollHeight;
}

/**
 * Renders a single message bubble into the chat window.
 * @param {string} role - 'user', 'bot', or 'system'
 * @param {string} content - The message content
 */
function addMessageToChat(role, content) {
    const chatWindow = document.getElementById('chat-messages');
    
    // Create the message container
    const messageContainer = document.createElement('div');
    messageContainer.classList.add('message-container', role);

    // If it's a system message, use the dedicated class
    if (role === 'system') {
        const systemDiv = document.createElement('div');
        systemDiv.classList.add('system-message');
        systemDiv.innerHTML = content;
        chatWindow.appendChild(systemDiv);
        scrollToBottom();
        return;
    }
    
    // Create the bubble
    const messageBubble = document.createElement('div');
    messageBubble.classList.add('message-bubble');
    
    // Simple markdown conversion for bolding (not a full parser)
    content = content.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
    
    messageBubble.innerHTML = content;
    
    messageContainer.appendChild(messageBubble);
    chatWindow.appendChild(messageContainer);
    
    scrollToBottom();
}

/**
 * Disables or enables the message input area and send button.
 * @param {boolean} disabled
 */
function toggleInput(disabled) {
    document.getElementById('message-input').disabled = disabled;
    document.getElementById('send-button').disabled = disabled;
}


// --- Chat History Management ---

/**
 * Loads the list of existing chats and renders them in the sidebar.
 */
async function loadChatList() {
    if (!currentUserId) return;
    
    const chatListElement = document.getElementById('chat-list');
    chatListElement.innerHTML = '<li><span class="loading-item">Loading chats...</span></li>';
    
    try {
        const url = getAbsoluteUrl(`/api/chats/${currentUserId}`);
        const chatList = await apiFetch(url, 'GET');

        chatListElement.innerHTML = ''; // Clear loading message

        if (chatList.length === 0) {
            chatListElement.innerHTML = '<li><span class="no-chats">Start a new chat!</span></li>';
            document.getElementById('chat-name-display').textContent = 'New Conversation';
            return;
        }

        chatList.forEach(chatName => {
            const li = document.createElement('li');
            li.classList.add('chat-item');
            li.dataset.chatName = chatName;
            li.innerHTML = `
                <span class="chat-name-text">${chatName}</span>
                <button class="rename-btn" title="Rename Chat">✎</button>
            `;
            li.addEventListener('click', () => switchChat(chatName));
            li.querySelector('.rename-btn').addEventListener('click', (e) => {
                e.stopPropagation(); // Prevent switchChat from being called
                promptRenameChat(chatName);
            });
            chatListElement.appendChild(li);
        });

        // Load the first chat by default if currentChatName is null
        if (!currentChatName) {
            switchChat(chatList[0]);
        } else {
            // Re-highlight the current chat after list reload
            const activeItem = document.querySelector(`.chat-item[data-chat-name="${currentChatName}"]`);
            if (activeItem) activeItem.classList.add('active');
        }

    } catch (error) {
        console.error("Error loading chat list:", error);
        chatListElement.innerHTML = '<li><span class="system-message error">Failed to load chats.</span></li>';
    }
}

/**
 * Switches the active chat and loads its history.
 * @param {string} chatName
 */
async function switchChat(chatName) {
    if (currentChatName === chatName) return; // Already active

    // Update active class in sidebar
    document.querySelectorAll('.chat-item').forEach(item => item.classList.remove('active'));
    const newActiveItem = document.querySelector(`.chat-item[data-chat-name="${chatName}"]`);
    if (newActiveItem) newActiveItem.classList.add('active');

    currentChatName = chatName;
    document.getElementById('chat-name-display').textContent = chatName;
    const chatWindow = document.getElementById('chat-messages');
    chatWindow.innerHTML = '<div class="system-message">Loading chat history...</div>';
    toggleInput(true); // Disable input while loading

    try {
        const url = getAbsoluteUrl(`/api/chats/${currentUserId}/${chatName}`);
        const history = await apiFetch(url, 'GET');

        chatWindow.innerHTML = ''; // Clear loading message
        history.forEach(msg => addMessageToChat(msg.role, msg.content));
        
        // Add a welcome message if the chat is empty (but loaded)
        if (history.length === 0) {
             addMessageToChat('system', `You are starting a new conversation: **${chatName}**. How can I help with your finances?`);
        }
        
    } catch (error) {
        console.error(`Error loading chat history for ${chatName}:`, error);
        chatWindow.innerHTML = `<div class="system-message error">Failed to load history: ${error.message}</div>`;
    } finally {
        toggleInput(false);
    }
}

/**
 * Creates a new chat session.
 * @param {string} chatName
 */
async function createNewChat(chatName) {
    if (!currentUserId) return;

    try {
        const url = getAbsoluteUrl(`/api/chats/${currentUserId}`);
        const response = await apiFetch(url, 'POST', { chat_name: chatName });
        
        if (response.success) {
            await loadChatList(); // Reload sidebar
            switchChat(chatName); // Switch to the new chat
        } else {
            alert(response.message || 'Failed to create new chat (name may already exist).');
        }
    } catch (error) {
        alert('Error creating chat: ' + error.message);
    }
}

/**
 * Prompts the user to create a new chat.
 */
function promptNewChat() {
    let chatName = prompt("Enter a name for the new chat:");
    if (chatName) {
        chatName = chatName.trim();
        if (chatName) {
            createNewChat(chatName);
        }
    }
}

/**
 * Prompts the user to rename the current chat.
 * @param {string} oldName
 */
async function promptRenameChat(oldName) {
    const newName = prompt(`Rename chat '${oldName}' to:`, oldName);
    
    if (newName && newName.trim() !== oldName) {
        const trimmedNewName = newName.trim();
        if (!trimmedNewName) {
            alert("Chat name cannot be empty.");
            return;
        }
        
        try {
            const url = getAbsoluteUrl(`/api/chats/${currentUserId}/${oldName}/rename`);
            const response = await apiFetch(url, 'POST', { new_name: trimmedNewName });
            
            if (response.success) {
                // If the chat we are renaming is the currently active one, update the display
                if (currentChatName === oldName) {
                    currentChatName = trimmedNewName;
                }
                loadChatList(); // Reload sidebar to show new name
            } else {
                alert(response.message || 'Failed to rename chat (new name may already exist).');
            }
        } catch (error) {
            alert('Error renaming chat: ' + error.message);
        }
    }
}

// --- Message Sending ---

/**
 * Handles sending a new message to the bot.
 */
async function sendMessage() {
    const inputElement = document.getElementById('message-input');
    let content = inputElement.value.trim();

    if (!content || !currentChatName) return;

    // 1. Clear input and disable
    inputElement.value = '';
    toggleInput(true);

    // 2. Add user message to chat
    addMessageToChat('user', content);

    // 3. Add temporary bot thinking message
    const chatWindow = document.getElementById('chat-messages');
    const thinkingMessage = document.createElement('div');
    thinkingMessage.id = 'bot-thinking';
    thinkingMessage.classList.add('message-container', 'bot');
    thinkingMessage.innerHTML = '<div class="message-bubble">Finny is typing...</div>';
    chatWindow.appendChild(thinkingMessage);
    scrollToBottom();

    try {
        // API will save user message, generate bot response, and save bot response
        const url = getAbsoluteUrl(`/api/chats/${currentUserId}/${currentChatName}/message`);
        const response = await apiFetch(url, 'POST', { content: content, user_id: currentUserId });

        // 4. Remove thinking message
        thinkingMessage.remove();

        if (response.success) {
            // 5. Add bot response
            addMessageToChat(response.role, response.content);
        } else {
            addMessageToChat('system', `Error: ${response.message || 'Could not get a response from the bot.'}`);
        }

    } catch (error) {
        // Check if thinking message exists before trying to remove it
        const thinking = document.getElementById('bot-thinking');
        if (thinking) thinking.remove();
        
        addMessageToChat('system', `Network Error: ${error.message}`);
    } finally {
        toggleInput(false);
    }
}


/**
 * Handles key presses in the input field (e.g., Enter to send).
 * @param {Event} event
 */
function handleKey(event) {
    if (event.key === 'Enter' && !event.shiftKey) {
        event.preventDefault(); // Prevent new line
        sendMessage();
    }
}


// --- Initialization ---

document.addEventListener('DOMContentLoaded', () => {
    if (checkAuthAndInit()) {
        loadChatList();
        
        // Attach event listeners for chat functionality
        document.getElementById('new-chat-button').addEventListener('click', promptNewChat);
        document.getElementById('send-button').addEventListener('click', sendMessage);
        document.getElementById('message-input').addEventListener('keydown', handleKey);
    }
});