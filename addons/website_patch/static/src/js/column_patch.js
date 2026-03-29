odoo.define('website_fix.column_fix', function (require) {
    'use strict';
    
    const SnippetEditor = require('web_editor.snippet.editor').SnippetEditor;
    
    const originalAreColsCustomized = SnippetEditor.prototype.areColsCustomized;
    
    if (originalAreColsCustomized) {
        SnippetEditor.prototype.areColsCustomized = function () {
            try {
                const columnEls = this.$target.find('> .row > [class*="col-"]');
                if (!columnEls || columnEls.length === 0) {
                    return false;
                }
                return originalAreColsCustomized.apply(this, arguments);
            } catch (e) {
                console.warn('Prevented error in areColsCustomized:', e);
                return false;
            }
        };
    }
});
