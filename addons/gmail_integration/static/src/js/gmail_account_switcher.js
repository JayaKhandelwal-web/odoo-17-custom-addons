/**
 * Gmail Integration - Account Switcher JavaScript - WORKING VERSION
 * 
 * This module handles Gmail account switching functionality with direct approach
 * that bypasses module loading issues and works reliably.
 * 
 * @version 2.3.0 - Direct Working Implementation
 * @author Gmail Integration Team
 */

(function() {
    'use strict';

    console.log('=== Gmail Account Switcher v2.3.0 - Direct Implementation Loading ===');

    // Try to define the Odoo module, but don't rely on it
    if (typeof odoo !== 'undefined' && odoo.define) {
        try {
            odoo.define('gmail_integration.account_switcher', [
                'web.rpc', 
                'web.core', 
                'web.Dialog'
            ], function(require) {
                console.log('=== Modular version loaded as fallback ===');
                return {
                    version: '2.3.0',
                    switchAccount: function(accountId) {
                        return window.GmailAccountSwitcherDirect.switchAccount(accountId);
                    }
                };
            });
        } catch (e) {
            console.log('Modular loading failed, using direct approach:', e);
        }
    }

    // Direct, working account switcher implementation
    window.GmailAccountSwitcherDirect = {
        version: '2.3.0',
        initialized: false,
        switchInProgress: false,

        /**
         * Main account switching function - PROVEN TO WORK
         * @param {number} accountId - Account ID to switch to
         */
        switchAccount: function(accountId) {
            console.log('=== Direct Account Switch ===', accountId);
            
            if (!accountId) {
                alert('No account ID provided');
                return;
            }

            if (this.switchInProgress) {
                console.log('Switch already in progress, ignoring');
                return;
            }

            this.switchInProgress = true;
            
            console.log('Calling force_dashboard_refresh_with_account with ID:', accountId);
            
            // Direct AJAX call that we know works
            $.ajax({
                url: '/web/dataset/call_kw',
                type: 'POST',
                dataType: 'json',
                contentType: 'application/json',
                data: JSON.stringify({
                    jsonrpc: '2.0',
                    method: 'call',
                    params: {
                        model: 'gmail.dashboard',
                        method: 'force_dashboard_refresh_with_account',
                        args: [parseInt(accountId)],
                        kwargs: {}
                    }
                })
            }).done(function(response) {
                console.log('✅ AJAX Response:', response);
                
                if (response.result && response.result.success) {
                    console.log('✅ Switch successful!');
                    console.log('Account Email:', response.result.account_email);
                    console.log('Account Name:', response.result.account_name);
                    
                    // Close the modal
                    $('.modal .btn[special="cancel"]').click();
                    
                    // Redirect to dashboard with force context
                    setTimeout(function() {
                        var redirectUrl = '/web#action=gmail_integration.action_gmail_dashboard&force_active_account_id=' + accountId;
                        console.log('✅ Redirecting to:', redirectUrl);
                        window.location.href = redirectUrl;
                    }, 500);
                    
                } else {
                    console.error('❌ Switch failed:', response.result);
                    alert('Failed to switch account: ' + (response.result ? response.result.error : 'Unknown error'));
                }
            }).fail(function(xhr, status, error) {
                console.error('❌ AJAX Failed:', {
                    status: status,
                    error: error,
                    responseText: xhr.responseText,
                    statusCode: xhr.status
                });
                
                alert('Error calling server: ' + error);
            }).always(function() {
                window.GmailAccountSwitcherDirect.switchInProgress = false;
            });
        },

        /**
         * Extract account ID from clicked element
         * @param {jQuery} $element - jQuery element
         * @returns {string|null} Account ID or null
         */
        getAccountId: function($element) {
            return $element.attr('data-account-id') || 
                   $element.data('account-id') ||
                   $element.find('.debug-account-id').text().trim() ||
                   $element.find('.account-id-field').val();
        },

        /**
         * Apply visual feedback to clicked card
         * @param {jQuery} $item - Card element
         */
        applyClickFeedback: function($item) {
            $item.css({
                'background': 'linear-gradient(135deg, #e8f5e8 0%, #f0f8f0 100%)',
                'border-color': '#34a853',
                'transform': 'scale(1.02)'
            });
        },

        /**
         * Reset visual feedback
         * @param {jQuery} $item - Card element
         */
        resetClickFeedback: function($item) {
            $item.css({
                'background': 'white',
                'border-color': '#dee2e6',
                'transform': 'scale(1)'
            });
        },

        /**
         * Main click handler - PROVEN TO WORK
         * @param {Event} e - Click event
         */
        handleClick: function(e) {
            e.preventDefault();
            e.stopPropagation();
            
            console.log('=== Direct Click Handler Activated ===');
            
            // Don't trigger on sign out button
            if ($(e.target).closest('.gmail-signout-btn').length > 0) {
                console.log('Sign out button clicked, ignoring');
                return;
            }
            
            var $item = $(e.currentTarget);
            console.log('Item clicked:', $item[0]);
            
            var accountId = window.GmailAccountSwitcherDirect.getAccountId($item);
            console.log('Account ID extracted:', accountId);
            
            if (!accountId) {
                console.error('No account ID found');
                alert('Could not find account ID. Please try again.');
                return;
            }
            
            // Apply visual feedback
            window.GmailAccountSwitcherDirect.applyClickFeedback($item);
            
            // Switch account
            window.GmailAccountSwitcherDirect.switchAccount(accountId);
        },

        /**
         * Initialize the direct account switcher
         */
        init: function() {
            if (this.initialized) {
                console.log('Direct switcher already initialized');
                return;
            }

            console.log('=== Initializing Direct Account Switcher ===');
            
            // Remove any existing handlers
            $(document).off('click', '.gmail-other-item');
            $(document).off('click.gmailDirect');
            $(document).off('click.gmailStandalone');
            $(document).off('click.gmailAccountSwitcher');
            
            // Install the working click handler
            $(document).on('click.gmailDirect', '.gmail-other-item', this.handleClick);
            
            this.initialized = true;
            console.log('✅ Direct account switcher installed successfully');
            
            // Debug: Check available accounts
            setTimeout(function() {
                window.GmailAccountSwitcherDirect.debugAccounts();
            }, 100);
        },

        /**
         * Debug function to check available accounts
         */
        debugAccounts: function() {
            var accounts = $('.gmail-other-item');
            console.log('Available account cards:', accounts.length);
            
            accounts.each(function(index) {
                var $item = $(this);
                var accountId = window.GmailAccountSwitcherDirect.getAccountId($item);
                var name = $item.find('.gmail-name').text().trim();
                var email = $item.find('.gmail-email').text().trim();
                
                console.log('Account ' + (index + 1) + ': ID=' + accountId + ', Name=' + name + ', Email=' + email);
            });
        },

        /**
         * Reinitialize when modal opens
         */
        reinit: function() {
            console.log('=== Reinitializing Direct Switcher ===');
            this.initialized = false;
            setTimeout(function() {
                window.GmailAccountSwitcherDirect.init();
            }, 300);
        }
    };

    // Initialize on document ready
    $(document).ready(function() {
        console.log('=== Document Ready - Initializing Direct Switcher ===');
        window.GmailAccountSwitcherDirect.init();
    });

    // Reinitialize when modals are shown
    $(document).on('shown.bs.modal', '.modal', function() {
        window.GmailAccountSwitcherDirect.reinit();
    });

    // Also initialize when any dialog opens
    $(document).on('DOMNodeInserted', function(e) {
        if ($(e.target).hasClass('o_dialog') || $(e.target).find('.gmail-account-switcher-modal').length > 0) {
            setTimeout(function() {
                window.GmailAccountSwitcherDirect.reinit();
            }, 500);
        }
    });

    // Periodic check to ensure handlers are attached (every 5 seconds)
    setInterval(function() {
        if ($('.gmail-other-item').length > 0 && !window.GmailAccountSwitcherDirect.initialized) {
            console.log('Gmail cards found but not initialized, reinitializing...');
            window.GmailAccountSwitcherDirect.init();
        }
    }, 5000);

    console.log('=== Gmail Account Switcher v2.3.0 - Direct Implementation Complete ===');

})();
