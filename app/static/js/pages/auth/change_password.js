/**
 * 修改密码页面 JavaScript
 * 使用 Just-Validate 统一表单验证，并保留密码强度提示等功能。
 */

let changePasswordValidator = null;

document.addEventListener('DOMContentLoaded', function () {
    initializeChangePasswordPage();
});

function initializeChangePasswordPage() {
    initializePasswordToggles();
    initializePasswordStrength();
    initializeFormValidation();
}

function initializePasswordToggles() {
    const toggles = [
        { button: 'toggleOldPassword', input: 'old_password' },
        { button: 'toggleNewPassword', input: 'new_password' },
        { button: 'toggleConfirmPassword', input: 'confirm_password' },
    ];

    toggles.forEach(({ button, input }) => {
        const toggleButton = document.getElementById(button);
        const inputElement = document.getElementById(input);

        if (toggleButton && inputElement) {
            toggleButton.addEventListener('click', function () {
                togglePasswordVisibility(inputElement, this);
            });
        }
    });
}

function togglePasswordVisibility(inputElement, toggleButton) {
    const type = inputElement.getAttribute('type') === 'password' ? 'text' : 'password';
    inputElement.setAttribute('type', type);

    const icon = toggleButton.querySelector('i');
    if (icon) {
        icon.classList.toggle('fa-eye');
        icon.classList.toggle('fa-eye-slash');
    }

    const title = type === 'password' ? '显示密码' : '隐藏密码';
    toggleButton.setAttribute('title', title);
}

function initializePasswordStrength() {
    const newPasswordInput = document.getElementById('new_password');

    if (newPasswordInput) {
        newPasswordInput.addEventListener('input', function () {
            const password = this.value;
            const strength = getPasswordStrength(password);
            updatePasswordStrength(strength);
            updatePasswordRequirements(password);

            if (changePasswordValidator) {
                changePasswordValidator.revalidateField('#new_password');
                changePasswordValidator.revalidateField('#confirm_password');
            }
        });

        updatePasswordRequirements(newPasswordInput.value || '');
    }
}

function getPasswordStrength(password) {
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
    } else if (strength < 3) {
        feedback = '密码强度：中等';
    } else if (strength < 5) {
        feedback = '密码强度：良好';
    } else if (strength < 6) {
        feedback = '密码强度：强';
    } else {
        feedback = '密码强度：非常强';
    }

    return { strength, feedback };
}

function updatePasswordStrength(strengthData) {
    const strengthBar = document.getElementById('passwordStrength');
    const strengthText = document.getElementById('passwordStrengthText');

    if (!strengthBar || !strengthText) return;

    const { strength, feedback } = strengthData;

    let percentage = 0;
    let colorClass = 'bg-secondary';

    if (strength >= 1) {
        percentage = 20;
        colorClass = 'bg-danger';
    }
    if (strength >= 3) {
        percentage = 40;
        colorClass = 'bg-warning';
    }
    if (strength >= 4) {
        percentage = 60;
        colorClass = 'bg-info';
    }
    if (strength >= 5) {
        percentage = 80;
        colorClass = 'bg-success';
    }
    if (strength >= 6) {
        percentage = 100;
        colorClass = 'bg-success';
    }

    strengthBar.style.width = percentage + '%';
    strengthBar.className = 'password-strength-fill ' + colorClass;
    strengthText.textContent = feedback;
}

function updatePasswordRequirements(password) {
    const requirementsContainer = document.getElementById('passwordRequirements');
    if (!requirementsContainer) return;

    const requirements = checkPasswordRequirements(password);

    let html = '<h6>密码要求:</h6><ul>';
    requirements.forEach((req) => {
        const statusClass = req.met ? 'requirement-met' : 'requirement-not-met';
        const icon = req.met ? '✓' : '✗';
        html += `<li class="${statusClass}">${icon} ${req.text}</li>`;
    });
    html += '</ul>';

    requirementsContainer.innerHTML = html;
}

function checkPasswordRequirements(password) {
    return [
        { text: '至少6个字符', met: password.length >= 6 },
        { text: '至少8个字符', met: password.length >= 8 },
        { text: '包含小写字母', met: /[a-z]/.test(password) },
        { text: '包含大写字母', met: /[A-Z]/.test(password) },
        { text: '包含数字', met: /[0-9]/.test(password) },
        { text: '包含特殊字符', met: /[^A-Za-z0-9]/.test(password) },
    ];
}

function initializeFormValidation() {
    if (!window.FormValidator || !window.ValidationRules) {
        console.error('表单校验模块未正确加载');
        return;
    }

    changePasswordValidator = window.FormValidator.create('#changePasswordForm');
    if (!changePasswordValidator) {
        return;
    }

    const newPasswordRules = window.ValidationRules.auth.changePassword.newPassword.slice();
    newPasswordRules.push({
        validator: function (value, fields) {
            const oldPasswordField = fields['#old_password'];
            const oldPassword = oldPasswordField ? oldPasswordField.elem.value : '';
            return value !== oldPassword;
        },
        errorMessage: '新密码不能与当前密码相同',
    });
    newPasswordRules.push({
        validator: function (value) {
            return getPasswordStrength(value).strength >= 2;
        },
        errorMessage: '密码强度太弱，请使用更复杂的密码',
    });

    changePasswordValidator
        .useRules('#old_password', window.ValidationRules.auth.changePassword.oldPassword)
        .useRules('#new_password', newPasswordRules)
        .useRules('#confirm_password', window.ValidationRules.auth.changePassword.confirmPassword)
        .onSuccess(function (event) {
            const form = event.target;
            showLoadingState(form);
            form.submit();
        })
        .onFail(function () {
            toast.error('请检查密码修改表单填写');
        });

    const oldPasswordInput = document.getElementById('old_password');
    if (oldPasswordInput) {
        oldPasswordInput.addEventListener('blur', function () {
            changePasswordValidator.revalidateField('#old_password');
            changePasswordValidator.revalidateField('#new_password');
        });
    }

    const confirmPasswordInput = document.getElementById('confirm_password');
    if (confirmPasswordInput) {
        confirmPasswordInput.addEventListener('input', function () {
            changePasswordValidator.revalidateField('#confirm_password');
        });
    }
}

function showLoadingState(form) {
    const submitBtn = form.querySelector('button[type="submit"]');
    if (submitBtn) {
        submitBtn.dataset.originalText = submitBtn.dataset.originalText || submitBtn.innerHTML;
        submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>更新中...';
        submitBtn.disabled = true;
    }
}

function hideLoadingState(form) {
    const submitBtn = form.querySelector('button[type="submit"]');
    if (submitBtn && submitBtn.dataset.originalText) {
        submitBtn.innerHTML = submitBtn.dataset.originalText;
        submitBtn.disabled = false;
    }
}

window.togglePasswordVisibility = togglePasswordVisibility;
window.getPasswordStrength = getPasswordStrength;
window.updatePasswordStrength = updatePasswordStrength;
window.updatePasswordRequirements = updatePasswordRequirements;
