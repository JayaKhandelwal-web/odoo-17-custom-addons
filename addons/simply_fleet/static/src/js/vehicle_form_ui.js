/* Simply Fleet – Vehicle form: move Discard button to top-right of control panel.
 *
 * Why JS instead of CSS:
 *   The control panel uses a nested flex layout inside `.o_action { overflow:hidden }`.
 *   CSS `position:absolute` is intercepted by intermediate flex containers created by
 *   Bootstrap utilities, making the button land in unpredictable places.
 *   `position:fixed` with JS-measured coordinates is the only reliable cross-theme approach.
 */
(function () {
    'use strict';

    var VEHICLE_MODEL = 'simply.fleet.vehicle';
    var _rafId = null;
    var _lastBtn = null;

    function applyDiscardStyle() {
        var action = document.querySelector(
            '.o_action[data-model="' + VEHICLE_MODEL + '"]'
        );
        if (!action) {
            _lastBtn = null;
            return;
        }

        var btn = action.querySelector('.o_form_button_cancel');
        if (!btn) {
            _lastBtn = null;
            return;
        }

        var cp = action.querySelector('.o_control_panel');
        if (!cp) return;

        var rect = cp.getBoundingClientRect();

        /* Button visual styling */
        btn.style.setProperty('background-color', '#fff', 'important');
        btn.style.setProperty('color', '#dc3545', 'important');
        btn.style.setProperty('border', '1px solid #dc3545', 'important');
        btn.style.setProperty('border-radius', '5px', 'important');
        btn.style.setProperty('padding', '5px 14px', 'important');
        btn.style.setProperty('font-size', '13px', 'important');
        btn.style.setProperty('font-weight', '500', 'important');

        /* Position: fixed to the top-right of the control panel row */
        btn.style.setProperty('position', 'fixed', 'important');
        btn.style.setProperty('right', '16px', 'important');
        btn.style.setProperty('top', (rect.top + rect.height / 2) + 'px', 'important');
        btn.style.setProperty('transform', 'translateY(-50%)', 'important');
        btn.style.setProperty('z-index', '9999', 'important');

        /* Add "Discard" label next to the icon if not already added */
        if (!btn.querySelector('.sf-discard-label')) {
            var label = document.createElement('span');
            label.className = 'sf-discard-label';
            label.textContent = ' Discard';
            btn.appendChild(label);
        }

        _lastBtn = btn;
    }

    function scheduleApply() {
        if (_rafId) return;
        _rafId = requestAnimationFrame(function () {
            _rafId = null;
            applyDiscardStyle();
        });
    }

    /* Watch for OWL re-renders and route changes */
    var observer = new MutationObserver(scheduleApply);
    observer.observe(document.body, { childList: true, subtree: true });

    /* Re-calculate on resize so fixed coordinates stay accurate */
    window.addEventListener('resize', scheduleApply);

    /* Initial application */
    scheduleApply();
})();
