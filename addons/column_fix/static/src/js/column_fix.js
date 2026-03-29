odoo.define('column_fix.patch', function (require) {
    "use strict";

    // We need to wait for the module to be loaded before patching it
    var ready = function (callback) {
        if (document.readyState !== 'loading') {
            callback();
        } else {
            document.addEventListener('DOMContentLoaded', callback);
        }
    };

    ready(function () {
        // Apply patches when DOM is ready
        var interval = setInterval(function() {
            if (window.odoo && window.odoo.web_editor) {
                clearInterval(interval);
                
                try {
                    // Find all the relevant objects or prototypes that might use the method
                    var targets = [];
                    
                    // Add any objects that have _areColsCustomized method
                    if (window.odoo.web_editor.snippets && 
                        window.odoo.web_editor.snippets.options) {
                        targets.push(window.odoo.web_editor.snippets.options);
                    }
                    
                    if (window.odoo.web_editor.ColumnLayoutMixin) {
                        targets.push(window.odoo.web_editor.ColumnLayoutMixin);
                    }
                    
                    // Try to find other potential targets
                    for (var key in window.odoo.web_editor) {
                        var obj = window.odoo.web_editor[key];
                        if (obj && typeof obj === 'object' && obj.prototype && 
                            typeof obj.prototype._areColsCustomized === 'function') {
                            targets.push(obj.prototype);
                        }
                    }
                    
                    // Patch each target
                    targets.forEach(function(target) {
                        if (target && typeof target._areColsCustomized === 'function') {
                            // Store the original function
                            var originalFn = target._areColsCustomized;
                            
                            // Replace with safer version
                            target._areColsCustomized = function(columnEls, isMobile) {
                                // Add safety check
                                if (!columnEls || columnEls.length === 0) {
                                    console.info('Fixed: Empty columnEls in _areColsCustomized');
                                    return false;
                                }
                                
                                try {
                                    return originalFn.apply(this, arguments);
                                } catch (e) {
                                    console.warn('Fixed error in _areColsCustomized:', e);
                                    return false;
                                }
                            };
                            console.log('Column layout fix applied to a target');
                        }
                    });
                    
                    console.log('Column layout fix initialization complete');
                } catch (e) {
                    console.error('Error applying column layout fix:', e);
                }
            }
        }, 200);
    });
});
