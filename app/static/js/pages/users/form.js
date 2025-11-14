/**
 * 用户表单脚本（创建/编辑）
 */
(function (window) {
    'use strict';

    const helpers = window.DOMHelpers;
    if (!helpers) {
        console.error('DOMHelpers 未初始化，无法加载用户表单脚本');
        return;
    }

    const { ready, selectOne } = helpers;

    let validator = null;
    let controller = null;

    ready(() => {
        const form = selectOne('#userForm');
        const formElement = form.first();
        if (!formElement) {
            return;
        }

        const root = selectOne('#user-form-root').first();
        const mode = root?.dataset?.formMode || 'create';

        if (window.ResourceFormController) {
            controller = new window.ResourceFormController(formElement, {
                loadingText: mode === 'edit' ? '保存中...' : '创建中...',
            });
        }

        if (!window.FormValidator || !window.ValidationRules) {
            console.error('表单校验模块未正确加载');
            return;
        }

        validator = window.FormValidator.create('#userForm');
        if (!validator) {
            return;
        }

        validator.useRules('#username', window.ValidationRules.user.username);
        validator.useRules('#role', window.ValidationRules.user.role);

        if (mode === 'edit') {
            validator.useRules('#password', window.ValidationRules.user.passwordOptional);
        } else {
            validator.useRules('#password', window.ValidationRules.user.passwordRequired);
        }

        validator
            .onSuccess((event) => {
                controller?.toggleLoading(true);
                event.target.submit();
            })
            .onFail(() => {
                window.toast.error('请检查用户表单填写');
            });

        setupRealtimeValidation();
    });

    function setupRealtimeValidation() {
        const fields = [
            { selector: '#username', eventName: 'blur' },
            { selector: '#password', eventName: 'blur' },
            { selector: '#role', eventName: 'change' },
        ];

        fields.forEach(({ selector, eventName }) => {
            const input = selectOne(selector);
            if (!input.length) {
                return;
            }
            input.on(eventName, () => {
                validator?.revalidateField(selector);
            });
        });
    }
})(window);
