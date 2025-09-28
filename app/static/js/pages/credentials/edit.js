/**
 * 编辑凭据页面JavaScript
 * 处理密码显示/隐藏、凭据类型切换、表单验证、凭据编辑提交等功能
 */

// 页面加载完成后初始化
document.addEventListener('DOMContentLoaded', function() {
    initializeEditCredentialPage();
});

// 初始化编辑凭据页面
function initializeEditCredentialPage() {
    try {
        console.log('开始初始化编辑凭据页面');
        initializePasswordToggle();
        initializeCredentialTypeToggle();
        initializeFormValidation();
        initializeFormSubmission();
        console.log('编辑凭据页面初始化完成');
    } catch (error) {
        console.error('编辑凭据页面初始化失败:', error);
    }
}

// 初始化密码显示/隐藏切换
function initializePasswordToggle() {
    const togglePassword = document.getElementById('togglePassword');
    const passwordInput = document.getElementById('password');
    
    if (togglePassword && passwordInput) {
        togglePassword.addEventListener('click', function() {
            togglePasswordVisibility(passwordInput, this);
        });
    }
}

// 切换密码可见性
function togglePasswordVisibility(inputElement, toggleButton) {
    const type = inputElement.getAttribute('type') === 'password' ? 'text' : 'password';
    inputElement.setAttribute('type', type);

    const icon = toggleButton.querySelector('i');
    if (icon) {
        icon.classList.toggle('fa-eye');
        icon.classList.toggle('fa-eye-slash');
    }

    // 更新按钮标题
    const title = type === 'password' ? '显示密码' : '隐藏密码';
    toggleButton.setAttribute('title', title);
}

// 初始化凭据类型切换
function initializeCredentialTypeToggle() {
    const credentialTypeSelect = document.getElementById('credential_type');
    const dbTypeSelect = document.getElementById('db_type');
    
    if (credentialTypeSelect && dbTypeSelect) {
        credentialTypeSelect.addEventListener('change', function() {
            toggleDatabaseTypeField(this.value, dbTypeSelect);
        });
        
        // 页面加载时检查当前类型
        toggleDatabaseTypeField(credentialTypeSelect.value, dbTypeSelect);
    }
}

// 切换数据库类型字段显示
function toggleDatabaseTypeField(credentialType, dbTypeSelect) {
    const dbTypeDiv = dbTypeSelect.closest('.mb-3');
    
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
}

// 初始化表单验证
function initializeFormValidation() {
    const nameInput = document.getElementById('name');
    const credentialTypeSelect = document.getElementById('credential_type');
    const dbTypeSelect = document.getElementById('db_type');
    const usernameInput = document.getElementById('username');
    const passwordInput = document.getElementById('password');

    if (nameInput) {
        nameInput.addEventListener('blur', function() {
            validateName(this);
        });
    }

    if (credentialTypeSelect) {
        credentialTypeSelect.addEventListener('change', function() {
            validateCredentialType(this);
        });
    }

    if (dbTypeSelect) {
        dbTypeSelect.addEventListener('change', function() {
            validateDatabaseType(this);
        });
    }

    if (usernameInput) {
        usernameInput.addEventListener('blur', function() {
            validateUsername(this);
        });
    }

    if (passwordInput) {
        passwordInput.addEventListener('blur', function() {
            validatePassword(this);
        });
    }
}

// 验证凭据名称
function validateName(input) {
    const value = input.value.trim();
    const isValid = value.length >= 2;

    updateFieldValidation(input, isValid, '凭据名称至少需要2个字符');
    return isValid;
}

// 验证凭据类型
function validateCredentialType(input) {
    const value = input.value;
    const isValid = value !== '';

    updateFieldValidation(input, isValid, '请选择凭据类型');
    return isValid;
}

// 验证数据库类型
function validateDatabaseType(input) {
    const credentialType = document.getElementById('credential_type').value;
    const value = input.value;
    
    // 只有当凭据类型为数据库时才验证
    if (credentialType === 'database') {
        const isValid = value !== '';
        updateFieldValidation(input, isValid, '请选择数据库类型');
        return isValid;
    }
    
    return true;
}

// 验证用户名
function validateUsername(input) {
    const value = input.value.trim();
    const isValid = value.length >= 2;

    updateFieldValidation(input, isValid, '用户名至少需要2个字符');
    return isValid;
}

// 验证密码
function validatePassword(input) {
    const value = input.value;
    const isValid = value.length >= 6;

    updateFieldValidation(input, isValid, '密码至少需要6个字符');
    return isValid;
}

