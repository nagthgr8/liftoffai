// LiftOff Theme System
// Loaded in <head> of every page to apply theme before render

(function () {
    const themes = {
        ocean: {
            name: 'Ocean', emoji: '🌊',
            c1: '#3b82f6', c2: '#8b5cf6',
            c1l: '#60a5fa', c2l: '#a78bfa',
            r1: '59,130,246', r2: '139,92,246'
        },
        emerald: {
            name: 'Emerald', emoji: '🌿',
            c1: '#10b981', c2: '#06b6d4',
            c1l: '#34d399', c2l: '#22d3ee',
            r1: '16,185,129', r2: '6,182,212'
        },
        sunset: {
            name: 'Sunset', emoji: '🌅',
            c1: '#f97316', c2: '#ec4899',
            c1l: '#fb923c', c2l: '#f472b6',
            r1: '249,115,22', r2: '236,72,153'
        },
        sakura: {
            name: 'Sakura', emoji: '🌸',
            c1: '#ec4899', c2: '#a855f7',
            c1l: '#f472b6', c2l: '#c084fc',
            r1: '236,72,153', r2: '168,85,247'
        },
        crimson: {
            name: 'Crimson', emoji: '🔥',
            c1: '#ef4444', c2: '#f97316',
            c1l: '#f87171', c2l: '#fb923c',
            r1: '239,68,68', r2: '249,115,22'
        },
        amber: {
            name: 'Amber', emoji: '✨',
            c1: '#f59e0b', c2: '#ea580c',
            c1l: '#fbbf24', c2l: '#f97316',
            r1: '245,158,11', r2: '234,88,12'
        },
        lavender: {
            name: 'Lavender', emoji: '💜',
            c1: '#8b5cf6', c2: '#d946ef',
            c1l: '#a78bfa', c2l: '#e879f9',
            r1: '139,92,246', r2: '217,70,239'
        },
        arctic: {
            name: 'Arctic', emoji: '❄️',
            c1: '#06b6d4', c2: '#3b82f6',
            c1l: '#22d3ee', c2l: '#60a5fa',
            r1: '6,182,212', r2: '59,130,246'
        }
    };

    function applyTheme(themeId) {
        if (!themes[themeId]) themeId = 'ocean';
        const t = themes[themeId];
        localStorage.setItem('liftoffTheme', themeId);

        // Remove old override
        var old = document.getElementById('liftoff-theme-css');
        if (old) old.remove();

        // Default theme needs no overrides
        if (themeId === 'ocean') return;

        var s = document.createElement('style');
        s.id = 'liftoff-theme-css';
        s.textContent = [
            // ── Navigation ──
            '.nav-item.active{background:linear-gradient(135deg,' + t.c1 + ',' + t.c2 + ')!important}',
            '.nav-item:hover{background:rgba(' + t.r1 + ',0.2)!important}',

            // ── Gradient text ──
            '.sidebar h2{background:linear-gradient(135deg,' + t.c1l + ',' + t.c2l + ')!important;-webkit-background-clip:text!important;background-clip:text!important}',
            '.logo-emoji{background:linear-gradient(135deg,' + t.c1l + ',' + t.c2l + ')!important;-webkit-background-clip:text!important;background-clip:text!important}',
            '.header h1{background:linear-gradient(135deg,' + t.c1l + ',' + t.c2l + ')!important;-webkit-background-clip:text!important;background-clip:text!important}',
            '.generating-message h3,.status-overlay h3{background:linear-gradient(135deg,' + t.c1l + ',' + t.c2l + ')!important;-webkit-background-clip:text!important;background-clip:text!important}',
            '.summary-score{background:linear-gradient(135deg,' + t.c1l + ',' + t.c2l + ')!important;-webkit-background-clip:text!important;background-clip:text!important}',
            '.score-percentage{background:linear-gradient(135deg,' + t.c1l + ',' + t.c2l + ')!important;-webkit-background-clip:text!important;background-clip:text!important}',

            // ── Buttons ──
            '.btn-primary,.btn.btn-primary{background:linear-gradient(135deg,' + t.c1 + ',' + t.c2 + ')!important}',
            '.btn-primary:hover,.btn.btn-primary:hover{box-shadow:0 6px 20px rgba(' + t.r1 + ',0.3)!important}',
            '.chat-send-btn{background:linear-gradient(135deg,' + t.c1 + ',' + t.c2 + ')!important}',
            '.btn-secondary:hover{background:rgba(' + t.r1 + ',0.2)!important;border-color:rgba(' + t.r1 + ',0.4)!important}',
            '.btn-next{background:linear-gradient(135deg,' + t.c1 + ',' + t.c2 + ')!important}',
            '.btn-next:hover{box-shadow:0 5px 15px rgba(' + t.r1 + ',0.3)!important}',

            // ── Chat ──
            '.message.user .message-bubble{background:linear-gradient(135deg,' + t.c1 + ',' + t.c2 + ')!important}',
            '.message.ai .message-bubble,.message.assistant .message-bubble{border-color:rgba(' + t.r1 + ',0.3)!important}',
            '.chat-header{border-bottom-color:rgba(' + t.r1 + ',0.2)!important}',

            // ── Upload / Input boxes ──
            '.upload-box,.input-box{border-color:rgba(' + t.r1 + ',0.5)!important;background:linear-gradient(135deg,rgba(' + t.r1 + ',0.1),rgba(' + t.r2 + ',0.1))!important}',
            '.upload-box:hover,.input-box:hover{border-color:rgba(' + t.r1 + ',0.8)!important;background:linear-gradient(135deg,rgba(' + t.r1 + ',0.2),rgba(' + t.r2 + ',0.2))!important}',

            // ── Cards & borders ──
            '.card{border-color:rgba(' + t.r1 + ',0.1)!important}',
            '.test-card{background:rgba(' + t.r1 + ',0.1)!important;border-color:rgba(' + t.r1 + ',0.3)!important}',
            '.test-card:hover{background:rgba(' + t.r1 + ',0.15)!important}',
            '.test-pdf-name{color:' + t.c1l + '!important}',

            // ── Progress & loader ──
            '.progress-fill{background:linear-gradient(90deg,' + t.c1 + ',' + t.c2 + ')!important}',
            '.loader{border-color:rgba(' + t.r1 + ',0.2)!important;border-top-color:' + t.c1l + '!important}',

            // ── Flashcard ──
            '.flashcard-front{background:linear-gradient(135deg,rgba(' + t.r1 + ',0.15),rgba(' + t.r2 + ',0.15))!important;border-color:rgba(' + t.r1 + ',0.3)!important}',
            '.know-btn{background:rgba(' + t.r1 + ',0.2)!important;border-color:rgba(' + t.r1 + ',0.4)!important;color:' + t.c1l + '!important}',
            '.know-btn:hover{background:rgba(' + t.r1 + ',0.3)!important}',
            '.next-after-reveal{background:rgba(' + t.r1 + ',0.2)!important;border-color:rgba(' + t.r1 + ',0.5)!important;color:' + t.c1l + '!important}',

            // ── Flowchart ──
            '.zoom-btn:hover{background:rgba(' + t.r1 + ',0.3)!important;border-color:rgba(' + t.r1 + ',0.5)!important}',

            // ── Inputs ──
            '.input-wrapper textarea:focus,.text-input-wrapper textarea:focus{border-color:rgba(' + t.r1 + ',0.5)!important}',

            // ── Misc accents ──
            '.upload-tip{border-left-color:rgba(' + t.r1 + ',0.4)!important;background:rgba(' + t.r1 + ',0.05)!important}',
            '.or-divider{color:rgba(' + t.r1 + ',0.6)!important}',
            '.status-dot{background:' + t.c1 + '!important}',
            '.difficulty-btn.selected{border-color:rgba(' + t.r1 + ',0.5)!important;background:rgba(' + t.r1 + ',0.15)!important}',
            '.topic-chip.selected{border-color:rgba(' + t.r1 + ',0.5)!important;background:rgba(' + t.r1 + ',0.15)!important}',
            '.topic-custom-row input:focus{border-color:' + t.c1 + '!important}',

            // ── Notes ──
            '.note-content h2{border-bottom-color:rgba(' + t.r1 + ',0.2)!important}',
            '.tooltip-box{border-color:rgba(' + t.r1 + ',0.3)!important}',

            // ── PDF loaded state ──
            '.pdf-loaded-bar{background:rgba(' + t.r1 + ',0.1)!important;border-color:rgba(' + t.r1 + ',0.3)!important}',

            // ── Option selected in tests ──
            '.option.selected{border-color:rgba(' + t.r1 + ',0.5)!important;background:rgba(' + t.r1 + ',0.1)!important}',

            // ── Level buttons (pdf-to-notes) ──
            '.level-btn:hover{background:rgba(' + t.r1 + ',0.2)!important;border-color:rgba(' + t.r1 + ',0.5)!important}',
            '.level-btn.selected{background:linear-gradient(135deg,' + t.c1 + ',' + t.c2 + ')!important;border-color:' + t.c1 + '!important}',

            // ── Aviator page specific ──
            '.aviator-input-area .input-wrapper textarea:focus{border-color:rgba(' + t.r1 + ',0.5)!important}',
            '.message.ai .message-avatar{background:linear-gradient(135deg,' + t.c1 + ',' + t.c2 + ')!important}',
            '.message.ai .message-bubble{background:rgba(' + t.r1 + ',0.2)!important;border-color:rgba(' + t.r1 + ',0.3)!important}',
            '.send-btn{background:linear-gradient(135deg,' + t.c1 + ',' + t.c2 + ')!important}',
            '.send-btn:hover{box-shadow:0 5px 15px rgba(' + t.r1 + ',0.4)!important}',
            '#chatInput:focus{border-color:rgba(' + t.r1 + ',0.7)!important}',
            '.spinner{border-color:rgba(' + t.r1 + ',0.3)!important;border-top-color:' + t.c1l + '!important}',
            '.info-panel{background:rgba(' + t.r1 + ',0.1)!important;border-color:rgba(' + t.r1 + ',0.3)!important}',
            '.info-panel h4{color:' + t.c1l + '!important}',
            '.messages-area::-webkit-scrollbar-thumb{background:rgba(' + t.r1 + ',0.5)!important}',

            // ── Dashboard stat borders ──
            '#totalTests{color:' + t.c1 + '!important}',
            '#avgScore{color:' + t.c1l + '!important}',
            '#bestScore{color:' + t.c2l + '!important}'
        ].join('\n');

        document.head.appendChild(s);
    }

    // Apply immediately (before DOM ready) to prevent flash
    var saved = localStorage.getItem('liftoffTheme') || 'ocean';
    applyTheme(saved);

    // Apply saved text size globally
    function applyTextSize(size) {
        var old = document.getElementById('liftoff-textsize-css');
        if (old) old.remove();
        var sizes = { small: '13px', normal: '15px', big: '18px' };
        var hSizes = { small: '16px', normal: '20px', big: '24px' };
        var h2Sizes = { small: '14px', normal: '17px', big: '21px' };
        var fs = sizes[size] || sizes.normal;
        var hs = hSizes[size] || hSizes.normal;
        var h2s = h2Sizes[size] || h2Sizes.normal;
        var s = document.createElement('style');
        s.id = 'liftoff-textsize-css';
        s.textContent = [
            'body,p,li,td,th,span,div,.note-content,.message-bubble,.test-card,.flashcard-back,.flashcard-front p{font-size:' + fs + '!important}',
            '.main h1,.header h1{font-size:' + hs + '!important}',
            'h2,h3,.note-content h2,.note-content h3{font-size:' + h2s + '!important}',
        ].join('\n');
        document.head.appendChild(s);
    }
    var textSize = localStorage.getItem('liftoffTextSize') || 'normal';
    if (textSize !== 'normal') applyTextSize(textSize);
    window.applyLiftoffTextSize = applyTextSize;

    // Expose API globally
    window.liftoffThemes = themes;
    window.applyLiftoffTheme = applyTheme;
    window.getCurrentTheme = function () { return localStorage.getItem('liftoffTheme') || 'ocean'; };
})();
