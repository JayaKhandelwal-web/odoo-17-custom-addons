/** @odoo-module **/

import { registry } from "@web/core/registry";

/**
 * RADICAL SOLUTION: Instead of creating widgets, we'll enhance existing DOM elements
 * This approach hooks into Odoo's form rendering and enhances specific fields
 */

class MyOperatorEnhancer {
    constructor() {
        this.initialized = false;
        this.observers = new Map();
    }

    init() {
        if (this.initialized) return;
        this.initialized = true;

        // Hook into form rendering
        this.setupFormObserver();

        // Also try immediate enhancement for any existing forms
        setTimeout(() => this.enhanceExistingForms(), 1000);
    }

    setupFormObserver() {
        // Create a mutation observer to watch for new forms
        const observer = new MutationObserver((mutations) => {
            mutations.forEach((mutation) => {
                mutation.addedNodes.forEach((node) => {
                    if (node.nodeType === Node.ELEMENT_NODE) {
                        this.enhanceNode(node);
                    }
                });
            });
        });

        // Start observing
        observer.observe(document.body, {
            childList: true,
            subtree: true
        });

        this.mainObserver = observer;
    }

    enhanceExistingForms() {
        // Find all existing forms and enhance them
        const forms = document.querySelectorAll('.o_form_view');
        forms.forEach(form => this.enhanceNode(form));
    }

    enhanceNode(node) {
        if (!node.querySelector) return;

        // Enhance phone fields
        this.enhancePhoneFields(node);

        // Enhance chat message fields
        this.enhanceChatFields(node);
    }

    enhancePhoneFields(container) {
        // Look for phone/mobile fields in MyOperator models
        const phoneFields = container.querySelectorAll(
            'div[name="phone"]:not(.enhanced), ' +
            'div[name="mobile"]:not(.enhanced), ' +
            'div[name="customer_contact"]:not(.enhanced), ' +
            'div[name="caller_number"]:not(.enhanced), ' +
            'div[name="called_number"]:not(.enhanced)'
        );

        phoneFields.forEach(field => {
            this.enhancePhoneField(field);
        });
    }

    enhancePhoneField(fieldDiv) {
        // Mark as enhanced to avoid duplicate processing
        fieldDiv.classList.add('enhanced');

        // Find the input or text element
        const phoneInput = fieldDiv.querySelector('input') || fieldDiv.querySelector('.o_field_widget');
        if (!phoneInput) return;

        const phoneNumber = phoneInput.value || phoneInput.textContent || '';
        if (!phoneNumber.trim()) return;

        // Create action buttons container
        const actionsContainer = document.createElement('div');
        actionsContainer.className = 'o_phone_actions d-flex gap-1 ms-2';
        actionsContainer.innerHTML = `
            <button type="button" class="btn btn-sm btn-outline-primary o_myop_call"
                    title="MyOperator Call" data-phone="${this.escapeHtml(phoneNumber)}">
                <i class="fa fa-phone"></i>
            </button>
            <button type="button" class="btn btn-sm btn-outline-success o_myop_whatsapp"
                    title="WhatsApp" data-phone="${this.escapeHtml(phoneNumber)}">
                <i class="fa fa-whatsapp"></i>
            </button>
        `;

        // Insert actions after the field
        if (fieldDiv.style.display !== 'none') {
            // Make sure parent has flex layout
            fieldDiv.style.display = 'flex';
            fieldDiv.style.alignItems = 'center';
            fieldDiv.appendChild(actionsContainer);
        }

        // Bind events
        this.bindPhoneActions(actionsContainer, phoneNumber);
    }

    bindPhoneActions(container, phoneNumber) {
        const callBtn = container.querySelector('.o_myop_call');
        const whatsappBtn = container.querySelector('.o_myop_whatsapp');

        if (callBtn) {
            callBtn.addEventListener('click', (e) => {
                e.preventDefault();
                e.stopPropagation();
                this.makeCall(phoneNumber);
            });
        }

        if (whatsappBtn) {
            whatsappBtn.addEventListener('click', (e) => {
                e.preventDefault();
                e.stopPropagation();
                this.openWhatsApp(phoneNumber);
            });
        }
    }

