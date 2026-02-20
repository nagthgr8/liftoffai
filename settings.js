// ── LiftOff Settings (auto-injected on all pages) ──
(function () {
    // Inject CSS
    var css = document.createElement('style');
    css.textContent = `
.settings-gear{position:fixed;top:18px;right:22px;font-size:22px;cursor:pointer;z-index:900;transition:transform 0.2s}
.settings-gear:hover{transform:rotate(20deg)}
.settings-overlay{display:none;position:fixed;inset:0;background:rgba(0,0,0,0.6);z-index:1000;align-items:center;justify-content:center;backdrop-filter:blur(4px)}
.settings-overlay.show{display:flex}
.settings-modal{background:#1e293b;border:1px solid rgba(71,85,105,0.4);border-radius:16px;width:580px;max-height:80vh;overflow:hidden;box-shadow:0 25px 60px rgba(0,0,0,0.5);display:flex}
.settings-sidebar{width:160px;background:rgba(15,23,42,0.6);border-right:1px solid rgba(71,85,105,0.3);display:flex;flex-direction:column;padding:20px 0;flex-shrink:0}
.settings-nav-item{padding:10px 18px;font-size:13px;color:#94a3b8;cursor:pointer;transition:all 0.2s;display:flex;align-items:center;gap:8px}
.settings-nav-item:hover{background:rgba(71,85,105,0.3);color:#e2e8f0}
.settings-nav-item.active{background:rgba(59,130,246,0.15);color:#60a5fa;border-right:2px solid #60a5fa}
.settings-nav-spacer{flex:1}
.settings-nav-item.logout{color:#f87171;border-top:1px solid rgba(71,85,105,0.3);padding-top:14px}
.settings-nav-item.logout:hover{background:rgba(248,113,113,0.1);color:#fca5a5}
.settings-content{flex:1;padding:30px;overflow-y:auto}
.settings-content h2{font-size:20px;margin-bottom:6px;color:#e2e8f0}
.settings-content .settings-subtitle{font-size:13px;color:#64748b;margin-bottom:24px}
.settings-section{margin-bottom:24px}
.settings-section h3{font-size:13px;text-transform:uppercase;letter-spacing:1.5px;color:#64748b;margin-bottom:14px}
.theme-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:12px}
.theme-swatch{background:rgba(30,41,59,0.8);border:2px solid rgba(71,85,105,0.3);border-radius:12px;padding:14px 8px;text-align:center;cursor:pointer;transition:all 0.25s}
.theme-swatch:hover{transform:translateY(-3px);box-shadow:0 8px 20px rgba(0,0,0,0.3)}
.theme-swatch.active{border-width:2px}
.swatch-preview{width:40px;height:40px;border-radius:50%;margin:0 auto 8px}
.swatch-name{font-size:11px;color:#94a3b8;font-weight:600}
.swatch-emoji{font-size:10px;display:block;margin-top:2px}
.textsize-grid{display:flex;gap:12px}
.textsize-option{flex:1;background:rgba(30,41,59,0.8);border:2px solid rgba(71,85,105,0.3);border-radius:12px;padding:18px 10px;text-align:center;cursor:pointer;transition:all 0.25s}
.textsize-option:hover{transform:translateY(-3px);box-shadow:0 8px 20px rgba(0,0,0,0.3)}
.textsize-option.active{border-color:#60a5fa;box-shadow:0 0 15px rgba(96,165,250,0.25)}
.textsize-option .size-label{font-weight:600;color:#94a3b8;margin-top:6px;font-size:12px}
.textsize-option .size-preview{color:#e2e8f0;font-weight:500}
.textsize-option[data-size="small"] .size-preview{font-size:12px}
.textsize-option[data-size="normal"] .size-preview{font-size:15px}
.textsize-option[data-size="big"] .size-preview{font-size:19px}
.settings-tab{display:none}.settings-tab.active{display:block}
.settings-close{background:rgba(71,85,105,0.3);border:1px solid rgba(71,85,105,0.4);color:#94a3b8;padding:10px 24px;border-radius:10px;font-size:13px;cursor:pointer;width:100%;transition:all 0.2s;margin-top:8px}
.settings-close:hover{background:rgba(71,85,105,0.5);color:#e2e8f0}
    `;
    document.head.appendChild(css);

    // Inject HTML when DOM is ready
    function inject() {
        // Don't inject if already present
        if (document.getElementById('settingsOverlay')) return;

        // Gear icon
        var gear = document.createElement('div');
        gear.className = 'settings-gear';
        gear.textContent = '⚙️';
        gear.onclick = openSettings;
        document.body.appendChild(gear);

        // Modal
        var overlay = document.createElement('div');
        overlay.className = 'settings-overlay';
        overlay.id = 'settingsOverlay';
        overlay.onclick = function (e) { if (e.target === overlay) closeSettings(); };
        overlay.innerHTML = `
<div class="settings-modal">
    <div class="settings-sidebar">
        <div class="settings-nav-item active" data-tab="themes" onclick="window._settingsShowTab('themes',this)">🎨 Themes</div>
        <div class="settings-nav-item" data-tab="text" onclick="window._settingsShowTab('text',this)">🔤 Text</div>
        <div class="settings-nav-spacer"></div>
        <div class="settings-nav-item logout" onclick="window._settingsLogout()">🚪 Logout</div>
    </div>
    <div class="settings-content">
        <h2>⚙️ Settings</h2>
        <p class="settings-subtitle">Customize your LiftOff experience</p>
        <div class="settings-tab active" id="settingsTabThemes">
            <div class="settings-section">
                <h3>🎨 Theme</h3>
                <div class="theme-grid" id="themeGrid"></div>
            </div>
        </div>
        <div class="settings-tab" id="settingsTabText">
            <div class="settings-section">
                <h3>🔤 Text Size</h3>
                <div class="textsize-grid" id="textsizeGrid">
                    <div class="textsize-option" data-size="small" onclick="window._settingsTextSize('small')">
                        <div class="size-preview">Aa</div><div class="size-label">Small</div>
                    </div>
                    <div class="textsize-option active" data-size="normal" onclick="window._settingsTextSize('normal')">
                        <div class="size-preview">Aa</div><div class="size-label">Normal</div>
                    </div>
                    <div class="textsize-option" data-size="big" onclick="window._settingsTextSize('big')">
                        <div class="size-preview">Aa</div><div class="size-label">Big</div>
                    </div>
                </div>
            </div>
        </div>
        <button class="settings-close" onclick="window._settingsClose()">Done</button>
    </div>
</div>`;
        document.body.appendChild(overlay);
    }

    function openSettings() {
        buildThemeGrid();
        refreshTextsizeGrid();
        if (window.playSound) window.playSound('settingsopen');
        document.getElementById('settingsOverlay').classList.add('show');
    }

    function closeSettings() {
        document.getElementById('settingsOverlay').classList.remove('show');
    }

    function buildThemeGrid() {
        var grid = document.getElementById('themeGrid');
        if (!grid || !window.liftoffThemes) return;
        var current = window.getCurrentTheme();
        var tier = localStorage.getItem('liftoffTier') || 'free';
        var isFreeTier = tier === 'free';
        grid.innerHTML = '';
        Object.entries(window.liftoffThemes).forEach(function (entry) {
            var id = entry[0], t = entry[1];
            // Restrict non-ocean themes for free tier
            if (isFreeTier && id !== 'ocean') {
                return; // Skip non-ocean themes for free tier
            }
            var swatch = document.createElement('div');
            swatch.className = 'theme-swatch' + (id === current ? ' active' : '');
            if (id === current) {
                swatch.style.borderColor = t.c1;
                swatch.style.boxShadow = '0 0 15px ' + t.c1 + '40';
            }
            swatch.innerHTML = '<div class="swatch-preview" style="background:linear-gradient(135deg,' + t.c1 + ',' + t.c2 + ')"></div><div class="swatch-name">' + t.name + '</div><span class="swatch-emoji">' + t.emoji + '</span>';
            swatch.onclick = function () {
                window.applyLiftoffTheme(id);
                buildThemeGrid();
            };
            grid.appendChild(swatch);
        });
        
        // Show locked themes message for free tier
        if (isFreeTier && grid.children.length === 1) {
            var msg = document.createElement('div');
            msg.style.cssText = 'grid-column: 1/-1; padding: 12px; background: rgba(59,130,246,0.1); border: 1px solid rgba(59,130,246,0.3); border-radius: 8px; color: #60a5fa; font-size: 12px;';
            msg.textContent = '🔒 Other themes are available in Pro and Ultra plans';
            grid.appendChild(msg);
        }
    }

    function refreshTextsizeGrid() {
        var current = localStorage.getItem('liftoffTextSize') || 'normal';
        document.querySelectorAll('.textsize-option').forEach(function (el) {
            el.classList.toggle('active', el.getAttribute('data-size') === current);
        });
    }

    // Expose functions globally
    window._settingsOpen = openSettings;
    window._settingsClose = closeSettings;
    window._settingsShowTab = function (tab, el) {
        document.querySelectorAll('.settings-nav-item:not(.logout)').forEach(function (n) { n.classList.remove('active'); });
        if (el) el.classList.add('active');
        document.querySelectorAll('.settings-tab').forEach(function (t) { t.classList.remove('active'); });
        var tabEl = document.getElementById('settingsTab' + tab.charAt(0).toUpperCase() + tab.slice(1));
        if (tabEl) tabEl.classList.add('active');
        if (tab === 'text') refreshTextsizeGrid();
    };
    window._settingsTextSize = function (size) {
        localStorage.setItem('liftoffTextSize', size);
        if (window.applyLiftoffTextSize) window.applyLiftoffTextSize(size);
        refreshTextsizeGrid();
    };
    window._settingsLogout = function () {
        localStorage.removeItem('liftoffUser');
        window.location.href = 'index.html';
    };

    // Escape key
    document.addEventListener('keydown', function (e) {
        if (e.key === 'Escape') closeSettings();
    });

    // Inject when DOM ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', inject);
    } else {
        inject();
    }
})();
