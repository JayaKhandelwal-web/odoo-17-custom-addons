/** Simply Fleet – Global Discard-button relocator
 *
 *  Hides the native Discard (×) button wherever it sits in the control
 *  panel and injects a styled proxy button pinned to the far-right end
 *  of the same horizontal bar.  Works across ALL Odoo 17 form views —
 *  no model restriction.
 *
 *  CSS companion: mobile_styles.css hides the original button via:
 *    .o_control_panel .o_form_button_cancel { display: none !important; }
 */
(function () {
    'use strict';

    const PROXY_ID = 'sf-global-discard-btn';
    let debounceTimer = null;

    /* ── real-button selector ─────────────────────────────────────────── */
    const REAL_BTN_SEL = [
        '.o_form_status_indicator .o_form_button_cancel',
        '.o_control_panel .o_form_button_cancel',
    ].join(', ');

    /* ── create / reuse the proxy button ─────────────────────────────── */
    function getProxy() {
        let btn = document.getElementById(PROXY_ID);
        if (btn) return btn;

        btn = document.createElement('button');
        btn.id    = PROXY_ID;
        btn.type  = 'button';
        btn.title = 'Discard changes';
        btn.innerHTML = '<i class="fa fa-times" style="margin-right:4px"></i>Discard';

        Object.assign(btn.style, {
            position:     'fixed',
            zIndex:       '10000',
            display:      'none',
            alignItems:   'center',
            background:   '#dc3545',
            color:        '#fff',
            border:       'none',
            borderRadius: '5px',
            padding:      '4px 14px',
            fontSize:     '13px',
            fontWeight:   '500',
            cursor:       'pointer',
            boxShadow:    '0 1px 4px rgba(0,0,0,.25)',
            lineHeight:   '1.5',
        });

        btn.addEventListener('mouseenter', () => { btn.style.background = '#c82333'; });
        btn.addEventListener('mouseleave', () => { btn.style.background = '#dc3545'; });

        btn.addEventListener('click', () => {
            const real = document.querySelector(REAL_BTN_SEL);
            if (real) {
                real.dispatchEvent(
                    new MouseEvent('click', { bubbles: true, cancelable: true })
                );
            }
        });

        document.body.appendChild(btn);
        return btn;
    }

    /* ── position the proxy alongside the control panel ──────────────── */
    function positionProxy() {
        const proxy = getProxy();
        const real  = document.querySelector(REAL_BTN_SEL);
        const cp    = document.querySelector('.o_control_panel');

        if (!real || !cp) {
            proxy.style.display = 'none';
            return;
        }

        const rect = cp.getBoundingClientRect();
        if (rect.height === 0) {
            // DOM not painted yet — retry shortly
            setTimeout(positionProxy, 150);
            return;
        }

        const proxyH = 30;
        proxy.style.top     = Math.round(rect.top + (rect.height - proxyH) / 2) + 'px';
        proxy.style.right   = '16px';
        proxy.style.display = 'flex';
    }

    function hideProxy() {
        const proxy = document.getElementById(PROXY_ID);
        if (proxy) proxy.style.display = 'none';
    }

    /* ── debounced sync (called on every DOM / attr mutation) ─────────── */
    function scheduleSync() {
        clearTimeout(debounceTimer);
        debounceTimer = setTimeout(() => {
            if (document.querySelector(REAL_BTN_SEL)) {
                positionProxy();
            } else {
                hideProxy();
            }
        }, 80);
    }

    /* ── observe the whole document for OWL re-renders ───────────────── */
    new MutationObserver(scheduleSync).observe(document.body, {
        childList:       true,
        subtree:         true,
        attributes:      true,
        attributeFilter: ['class', 'style'],
    });

    /* reposition when window is resized */
    window.addEventListener('resize', scheduleSync);

    /* ── initial boot ─────────────────────────────────────────────────── */
    function boot() { setTimeout(scheduleSync, 400); }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', boot);
    } else {
        boot();
    }
})();
