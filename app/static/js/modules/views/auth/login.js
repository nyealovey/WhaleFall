/**
 * 登录页面脚本：统一使用 Umbrella JS 处理 DOM/事件，并依赖表单校验封装。
 */
function mountLoginPage(global) {
    'use strict';

    const helpers = global.DOMHelpers;

    if (!helpers) {
        console.error('DOMHelpers 未初始化，无法加载登录页面脚本');
        return;
    }

    const { ready, selectOne, from, value } = helpers;
    let loginFormValidator = null;

    ready(() => {
        initializePasswordToggle();
        initializeFormValidation();
        initializePasswordStrengthWatcher();
    });

    /**
     * 绑定密码显示/隐藏按钮。
     */
    function initializePasswordToggle() {
        const togglePassword = selectOne('#togglePassword');
        const passwordInput = selectOne('#password');

        if (!togglePassword.length || !passwordInput.length) {
            return;
        }

        togglePassword.on('click', (event) => {
            const trigger = from(event.currentTarget);
            togglePasswordVisibility(passwordInput, trigger);
        });
    }

    /**
     * 切换密码可见性，同时更新图标与标题提示。
     */
    function togglePasswordVisibility(passwordInput, toggleButton) {
        const currentType = passwordInput.attr('type') === 'password' ? 'text' : 'password';
        passwordInput.attr('type', currentType);

        const icon = toggleButton.find('i');
        if (icon.length) {
            icon.toggleClass('fa-eye');
            icon.toggleClass('fa-eye-slash');
        }

        toggleButton.attr('title', currentType === 'password' ? '显示密码' : '隐藏密码');
    }

    /**
     * 初始化 JustValidate，校验用户名/密码。
     */
    function initializeFormValidation() {
        if (!global.FormValidator || !global.ValidationRules) {
            console.error('表单校验模块未正确加载');
            return;
        }

        loginFormValidator = global.FormValidator.create('#loginForm');
        if (!loginFormValidator) {
            return;
        }

        loginFormValidator
            .useRules('#username', global.ValidationRules.auth.login.username)
            .useRules('#password', global.ValidationRules.auth.login.password)
            .onSuccess((event) => {
                const form = event.target;
                showLoadingState(form);
                form.submit();
            })
            .onFail(() => {
                global.toast.error('请输入正确的用户名和密码');
            });
    }

    /**
     * 监听密码输入并更新强度条。
     */
    function initializePasswordStrengthWatcher() {
        const passwordInput = selectOne('#password');
        if (!passwordInput.length) {
            return;
        }

        passwordInput.on('input', (event) => {
            updatePasswordStrength(event.target.value);
        });

        updatePasswordStrength(value(passwordInput) || '');
    }

    /**
     * 提交时禁用按钮并展示加载态，防止重复提交。
     */
    function showLoadingState(form) {
        const formWrapper = from(form);
        const submitBtn = formWrapper.find('button[type="submit"]');
        if (!submitBtn.length) {
            return;
        }
        submitBtn.html('<i class="fas fa-spinner fa-spin me-2"></i>登录中...');
        submitBtn.attr('disabled', 'disabled');
    }

    /**
     * 恢复提交按钮的默认文案和可用状态。
     */
    function hideLoadingState(form) {
        const formWrapper = from(form);
        const submitBtn = formWrapper.find('button[type="submit"]');
        if (!submitBtn.length) {
            return;
        }
        submitBtn.html('<i class="fas fa-sign-in-alt me-2"></i>登录');
        submitBtn.attr('disabled', null);
    }

    /**
     * 简易密码强度评分：长度/大小写/数字/特殊符号。
     */
    function checkPasswordStrength(password) {
        let strength = 0;
        let feedback = '';

        if (password.length >= 6) strength++;
        if (password.length >= 8) strength++;
        if (/[a-z]/.test(password)) strength++;
        if (/[A-Z]/.test(password)) strength++;
        if (/[0-9]/.test(password)) strength++;
        if (/[^A-Za-z0-9]/.test(password)) strength++;

        if (strength < 2) {
            feedback = '密码强度：弱';
        } else if (strength < 4) {
            feedback = '密码强度：中等';
        } else if (strength < 6) {
            feedback = '密码强度：良好';
        } else {
            feedback = '密码强度：强';
        }

        return { strength, feedback };
    }

    /**
     * 重置强度条样式，避免叠加 class。
     */
    function resetStrengthBarClasses(strengthBar) {
        strengthBar.attr('class', 'password-strength-bar');
    }

    /**
     * 根据密码强度更新提示文案与样式。
     */
    function updatePasswordStrength(password) {
        const strengthBar = selectOne('.password-strength-bar');
        if (!strengthBar.length) {
            return;
        }
        const strengthText = selectOne('.password-strength-text');
        const result = checkPasswordStrength(password || '');

        resetStrengthBarClasses(strengthBar);

        if (result.strength < 2) {
            strengthBar.addClass('weak');
        } else if (result.strength < 4) {
            strengthBar.addClass('fair');
        } else if (result.strength < 6) {
            strengthBar.addClass('good');
        } else {
            strengthBar.addClass('strong');
        }

        if (strengthText.length) {
            strengthText.text(result.feedback);
        }
    }

    global.togglePasswordVisibility = togglePasswordVisibility;
    global.hideLoadingState = hideLoadingState;
    global.updatePasswordStrength = updatePasswordStrength;
}

window.LoginPage = {
    mount: function () {
        mountLoginPage(window);
    },
};
