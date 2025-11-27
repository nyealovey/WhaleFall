(function (global) {
    'use strict';

    function getStyles() {
        return getComputedStyle(document.documentElement);
    }

    function resolveCssVar(name) {
        return getStyles().getPropertyValue(name)?.trim() || '';
    }

    function withAlpha(color, alpha) {
        if (!color) {
            return '';
        }
        if (alpha === undefined || alpha === null || alpha >= 1) {
            return color;
        }
        if (alpha <= 0) {
            return 'transparent';
        }
        const percent = Math.round(alpha * 100);
        return `color-mix(in srgb, ${color} ${percent}%, transparent)`;
    }

    function getChartPalette() {
        const keys = [
            '--chart-color-1',
            '--chart-color-2',
            '--chart-color-3',
            '--chart-color-4',
            '--chart-color-5',
        ];
        return keys
            .map((key) => resolveCssVar(key))
            .filter((value) => Boolean(value));
    }

    function getChartColor(index, alpha) {
        const palette = getChartPalette();
        if (!palette.length) {
            return withAlpha(resolveCssVar('--accent-primary'), alpha);
        }
        const base = palette[index % palette.length];
        return withAlpha(base, alpha);
    }

    function getAccentColor(alpha) {
        return withAlpha(resolveCssVar('--accent-primary'), alpha);
    }

    function getSurfaceColor(alpha) {
        return withAlpha(resolveCssVar('--surface-elevated'), alpha);
    }

    function getStatusColor(status, alpha) {
        const map = {
            success: '--success-color',
            warning: '--warning-color',
            danger: '--danger-color',
            error: '--danger-color',
            info: '--info-color',
        };
        const token = map[status] || '--info-color';
        return withAlpha(resolveCssVar(token), alpha);
    }

    global.ColorTokens = {
        resolveCssVar,
        withAlpha,
        getChartPalette,
        getChartColor,
        getAccentColor,
        getSurfaceColor,
        getStatusColor,
    };
})(window);
