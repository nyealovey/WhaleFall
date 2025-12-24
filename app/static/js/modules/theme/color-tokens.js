(function (global) {
    'use strict';

    const CHART_COLOR_KEYS = Array.from({ length: 22 }, (_, index) => `--chart-color-${index + 1}`);
    const FALLBACK_CHART_TOKENS = [
        '--accent-primary',
        '--status-info',
        '--status-success',
        '--status-warning',
        '--status-danger',
        '--orange-base',
    ];
    const VARIANT_TRANSFORM_PRESETS = {
        default: [
            {},
            { lightness: 0.2 },
            { lightness: -0.2 },
            { saturation: 0.25 },
            { saturation: -0.25 },
            { hue: 24 },
            { hue: -24 },
            { lightness: 0.32, saturation: -0.12 },
            { lightness: -0.32, saturation: 0.12 },
            { hue: 48, lightness: 0.08 },
            { hue: -48, lightness: -0.08 },
            { saturation: 0.18, lightness: 0.12 },
            { saturation: -0.18, lightness: -0.12 },
        ],
        contrast: [
            {},
            { hue: 30 },
            { hue: -30 },
            { saturation: 0.35 },
            { saturation: -0.35 },
            { lightness: 0.28 },
            { lightness: -0.28 },
        ],
    };

    let parserElement = null;
    let cachedPaletteSignature = null;
    let cachedBasePalette = [];
    const sequentialCache = new Map();
    let warnedChartPaletteMissing = false;

    function getStyles() {
        return getComputedStyle(document.documentElement);
    }

    function resolveCssVar(name) {
        return getStyles().getPropertyValue(name)?.trim() || '';
    }

    function clamp(value, min, max) {
        if (Number.isNaN(value)) {
            return min;
        }
        return Math.min(Math.max(value, min), max);
    }

    function ensureParserElement() {
        if (parserElement) {
            return parserElement;
        }
        const span = document.createElement('span');
        span.style.position = 'absolute';
        span.style.left = '-9999px';
        span.style.top = '-9999px';
        span.style.pointerEvents = 'none';
        span.style.opacity = '0';
        span.style.zIndex = '-1';
        (document.head || document.documentElement).appendChild(span);
        parserElement = span;
        return parserElement;
    }

    function parseComputedColor(value) {
        if (!value) {
            return null;
        }
        const match = value.match(/rgba?\(([^)]+)\)/i);
        if (!match) {
            return null;
        }
        const parts = match[1].trim().split(/[\s,/]+/).filter(Boolean);
        if (parts.length < 3) {
            return null;
        }
        const r = parseFloat(parts[0]);
        const g = parseFloat(parts[1]);
        const b = parseFloat(parts[2]);
        const a = parts[3] !== undefined ? parseFloat(parts[3]) : 1;
        if ([r, g, b].some((component) => Number.isNaN(component))) {
            return null;
        }
        return { r, g, b, a: Number.isNaN(a) ? 1 : clamp(a, 0, 1) };
    }

    function resolveColorToRgba(color) {
        const normalized = (color || '').trim();
        if (!normalized) {
            return null;
        }
        const element = ensureParserElement();
        element.style.color = '';
        element.style.color = normalized;
        const computed = getComputedStyle(element).color;
        return parseComputedColor(computed);
    }

    function toCssColor(rgba) {
        if (!rgba) {
            return '';
        }
        const r = Math.round(clamp(rgba.r, 0, 255));
        const g = Math.round(clamp(rgba.g, 0, 255));
        const b = Math.round(clamp(rgba.b, 0, 255));
        const a = clamp(rgba.a ?? 1, 0, 1);
        if (a >= 0.999) {
            return `rgb(${r}, ${g}, ${b})`;
        }
        return `rgba(${r}, ${g}, ${b}, ${Math.round(a * 1000) / 1000})`;
    }

    function rgbToHsl(rgba) {
        const r = clamp(rgba.r, 0, 255) / 255;
        const g = clamp(rgba.g, 0, 255) / 255;
        const b = clamp(rgba.b, 0, 255) / 255;
        const max = Math.max(r, g, b);
        const min = Math.min(r, g, b);
        let h = 0;
        let s = 0;
        const l = (max + min) / 2;
        const delta = max - min;
        if (delta !== 0) {
            s = l > 0.5 ? delta / (2 - max - min) : delta / (max + min);
            switch (max) {
                case r:
                    h = (g - b) / delta + (g < b ? 6 : 0);
                    break;
                case g:
                    h = (b - r) / delta + 2;
                    break;
                default:
                    h = (r - g) / delta + 4;
                    break;
            }
            h /= 6;
        }
        return { h: h * 360, s, l, a: rgba.a ?? 1 };
    }

    function hslToRgb(hsl) {
        const h = ((hsl.h % 360) + 360) % 360 / 360;
        const s = clamp(hsl.s, 0, 1);
        const l = clamp(hsl.l, 0, 1);
        if (s === 0) {
            const gray = Math.round(l * 255);
            return { r: gray, g: gray, b: gray, a: hsl.a ?? 1 };
        }
        const q = l < 0.5 ? l * (1 + s) : l + s - l * s;
        const p = 2 * l - q;

        function hueToRgb(t) {
            if (t < 0) t += 1;
            if (t > 1) t -= 1;
            if (t < 1 / 6) return p + (q - p) * 6 * t;
            if (t < 1 / 2) return q;
            if (t < 2 / 3) return p + (q - p) * (2 / 3 - t) * 6;
            return p;
        }

        const r = hueToRgb(h + 1 / 3);
        const g = hueToRgb(h);
        const b = hueToRgb(h - 1 / 3);
        return { r: r * 255, g: g * 255, b: b * 255, a: hsl.a ?? 1 };
    }

    function transformColor(color, transform = {}) {
        const rgba = resolveColorToRgba(color);
        if (!rgba) {
            return color;
        }
        const hsl = rgbToHsl(rgba);
        if (typeof transform.hue === 'number') {
            hsl.h = ((hsl.h + transform.hue) % 360 + 360) % 360;
        }
        if (typeof transform.saturation === 'number') {
            hsl.s = clamp(hsl.s + transform.saturation, 0, 1);
        }
        if (typeof transform.lightness === 'number') {
            hsl.l = clamp(hsl.l + transform.lightness, 0, 1);
        }
        const next = hslToRgb(hsl);
        const alpha = transform.alpha !== undefined ? clamp(transform.alpha, 0, 1) : (rgba.a ?? 1);
        return toCssColor({ ...next, a: alpha });
    }

    function normalizeColor(color) {
        return (color || '').trim();
    }

    function convertToCssColor(color) {
        const rgba = resolveColorToRgba(color);
        return rgba ? toCssColor(rgba) : color;
    }

    function withAlpha(color, alpha) {
        const normalized = normalizeColor(color);
        if (!normalized) {
            return '';
        }
        if (alpha === undefined || alpha === null) {
            return convertToCssColor(normalized);
        }
        const value = Number(alpha);
        if (Number.isNaN(value)) {
            return convertToCssColor(normalized);
        }
        if (value <= 0) {
            return 'transparent';
        }
        const rgba = resolveColorToRgba(normalized);
        if (!rgba) {
            return normalized;
        }
        return toCssColor({ ...rgba, a: clamp(value, 0, 1) });
    }

    function readChartPaletteFromCss() {
        return CHART_COLOR_KEYS.map((key) => resolveCssVar(key)).filter(Boolean);
    }

    function readChartFallbackFromTokens() {
        return FALLBACK_CHART_TOKENS.map((token) => resolveCssVar(token)).filter(Boolean);
    }

    function ensureBasePalette() {
        const palette = readChartPaletteFromCss();
        let effective = palette;
        if (!effective.length) {
            if (!warnedChartPaletteMissing) {
                warnedChartPaletteMissing = true;
                console.warn(
                    '未读取到 --chart-color-1..22，将退回到语义 token 生成图表色板（请在 variables.css 补齐 chart token）。'
                );
            }
            effective = readChartFallbackFromTokens();
        }

        if (!effective.length) {
            if (!warnedChartPaletteMissing) {
                warnedChartPaletteMissing = true;
                console.warn('图表色板 token 缺失且无法读取 fallback token，将退回到当前文本色生成色板。');
            }
            const fallback = getComputedStyle(document.documentElement).color;
            effective = fallback ? [fallback] : [];
        }

        const signature = effective.join('|');
        if (signature !== cachedPaletteSignature) {
            cachedPaletteSignature = signature;
            cachedBasePalette = effective.slice();
            sequentialCache.clear();
        }
        return cachedBasePalette.slice();
    }

    const UNSAFE_KEYS = ['__proto__', 'prototype', 'constructor'];
    const isSafeKey = (key) => {
        const normalized = typeof key === 'number' ? String(key) : key;
        return typeof normalized === 'string' && !UNSAFE_KEYS.includes(normalized);
    };

    function getVariantTransforms(strategy) {
        if (strategy === 'contrast') {
            return VARIANT_TRANSFORM_PRESETS.contrast;
        }
        return VARIANT_TRANSFORM_PRESETS.default;
    }

    function applyVariant(color, transform) {
        if (!transform || Object.keys(transform).length === 0) {
            return convertToCssColor(color);
        }
        return transformColor(color, transform);
    }

    function buildSequentialPalette(size, strategy) {
        const baseColors = ensureBasePalette();
        const target = Math.max(1, Number(size) || 1);
        const transforms = getVariantTransforms(strategy);
        const palette = [];
        let round = 0;
        while (palette.length < target) {
            const transform = transforms[round % transforms.length];
            baseColors.forEach((color) => {
                if (palette.length >= target) {
                    return;
                }
                palette.push(applyVariant(color, transform));
            });
            round += 1;
        }
        return palette.slice(0, target);
    }

    function getSequentialPalette(size, options = {}) {
        const target = Math.max(1, Number(size) || 1);
        const strategy = options.strategy || 'default';
        ensureBasePalette();
        const cacheKey = `${target}:${strategy}:${cachedPaletteSignature}`;
        if (!sequentialCache.has(cacheKey)) {
            sequentialCache.set(cacheKey, buildSequentialPalette(target, strategy));
        }
        return sequentialCache.get(cacheKey).slice(0, target);
    }

    function getChartPalette(size) {
        const base = ensureBasePalette();
        if (!size) {
            return base.slice().map((color) => convertToCssColor(color));
        }
        const target = Math.max(1, Number(size) || 1);
        if (base.length >= target) {
            return base.slice(0, target).map((color) => convertToCssColor(color));
        }
        return getSequentialPalette(target);
    }

    function getChartColor(index, alpha) {
        const palette = getSequentialPalette(Math.max((index ?? 0) + 1, 1));
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
        let token = '--status-info';
        if (isSafeKey(status)) {
            switch (status) {
                case 'success':
                    token = '--status-success';
                    break;
                case 'warning':
                    token = '--status-warning';
                    break;
                case 'danger':
                case 'error':
                    token = '--status-danger';
                    break;
                case 'info':
                    token = '--status-info';
                    break;
                default:
                    break;
            }
        }
        return withAlpha(resolveCssVar(token), alpha);
    }

    function getOrangeColor(options = {}) {
        let toneKey = '--orange-base';
        if (isSafeKey(options.tone)) {
            switch (options.tone) {
                case 'muted':
                    toneKey = '--orange-muted';
                    break;
                case 'strong':
                    toneKey = '--orange-strong';
                    break;
                case 'highlight':
                    toneKey = '--orange-highlight';
                    break;
                case 'contrast':
                    toneKey = '--orange-contrast';
                    break;
                default:
                    toneKey = '--orange-base';
                    break;
            }
        }
        const presetAlphaTokens = {
            0.2: '--orange-alpha-20',
            0.4: '--orange-alpha-40',
        };
        const normalizedAlpha = options.alpha === undefined ? 1 : Number(options.alpha);
        if (
            (!options.tone || options.tone === 'base')
            && !Number.isNaN(normalizedAlpha)
            && normalizedAlpha > 0
            && normalizedAlpha < 1
        ) {
            let presetToken = null;
            if (normalizedAlpha === 0.2) {
                presetToken = presetAlphaTokens[0.2];
            } else if (normalizedAlpha === 0.4) {
                presetToken = presetAlphaTokens[0.4];
            }
            if (presetToken) {
                const preset = resolveCssVar(presetToken);
                if (preset) {
                    return convertToCssColor(preset);
                }
            }
        }
        return withAlpha(resolveCssVar(toneKey), options.alpha);
    }

    function generateVariants(color) {
        return getVariantTransforms('default').map((transform) => applyVariant(color, transform));
    }

    global.ColorTokens = {
        resolveCssVar,
        withAlpha,
        getChartPalette,
        getChartColor,
        getAccentColor,
        getSurfaceColor,
        getStatusColor,
        getSequentialPalette,
        getOrangeColor,
        generateVariants,
    };
})(window);
