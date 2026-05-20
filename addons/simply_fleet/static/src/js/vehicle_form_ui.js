/** Simply Fleet – Global button relocator
 *
 *  1. Discard button: hidden from its native position, re-created as a
 *     fixed-position proxy at the far-right of the control-panel row.
 *  2. Save + Gear buttons: repositioned via position:fixed to the right
 *     side of the same control-panel row, just left of the Discard button.
 *
 *  Works across ALL Odoo 17 form views — no model restriction.
 */
(function () {
    'use strict';

    const PROXY_ID   = 'sf-global-discard-btn';
    const REAL_SEL   = '.o_form_status_indicator_buttons .o_form_button_cancel';
    const STATUS_SEL = '.o_form_status_indicator_buttons';
    const SAVE_SEL   = '.o_form_button_save';
    const GEAR_SEL   = '.o_cp_action_menus';
    let   debounce   = null;

    /* ── build / reuse the discard proxy button ───────────────────────── */
    function getProxy() {
        let btn = document.getElementById(PROXY_ID);
        if (btn) return btn;

        btn = document.createElement('button');
        btn.id    = PROXY_ID;
        btn.type  = 'button';
        btn.title = 'Discard changes';
        btn.setAttribute('data-tooltip', 'Discard changes');
        btn.innerHTML = '<i class="fa fa-undo" style="margin-right:5px"></i>Discard';

        Object.assign(btn.style, {
            position:     'fixed',
            zIndex:       '10000',
            display:      'none',
            alignItems:   'center',
            background:   '#dc3545',
            color:        '#fff',
            border:       'none',
            borderRadius: '5px',
            padding:      '5px 14px',
            fontSize:     '13px',
            fontWeight:   '500',
            cursor:       'pointer',
            boxShadow:    '0 1px 4px rgba(0,0,0,.3)',
            lineHeight:   '1.5',
        });

        btn.addEventListener('mouseenter', () => { btn.style.background = '#c82333'; });
        btn.addEventListener('mouseleave', () => { btn.style.background = '#dc3545'; });

        btn.addEventListener('click', () => {
            const real = document.querySelector(REAL_SEL);
            if (real) real.dispatchEvent(
                new MouseEvent('click', { bubbles: true, cancelable: true })
            );
        });

        document.body.appendChild(btn);
        return btn;
    }

    /* ── position the discard proxy ───────────────────────────────────── */
    function syncProxy() {
        const proxy     = getProxy();
        const real      = document.querySelector(REAL_SEL);
        const statusDiv = document.querySelector(STATUS_SEL);

        if (!real || !statusDiv) {
            proxy.style.display = 'none';
            resetSaveGear();
            return;
        }

        const rect = statusDiv.getBoundingClientRect();
        if (rect.height === 0) {
            setTimeout(syncProxy, 150);
            return;
        }

        const proxyH = 30;
        proxy.style.top     = Math.round(rect.top + (rect.height - proxyH) / 2) + 'px';
        proxy.style.right   = '16px';
        proxy.style.display = 'flex';

        syncSaveGear(rect);
    }

    /* ── move save + gear to the right side of the same row ──────────── */
    function syncSaveGear(rect) {
        if (!rect) {
            const statusDiv = document.querySelector(STATUS_SEL);
            if (!statusDiv) return;
            rect = statusDiv.getBoundingClientRect();
            if (rect.height === 0) return;
        }

        const btnH   = 50;   // circular button height
        const top    = Math.round(rect.top + (rect.height - btnH) / 2);

        // Save button — 56px left of discard (50px btn + 6px gap)
        const saveBtn = document.querySelector(SAVE_SEL);
        if (saveBtn) {
            saveBtn.style.setProperty('position', 'fixed', 'important');
            saveBtn.style.setProperty('top',      top + 'px', 'important');
            saveBtn.style.setProperty('right',    '130px', 'important');
            saveBtn.style.setProperty('left',     'auto', 'important');
            saveBtn.style.setProperty('z-index',  '9999', 'important');
        }

        // Gear container — 56px left of save (50px btn + 6px gap)
        const gear = document.querySelector(GEAR_SEL);
        if (gear) {
            gear.style.setProperty('position', 'fixed', 'important');
            gear.style.setProperty('top',      top + 'px', 'important');
            gear.style.setProperty('right',    '188px', 'important');
            gear.style.setProperty('left',     'auto', 'important');
            gear.style.setProperty('z-index',  '9999', 'important');
        }
    }

    /* ── reset save + gear when form is not in edit mode ─────────────── */
    function resetSaveGear() {
        const saveBtn = document.querySelector(SAVE_SEL);
        if (saveBtn) {
            saveBtn.style.removeProperty('position');
            saveBtn.style.removeProperty('top');
            saveBtn.style.removeProperty('right');
            saveBtn.style.removeProperty('left');
            saveBtn.style.removeProperty('z-index');
        }
        const gear = document.querySelector(GEAR_SEL);
        if (gear) {
            gear.style.removeProperty('position');
            gear.style.removeProperty('top');
            gear.style.removeProperty('right');
            gear.style.removeProperty('left');
            gear.style.removeProperty('z-index');
        }
    }

    function hideProxy() {
        const p = document.getElementById(PROXY_ID);
        if (p) p.style.display = 'none';
        resetSaveGear();
    }

    /* ── debounced trigger ────────────────────────────────────────────── */
    function schedule() {
        clearTimeout(debounce);
        debounce = setTimeout(() => {
            document.querySelector(REAL_SEL) ? syncProxy() : hideProxy();
        }, 80);
    }

    window.addEventListener('resize', schedule);
    window.addEventListener('scroll', schedule, true);

    /* ── observe + boot ───────────────────────────────────────────────── */
    function init() {
        if (document.body) {
            new MutationObserver(schedule).observe(document.body, {
                childList:       true,
                subtree:         true,
                attributes:      true,
                attributeFilter: ['class', 'style'],
            });
            setTimeout(schedule, 500);
        } else {
            document.addEventListener('DOMContentLoaded', () => {
                new MutationObserver(schedule).observe(document.body, {
                    childList:       true,
                    subtree:         true,
                    attributes:      true,
                    attributeFilter: ['class', 'style'],
                });
                setTimeout(schedule, 500);
            });
        }
    }

    init();
})();
