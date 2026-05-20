/* Simply Fleet – Vehicle form: move Discard button to top-right of control panel.
 *
 * Uses position:fixed with live getBoundingClientRect() coords so it works
 * regardless of Odoo's nested flex / overflow:hidden layout or active theme.
 * A MutationObserver re-applies after every OWL re-render.
 */
(function () {
    'use strict';

    var MODEL = 'simply.fleet.vehicle';
    var _rafId = null;
    var _retryTimer = null;

    function applyDiscardStyle() {
        var action = document.querySelector('.o_action[data-model="' + MODEL + '"]');
        if (!action) return;

        var btn = action.querySelector('.o_form_button_cancel');
        if (!btn) return;

        var cp = action.querySelector('.o_control_panel');
        if (!cp) return;

        var rect = cp.getBoundingClientRect();

        /* Control panel not yet rendered – retry after a short delay */
        if (!rect || rect.height === 0 || rect.top < 0) {
            if (!_retryTimer) {
                _retryTimer = setTimeout(function () {
                    _retryTimer = null;
                    applyDiscardStyle();
                }, 150);
            }
            return;
        }

        /* Vertical center of the control panel row */
        var topPx = rect.top + rect.height / 2;

        /* Button styling */
        btn.style.setProperty('background-color', '#ffffff', 'important');
        btn.style.setProperty('color',            '#dc3545', 'important');
        btn.style.setProperty('border',           '1px solid #dc3545', 'important');
        btn.style.setProperty('border-radius',    '5px',    'important');
        btn.style.setProperty('padding',          '5px 14px', 'important');
        btn.style.setProperty('font-size',        '13px',   'important');
        btn.style.setProperty('font-weight',      '500',    'important');
        btn.style.setProperty('cursor',           'pointer', 'important');
        btn.style.setProperty('line-height',      '1.5',    'important');

        /* Positioning – fixed to viewport right edge, vertically centred on the CP row */
        btn.style.setProperty('position',  'fixed',             'important');
        btn.style.setProperty('right',     '16px',              'important');
        btn.style.setProperty('top',       topPx + 'px',        'important');
        btn.style.setProperty('transform', 'translateY(-50%)',   'important');
        btn.style.setProperty('z-index',   '9999',              'important');

        /* Add "Discard" text label next to icon (only once) */
        if (!btn.querySelector('.sf-discard-label')) {
            var lbl = document.createElement('span');
            lbl.className = 'sf-discard-label';
            lbl.style.marginLeft = '4px';
            lbl.textContent = 'Discard';
            btn.appendChild(lbl);
        }
    }

    /* Throttle via rAF so we don't thrash on rapid DOM mutations */
    function scheduleApply() {
        if (_rafId) return;
        _rafId = requestAnimationFrame(function () {
            _rafId = null;
            applyDiscardStyle();
        });
    }

    /* Re-apply whenever OWL patches the DOM */
    var observer = new MutationObserver(scheduleApply);
    observer.observe(document.body, { childList: true, subtree: true });

    /* Re-calculate on resize / scroll (sticky bar position can change) */
    window.addEventListener('resize', scheduleApply);
    window.addEventListener('scroll', scheduleApply, true);

    /* Trigger on Odoo hash-based navigation */
    window.addEventListener('hashchange', function () {
        setTimeout(scheduleApply, 300);
    });

    /* First attempt once DOM is interactive */
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', scheduleApply);
    } else {
        scheduleApply();
    }

    /* Fallback: try again after full page load */
    window.addEventListener('load', function () {
        setTimeout(scheduleApply, 200);
    });
})();
