/** @odoo-module **/
/**
 * Gmail Integration System Check - Updated for Integrated Model
 * 
 * This module is scoped to gmail_integration only and works with the new
 * gmail.configuration model instead of res.config.settings.
 */

// Create scoped namespace for Gmail Integration
const GmailIntegration = {
    namespace: 'gmail_integration',
    version: '2.0.0',
    
    // Configuration
    config: {
        checkInterval: 5 * 60 * 1000, // 5 minutes
        autoCheck: true,
        showNotifications: true,
        model: 'gmail.configuration', // Updated model name
    },

    // State management
    state: {
        isConfigured: false,
        isChecking: false,
        lastCheck: null,
        activeConfig: null,
        configId: null,
    },

    // Services (will be injected)
    services: {
        orm: null,
        notification: null,
        action: null,
    },

    /**
     * Initialize the Gmail system check (scoped to gmail views only)
     */
    init: function() {
        // Only initialize in Gmail-related contexts
        if (!this.isGmailContext()) {
            return;
        }

        console.log('[Gmail Integration v2.0] System check initialized');
        this.bindEvents();
        this.checkConfiguration();
        
        if (this.config.autoCheck) {
            this.startAutoCheck();
        }
    },

    /**
     * Check if current context is Gmail-related
     */
    isGmailContext: function() {
        const url = window.location.href;
        const action = window.odoo?.__WOWL_DEBUG__?.env?.services?.action?.currentController?.action;
        
        // Check URL patterns
        const gmailUrlPatterns = [
            '/web#.*gmail',
            '/gmail/',
            'model=gmail\\.',
            'action.*gmail',
            'gmail.configuration',
            'gmail_integration'
        ];
        
        const urlMatch = gmailUrlPatterns.some(pattern => 
            new RegExp(pattern, 'i').test(url)
        );
        
        // Check action context
        const actionMatch = action && (
            (action.res_model && action.res_model.startsWith('gmail.')) ||
            (action.xml_id && action.xml_id.includes('gmail_integration')) ||
            (action.name && action.name.toLowerCase().includes('gmail'))
        );
        
        return urlMatch || actionMatch;
    },

    /**
     * Bind events (scoped to Gmail elements only)
     */
    bindEvents: function() {
        // Only bind to elements with gmail-integration class
        document.addEventListener('click', (event) => {
            const target = event.target.closest('.gmail-integration, .gmail_oauth_config, .gmail_account_form');
            if (!target) return;
            
            // Handle Gmail-specific events
            if (target.hasAttribute('data-gmail-action')) {
                this.handleGmailAction(target, event);
            }
        });

        // Listen for Gmail form changes (updated field names)
        document.addEventListener('input', (event) => {
            const target = event.target;
            if (!target.closest('.gmail-integration')) return;
            
            // Updated field names to match new model
            if (target.name === 'client_id') {
                this.validateClientId(target.value);
            } else if (target.name === 'client_secret') {
                this.validateClientSecret(target.value);
            } else if (target.name === 'oauth_enabled') {
                this.onOAuthEnabledChange(target.checked);
            }
        });

        // Listen for configuration save events
        document.addEventListener('gmail-config-saved', (event) => {
            this.onConfigurationSaved(event.detail);
        });
    },

    /**
     * Handle OAuth enabled change
     */
    onOAuthEnabledChange: function(enabled) {
        const configForm = document.querySelector('.gmail_oauth_config');
        if (configForm) {
            configForm.classList.toggle('oauth-enabled', enabled);
            configForm.classList.toggle('oauth-disabled', !enabled);
        }
        
        // Show appropriate message
        if (enabled) {
            this.showNotification('OAuth enabled. Please configure Client ID and Secret.', 'info');
        } else {
            this.showNotification('OAuth disabled. Users cannot connect Gmail accounts.', 'warning');
        }
    },

    /**
     * Handle Gmail-specific actions
     */
    handleGmailAction: function(element, event) {
        const action = element.getAttribute('data-gmail-action');
        
        switch (action) {
            case 'test-config':
                event.preventDefault();
                this.testConfiguration();
                break;
            case 'refresh-status':
                event.preventDefault();
                this.checkConfiguration();
                break;
            case 'save-apply':
                event.preventDefault();
                this.saveAndApplyConfiguration();
                break;
            case 'reset-config':
                event.preventDefault();
                this.resetConfiguration();
                break;
            case 'open-guide':
                this.openSetupGuide();
                break;
            case 'migrate-config':
                event.preventDefault();
                this.migrateConfiguration();
                break;
        }
    },

    /**
     * Check Gmail OAuth configuration status (updated for new model)
     */
    checkConfiguration: async function() {
        if (!this.isGmailContext()) {
            return;
        }

        this.state.isChecking = true;
        this.updateStatusIndicators();

        try {
            // Use new gmail.configuration model
            const result = await this.scopedRPC('gmail.configuration', 'is_gmail_oauth_configured');
            const config = await this.scopedRPC('gmail.configuration', 'get_gmail_oauth_config');
            const activeConfig = await this.scopedRPC('gmail.configuration', 'get_active_config');

            this.state.isConfigured = result;
            this.state.activeConfig = config;
            this.state.configId = activeConfig ? activeConfig.id : null;
            this.state.lastCheck = new Date();

            this.updateUI();
            
            if (!result && this.config.showNotifications) {
                this.showConfigurationWarning();
            }

        } catch (error) {
            console.error('[Gmail Integration] Configuration check failed:', error);
            this.showError('Failed to check Gmail configuration');
        } finally {
            this.state.isChecking = false;
            this.updateStatusIndicators();
        }
    },

    /**
     * Scoped RPC call (updated for new model)
     */
    scopedRPC: async function(model, method, args = [], kwargs = {}) {
        // Ensure we only call Gmail-related models
        if (!model.startsWith('gmail.')) {
            throw new Error('[Gmail Integration] Unauthorized model access: ' + model);
        }

        try {
            // Use Odoo's RPC mechanism
            const rpcData = {
                model: model,
                method: method,
                args: args,
                kwargs: kwargs,
            };

            // Try different RPC endpoints based on Odoo version
            const rpcEndpoints = [
                '/web/dataset/call_kw',
                '/web/dataset/call_kw_model'
            ];

            for (const endpoint of rpcEndpoints) {
                try {
                    const response = await fetch(endpoint, {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                        },
                        body: JSON.stringify({
                            jsonrpc: '2.0',
                            method: 'call',
                            params: rpcData,
                            id: Math.floor(Math.random() * 1000000),
                        }),
                    });

                    if (response.ok) {
                        const data = await response.json();
                        if (data.error) {
                            throw new Error(data.error.message || 'RPC Error');
                        }
                        return data.result;
                    }
                } catch (endpointError) {
                    console.warn(`RPC endpoint ${endpoint} failed:`, endpointError);
                    continue;
                }
            }

            throw new Error('All RPC endpoints failed');

        } catch (error) {
            console.error(`[Gmail Integration] RPC call failed: ${model}.${method}`, error);
            throw error;
        }
    },

    /**
     * Validate Client ID format (updated field name)
     */
    validateClientId: function(clientId) {
        const isValid = clientId && clientId.endsWith('.apps.googleusercontent.com');
        this.updateFieldValidation('client_id', isValid, 
            isValid ? 'Valid Client ID format' : 'Client ID should end with .apps.googleusercontent.com'
        );
        return isValid;
    },

    /**
     * Validate Client Secret format (updated field name)
     */
    validateClientSecret: function(clientSecret) {
        const isValid = clientSecret && clientSecret.length >= 20;
        this.updateFieldValidation('client_secret', isValid,
            isValid ? 'Valid Client Secret length' : 'Client Secret appears to be too short'
        );
        return isValid;
    },

    /**
     * Update field validation (updated for new form structure)
     */
    updateFieldValidation: function(fieldName, isValid, message) {
        // Only update fields within Gmail integration forms
        const gmailForm = document.querySelector('.gmail-integration, .gmail_oauth_config');
        if (!gmailForm) return;

        const field = gmailForm.querySelector(`[name="${fieldName}"]`);
        if (!field) return;

        // Update field styling
        field.classList.remove('gmail-valid', 'gmail-invalid');
        field.classList.add(isValid ? 'gmail-valid' : 'gmail-invalid');

        // Update or create validation message
        let messageEl = field.parentElement.querySelector('.gmail-validation-message');
        if (!messageEl) {
            messageEl = document.createElement('div');
            messageEl.className = 'gmail-validation-message';
            field.parentElement.appendChild(messageEl);
        }
        
        messageEl.textContent = message;
        messageEl.className = `gmail-validation-message ${isValid ? 'gmail-success' : 'gmail-error'}`;
    },

    /**
     * Update UI elements (updated for new model)
     */
    updateUI: function() {
        // Update status indicators in Gmail views only
        const statusElements = document.querySelectorAll('.gmail-status-indicator');
        statusElements.forEach(el => {
            const status = this.state.isConfigured ? 'configured' : 'not-configured';
            el.setAttribute('data-gmail-status', status);
            el.textContent = this.getStatusText();
        });

        // Update configuration panels
        const configPanels = document.querySelectorAll('.gmail-config-panel');
        configPanels.forEach(panel => {
            panel.classList.toggle('gmail-configured', this.state.isConfigured);
        });

        // Update configuration form status
        const configForm = document.querySelector('.gmail_oauth_config');
        if (configForm) {
            configForm.setAttribute('data-config-status', this.state.isConfigured ? 'configured' : 'not-configured');
        }
    },

    /**
     * Test configuration (updated for new model)
     */
    testConfiguration: async function() {
        if (!this.isGmailContext() || !this.state.configId) {
            return;
        }

        try {
            this.showNotification('Testing Gmail configuration...', 'info');
            
            const result = await this.scopedRPC('gmail.configuration', 'action_test_oauth_config', [this.state.configId]);
            
            // Handle the result based on its structure
            if (result && result.params) {
                this.showNotification(
                    result.params.message,
                    result.params.type === 'success' ? 'success' : 'error',
                    result.params.title
                );
            } else {
                this.showNotification('Configuration test completed', 'success');
            }
            
            // Refresh configuration status
            setTimeout(() => this.checkConfiguration(), 1000);
            
        } catch (error) {
            this.showError('Configuration test failed: ' + error.message);
        }
    },

    /**
     * Save and apply configuration
     */
    saveAndApplyConfiguration: async function() {
        if (!this.state.configId) return;

        try {
            this.showNotification('Saving configuration...', 'info');
            
            const result = await this.scopedRPC('gmail.configuration', 'action_save_and_apply', [this.state.configId]);
            
            if (result && result.params) {
                this.showNotification(result.params.message, 'success', result.params.title);
            }
            
            // Trigger configuration saved event
            document.dispatchEvent(new CustomEvent('gmail-config-saved', {
                detail: { configId: this.state.configId }
            }));
            
            // Refresh status
            setTimeout(() => this.checkConfiguration(), 1000);
            
        } catch (error) {
            this.showError('Failed to save configuration: ' + error.message);
        }
    },

    /**
     * Reset configuration
     */
    resetConfiguration: async function() {
        if (!this.state.configId) return;

        if (!confirm('Are you sure you want to reset the Gmail configuration? This will disconnect all accounts.')) {
            return;
        }

        try {
            this.showNotification('Resetting configuration...', 'warning');
            
            const result = await this.scopedRPC('gmail.configuration', 'action_reset_oauth_config', [this.state.configId]);
            
            if (result && result.params) {
                this.showNotification(result.params.message, 'warning', result.params.title);
            }
            
            // Refresh status
            setTimeout(() => this.checkConfiguration(), 1000);
            
        } catch (error) {
            this.showError('Failed to reset configuration: ' + error.message);
        }
    },

    /**
     * Migrate configuration from old model
     */
    migrateConfiguration: async function() {
        try {
            this.showNotification('Migrating configuration from old settings...', 'info');
            
            await this.scopedRPC('gmail.configuration', 'migrate_from_res_config_settings');
            
            this.showNotification('Configuration migrated successfully!', 'success');
            
            // Refresh status
            setTimeout(() => this.checkConfiguration(), 1000);
            
        } catch (error) {
            this.showError('Migration failed: ' + error.message);
        }
    },

    /**
     * Handle configuration saved event
     */
    onConfigurationSaved: function(detail) {
        console.log('[Gmail Integration] Configuration saved:', detail);
        this.checkConfiguration();
    },

    /**
     * Show configuration warning (updated message)
     */
    showConfigurationWarning: function() {
        this.showNotification(
            'Gmail OAuth is not configured in the new Gmail Settings. Please ask your administrator to set up Gmail integration.',
            'warning',
            'Gmail Configuration Required'
        );
    },

    /**
     * Show scoped notification (enhanced)
     */
    showNotification: function(message, type = 'info', title = '') {
        // Only show notifications in Gmail context
        if (!this.isGmailContext()) {
            return;
        }

        // Create notification element scoped to Gmail
        const notification = document.createElement('div');
        notification.className = `gmail-notification gmail-notification-${type}`;
        notification.innerHTML = `
            <div class="gmail-notification-content">
                ${title ? `<strong>${title}</strong><br/>` : ''}
                ${message}
                <button class="gmail-notification-close" onclick="this.parentElement.parentElement.remove()">×</button>
            </div>
        `;

        // Add to Gmail container only
        const gmailContainer = document.querySelector('.gmail-integration') || 
                              document.querySelector('.gmail_oauth_config') ||
                              document.querySelector('.o_action_manager');
        
        if (gmailContainer) {
            gmailContainer.appendChild(notification);
            
            // Auto-remove after 5 seconds
            setTimeout(() => {
                if (notification.parentElement) {
                    notification.remove();
                }
            }, 5000);
        }
    },

    /**
     * Show error message (scoped)
     */
    showError: function(message) {
        this.showNotification(message, 'error', 'Gmail Integration Error');
    },

    /**
     * Get human-readable status text (updated)
     */
    getStatusText: function() {
        if (this.state.isChecking) {
            return 'Checking Gmail configuration...';
        }
        return this.state.isConfigured ? 
            'Gmail integration is configured' : 
            'Gmail OAuth configuration required';
    },

    /**
     * Update loading indicators (scoped)
     */
    updateStatusIndicators: function() {
        const indicators = document.querySelectorAll('.gmail-loading-indicator');
        indicators.forEach(indicator => {
            indicator.classList.toggle('gmail-checking', this.state.isChecking);
        });
    },

    /**
     * Open setup guide
     */
    openSetupGuide: function() {
        window.open('https://console.cloud.google.com/apis/credentials', '_blank');
    },

    /**
     * Start automatic checking (scoped interval)
     */
    startAutoCheck: function() {
        if (!this.isGmailContext()) {
            return;
        }

        // Clear any existing intervals for this namespace
        if (this.autoCheckInterval) {
            clearInterval(this.autoCheckInterval);
        }

        this.autoCheckInterval = setInterval(() => {
            // Only continue if still in Gmail context
            if (this.isGmailContext()) {
                this.checkConfiguration();
            } else {
                this.stopAutoCheck();
            }
        }, this.config.checkInterval);
    },

    /**
     * Stop automatic checking
     */
    stopAutoCheck: function() {
        if (this.autoCheckInterval) {
            clearInterval(this.autoCheckInterval);
            this.autoCheckInterval = null;
        }
    },

    /**
     * Cleanup when leaving Gmail context
     */
    cleanup: function() {
        this.stopAutoCheck();
        
        // Remove Gmail-specific event listeners
        const gmailElements = document.querySelectorAll('.gmail-notification');
        gmailElements.forEach(el => el.remove());
        
        console.log('[Gmail Integration v2.0] System check cleaned up');
    }
};

// Initialize only when DOM is ready and in Gmail context
document.addEventListener('DOMContentLoaded', function() {
    // Wait for Odoo to be fully loaded
    const initGmail = () => {
        if (GmailIntegration.isGmailContext()) {
            GmailIntegration.init();
        }
    };

    if (window.odoo) {
        initGmail();
    } else {
        // Wait for Odoo to load
        const checkOdoo = setInterval(() => {
            if (window.odoo) {
                clearInterval(checkOdoo);
                initGmail();
            }
        }, 100);
    }
});

// Cleanup when navigating away from Gmail
window.addEventListener('beforeunload', function() {
    GmailIntegration.cleanup();
});

// Handle SPA navigation in Odoo
document.addEventListener('DOMContentLoaded', function() {
    // Listen for Odoo route changes
    let currentUrl = window.location.href;
    setInterval(() => {
        if (window.location.href !== currentUrl) {
            currentUrl = window.location.href;
            
            if (GmailIntegration.isGmailContext()) {
                GmailIntegration.init();
            } else {
                GmailIntegration.cleanup();
            }
        }
    }, 1000);
});

// Expose only to Gmail Integration namespace (no global pollution)
window.GmailIntegration = GmailIntegration;
