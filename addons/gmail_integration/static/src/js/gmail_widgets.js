/* Gmail Integration Module JavaScript - Properly Scoped Version */

odoo.define('gmail_integration.widgets', [
    'web.AbstractField',
    'web.field_registry', 
    'web.core',
    'web.Dialog',
    'web.rpc',
    'web.session'
], function (require) {
'use strict';

const AbstractField = require('web.AbstractField');
const fieldRegistry = require('web.field_registry');
const core = require('web.core');
const Dialog = require('web.Dialog');
const rpc = require('web.rpc');
const session = require('web.session');

const _t = core._t;

/**
 * Gmail Status Widget - Scoped to gmail_integration module
 * Shows Gmail account connection status with color indicators
 */
const GmailStatusWidget = AbstractField.extend({
    className: 'gmail_integration_module gmail_status_widget',
    
    init: function () {
        this._super.apply(this, arguments);
        this.statusClasses = {
            'connected': 'gmail-status-connected',
            'error': 'gmail-status-error',
            'connecting': 'gmail-status-connecting',
            'draft': 'gmail-status-draft'
        };
    },
    
    _render: function () {
        const value = this.value || 'draft';
        const statusClass = this.statusClasses[value] || 'gmail-status-draft';
        const statusText = this._getStatusText(value);
        
        this.$el.empty().append(
            $('<span>')
                .addClass('gmail_integration_module ' + statusClass)
                .text(statusText)
        );
    },
    
    _getStatusText: function (status) {
        const statusTexts = {
            'connected': _t('Connected'),
            'error': _t('Error'),
            'connecting': _t('Connecting'),
            'draft': _t('Not Connected')
        };
        return statusTexts[status] || _t('Unknown');
    }
});

/**
 * Gmail Quota Widget - Scoped to gmail_integration module
 * Displays Gmail API quota usage with progress bar
 */
const GmailQuotaWidget = AbstractField.extend({
    className: 'gmail_integration_module gmail_quota_widget',
    
    _render: function () {
        const percentage = this.value || 0;
        const quotaClass = this._getQuotaClass(percentage);
        
        const $container = $('<div>').addClass('gmail_integration_module gmail-quota-container');
        const $bar = $('<div>').addClass('gmail_integration_module gmail-quota-bar');
        const $fill = $('<div>')
            .addClass('gmail_integration_module gmail-quota-fill')
            .addClass(quotaClass)
            .css('width', Math.min(percentage, 100) + '%');
        const $text = $('<div>')
            .addClass('gmail_integration_module gmail-quota-text')
            .text(percentage.toFixed(1) + '% used');
        
        $bar.append($fill);
        $container.append($bar, $text);
        this.$el.empty().append($container);
    },
    
    _getQuotaClass: function (percentage) {
        if (percentage < 70) return 'quota-normal';
        if (percentage < 90) return 'quota-warning';
        return 'quota-critical';
    }
});

/**
 * Gmail Message Count Widget - Scoped to gmail_integration module
 * Displays message count with formatting
 */
const GmailMessageCountWidget = AbstractField.extend({
    className: 'gmail_integration_module gmail_message_count_widget',
    
    _render: function () {
        const count = this.value || 0;
        const formattedCount = this._formatCount(count);
        
        this.$el.empty().append(
            $('<span>')
                .addClass('gmail_integration_module gmail-message-count')
                .text(formattedCount)
        );
    },
    
    _formatCount: function (count) {
        if (count < 1000) return count.toString();
        if (count < 1000000) return (count / 1000).toFixed(1) + 'K';
        return (count / 1000000).toFixed(1) + 'M';
    }
});

/**
 * Gmail Sync Progress Widget - Scoped to gmail_integration module
 * Shows sync progress with animated progress bar
 */
const GmailSyncProgressWidget = AbstractField.extend({
    className: 'gmail_integration_module gmail_sync_progress_widget',
    
    _render: function () {
        const progress = Math.max(0, Math.min(100, this.value || 0));
        
        const $container = $('<div>').addClass('gmail_integration_module gmail-progress-container');
        const $bar = $('<div>')
            .addClass('gmail_integration_module gmail-progress-bar')
            .css('width', progress + '%');
        const $text = $('<span>')
            .addClass('gmail_integration_module gmail-progress-text')
            .text(progress.toFixed(0) + '%');
        
        $bar.append($text);
        $container.append($bar);
        this.$el.empty().append($container);
    }
});

/**
 * Gmail Connection Test Widget - Scoped to gmail_integration module
 * Provides interactive connection testing
 */
const GmailConnectionTestWidget = AbstractField.extend({
    className: 'gmail_integration_module gmail_connection_test_widget',
    events: {
        'click .gmail-test-connection': '_onTestConnection'
    },
    
    _render: function () {
        const $button = $('<button>')
            .addClass('gmail_integration_module btn btn-secondary gmail-test-connection')
            .text(_t('Test Connection'));
        
        const $status = $('<div>')
            .addClass('gmail_integration_module gmail-connection-status mt-2')
            .hide();
        
        this.$el.empty().append($button, $status);
    },
    
    _onTestConnection: function () {
        const $button = this.$('.gmail-test-connection');
        const $status = this.$('.gmail-connection-status');
        
        $button.prop('disabled', true).html(
            '<i class="fa fa-spinner fa-spin"></i> ' + _t('Testing...')
        );
        
        $status.hide();
        
        rpc.query({
            route: '/gmail/auth/test',
            params: {
                account_id: this.res_id
            }
        }).then(function(result) {
            $button.prop('disabled', false).text(_t('Test Connection'));
            
            if (result.success) {
                $status
                    .removeClass('alert-danger')
                    .addClass('gmail_integration_module alert alert-success')
                    .html('<i class="fa fa-check"></i> ' + result.message)
                    .show();
            } else {
                $status
                    .removeClass('alert-success')
                    .addClass('gmail_integration_module alert alert-danger')
                    .html('<i class="fa fa-times"></i> ' + result.error)
                    .show();
            }
        }).catch(function(error) {
            $button.prop('disabled', false).text(_t('Test Connection'));
            $status
                .removeClass('alert-success')
                .addClass('gmail_integration_module alert alert-danger')
                .html('<i class="fa fa-times"></i> ' + _t('Connection test failed'))
                .show();
        });
    }
});

/**
 * Gmail Email Preview Widget - Scoped to gmail_integration module
 * Shows email content preview with HTML rendering
 */
const GmailEmailPreviewWidget = AbstractField.extend({
    className: 'gmail_integration_module gmail_email_preview_widget',
    
    _render: function () {
        const content = this.value || '';
        
        const $container = $('<div>').addClass('gmail_integration_module gmail-email-preview');
        const $frame = $('<iframe>')
            .addClass('gmail_integration_module gmail-preview-frame')
            .attr({
                'frameborder': '0',
                'width': '100%',
                'height': '400px'
            });
        
        $container.append($frame);
        this.$el.empty().append($container);
        
        // Set iframe content safely with scoped styles
        const iframe = $frame[0];
        const doc = iframe.contentDocument || iframe.contentWindow.document;
        doc.open();
        doc.write(
            '<html>' +
            '<head>' +
                '<meta charset="UTF-8">' +
                '<style>' +
                    '/* Scoped styles for Gmail Integration iframe */' +
                    '.gmail_integration_preview_content { ' +
                        'font-family: Arial, sans-serif; ' +
                        'padding: 20px; ' +
                        'margin: 0;' +
                        'background: #f8f9fa;' +
                    '}' +
                    '.gmail_integration_email_content {' +
                        'background: white;' +
                        'padding: 20px;' +
                        'border-radius: 8px;' +
                        'box-shadow: 0 2px 10px rgba(0,0,0,0.1);' +
                    '}' +
                '</style>' +
            '</head>' +
            '<body class="gmail_integration_preview_content">' +
                '<div class="gmail_integration_email_content">' +
                    content +
                '</div>' +
            '</body>' +
            '</html>'
        );
        doc.close();
    }
});

/**
 * Gmail Template Variables Widget - Scoped to gmail_integration module
 * Interactive widget for template variable management
 */
const GmailTemplateVariablesWidget = AbstractField.extend({
    className: 'gmail_integration_module gmail_template_variables_widget',
    events: {
        'click .gmail-add-variable': '_onAddVariable',
        'click .gmail-remove-variable': '_onRemoveVariable',
        'change .gmail-variable-input': '_onVariableChange'
    },
    
    init: function () {
        this._super.apply(this, arguments);
        this.variables = [];
    },
    
    _render: function () {
        this.variables = this.value || [];
        
        const $container = $('<div>').addClass('gmail_integration_module gmail-variables-container');
        const $header = $('<div>')
            .addClass('gmail_integration_module gmail-variables-header')
            .append(
                $('<h4>').addClass('gmail_integration_module').text(_t('Template Variables')),
                $('<button>')
                    .addClass('gmail_integration_module btn btn-sm btn-primary gmail-add-variable')
                    .text(_t('Add Variable'))
            );
        
        const $list = $('<div>').addClass('gmail_integration_module gmail-variables-list');
        
        const self = this;
        this.variables.forEach(function(variable, index) {
            $list.append(self._renderVariable(variable, index));
        });
        
        $container.append($header, $list);
        this.$el.empty().append($container);
    },
    
    _renderVariable: function (variable, index) {
        const $item = $('<div>')
            .addClass('gmail_integration_module gmail-variable-item')
            .data('index', index);
        
        const $nameInput = $('<input>')
            .addClass('gmail_integration_module form-control gmail-variable-input')
            .attr({
                'type': 'text',
                'placeholder': _t('Variable Name'),
                'data-field': 'name'
            })
            .val(variable.name || '');
        
        const $valueInput = $('<input>')
            .addClass('gmail_integration_module form-control gmail-variable-input')
            .attr({
                'type': 'text',
                'placeholder': _t('Default Value'),
                'data-field': 'value'
            })
            .val(variable.value || '');
        
        const $removeBtn = $('<button>')
            .addClass('gmail_integration_module btn btn-sm btn-danger gmail-remove-variable')
            .html('<i class="fa fa-trash"></i>');
        
        $item.append(
            $('<div>').addClass('gmail_integration_module row').append(
                $('<div>').addClass('gmail_integration_module col-md-4').append($nameInput),
                $('<div>').addClass('gmail_integration_module col-md-6').append($valueInput),
                $('<div>').addClass('gmail_integration_module col-md-2').append($removeBtn)
            )
        );
        
        return $item;
    },
    
    _onAddVariable: function () {
        this.variables.push({ name: '', value: '' });
        this._render();
        this._updateValue();
    },
    
    _onRemoveVariable: function (ev) {
        const index = $(ev.currentTarget).closest('.gmail-variable-item').data('index');
        this.variables.splice(index, 1);
        this._render();
        this._updateValue();
    },
    
    _onVariableChange: function (ev) {
        const $input = $(ev.currentTarget);
        const index = $input.closest('.gmail-variable-item').data('index');
        const field = $input.data('field');
        
        if (this.variables[index]) {
            this.variables[index][field] = $input.val();
            this._updateValue();
        }
    },
    
    _updateValue: function () {
        this._setValue(this.variables);
    }
});

// Register all widgets with gmail_integration namespace
fieldRegistry.add('gmail_integration_status', GmailStatusWidget);
fieldRegistry.add('gmail_integration_quota', GmailQuotaWidget);
fieldRegistry.add('gmail_integration_message_count', GmailMessageCountWidget);
fieldRegistry.add('gmail_integration_sync_progress', GmailSyncProgressWidget);
fieldRegistry.add('gmail_integration_connection_test', GmailConnectionTestWidget);
fieldRegistry.add('gmail_integration_email_preview', GmailEmailPreviewWidget);
fieldRegistry.add('gmail_integration_template_variables', GmailTemplateVariablesWidget);

/**
 * Gmail Integration Utilities - Namespaced
 * Helper functions for Gmail integration
 */
const GmailIntegrationUtils = {
    
    /**
     * Format email address for display
     */
    formatEmailAddress: function (email, name) {
        if (name && name !== email) {
            return name + ' <' + email + '>';
        }
        return email;
    },
    
    /**
     * Validate email address format
     */
    isValidEmail: function (email) {
        const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        return emailRegex.test(email);
    },
    
    /**
     * Parse multiple email addresses
     */
    parseEmailList: function (emailString) {
        if (!emailString) return [];
        
        const self = this;
        return emailString
            .split(',')
            .map(function(email) { return email.trim(); })
            .filter(function(email) { return email && self.isValidEmail(email); });
    },
    
    /**
     * Format file size
     */
    formatFileSize: function (bytes) {
        if (bytes === 0) return '0 B';
        
        const k = 1024;
        const sizes = ['B', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        
        return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
    }
};

// Export for use in other modules with proper namespacing
return {
    GmailStatusWidget: GmailStatusWidget,
    GmailQuotaWidget: GmailQuotaWidget,
    GmailMessageCountWidget: GmailMessageCountWidget,
    GmailSyncProgressWidget: GmailSyncProgressWidget,
    GmailConnectionTestWidget: GmailConnectionTestWidget,
    GmailEmailPreviewWidget: GmailEmailPreviewWidget,
    GmailTemplateVariablesWidget: GmailTemplateVariablesWidget,
    GmailIntegrationUtils: GmailIntegrationUtils
};

});
