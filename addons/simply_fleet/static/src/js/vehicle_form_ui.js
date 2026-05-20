/** Simply Fleet – Global Discard-button relocator
 *
 *  The native Discard button (.o_form_button_cancel inside
 *  .o_form_status_indicator_buttons) is hidden via CSS (mobile_styles.css).
 *  This script creates a red "Discard" proxy button pinned with
 *  position:fixed to the far-right end of the control-panel row.
 *  It forwards clicks to the real (hidden) button and auto-repositions
 *  on every OWL re-render and window resize.
 *
 *  Works across ALL Odoo 17 form views — no model restriction.
 */
(function () {
    'use strict';

    const PROXY_ID   = 'sf-global-discard-btn';
    const REAL_SEL   = '.o_form_status_indicator_buttons .o_form_button_cancel';
    const STATUS_SEL = '.o_form_status_indicator_buttons';
    let   debounce   = null;

    /* ── build / reuse the proxy button ──────────────────────────────── */
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

    /* ── position the proxy over the far-right of the control panel ───── */
    function syncProxy() {
        const proxy     = getProxy();
        const real      = document.querySelector(REAL_SEL);
        const statusDiv = document.querySelector(STATUS_SEL);

        if (!real || !statusDiv) {
            proxy.style.display = 'none';
            return;
        }

        const rect = statusDiv.getBoundingClientRect();
        if (rect.height === 0) {           // DOM not painted yet — retry
            setTimeout(syncProxy, 150);
            return;
        }

        const proxyH = 30;                 // approx button height in px
        proxy.style.top     = Math.round(rect.top + (rect.height - proxyH) / 2) + 'px';
        proxy.style.right   = '16px';
        proxy.style.display = 'flex';
    }

    function hideProxy() {
        const p = document.getElementById(PROXY_ID);
        if (p) p.style.display = 'none';
    }

    /* ── debounced trigger (OWL re-renders can fire many mutations) ───── */
    function schedule() {
        clearTimeout(debounce);
        debounce = setTimeout(() => {
            document.querySelector(REAL_SEL) ? syncProxy() : hideProxy();
        }, 80);
    }

    window.addEventListener('resize', schedule);
    window.addEventListener('scroll', schedule, true);   // capture scroll

    /* ── observe + boot (safe: wait for body to exist) ───────────────── */
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
            // body not ready yet — wait for DOMContentLoaded
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
