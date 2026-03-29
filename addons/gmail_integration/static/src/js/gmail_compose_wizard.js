/** @odoo-module **/

import { FormController } from "@web/views/form/form_controller";
import { patch } from "@web/core/utils/patch";

// Gmail Compose Wizard JavaScript Functions (Scoped)
class GmailComposeWizard {
    
    static initializeGmailCompose() {
        // Initialize Gmail compose functionality only within the wizard
        const wizardContainer = document.querySelector('.gmail_compose_wizard');
        if (!wizardContainer) return;
        
        this.setupCcBccToggles(wizardContainer);
        this.setupAttachmentHandling(wizardContainer);
        this.setupKeyboardShortcuts(wizardContainer);
        this.adjustWizardHeight(wizardContainer);
    }
    
    static setupCcBccToggles(wizardContainer) {
        // Setup CC/BCC toggle functionality scoped to wizard
        wizardContainer.addEventListener('click', function(e) {
            if (e.target.classList.contains('gmail_cc_toggle')) {
                e.preventDefault();
                GmailComposeWizard.toggleCcField(wizardContainer);
            }
            
            if (e.target.classList.contains('gmail_bcc_toggle')) {
                e.preventDefault();
                GmailComposeWizard.toggleBccField(wizardContainer);
            }
        });
    }
    
    static toggleCcField(wizardContainer = null) {
        const container = wizardContainer || document.querySelector('.gmail_compose_wizard');
        if (!container) return;
        
        const ccRow = container.querySelector('.gmail_cc_row');
        const ccToggle = container.querySelector('.gmail_cc_toggle');
        
        if (ccRow) {
            if (ccRow.style.display === 'none' || ccRow.style.display === '') {
                ccRow.style.display = 'flex';
                const input = ccRow.querySelector('input, textarea');
                if (input) {
                    setTimeout(() => input.focus(), 100);
                }
                if (ccToggle) {
                    ccToggle.style.color = '#1a73e8';
                    ccToggle.style.fontWeight = '600';
                }
            } else {
                ccRow.style.display = 'none';
                if (ccToggle) {
                    ccToggle.style.color = '#5f6368';
                    ccToggle.style.fontWeight = '400';
                }
            }
        }
    }
    
    static toggleBccField(wizardContainer = null) {
        const container = wizardContainer || document.querySelector('.gmail_compose_wizard');
        if (!container) return;
        
        const bccRow = container.querySelector('.gmail_bcc_row');
        const bccToggle = container.querySelector('.gmail_bcc_toggle');
        
        if (bccRow) {
            if (bccRow.style.display === 'none' || bccRow.style.display === '') {
                bccRow.style.display = 'flex';
                const input = bccRow.querySelector('input, textarea');
                if (input) {
                    setTimeout(() => input.focus(), 100);
                }
                if (bccToggle) {
                    bccToggle.style.color = '#1a73e8';
                    bccToggle.style.fontWeight = '600';
                }
            } else {
                bccRow.style.display = 'none';
                if (bccToggle) {
                    bccToggle.style.color = '#5f6368';
                    bccToggle.style.fontWeight = '400';
                }
            }
        }
    }
    
    static setupAttachmentHandling(wizardContainer) {
        // Setup attachment functionality scoped to wizard
        wizardContainer.addEventListener('click', function(e) {
            if (e.target.classList.contains('gmail_attach_btn') || 
                e.target.closest('.gmail_attach_btn')) {
                e.preventDefault();
                GmailComposeWizard.addAttachment(wizardContainer);
            }
        });
    }
    
    static addAttachment(wizardContainer = null) {
        const container = wizardContainer || document.querySelector('.gmail_compose_wizard');
        if (!container) return;
        
        // Find and show attachment section within the wizard
        const attachmentSection = container.querySelector('.gmail_attachments_section');
        if (attachmentSection) {
            attachmentSection.style.display = 'block';
            
            // Try to trigger add line in Odoo list view
            const addButton = attachmentSection.querySelector('.o_field_x2many_list_row_add a, .btn-primary');
            if (addButton) {
                addButton.click();
            } else {
                // Fallback: create a new attachment row
                this.createNewAttachmentRow(container);
            }
        }
    }
    
