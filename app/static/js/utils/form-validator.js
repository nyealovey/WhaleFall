/**
 * FormValidator - JustValidate 轻量封装
 *
 * 提供统一的表单校验初始化方法，并预置 Bootstrap 友好的样式。
 */
(function (global) {
    'use strict';

    function ensureLibrary() {
        if (!global.JustValidate) {
            console.error('JustValidate 未加载，无法初始化表单校验');
            return false;
        }
        return true;
    }

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

    function createValidator(formSelector, options) {
        if (!ensureLibrary()) {
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
