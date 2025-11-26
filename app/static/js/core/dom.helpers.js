(function (global) {
    'use strict';

    if (typeof global.u === 'undefined') {
        console.error('Umbrella JS 未加载，无法初始化 DOMHelpers');
        return;
    }

    const umbrella = global.u;

    /**
     * 将输入转换为 umbrella 对象，支持选择器、Element 与现有实例。
     *
     * @param {string|HTMLElement|Array|Object} target 目标。
     * @param {HTMLElement|Object} [context] 限定上下文。
     * @returns {Object} umbrella 实例。
     */
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

    /**
     * 便捷方法：返回 umbrella 选择结果。
     *
     * @param {string|HTMLElement} selector 选择器或元素。
     * @param {HTMLElement} [context] 上下文。
     * @returns {Object} umbrella 实例。
     */
    function select(selector, context) {
        return toUmbrella(selector, context);
    }

    /**
     * 只取首个匹配的元素，返回 umbrella。
     *
     * @param {string|HTMLElement} selector 选择器或元素。
     * @param {HTMLElement} [context] 上下文。
     * @returns {Object} umbrella 实例。
     */
    function selectOne(selector, context) {
        const scoped = toUmbrella(selector, context);
        const first = scoped.first();
        return first ? umbrella(first) : umbrella([]);
    }

    /**
     * 将任意输入包装成 umbrella，供内部复用。
     *
     * @param {*} target 目标。
     * @param {HTMLElement} [context] 上下文。
     * @returns {Object} umbrella 实例。
     */
    function from(target, context) {
        return toUmbrella(target, context);
    }

    /**
     * DOMContentLoaded 就绪封装，直接执行或注册回调。
     *
     * @param {Function} callback 回调函数。
     * @returns {void}
     */
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

    /**
     * 读取或设置文本内容。
     *
     * @param {string|HTMLElement} target 目标。
     * @param {string} [value] 新文本。
     * @returns {Object|string} umbrella 实例或当前文本。
     */
    function text(target, value) {
        const element = from(target);
        if (!element.length) {
            return element;
        }
        return typeof value === 'undefined' ? element.text() : element.text(value);
    }

    /**
     * 读取或设置 innerHTML。
     *
     * @param {string|HTMLElement} target 目标。
     * @param {string} [value] 新 HTML。
     * @returns {Object|string} umbrella 实例或当前 HTML。
     */
    function html(target, value) {
        const element = from(target);
        if (!element.length) {
            return element;
        }
        return typeof value === 'undefined' ? element.html() : element.html(value);
    }

    /**
     * 表单值 getter/setter。
     *
     * @param {string|HTMLElement} target 目标。
     * @param {*} [newValue] 新值。
     * @returns {Object|*} umbrella 实例或当前值。
     */
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

    /**
     * 切换 disabled 属性。
     *
     * @param {string|HTMLElement} target 目标。
     * @param {boolean} disabled 是否禁用。
     * @returns {Object} umbrella 实例。
     */
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
