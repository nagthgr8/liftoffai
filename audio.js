// ── LiftOff Sound Effects ──
(function () {
    var sounds = {
        generate: new Audio('generate.mp3'),
        aviatormessage: new Audio('aviatormessage.mp3'),
        flashcardnew: new Audio('flashcardnew.mp3'),
        settingsopen: new Audio('settingsopen.mp3')
    };

    // Preload all
    Object.values(sounds).forEach(function (a) {
        a.preload = 'auto';
        a.volume = 0.5;
    });

    // Preload click as a src string — we clone it each time for reliability
    var clickSrc = 'click.mp3';
    // Warm up the cache
    var warmup = new Audio(clickSrc);
    warmup.preload = 'auto';
    warmup.volume = 0;
    warmup.play().then(function () { warmup.pause(); }).catch(function () {});

    function play(name) {
        if (name === 'click') {
            // Always create a fresh Audio so rapid/overlapping clicks work
            var c = new Audio(clickSrc);
            c.volume = 0.5;
            c.play().catch(function () {});
            return;
        }
        var s = sounds[name];
        if (!s) return;
        s.currentTime = 0;
        s.play().catch(function () {});
    }

    // Expose globally
    window.playSound = play;

    // ── Click sound on interactive elements ──
    // Use capture phase so we run before inline onclick handlers
    document.addEventListener('click', function (e) {
        var el = e.target.closest('button, .nav-item, .btn, .btn-primary, .btn-secondary, .level-btn, .difficulty-btn, .option, .upload-box, .zoom-btn, .theme-swatch, .textsize-option');
        if (!el) return;
        play('click');

        // If the element navigates away, delay navigation so the sound plays
        var nav = el.closest('[onclick]');
        if (nav) {
            var oc = nav.getAttribute('onclick') || '';
            var m = oc.match(/window\.location\.href\s*=\s*['"](.*?)['"]/);
            if (m) {
                e.preventDefault();
                e.stopImmediatePropagation();
                // Remove onclick temporarily so it doesn't fire
                nav.removeAttribute('onclick');
                var dest = m[1];
                setTimeout(function () { window.location.href = dest; }, 120);
            }
        }
    }, true); // <-- capture phase
})();
