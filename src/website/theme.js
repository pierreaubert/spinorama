// Theme Manager for Spinorama
// Manages light/dark theme toggle with localStorage persistence

(function () {
    const STORAGE_KEY = 'spinorama-theme';

    function applyTheme(theme) {
        const root = document.documentElement;
        if (theme === 'light' || theme === 'dark') {
            root.setAttribute('data-theme', theme);
        } else {
            // system: follow OS preference
            const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
            root.setAttribute('data-theme', prefersDark ? 'dark' : 'light');
        }
    }

    function updateToggleUI(theme) {
        document.querySelectorAll('.theme-toggle-btn').forEach(function (btn) {
            btn.classList.toggle('is-active', btn.dataset.theme === theme);
        });
    }

    function init() {
        const stored = localStorage.getItem(STORAGE_KEY);
        const theme = stored || 'light';
        applyTheme(theme);
        updateToggleUI(theme);

        document.querySelectorAll('.theme-toggle').forEach(function (toggle) {
            toggle.addEventListener('click', function (e) {
                const btn = e.target.closest('.theme-toggle-btn');
                if (!btn) return;
                const newTheme = btn.dataset.theme;
                localStorage.setItem(STORAGE_KEY, newTheme);
                applyTheme(newTheme);
                updateToggleUI(newTheme);
            });
        });

        window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', function () {
            const current = localStorage.getItem(STORAGE_KEY);
            if (current === 'system') {
                applyTheme('system');
            }
        });
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
