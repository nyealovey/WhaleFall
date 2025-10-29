/**
 * 编辑凭据页面 JavaScript
 * 统一使用 Just-Validate 进行表单验证。
 */

let credentialEditValidator = null;

document.addEventListener('DOMContentLoaded', function () {
    initializeEditCredentialPage();
});

function initializeEditCredentialPage() {
    try {
        initializePasswordToggle();
        initializeCredentialTypeToggle();
        initializeFormValidation();
        initializePasswordStrengthWatcher();
    } catch (error) {
        console.error('编辑凭据页面初始化失败:', error);
    }
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

function togglePasswordVisibility(inputElement, toggleButton) {
    const type = inputElement.getAttribute('type') === 'password' ? 'text' : 'password';
    inputElement.setAttribute('type', type);

    const icon = toggleButton.querySelector('i');
    if (icon) {
        icon.classList.toggle('fa-eye');
        icon.classList.toggle('fa-eye-slash');
    }

    toggleButton.setAttribute('title', type === 'password' ? '显示密码' : '隐藏密码');
}

function initializeCredentialTypeToggle() {
    const credentialTypeSelect = document.getElementById('credential_type');
    const dbTypeSelect = document.getElementById('db_type');

    if (!credentialTypeSelect || !dbTypeSelect) {
        return;
    }

    credentialTypeSelect.addEventListener('change', function () {
        toggleDatabaseTypeField(this.value, dbTypeSelect);
    });

    toggleDatabaseTypeField(credentialTypeSelect.value, dbTypeSelect);
}

function toggleDatabaseTypeField(credentialType, dbTypeSelect) {
    const dbTypeDiv = dbTypeSelect.closest('.mb-3');

    if (!dbTypeDiv) {
        return;
    }

    if (credentialType === 'database') {
        dbTypeDiv.style.display = 'block';
        dbTypeDiv.classList.add('visible');
        dbTypeDiv.classList.remove('hidden');
        dbTypeSelect.required = true;
    } else {
        dbTypeDiv.style.display = 'none';
        dbTypeDiv.classList.add('hidden');
        dbTypeDiv.classList.remove('visible');
        dbTypeSelect.required = false;
        dbTypeSelect.value = '';
    }

    if (credentialEditValidator) {
        credentialEditValidator.revalidateField('#db_type');
    }
}

function initializeFormValidation() {
    if (!window.FormValidator || !window.ValidationRules) {
        console.error('表单校验模块未正确加载');
        return;
    }

    credentialEditValidator = window.FormValidator.create('#credentialForm');
    if (!credentialEditValidator) {
        return;
    }

    credentialEditValidator
        .useRules('#name', window.ValidationRules.credential.name)
        .useRules('#credential_type', window.ValidationRules.credential.credentialType)
        .useRules('#db_type', window.ValidationRules.credential.dbType)
        .useRules('#username', window.ValidationRules.credential.username)
        .useRules('#password', window.ValidationRules.credential.password)
        .onSuccess(function (event) {
            const form = event.target;
            showLoadingState(form);
            form.submit();
        })
        .onFail(function () {
            toast.error('请检查表单填写');
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
        submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>保存中...';
        submitBtn.disabled = true;
    }
}

function hideLoadingState(form) {
    const submitBtn = form.querySelector('button[type="submit"]');
    if (submitBtn) {
        submitBtn.innerHTML = '<i class="fas fa-save me-2"></i>保存更改';
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
    } else if (strength < 3) {
        feedback = '密码强度：中等';
    } else if (strength < 5) {
        feedback = '密码强度：良好';
    } else if (strength < 6) {
        feedback = '密码强度：强';
    } else {
        feedback = '密码强度：非常强';
    }

    return { strength: strength, feedback: feedback };
}

function updatePasswordStrength(password) {
    const strengthBar = document.getElementById('passwordStrength');
    const strengthText = document.getElementById('passwordStrengthText');

    if (!strengthBar || !strengthText) {
        return;
    }

    const result = checkPasswordStrength(password);

    var percentage = 0;
    var colorClass = 'bg-secondary';

    if (result.strength >= 1) {
        percentage = 20;
        colorClass = 'bg-danger';
    }
    if (result.strength >= 3) {
        percentage = 40;
        colorClass = 'bg-warning';
    }
    if (result.strength >= 4) {
        percentage = 60;
        colorClass = 'bg-info';
    }
    if (result.strength >= 5) {
        percentage = 80;
        colorClass = 'bg-success';
    }
    if (result.strength >= 6) {
        percentage = 100;
        colorClass = 'bg-success';
    }

    strengthBar.style.width = percentage + '%';
    strengthBar.className = 'password-strength-fill ' + colorClass;
    strengthText.textContent = result.feedback;
}

window.togglePasswordVisibility = togglePasswordVisibility;
window.hideLoadingState = hideLoadingState;
window.updatePasswordStrength = updatePasswordStrength;