    enhanceChatFields(container) {
        // Look for message_ids fields in conversation forms
        const chatFields = container.querySelectorAll(
            'div[name="message_ids"]:not(.chat-enhanced), ' +
            '.o_field_one2many[data-field-name="message_ids"]:not(.chat-enhanced)'
        );

        chatFields.forEach(field => {
            this.enhanceChatField(field);
        });

        // Also look for conversation forms specifically
        if (container.classList.contains('o_form_view')) {
            const modelName = container.getAttribute('data-model') || '';
            if (modelName === 'myoperator.conversation') {
                this.enhanceConversationForm(container);
            }
        }
    }

    enhanceChatField(fieldDiv) {
        // Mark as enhanced
        fieldDiv.classList.add('chat-enhanced');

        // Get the record ID from the form
        const form = fieldDiv.closest('.o_form_view');
        const recordId = this.extractRecordId(form);

        if (!recordId) {
            console.warn('No record ID found for chat enhancement');
            return;
        }

        // Create chat interface
        const chatInterface = this.createChatInterface(recordId);

        // Replace or enhance the field
        if (fieldDiv.querySelector('.o_list_view')) {
            // Replace list view with chat interface
            fieldDiv.innerHTML = '';
            fieldDiv.appendChild(chatInterface);
        } else {
            // Add chat interface
            fieldDiv.appendChild(chatInterface);
        }
    }

    enhanceConversationForm(form) {
        if (form.classList.contains('conversation-enhanced')) return;
        form.classList.add('conversation-enhanced');

        const recordId = this.extractRecordId(form);
        if (!recordId) return;

        // Add floating chat button
        const chatButton = document.createElement('button');
        chatButton.type = 'button';
        chatButton.className = 'btn btn-primary btn-sm o_chat_toggle';
        chatButton.style.cssText = 'position: fixed; bottom: 20px; right: 20px; z-index: 1000; border-radius: 50%; width: 60px; height: 60px;';
        chatButton.innerHTML = '<i class="fa fa-comments fa-lg"></i>';
        chatButton.title = 'Toggle Chat Interface';

        document.body.appendChild(chatButton);

        // Create floating chat interface
        const chatInterface = this.createFloatingChat(recordId);
        document.body.appendChild(chatInterface);

        // Toggle functionality
        chatButton.addEventListener('click', () => {
            const isVisible = chatInterface.style.display !== 'none';
            chatInterface.style.display = isVisible ? 'none' : 'block';
        });
    }

    createChatInterface(recordId) {
        const container = document.createElement('div');
        container.className = 'o_myoperator_chat_interface';
        container.innerHTML = `
            <div class="card">
                <div class="card-header bg-primary text-white d-flex justify-content-between align-items-center">
                    <h6 class="mb-0">
                        <i class="fa fa-comments me-2"></i>Chat Messages
                    </h6>
                    <div class="btn-group btn-group-sm">
                        <button type="button" class="btn btn-outline-light o_refresh_chat" title="Refresh">
                            <i class="fa fa-refresh"></i>
                        </button>
                        <button type="button" class="btn btn-outline-light o_send_message" title="Send Message">
                            <i class="fa fa-paper-plane"></i>
                        </button>
                    </div>
                </div>
                <div class="card-body p-0">
                    <div class="o_messages_area" style="height: 400px; overflow-y: auto; background: #f8f9fa;">
                        <div class="o_loading text-center p-4" style="display: none;">
                            <i class="fa fa-spinner fa-spin"></i> Loading messages...
                        </div>
                        <div class="o_messages_list p-3">
                            <div class="text-center text-muted">
                                <i class="fa fa-comments fa-2x mb-2"></i>
                                <p>Click refresh to load messages</p>
                            </div>
                        </div>
                    </div>
                </div>
                <div class="card-footer">
                    <div class="o_quick_replies">
                        <small class="text-muted d-block mb-2">Quick Replies:</small>
                        <div class="btn-group-sm">
                            <button type="button" class="btn btn-outline-secondary btn-sm me-1 o_quick_reply"
                                    data-message="Hello! How can I help you today?">
                                👋 Hello
                            </button>
                            <button type="button" class="btn btn-outline-secondary btn-sm me-1 o_quick_reply"
                                    data-message="Thank you for contacting us.">
                                🙏 Thank you
                            </button>
                            <button type="button" class="btn btn-outline-secondary btn-sm o_quick_reply"
                                    data-message="I will get back to you shortly.">
                                ⏰ Will get back
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        `;

        // Bind events
        this.bindChatEvents(container, recordId);

        return container;
    }