    static createNewAttachmentRow(wizardContainer) {
        // Trigger the creation of a new attachment row within wizard
        const attachmentField = wizardContainer.querySelector('div[name="attachment_ids"]');
        if (attachmentField) {
            // Dispatch a custom event to add new row
            const event = new CustomEvent('add_attachment_row', {
                bubbles: true,
                detail: { field: 'attachment_ids' }
            });
            attachmentField.dispatchEvent(event);
        }
    }
    
    static setupKeyboardShortcuts(wizardContainer) {
        // Setup Gmail-like keyboard shortcuts scoped to wizard
        wizardContainer.addEventListener('keydown', function(e) {
            // Only process shortcuts when focus is within the wizard
            if (!wizardContainer.contains(e.target)) return;
            
            // Ctrl+Enter or Cmd+Enter to send
            if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
                e.preventDefault();
                const sendButton = wizardContainer.querySelector('.gmail_send_btn');
                if (sendButton) {
                    sendButton.click();
                }
            }
            
            // Ctrl+Shift+C to toggle CC
            if ((e.ctrlKey || e.metaKey) && e.shiftKey && e.key === 'C') {
                e.preventDefault();
                GmailComposeWizard.toggleCcField(wizardContainer);
            }
            
            // Ctrl+Shift+B to toggle BCC
            if ((e.ctrlKey || e.metaKey) && e.shiftKey && e.key === 'B') {
                e.preventDefault();
                GmailComposeWizard.toggleBccField(wizardContainer);
            }
            
            // Escape to close (if supported)
            if (e.key === 'Escape') {
                const cancelButton = wizardContainer.querySelector('.gmail_cancel_btn');
                if (cancelButton && e.target.tagName !== 'INPUT' && e.target.tagName !== 'TEXTAREA') {
                    e.preventDefault();
                    cancelButton.click();
                }
            }
        });
    }
    
    static adjustWizardHeight(wizardContainer) {
        // Adjust wizard height based on content
        if (!wizardContainer) return;
        
        const modal = wizardContainer.querySelector('.modal-dialog');
        if (modal) {
            // Set fixed height for consistency
            modal.style.height = '600px';
            modal.style.maxHeight = '600px';
            
            // Adjust for screen size
            const screenHeight = window.innerHeight;
            if (screenHeight < 700) {
                modal.style.height = `${screenHeight - 100}px`;
                modal.style.maxHeight = `${screenHeight - 100}px`;
            }
        }
    }
    
    static enhanceMessageBody(wizardContainer = null) {
        const container = wizardContainer || document.querySelector('.gmail_compose_wizard');
        if (!container) return;
        
        // Enhance the message body editor within wizard
        const messageBody = container.querySelector('.gmail_message_body');
        if (messageBody) {
            // Auto-resize functionality
            const editor = messageBody.querySelector('.note-editable, textarea');
            if (editor) {
                editor.addEventListener('input', function() {
                    GmailComposeWizard.adjustEditorHeight(this);
                });
            }
        }
    }
    
    static adjustEditorHeight(editor) {
        // Auto-adjust editor height based on content
        if (editor.scrollHeight > editor.clientHeight) {
            const container = editor.closest('.gmail_message_body');
            if (container && container.scrollHeight < 500) {
                editor.style.height = 'auto';
                editor.style.height = editor.scrollHeight + 'px';
            }
        }
    }
    
    static validateEmailAddresses(wizardContainer = null) {
        const container = wizardContainer || document.querySelector('.gmail_compose_wizard');
        if (!container) return;
        
        // Validate email addresses in real-time within wizard
        const emailFields = container.querySelectorAll(
            'input[name="to_emails"], input[name="cc_emails"], input[name="bcc_emails"]'
        );
        
        emailFields.forEach(field => {
            field.addEventListener('blur', function() {
                GmailComposeWizard.validateEmailField(this);
            });
        });
    }
    
    static validateEmailField(field) {
        const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        const value = field.value.trim();
        
        if (value) {
            const emails = value.split(',').map(email => email.trim());
            const invalidEmails = emails.filter(email => email && !emailRegex.test(email));
            
            if (invalidEmails.length > 0) {
                field.style.borderColor = '#d93025';
                field.style.backgroundColor = '#fce8e6';
                field.title = `Invalid email addresses: ${invalidEmails.join(', ')}`;
            } else {
                field.style.borderColor = '';
                field.style.backgroundColor = '';
                field.title = '';
            }
        }
    }
    
    static initializeEmailSuggestions(wizardContainer = null) {
        const container = wizardContainer || document.querySelector('.gmail_compose_wizard');
        if (!container) return;
        
        // Initialize email address suggestions (future enhancement) within wizard
        const emailFields = container.querySelectorAll(
            'input[name="to_emails"], input[name="cc_emails"], input[name="bcc_emails"]'
        );
        
        emailFields.forEach(field => {
            field.addEventListener('input', function(e) {
                // Future: implement email suggestions from contacts
                console.log('Email suggestion feature - to be implemented');
            });
        });
    }
    
    static handleWindowResize() {
        // Handle window resize only for existing wizards
        const wizardContainer = document.querySelector('.gmail_compose_wizard');
        if (wizardContainer) {
            GmailComposeWizard.adjustWizardHeight(wizardContainer);
        }
    }
}

