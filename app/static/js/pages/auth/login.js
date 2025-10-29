/**
 * 登录页面 JavaScript
 * 统一使用 Just-Validate 进行表单验证。
 */

let loginFormValidator = null;

document.addEventListener('DOMContentLoaded', function () {
    initializeLoginPage();
});

function initializeLoginPage() {
    initializePasswordToggle();
    initializeFormValidation();
    initializePasswordStrengthWatcher();
}

function initializePasswordToggle() {
    const togglePassword = document.getElementById('togglePassword');
    const passwordInput = document.getElementById('password');

    if (togglePassword && passwordInput) {
        togglePassword.addEventListener('click', function () {
            togglePasswordVisibility(passwordInput, this);
        });
    }
}

function togglePasswordVisibility(passwordInput, toggleButton) {
    const type = passwordInput.getAttribute('type') === 'password' ? 'text' : 'password';
    passwordInput.setAttribute('type', type);

    const icon = toggleButton.querySelector('i');
    if (icon) {
        icon.classList.toggle('fa-eye');
        icon.classList.toggle('fa-eye-slash');
    }

    toggleButton.setAttribute('title', type === 'password' ? '显示密码' : '隐藏密码');
}

function initializeFormValidation() {
    if (!window.FormValidator || !window.ValidationRules) {
        console.error('表单校验模块未正确加载');
        return;
    }

    loginFormValidator = window.FormValidator.create('#loginForm');
    if (!loginFormValidator) {
        return;
    }

    loginFormValidator
        .useRules('#username', window.ValidationRules.auth.login.username)
        .useRules('#password', window.ValidationRules.auth.login.password)
        .onSuccess(function (event) {
            const form = event.target;
            showLoadingState(form);
            form.submit();
        })
        .onFail(function () {
            toast.error('请输入正确的用户名和密码');
        });
}

function initializePasswordStrengthWatcher() {
    const passwordInput = document.getElementById('password');

    if (!passwordInput) {
        return;
    }

    passwordInput.addEventListener('input', function () {
        updatePasswordStrength(this.value);
    });

    updatePasswordStrength(passwordInput.value || '');
}

function showLoadingState(form) {
    const submitBtn = form.querySelector('button[type="submit"]');
    if (submitBtn) {
        submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>登录中...';
        submitBtn.disabled = true;
    }
}

function hideLoadingState(form) {
    const submitBtn = form.querySelector('button[type="submit"]');
    if (submitBtn) {
        submitBtn.innerHTML = '<i class="fas fa-sign-in-alt me-2"></i>登录';
        submitBtn.disabled = false;
    }
}

function checkPasswordStrength(password) {
    var strength = 0;
    var feedback = '';

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

    return { strength: strength, feedback: feedback };
}

function updatePasswordStrength(password) {
    const strengthBar = document.querySelector('.password-strength-bar');
    const strengthText = document.querySelector('.password-strength-text');

    if (!strengthBar) {
        return;
    }

    const result = checkPasswordStrength(password);

    strengthBar.className = 'password-strength-bar';
    if (result.strength < 2) {
        strengthBar.classList.add('weak');
    } else if (result.strength < 4) {
        strengthBar.classList.add('fair');
    } else if (result.strength < 6) {
        strengthBar.classList.add('good');
    } else {
        strengthBar.classList.add('strong');
    }

    if (strengthText) {
        strengthText.textContent = result.feedback;
    }
}

window.togglePasswordVisibility = togglePasswordVisibility;
window.hideLoadingState = hideLoadingState;
window.updatePasswordStrength = updatePasswordStrength;
