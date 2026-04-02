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
                // Notify graphs to re-render with new theme colors
                window.dispatchEvent(new CustomEvent('spinorama-config-change'));
            });
        });

        window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', function () {
            const current = localStorage.getItem(STORAGE_KEY);
            if (current === 'system') {
                applyTheme('system');
            }
        });

        // Filters dropdown toggle (click-based, not hover)
        var filtersDropdown = document.getElementById('filters-dropdown');
        var filtersTrigger = document.getElementById('filters-dropdown-trigger');
        if (filtersDropdown && filtersTrigger) {
            filtersTrigger.addEventListener('click', function () {
                filtersDropdown.classList.toggle('is-active');
            });
        }
    }

    // --- Unit system (metric / imperial) ---
    var UNITS_KEY = 'spinorama-units';

    var conversions = {
        mm:  { factor: 0.03937008, label: 'in',  decimals: 1 },
        kg:  { factor: 2.20462,    label: 'lbs', decimals: 1 },
        m:   { factor: 3.28084,    label: 'ft',  decimals: 1 }
    };

    function applyUnits(system) {
        document.querySelectorAll('.unit-value').forEach(function (el) {
            var unit = el.dataset.unit;
            var raw = parseFloat(el.dataset.value);
            if (isNaN(raw)) return;
            if (system === 'imperial' && conversions[unit]) {
                var c = conversions[unit];
                el.textContent = (raw * c.factor).toFixed(c.decimals);
            } else {
                // metric: restore original
                var d = (unit === 'mm') ? 0 : 1;
                el.textContent = parseFloat(raw.toFixed(d)) + '';
            }
        });
        document.querySelectorAll('.unit-label').forEach(function (el) {
            var unit = el.dataset.unit;
            if (system === 'imperial' && conversions[unit]) {
                el.textContent = conversions[unit].label;
            } else {
                el.textContent = unit;
            }
        });
        // Update the size diagram if present
        var diagram = document.getElementById('size-diagram');
        if (diagram && diagram.dataset.height) {
            diagram.setAttribute('data-system', system);
            // Re-dispatch to let the inline script know (it reads data attrs)
            diagram.dispatchEvent(new Event('units-changed'));
        }
    }

    function updateUnitBtns(system) {
        document.querySelectorAll('.unit-btn').forEach(function (btn) {
            btn.classList.toggle('is-active', btn.dataset.units === system);
        });
    }

    function initUnits() {
        var system = localStorage.getItem(UNITS_KEY) || 'metric';
        applyUnits(system);
        updateUnitBtns(system);

        document.querySelectorAll('.unit-btn').forEach(function (btn) {
            btn.addEventListener('click', function () {
                var s = btn.dataset.units;
                localStorage.setItem(UNITS_KEY, s);
                applyUnits(s);
                updateUnitBtns(s);
            });
        });
    }

    // --- Graph columns (1, 2, 4 per row) ---
    var COLS_KEY = 'spinorama-columns';

    function applyColumns(cols) {
        document.documentElement.setAttribute('data-graph-cols', cols);
    }

    function updateColBtns(cols) {
        document.querySelectorAll('.col-btn').forEach(function (btn) {
            btn.classList.toggle('is-active', btn.dataset.cols === cols);
        });
    }

    function initColumns() {
        var cols = localStorage.getItem(COLS_KEY) || '1';
        applyColumns(cols);
        updateColBtns(cols);

        document.querySelectorAll('.col-btn').forEach(function (btn) {
            btn.addEventListener('click', function () {
                var c = btn.dataset.cols;
                localStorage.setItem(COLS_KEY, c);
                applyColumns(c);
                updateColBtns(c);
                window.dispatchEvent(new CustomEvent('spinorama-config-change'));
            });
        });
    }

    function initAll() {
        init();
        initUnits();
        initColumns();
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initAll);
    } else {
        initAll();
    }
})();