// Patch the FormController to initialize Gmail compose functionality
patch(FormController.prototype, {
    setup() {
        super.setup();
        
        // Check if this is a Gmail compose wizard
        if (this.props.resModel === 'gmail.send.mail') {
            this.isGmailCompose = true;
        }
    },
    
    async willStart() {
        const result = await super.willStart();
        
        if (this.isGmailCompose) {
            // Initialize Gmail compose functionality after a short delay
            setTimeout(() => {
                const wizardContainer = document.querySelector('.gmail_compose_wizard');
                if (wizardContainer) {
                    GmailComposeWizard.initializeGmailCompose();
                    GmailComposeWizard.enhanceMessageBody(wizardContainer);
                    GmailComposeWizard.validateEmailAddresses(wizardContainer);
                    GmailComposeWizard.initializeEmailSuggestions(wizardContainer);
                }
            }, 300);
        }
        
        return result;
    },
    
    onRendered() {
        super.onRendered();
        
        if (this.isGmailCompose) {
            // Re-initialize functionality after re-render
            setTimeout(() => {
                const wizardContainer = document.querySelector('.gmail_compose_wizard');
                if (wizardContainer) {
                    GmailComposeWizard.initializeGmailCompose();
                }
            }, 100);
        }
    }
});

// Global functions for template usage (scoped)
window.toggleCcField = () => {
    const wizardContainer = document.querySelector('.gmail_compose_wizard');
    if (wizardContainer) {
        GmailComposeWizard.toggleCcField(wizardContainer);
    }
};

window.toggleBccField = () => {
    const wizardContainer = document.querySelector('.gmail_compose_wizard');
    if (wizardContainer) {
        GmailComposeWizard.toggleBccField(wizardContainer);
    }
};

window.addAttachment = () => {
    const wizardContainer = document.querySelector('.gmail_compose_wizard');
    if (wizardContainer) {
        GmailComposeWizard.addAttachment(wizardContainer);
    }
};

// Initialize on DOM ready (scoped)
document.addEventListener('DOMContentLoaded', function() {
    // Wait for potential dynamic content
    setTimeout(() => {
        const wizardContainer = document.querySelector('.gmail_compose_wizard');
        if (wizardContainer) {
            GmailComposeWizard.initializeGmailCompose();
        }
    }, 500);
});

// Handle window resize (scoped)
window.addEventListener('resize', GmailComposeWizard.handleWindowResize);

export { GmailComposeWizard };