// 更新字段验证状态
function updateFieldValidation(input, isValid, message) {
    const feedback = input.parentNode.querySelector('.invalid-feedback') || 
                    input.parentNode.querySelector('.valid-feedback');
    
    if (isValid) {
        input.classList.remove('is-invalid');
        input.classList.add('is-valid');
        if (feedback) {
            feedback.textContent = message || '';
            feedback.style.display = message ? 'block' : 'none';
        }
    } else {
        input.classList.remove('is-valid');
        input.classList.add('is-invalid');
        if (feedback) {
            feedback.textContent = message || '';
            feedback.style.display = 'block';
        }
    }
}

// 初始化表单提交
function initializeFormSubmission() {
    const credentialForm = document.getElementById('credentialForm');
    
    if (credentialForm) {
        credentialForm.addEventListener('submit', function(e) {
            handleFormSubmission(e, this);
        });
    }
}

// 处理表单提交
function handleFormSubmission(event, form) {
    const name = document.getElementById('name').value.trim();
    const credentialType = document.getElementById('credential_type').value;
    const dbType = document.getElementById('db_type').value;
    const username = document.getElementById('username').value.trim();
    const password = document.getElementById('password').value;

    // 验证表单
    if (!validateForm(name, credentialType, dbType, username, password)) {
        event.preventDefault();
        return false;
    }

    // 显示加载状态
    showLoadingState(form);
    
    // 如果保存失败，恢复按钮状态
    setTimeout(() => {
        hideLoadingState(form);
    }, 5000);
}

// 验证表单
function validateForm(name, credentialType, dbType, username, password) {
    // 基本验证
    if (!name || !credentialType || !username || !password) {
        showAlert('warning', '所有必填字段都不能为空');
        return false;
    }

    if (name.length < 2) {
        showAlert('warning', '凭据名称至少需要2个字符');
        return false;
    }

    if (username.length < 2) {
        showAlert('warning', '用户名至少需要2个字符');
        return false;
    }

    if (password.length < 6) {
        showAlert('warning', '密码至少需要6个字符');
        return false;
    }

    // 数据库类型验证
    if (credentialType === 'database' && !dbType) {
        showAlert('warning', '请选择数据库类型');
        return false;
    }

    return true;
}

// 显示加载状态
function showLoadingState(form) {
    const submitBtn = form.querySelector('button[type="submit"]');
    if (submitBtn) {
        submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>保存中...';
        submitBtn.disabled = true;
    }
}

// 隐藏加载状态
function hideLoadingState(form) {
    const submitBtn = form.querySelector('button[type="submit"]');
    if (submitBtn) {
        submitBtn.innerHTML = '<i class="fas fa-save me-2"></i>保存更改';
        submitBtn.disabled = false;
    }
}

// 显示提示信息
function showAlert(type, message) {
    const alertDiv = document.createElement('div');
    alertDiv.className = `alert alert-${type} alert-dismissible fade show`;
    alertDiv.innerHTML = `
        <i class="fas fa-${type === 'success' ? 'check-circle' : 'exclamation-triangle'} me-2"></i>
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    
    const container = document.querySelector('.container');
    if (container) {
        container.insertBefore(alertDiv, container.firstChild);
    }
    
    setTimeout(() => {
        alertDiv.remove();
    }, 5000);
}

// 显示成功提示
function showSuccessAlert(message) {
    showAlert('success', message);
}

// 显示警告提示
function showWarningAlert(message) {
    showAlert('warning', message);
}

// 显示错误提示
function showErrorAlert(message) {
    showAlert('danger', message);
}

// 密码强度检查
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

// 更新密码强度显示
function updatePasswordStrength(password) {
    const strengthBar = document.getElementById('passwordStrength');
    const strengthText = document.getElementById('passwordStrengthText');

    if (!strengthBar || !strengthText) return;

    const { strength, feedback } = checkPasswordStrength(password);
    
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

    // 更新强度条
    strengthBar.style.width = percentage + '%';
    strengthBar.className = 'password-strength-fill ' + colorClass;
    
    // 更新强度文本
    strengthText.textContent = feedback;
}

// 键盘快捷键
function initializeKeyboardShortcuts() {
    document.addEventListener('keydown', function(e) {
        // Ctrl+Enter 快速提交
        if (e.ctrlKey && e.key === 'Enter') {
            const form = document.getElementById('credentialForm');
            if (form) {
                form.submit();
            }
        }
        
        // Escape 重置表单
        if (e.key === 'Escape') {
            const form = document.getElementById('credentialForm');
            if (form) {
                form.reset();
                // 清除验证状态
                const inputs = form.querySelectorAll('.is-valid, .is-invalid');
                inputs.forEach(input => {
                    input.classList.remove('is-valid', 'is-invalid');
                });
            }
        }
    });
}

// 初始化键盘快捷键
initializeKeyboardShortcuts();

// 导出函数供全局使用
window.togglePasswordVisibility = togglePasswordVisibility;
window.validateForm = validateForm;
window.showAlert = showAlert;
window.showSuccessAlert = showSuccessAlert;
window.showWarningAlert = showWarningAlert;
window.showErrorAlert = showErrorAlert;
