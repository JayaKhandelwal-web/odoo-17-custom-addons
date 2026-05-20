/** Simply Fleet – Global button relocator
 *
 *  1. Discard: hidden from native position, re-created as a fixed proxy
 *     at the far-right of the control-panel row.
 *  2. Save + Gear: shifted 1.5cm (57px) to the right via inline style,
 *     same gap kept between them, functionality unchanged.
 */
(function () {
    'use strict';

    const PROXY_ID   = 'sf-global-discard-btn';
    const REAL_SEL   = '.o_form_status_indicator_buttons .o_form_button_cancel';
    const STATUS_SEL = '.o_form_status_indicator_buttons';
    const SAVE_SEL   = '.o_form_button_save';
    const GEAR_SEL   = '.o_cp_action_menus';
    const GEAR_SHIFT = '57px';   /* 1.5 cm ≈ 57 px at 96 dpi */
    const SAVE_SHIFT = '-7px';   /* 1px - 0.2cm(8px) = -7px */
    let   debounce   = null;

    /* ── discard proxy ────────────────────────────────────────────────── */
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

    function syncProxy() {
        const proxy     = getProxy();
        const real      = document.querySelector(REAL_SEL);
        const statusDiv = document.querySelector(STATUS_SEL);

        if (!real || !statusDiv) { proxy.style.display = 'none'; resetShift(); return; }

        const rect = statusDiv.getBoundingClientRect();
        if (rect.height === 0) { setTimeout(syncProxy, 150); return; }

        proxy.style.top     = Math.round(rect.top + (rect.height - 30) / 2) + 'px';
        proxy.style.right   = '16px';
        proxy.style.display = 'flex';

        applyShift();
    }

    /* ── shift save + gear 1.5cm right, same gap ──────────────────────── */
    function applyShift() {
        const gear = document.querySelector(GEAR_SEL);
        if (gear) {
            gear.style.setProperty('margin-left', GEAR_SHIFT, 'important');
        }

        const save = document.querySelector(SAVE_SEL);
        if (save) {
            save.style.setProperty('margin-left', SAVE_SHIFT, 'important');
        }
    }

    function resetShift() {
        const gear = document.querySelector(GEAR_SEL);
        if (gear) gear.style.removeProperty('margin-left');

        const save = document.querySelector(SAVE_SEL);
        if (save) save.style.removeProperty('margin-left');
    }

    function hideProxy() {
        const p = document.getElementById(PROXY_ID);
        if (p) p.style.display = 'none';
        resetShift();
    }

    /* ── debounce + observe ───────────────────────────────────────────── */
    function schedule() {
        clearTimeout(debounce);
        debounce = setTimeout(() => {
            document.querySelector(REAL_SEL) ? syncProxy() : hideProxy();
        }, 80);
    }

    window.addEventListener('resize', schedule);
    window.addEventListener('scroll', schedule, true);

    function init() {
        const boot = () => {
            new MutationObserver(schedule).observe(document.body, {
                childList: true, subtree: true,
                attributes: true, attributeFilter: ['class', 'style'],
            });
            setTimeout(schedule, 500);
        };
        document.body ? boot() : document.addEventListener('DOMContentLoaded', boot);
    }

    init();
})();