    createFloatingChat(recordId) {
        const container = document.createElement('div');
        container.className = 'o_floating_chat';
        container.style.cssText = `
            position: fixed;
            bottom: 90px;
            right: 20px;
            width: 400px;
            height: 500px;
            z-index: 999;
            display: none;
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        `;

        container.appendChild(this.createChatInterface(recordId));
        return container;
    }

    bindChatEvents(container, recordId) {
        // Refresh button
        const refreshBtn = container.querySelector('.o_refresh_chat');
        if (refreshBtn) {
            refreshBtn.addEventListener('click', () => {
                this.loadMessages(container, recordId);
            });
        }

        // Send message button
        const sendBtn = container.querySelector('.o_send_message');
        if (sendBtn) {
            sendBtn.addEventListener('click', () => {
                this.openSendDialog(recordId);
            });
        }

        // Quick reply buttons
        const quickBtns = container.querySelectorAll('.o_quick_reply');
        quickBtns.forEach(btn => {
            btn.addEventListener('click', (e) => {
                const message = e.target.dataset.message;
                if (message) {
                    this.sendQuickMessage(recordId, message);
                }
            });
        });
    }

    async loadMessages(container, recordId) {
        const loadingEl = container.querySelector('.o_loading');
        const messagesEl = container.querySelector('.o_messages_list');

        if (loadingEl) loadingEl.style.display = 'block';

        try {
            // Use direct RPC call
            const response = await fetch('/web/dataset/call_kw', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    jsonrpc: '2.0',
                    method: 'call',
                    params: {
                        model: 'myoperator.message',
                        method: 'search_read',
                        args: [[['conversation_id', '=', recordId]]],
                        kwargs: {
                            fields: ['direction', 'content', 'timestamp', 'message_type', 'read_status'],
                            order: 'timestamp ASC'
                        }
                    }
                })
            });

            const result = await response.json();

            if (result.result) {
                this.displayMessages(messagesEl, result.result);
            }

        } catch (error) {
            console.error('Error loading messages:', error);
            if (messagesEl) {
                messagesEl.innerHTML = `
                    <div class="text-center text-danger p-3">
                        <i class="fa fa-exclamation-triangle"></i>
                        <p>Failed to load messages</p>
                    </div>
                `;
            }
        } finally {
            if (loadingEl) loadingEl.style.display = 'none';
        }
    }

    displayMessages(container, messages) {
        if (!container) return;

        container.innerHTML = '';

        if (!messages || messages.length === 0) {
            container.innerHTML = `
                <div class="text-center text-muted p-3">
                    <i class="fa fa-comments fa-2x mb-2"></i>
                    <p>No messages yet</p>
                </div>
            `;
            return;
        }

        messages.forEach(message => {
            const messageEl = this.createMessageElement(message);
            container.appendChild(messageEl);
        });

        // Scroll to bottom
        const scrollContainer = container.closest('.o_messages_area');
        if (scrollContainer) {
            setTimeout(() => {
                scrollContainer.scrollTop = scrollContainer.scrollHeight;
            }, 100);
        }
    }

    createMessageElement(message) {
        const messageEl = document.createElement('div');
        const isIncoming = message.direction === 'incoming';

        messageEl.className = `mb-3 d-flex ${isIncoming ? 'justify-content-start' : 'justify-content-end'}`;

        const bubbleClass = isIncoming ? 'bg-white border' : 'bg-primary text-white';
        const content = this.escapeHtml(message.content || 'No content');
        const timeStr = this.formatTime(message.timestamp);

        let statusIcon = '';
        if (!isIncoming) {
            statusIcon = message.read_status
                ? '<i class="fa fa-check-double ms-1" style="opacity: 0.8;"></i>'
                : '<i class="fa fa-check ms-1" style="opacity: 0.8;"></i>';
        }

        messageEl.innerHTML = `
            <div class="message-bubble ${bubbleClass} p-2 rounded shadow-sm" style="max-width: 70%;">
                <div class="message-content">
                    ${message.message_type === 'text' ? content : `<i class="fa fa-file me-1"></i>${message.message_type} file`}
                </div>
                <div class="message-time small mt-1" style="font-size: 0.75rem; opacity: 0.8;">
                    ${timeStr}${statusIcon}
                </div>
            </div>
        `;

        return messageEl;
    }

    async sendQuickMessage(recordId, messageText) {
        try {
            // Show temporary message
            this.showNotification('Sending message...', 'info');

            // Use direct RPC to send message
            const response = await fetch('/web/dataset/call_kw', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    jsonrpc: '2.0',
                    method: 'call',
                    params: {
                        model: 'myoperator.conversation',
                        method: 'send_quick_message',
                        args: [recordId, messageText],
                        kwargs: {}
                    }
                })
            });

            const result = await response.json();

            if (result.result && result.result.success) {
                this.showNotification('Message sent successfully!', 'success');

                // Reload messages
                const chatContainer = document.querySelector('.o_myoperator_chat_interface');
                if (chatContainer) {
                    setTimeout(() => this.loadMessages(chatContainer, recordId), 1000);
                }
            } else {
                throw new Error(result.result?.message || 'Failed to send message');
            }

        } catch (error) {
            console.error('Error sending message:', error);
            this.showNotification('Failed to send message', 'danger');
        }
    }

    openSendDialog(recordId) {
        // Simple dialog implementation
        const message = prompt('Enter your message:');
        if (message && message.trim()) {
            this.sendQuickMessage(recordId, message.trim());
        }
    }

    // Utility methods
    extractRecordId(form) {
        if (!form) return null;

        // Try to get from data attributes
        const recordId = form.getAttribute('data-record-id') ||
                        form.getAttribute('data-res-id');

        if (recordId) return parseInt(recordId);

        // Try to extract from URL
        const url = window.location.href;
        const match = url.match(/id=(\d+)/);
        return match ? parseInt(match[1]) : null;
    }

    makeCall(phoneNumber) {
        if (!phoneNumber) {
            this.showNotification('No phone number available', 'warning');
            return;
        }

        try {
            const cleanNumber = phoneNumber.replace(/[^\d+]/g, '');
            const url = `https://in.app.myoperator.com/webcall?number=${cleanNumber}`;
            window.open(url, '_blank');
            this.showNotification(`Initiating call to ${phoneNumber}`, 'info');
        } catch (error) {
            this.showNotification('Failed to initiate call', 'danger');
        }
    }

    openWhatsApp(phoneNumber) {
        if (!phoneNumber) {
            this.showNotification('No phone number available', 'warning');
            return;
        }

        // Simple implementation - you can enhance this
        const message = prompt(`Send WhatsApp message to ${phoneNumber}:`);
        if (message) {
            this.showNotification(`WhatsApp message would be sent to ${phoneNumber}: ${message}`, 'info');
        }
    }

    formatTime(timestamp) {
        if (!timestamp) return '';
        return new Date(timestamp).toLocaleTimeString([], {
            hour: '2-digit',
            minute: '2-digit'
        });
    }

    escapeHtml(text) {
        if (!text) return '';
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    showNotification(message, type) {
        // Simple notification implementation
        const notification = document.createElement('div');
        notification.className = `alert alert-${type === 'danger' ? 'danger' : type === 'success' ? 'success' : 'info'}
                                 position-fixed`;
        notification.style.cssText = 'top: 20px; right: 20px; z-index: 9999; max-width: 300px;';
        notification.textContent = message;

        document.body.appendChild(notification);

        setTimeout(() => {
            notification.remove();
        }, 3000);
    }

    destroy() {
        if (this.mainObserver) {
            this.mainObserver.disconnect();
        }
        this.observers.forEach(observer => observer.disconnect());
    }
}

// Initialize the enhancer
const myOpEnhancer = new MyOperatorEnhancer();

// Start enhancement when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => myOpEnhancer.init());
} else {
    myOpEnhancer.init();
}

// Also start on page navigation (for SPA behavior)
window.addEventListener('popstate', () => {
    setTimeout(() => myOpEnhancer.enhanceExistingForms(), 500);
});

// Register a simple service for potential cleanup
registry.category("services").add("myoperator_enhancer", {
    start() {
        return myOpEnhancer;
    },
});