/**
 * 创建凭据页面 JavaScript
 * 统一使用 Just-Validate 进行表单验证。
 */

let credentialFormValidator = null;

document.addEventListener('DOMContentLoaded', function () {
    initializeCreateCredentialPage();
});

function initializeCreateCredentialPage() {
    initializePasswordToggle();
    initializeCredentialTypeToggle();
    initializeFormValidation();
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

    // 初始化时根据默认值同步数据库类型区域
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

    if (credentialFormValidator) {
        credentialFormValidator.revalidateField('#db_type');
    }
}

function initializeFormValidation() {
    if (!window.FormValidator || !window.ValidationRules) {
        console.error('表单校验模块未正确加载');
        return;
    }

    credentialFormValidator = window.FormValidator.create('#credentialForm');
    if (!credentialFormValidator) {
        return;
    }

    credentialFormValidator
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

function showLoadingState(form) {
    const submitBtn = form.querySelector('button[type="submit"]');
    if (submitBtn) {
        submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>创建中...';
        submitBtn.disabled = true;
    }
}

function hideLoadingState(form) {
    const submitBtn = form.querySelector('button[type="submit"]');
    if (submitBtn) {
        submitBtn.innerHTML = '<i class="fas fa-plus me-2"></i>创建凭据';
        submitBtn.disabled = false;
    }
}

// 供其他脚本按需使用
window.togglePasswordVisibility = togglePasswordVisibility;
window.hideLoadingState = hideLoadingState;
