// ── LiftOff Subscription UI ──
(function () {
    /* ── Tier data ── */
    var tiers = [
        {
            id: 'free',
            name: 'Free',
            price: '$0',
            period: '/forever',
            emoji: '🆓',
            color: '#94a3b8',
            gradient: 'linear-gradient(135deg, #64748b, #94a3b8)',
            badge: '',
            features: [
                { text: '1 note generation / day', icon: '📝' },
                { text: '2 note regenerations / day', icon: '🔄' },
                { text: 'No Advanced mode', icon: '🚫' },
                { text: '2 tests / day (max 10 questions)', icon: '🧪' },
                { text: '2 flowcharts / day', icon: '📊' },
                { text: '1 flowchart regeneration / day', icon: '🔄' },
                { text: '3 flashcard generations / day', icon: '🃏' },
                { text: '10 Aviator messages / day', icon: '🤖' },
                { text: 'Aviator in Aviator tab only', icon: '🔒' },
                { text: 'Ocean theme only', icon: '🎨' }
            ]
        },
        {
            id: 'pro',
            name: 'Pro',
            price: '$9.99',
            period: '/month',
            emoji: '⭐',
            color: '#3b82f6',
            gradient: 'linear-gradient(135deg, #3b82f6, #8b5cf6)',
            badge: 'POPULAR',
            features: [
                { text: '15 note generations / day', icon: '📝' },
                { text: '50 note regenerations / day', icon: '🔄' },
                { text: 'Edit notes (coming soon)', icon: '✏️' },
                { text: 'Advanced mode access', icon: '🚀' },
                { text: '30 tests / day', icon: '🧪' },
                { text: '20 flowcharts / day', icon: '📊' },
                { text: '50 flowchart regenerations / day', icon: '🔄' },
                { text: '20 flashcard generations / day', icon: '🃏' },
                { text: 'Unlimited Aviator messages', icon: '🤖' },
                { text: 'No ads', icon: '🚫' },
                { text: 'All themes unlocked', icon: '🎨' }
            ]
        },
        {
            id: 'ultra',
            name: 'Ultra',
            price: '$19.99',
            period: '/month',
            emoji: '👑',
            color: '#f59e0b',
            gradient: 'linear-gradient(135deg, #f59e0b, #ef4444)',
            badge: 'BEST VALUE',
            features: [
                { text: 'Unlimited note generations', icon: '📝' },
                { text: 'Unlimited regenerations', icon: '🔄' },
                { text: 'Full note editing access', icon: '✏️' },
                { text: 'Advanced mode access', icon: '🚀' },
                { text: 'Unlimited tests', icon: '🧪' },
                { text: 'Unlimited flowcharts', icon: '📊' },
                { text: 'Unlimited flashcard generations', icon: '🃏' },
                { text: 'Unlimited Aviator messages', icon: '🤖' },
                { text: 'Weakness analysis & charts', icon: '📈' },
                { text: 'All themes unlocked', icon: '🎨' },
                { text: 'No ads', icon: '🚫' }
            ]
        }
    ];

    /* ── Inject CSS ── */
    var style = document.createElement('style');
    style.textContent = `
        /* ── Subscription Button (sidebar) ── */
        .sub-btn {
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 8px;
            margin-top: auto;
            padding: 12px 15px;
            border-radius: 12px;
            background: linear-gradient(135deg, #f59e0b, #eab308);
            color: #1e1b0f;
            font-weight: 700;
            font-size: 14px;
            cursor: pointer;
            transition: all 0.3s;
            border: none;
            width: 100%;
            box-sizing: border-box;
        }
        .sub-btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 20px rgba(245, 158, 11, 0.4);
        }
        .sub-btn .crown { font-size: 18px; }

        /* make sidebar a flex column so button sticks to bottom */
        .sidebar {
            display: flex !important;
            flex-direction: column !important;
        }
        .sidebar .sub-btn { margin-top: auto; }

        /* ── Overlay + Modal ── */
        .sub-overlay {
            position: fixed; inset: 0;
            background: rgba(0,0,0,0.7);
            backdrop-filter: blur(6px);
            z-index: 100000;
            display: none;
            align-items: center;
            justify-content: center;
        }
        .sub-overlay.open { display: flex; }

        .sub-modal {
            background: #0f172a;
            border-radius: 20px;
            border: 1px solid rgba(71,85,105,0.4);
            width: 940px;
            max-width: 95vw;
            max-height: 90vh;
            overflow-y: auto;
            padding: 40px 36px;
            position: relative;
            animation: subSlideUp 0.35s ease;
        }
        @keyframes subSlideUp {
            from { opacity: 0; transform: translateY(30px); }
            to   { opacity: 1; transform: translateY(0); }
        }

        .sub-modal-close {
            position: absolute;
            top: 16px; right: 20px;
            background: none; border: none;
            color: #94a3b8; font-size: 22px;
            cursor: pointer;
            transition: color 0.2s;
        }
        .sub-modal-close:hover { color: #fff; }

        .sub-modal-title {
            text-align: center;
            font-size: 28px;
            font-weight: 800;
            margin-bottom: 6px;
            background: linear-gradient(135deg, #f59e0b, #ef4444);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }
        .sub-modal-subtitle {
            text-align: center;
            color: #94a3b8;
            font-size: 14px;
            margin-bottom: 32px;
        }

        /* ── Tier Cards Grid ── */
        .sub-grid {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 20px;
        }
        @media (max-width: 800px) {
            .sub-grid { grid-template-columns: 1fr; }
        }

        .sub-card {
            border-radius: 16px;
            border: 1px solid rgba(71,85,105,0.3);
            padding: 28px 22px;
            position: relative;
            background: rgba(15,23,42,0.6);
            display: flex;
            flex-direction: column;
            transition: transform 0.25s, box-shadow 0.25s;
        }
        .sub-card:hover {
            transform: translateY(-4px);
            box-shadow: 0 8px 30px rgba(0,0,0,0.3);
        }
        .sub-card.highlight {
            border-color: #3b82f6;
            box-shadow: 0 0 30px rgba(59,130,246,0.15);
        }
        .sub-card.highlight-ultra {
            border-color: #f59e0b;
            box-shadow: 0 0 30px rgba(245,158,11,0.15);
        }

        .sub-badge {
            position: absolute;
            top: -11px;
            left: 50%;
            transform: translateX(-50%);
            padding: 4px 14px;
            border-radius: 20px;
            font-size: 11px;
            font-weight: 700;
            letter-spacing: 1px;
            color: #fff;
        }

        .sub-card-emoji {
            font-size: 36px;
            margin-bottom: 10px;
        }
        .sub-card-name {
            font-size: 22px;
            font-weight: 800;
            color: #f1f5f9;
            margin-bottom: 4px;
        }
        .sub-card-price {
            font-size: 32px;
            font-weight: 800;
            margin-bottom: 2px;
        }
        .sub-card-period {
            font-size: 13px;
            color: #64748b;
            margin-bottom: 20px;
        }

        .sub-divider {
            height: 1px;
            background: rgba(71,85,105,0.3);
            margin-bottom: 18px;
        }

        .sub-feature {
            display: flex;
            align-items: flex-start;
            gap: 10px;
            margin-bottom: 12px;
            font-size: 13px;
            color: #cbd5e1;
            line-height: 1.4;
        }
        .sub-feature-icon { flex-shrink: 0; font-size: 15px; }

        .sub-card-btn {
            margin-top: auto;
            padding: 12px;
            border-radius: 10px;
            border: none;
            font-weight: 700;
            font-size: 14px;
            cursor: pointer;
            transition: all 0.25s;
            text-align: center;
            width: 100%;
        }
        .sub-card-btn:hover {
            transform: translateY(-1px);
            box-shadow: 0 4px 15px rgba(0,0,0,0.3);
        }
        .sub-card-btn.current {
            background: rgba(71,85,105,0.3);
            color: #94a3b8;
            cursor: default;
        }
        .sub-card-btn.current:hover {
            transform: none;
            box-shadow: none;
        }
    `;
    document.head.appendChild(style);

    /* ── Global fetch interceptor: Add headers to all API calls ── */
    var originalFetch = window.fetch;
    window.fetch = function(url, options) {
        options = options || {};
        
        // Only add headers to LiftOff API calls
        if (typeof url === 'string' && url.includes('/api/')) {
            var headers = {};
            var tier = localStorage.getItem('liftoffTier') || 'free';
            headers['X-User-Tier'] = tier;
            
            // Only set Content-Type if NOT uploading files (FormData)
            // FormData should be sent without Content-Type so browser can set it with proper boundary
            if (!(options.body instanceof FormData)) {
                headers['Content-Type'] = 'application/json';
            }
            
            options.headers = Object.assign({}, headers, options.headers || {});
        }
        
        return originalFetch.call(window, url, options);
    };

    /* ── Helper: Get API headers with subscription tier ── */
    function getApiHeaders() {
        var tier = localStorage.getItem('liftoffTier') || 'free';
        return {
            'X-User-Tier': tier,
            'Content-Type': 'application/json'
        };
    }

    /* ── Helper: Check if feature is available ── */
    window.isFeatureAllowed = function(feature) {
        var tier = localStorage.getItem('liftoffTier') || 'free';
        var tiersConfig = {
            'free': { advanced_mode: false, all_themes: false, aviator_everywhere: false },
            'pro': { advanced_mode: true, all_themes: true, aviator_everywhere: true },
            'ultra': { advanced_mode: true, all_themes: true, aviator_everywhere: true }
        };
        return tiersConfig[tier] && tiersConfig[tier][feature];
    };

    /* ── Helper: Show upgrade modal ── */
    window.showUpgradeRequired = function(feature) {
        var messages = {
            'advanced_mode': 'Advanced Mode is only available in Pro and Ultra plans',
            'all_themes': 'Premium themes are only available in Pro and Ultra plans',
            'aviator_everywhere': 'Aviator access outside the Aviator tab is only available in Pro and Ultra plans'
        };
        alert(messages[feature] || 'This feature requires an upgrade');
        window._subOpen();
    };

    /* ── Build modal HTML ── */
    function buildModal() {
        var currentTier = localStorage.getItem('liftoffTier') || 'free';

        var html = '<div class="sub-overlay" id="subOverlay">';
        html += '<div class="sub-modal">';
        html += '<button class="sub-modal-close" onclick="window._subClose()">✕</button>';
        html += '<div class="sub-modal-title">👑 Upgrade Your Plan</div>';
        html += '<div class="sub-modal-subtitle">Choose the plan that fits your learning journey</div>';
        html += '<div class="sub-grid">';

        tiers.forEach(function (t) {
            var isCurrent = t.id === currentTier;
            var highlightClass = t.id === 'pro' ? ' highlight' : (t.id === 'ultra' ? ' highlight-ultra' : '');

            html += '<div class="sub-card' + highlightClass + '">';

            // Badge
            if (t.badge) {
                html += '<div class="sub-badge" style="background:' + t.gradient + '">' + t.badge + '</div>';
            }

            html += '<div class="sub-card-emoji">' + t.emoji + '</div>';
            html += '<div class="sub-card-name">' + t.name + '</div>';
            html += '<div class="sub-card-price" style="color:' + t.color + '">' + t.price + '</div>';
            html += '<div class="sub-card-period">' + t.period + '</div>';
            html += '<div class="sub-divider"></div>';

            // Features
            t.features.forEach(function (f) {
                html += '<div class="sub-feature">';
                html += '<span class="sub-feature-icon">' + f.icon + '</span>';
                html += '<span>' + f.text + '</span>';
                html += '</div>';
            });

            // Button
            if (isCurrent) {
                html += '<button class="sub-card-btn current">Current Plan</button>';
            } else {
                var btnStyle = 'background:' + t.gradient + ';color:#fff;';
                html += '<button class="sub-card-btn" style="' + btnStyle + '" onclick="window._subSelect(\'' + t.id + '\')">';
                html += t.id === 'free' ? 'Downgrade' : 'Upgrade';
                html += '</button>';
            }

            html += '</div>'; // card
        });

        html += '</div>'; // grid
        html += '</div>'; // modal
        html += '</div>'; // overlay

        return html;
    }

    /* ── Inject sidebar button ── */
    function injectButton() {
        var sidebar = document.querySelector('.sidebar');
        if (!sidebar) return;

        var btn = document.createElement('div');
        btn.className = 'sub-btn';
        btn.onclick = function () { window._subOpen(); };
        btn.innerHTML = '<span class="crown">👑</span> Subscription';
        sidebar.appendChild(btn);
    }

    /* ── Inject modal into body ── */
    function injectModal() {
        var wrap = document.createElement('div');
        wrap.id = 'subWrap';
        wrap.innerHTML = buildModal();
        document.body.appendChild(wrap);
    }

    /* ── Refresh (re-render after tier change) ── */
    function refresh() {
        var old = document.getElementById('subWrap');
        if (old) old.remove();
        injectModal();
    }

    /* ── Public API ── */
    window._subOpen = function () {
        refresh(); // always rebuild with latest tier
        var ov = document.getElementById('subOverlay');
        if (ov) ov.classList.add('open');
        if (window.playSound) playSound('settingsopen');
    };

    window._subClose = function () {
        var ov = document.getElementById('subOverlay');
        if (ov) ov.classList.remove('open');
    };

    window._subSelect = function (tierId) {
        // For now just save locally (payment integration later)
        localStorage.setItem('liftoffTier', tierId);
        refresh();
        var ov = document.getElementById('subOverlay');
        if (ov) ov.classList.add('open');
    };

    /* ── close on overlay click ── */
    document.addEventListener('click', function (e) {
        if (e.target && e.target.id === 'subOverlay') {
            window._subClose();
        }
    });

    /* ── Init ── */
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', function () {
            injectButton();
            injectModal();
        });
    } else {
        injectButton();
        injectModal();
    }
})();
