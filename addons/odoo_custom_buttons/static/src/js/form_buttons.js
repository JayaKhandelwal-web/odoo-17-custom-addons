/** @odoo-module **/

/**
 * Universal Custom Buttons - JavaScript
 * Adds additional functionality to custom form buttons
 */

import { FormController } from "@web/views/form/form_controller";
import { patch } from "@web/core/utils/patch";

// Patch the FormController to add custom button handlers
patch(FormController.prototype, {
    
    /**
     * Setup method - called when the controller is initialized
     */
    setup() {
        super.setup(...arguments);
        console.log('Custom buttons module loaded successfully');
    },

    /**
     * Add custom class to form view for styling purposes
     */
    get className() {
        return `${super.className || ''} o_form_with_custom_buttons`;
    },
});

// Add event listeners for keyboard shortcuts (optional)
document.addEventListener('DOMContentLoaded', function() {
    
    // Optional: Add keyboard shortcuts
    // Ctrl+S or Cmd+S for Save
    document.addEventListener('keydown', function(e) {
        // Save shortcut: Ctrl+S or Cmd+S
        if ((e.ctrlKey || e.metaKey) && e.key === 's') {
            const saveButton = document.querySelector('.o_form_button_save');
            if (saveButton && !saveButton.disabled) {
                e.preventDefault();
                saveButton.click();
            }
        }
        
        // Back shortcut: Escape key
        if (e.key === 'Escape') {
            const backButton = document.querySelector('.o_form_button_back');
            if (backButton && !backButton.disabled) {
                // Only trigger if not in a modal or focused input
                if (!document.querySelector('.modal.show') && 
                    document.activeElement.tagName !== 'INPUT' && 
                    document.activeElement.tagName !== 'TEXTAREA') {
                    backButton.click();
                }
            }
        }
    });

    console.log('Custom buttons keyboard shortcuts enabled');
});

/**
 * Utility function to show loading state on buttons
 */
export function setButtonLoading(buttonElement, isLoading) {
    if (isLoading) {
        buttonElement.classList.add('loading');
        buttonElement.disabled = true;
    } else {
        buttonElement.classList.remove('loading');
        buttonElement.disabled = false;
    }
}

/**
 * Utility function to show success feedback
 */
export function showButtonSuccess(buttonElement) {
    const originalHTML = buttonElement.innerHTML;
    buttonElement.innerHTML = '<i class="fa fa-check"></i> SUCCESS';
    buttonElement.style.pointerEvents = 'none';
    
    setTimeout(() => {
        buttonElement.innerHTML = originalHTML;
        buttonElement.style.pointerEvents = 'auto';
    }, 2000);
}
