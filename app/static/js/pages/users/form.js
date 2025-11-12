/**
 * 用户表单脚本（创建/编辑）
 */

(function () {
    'use strict';

    let validator = null;
    let controller = null;

    document.addEventListener('DOMContentLoaded', function () {
        const form = document.getElementById('userForm');
        if (!form) {
            return;
        }

        const root = document.getElementById('user-form-root');
        const mode = root?.dataset.formMode || 'create';

        if (window.ResourceFormController) {
            controller = new window.ResourceFormController(form, {
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
            .onSuccess(function (event) {
                controller?.toggleLoading(true);
                event.target.submit();
            })
            .onFail(function () {
                window.toast?.error('请检查用户表单填写');
            });

        setupRealtimeValidation();
    });

    function setupRealtimeValidation() {
        const usernameInput = document.getElementById('username');
        const passwordInput = document.getElementById('password');
        const roleSelect = document.getElementById('role');

        usernameInput?.addEventListener('blur', function () {
            validator?.revalidateField('#username');
        });

        passwordInput?.addEventListener('blur', function () {
            validator?.revalidateField('#password');
        });

        roleSelect?.addEventListener('change', function () {
            validator?.revalidateField('#role');
        });
    }
})();
