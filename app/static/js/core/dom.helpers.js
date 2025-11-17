(function (global) {
    'use strict';

    if (typeof global.u === 'undefined') {
        console.error('Umbrella JS 未加载，无法初始化 DOMHelpers');
        return;
    }

    const umbrella = global.u;

    function toUmbrella(target, context) {
        if (target instanceof umbrella) {
            return target;
        }
        if (typeof target === 'string') {
            if (context) {
                return context instanceof umbrella ? context.find(target) : umbrella(target, context);
            }
            return umbrella(target);
        }
        if (!target) {
            return umbrella([]);
        }
        if (target.nodeType || target === window || target === document) {
            return umbrella(target);
        }
        if (Array.isArray(target) || target.length) {
            return umbrella(target);
        }
        return umbrella([]);
    }

    function select(selector, context) {
        return toUmbrella(selector, context);
    }

    function selectOne(selector, context) {
        const scoped = toUmbrella(selector, context);
        const first = scoped.first();
        return first ? umbrella(first) : umbrella([]);
    }

    function from(target, context) {
        return toUmbrella(target, context);
    }

    function ready(callback) {
        if (typeof callback !== 'function') {
            return;
        }
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', callback, { once: true });
        } else {
            callback();
        }
    }

    function text(target, value) {
        const element = from(target);
        if (!element.length) {
            return element;
        }
        return typeof value === 'undefined' ? element.text() : element.text(value);
    }

    function html(target, value) {
        const element = from(target);
        if (!element.length) {
            return element;
        }
        return typeof value === 'undefined' ? element.html() : element.html(value);
    }

    function value(target, newValue) {
        const element = from(target);
        if (!element.length) {
            return undefined;
        }
        if (typeof newValue === 'undefined') {
            const node = element.first();
            return node && Object.prototype.hasOwnProperty.call(node, 'value') ? node.value : undefined;
        }
        element.each((node) => {
            if ('value' in node) {
                node.value = newValue;
            }
        });
        return element;
    }

    function toggleDisabled(target, disabled) {
        const element = from(target);
        if (!element.length) {
            return element;
        }
        if (disabled) {
            element.attr('disabled', 'disabled');
        } else {
            element.attr('disabled', null);
        }
        return element;
    }

    global.DOMHelpers = Object.freeze({
        ready,
        select,
        selectOne,
        from,
        text,
        html,
        value,
        toggleDisabled,
    });
})(window);
