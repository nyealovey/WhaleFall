/**
 * FormValidator - JustValidate 轻量封装
 *
 * 提供统一的表单校验初始化方法，并预置 Bootstrap 友好的样式。
 */
(function (global) {
    'use strict';

    /**
     * 确保 JustValidate 已加载。
     *
     * @param {Window} [context=global] 需要检测的全局对象。
     * @returns {boolean} 库存在返回 true，否则 false。
     */
    function ensureLibrary(context) {
        var host = context || global;
        if (!host.JustValidate) {
            console.error('JustValidate 未加载，无法初始化表单校验');
            return false;
        }
        return true;
    }

    /**
     * 接受单个/数组/工厂函数，统一成数组。
     *
     * @param {any|any[]|Function} rules 单个规则、规则数组或返回规则的函数。
     * @returns {Array} 规则数组。
     */
    function toArray(rules) {
        if (!rules) {
            return [];
        }
        if (Array.isArray(rules)) {
            return rules;
        }
        if (typeof rules === 'function') {
            return toArray(rules());
        }
        return [rules];
    }

    /**
     * 创建表单校验实例，封装常用链式 API。
     *
     * @param {string|HTMLElement} formSelector 表单选择器或 DOM 元素。
     * @param {Object} [options] JustValidate 原生配置。
     * @returns {Object|null} 封装后的 API，如果库缺失则返回 null。
     */
    function createValidator(formSelector, options) {
        if (!ensureLibrary(global)) {
            return null;
        }

        var config = Object.assign(
            {
                errorFieldCssClass: 'is-invalid',
                successFieldCssClass: 'is-valid',
                errorLabelCssClass: 'invalid-feedback',
                focusInvalidField: true,
                lockForm: true,
            },
            options || {}
        );

        var validator = new global.JustValidate(formSelector, config);

        var api = {
            addField: function addField(selector, rules) {
                validator.addField(selector, toArray(rules));
                return api;
            },
            useRules: function useRules(selector, rules) {
                return api.addField(selector, rules);
            },
            addRequired: function addRequired(selector, message) {
                return api.addField(selector, [
                    {
                        rule: 'required',
                        errorMessage: message,
                    },
                ]);
            },
            addMinLength: function addMinLength(selector, length, message) {
                return api.addField(selector, [
                    {
                        rule: 'required',
                        errorMessage: message,
                    },
                    {
                        rule: 'minLength',
                        value: length,
                        errorMessage: message,
                    },
                ]);
            },
            addNumberRange: function addNumberRange(selector, min, max, message) {
                return api.addField(selector, [
                    {
                        rule: 'required',
                        errorMessage: message,
                    },
                    {
                        rule: 'number',
                        errorMessage: message,
                    },
                    {
                        rule: 'minNumber',
                        value: min,
                        errorMessage: message,
                    },
                    {
                        rule: 'maxNumber',
                        value: max,
                        errorMessage: message,
                    },
                ]);
            },
            addCustomRule: function addCustomRule(selector, validatorFn, message) {
                return api.addField(selector, [
                    {
                        validator: validatorFn,
                        errorMessage: message,
                    },
                ]);
            },
            onSuccess: function onSuccess(callback) {
                validator.onSuccess(function (event) {
                    if (typeof callback === 'function') {
                        callback(event, api);
                    }
                });
                return api;
            },
            onFail: function onFail(callback) {
                validator.onFail(function (fields) {
                    if (typeof callback === 'function') {
                        callback(fields, api);
                    }
                });
                return api;
            },
            revalidateField: function revalidateField(selector) {
                if (typeof validator.revalidateField === 'function') {
                    validator.revalidateField(selector);
                } else if (typeof validator.revalidate === 'function') {
                    validator.revalidate();
                }
                return api;
            },
            revalidate: function revalidate() {
                if (typeof validator.revalidate === 'function') {
                    validator.revalidate();
                }
                return api;
            },
            destroy: function destroy() {
                if (typeof validator.destroy === 'function') {
                    validator.destroy();
                }
            },
            instance: validator,
        };

        return api;
    }

    global.FormValidator = {
        create: createValidator,
    };
})(window);
