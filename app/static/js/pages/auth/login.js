/**
 * 登录页面JavaScript
 * 处理密码显示/隐藏、表单验证、登录提交等功能
 */

// 页面加载完成后初始化
document.addEventListener('DOMContentLoaded', function() {
    initializeLoginPage();
});

// 初始化登录页面
function initializeLoginPage() {
    initializePasswordToggle();
    initializeFormValidation();
    initializeFormSubmission();
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
function togglePasswordVisibility(passwordInput, toggleButton) {
    const type = passwordInput.getAttribute('type') === 'password' ? 'text' : 'password';
    passwordInput.setAttribute('type', type);

    const icon = toggleButton.querySelector('i');
    if (icon) {
        icon.classList.toggle('fa-eye');
        icon.classList.toggle('fa-eye-slash');
    }

    // 更新按钮标题
    const title = type === 'password' ? '显示密码' : '隐藏密码';
    toggleButton.setAttribute('title', title);
}

// 初始化表单验证
function initializeFormValidation() {
    const usernameInput = document.getElementById('username');
    const passwordInput = document.getElementById('password');

    if (usernameInput) {
        usernameInput.addEventListener('blur', function() {
            validateUsername(this);
        });
    }

    if (passwordInput) {
        passwordInput.addEventListener('input', function() {
            validatePassword(this);
        });
    }
}

// 验证用户名
function validateUsername(input) {
    const value = input.value.trim();
    const isValid = value.length >= 3;

    updateFieldValidation(input, isValid, '用户名至少需要3个字符');
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
            feedback.textContent = '';
            feedback.style.display = 'none';
        }
    } else {
        input.classList.remove('is-valid');
        input.classList.add('is-invalid');
        if (feedback) {
            feedback.textContent = message;
            feedback.style.display = 'block';
        }
    }
}

// 初始化表单提交
function initializeFormSubmission() {
    const loginForm = document.getElementById('loginForm');
    
    if (loginForm) {
        loginForm.addEventListener('submit', function(e) {
            handleFormSubmission(e, this);
        });
    }
}

// 处理表单提交
function handleFormSubmission(event, form) {
    const username = document.getElementById('username').value.trim();
    const password = document.getElementById('password').value;

    // 验证表单
    if (!validateForm(username, password)) {
        event.preventDefault();
        return false;
    }

    // 显示加载状态
    showLoadingState(form);
    
    // 如果登录失败，恢复按钮状态
    setTimeout(() => {
        hideLoadingState(form);
    }, 3000);
}

// 验证表单
function validateForm(username, password) {
    if (!username || !password) {
        showWarningAlert('请输入用户名和密码');
        return false;
    }

    if (username.length < 3) {
        showWarningAlert('用户名至少需要3个字符');
        return false;
    }

    if (password.length < 6) {
        showWarningAlert('密码至少需要6个字符');
        return false;
    }

    return true;
}

// 显示加载状态
function showLoadingState(form) {
    const submitBtn = form.querySelector('button[type="submit"]');
    if (submitBtn) {
        submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>登录中...';
        submitBtn.disabled = true;
    }
}

// 隐藏加载状态
function hideLoadingState(form) {
    const submitBtn = form.querySelector('button[type="submit"]');
    if (submitBtn) {
        submitBtn.innerHTML = '<i class="fas fa-sign-in-alt me-2"></i>登录';
        submitBtn.disabled = false;
    }
}

// 显示警告提示
function showWarningAlert(message) {
    if (typeof window.showWarningAlert === 'function') {
        window.showWarningAlert(message);
    } else {
        // 备用提示方法
        const alertDiv = document.createElement('div');
        alertDiv.className = 'alert alert-warning alert-dismissible fade show';
        alertDiv.innerHTML = `
            <i class="fas fa-exclamation-triangle me-2"></i>
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;
        
        const form = document.getElementById('loginForm');
        if (form) {
            form.insertBefore(alertDiv, form.firstChild);
        }
        
        setTimeout(() => {
            alertDiv.remove();
        }, 5000);
    }
}

// 显示错误提示
function showErrorAlert(message) {
    notify.error(message);
}

function showSuccessAlert(message) {
    notify.success(message);
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
    } else if (strength < 4) {
        feedback = '密码强度：中等';
    } else if (strength < 6) {
        feedback = '密码强度：良好';
    } else {
        feedback = '密码强度：强';
    }

    return { strength, feedback };
}

// 更新密码强度指示器
function updatePasswordStrength(password) {
    const strengthBar = document.querySelector('.password-strength-bar');
    const strengthText = document.querySelector('.password-strength-text');
    
    if (!strengthBar) return;

    const { strength, feedback } = checkPasswordStrength(password);
    
    // 更新强度条
    strengthBar.className = 'password-strength-bar';
    if (strength < 2) {
        strengthBar.classList.add('weak');
    } else if (strength < 4) {
        strengthBar.classList.add('fair');
    } else if (strength < 6) {
        strengthBar.classList.add('good');
    } else {
        strengthBar.classList.add('strong');
    }

    // 更新强度文本
    if (strengthText) {
        strengthText.textContent = feedback;
    }
}

// 自动填充检测
function detectAutoFill() {
    const inputs = document.querySelectorAll('input[type="text"], input[type="password"]');
    
    inputs.forEach(input => {
        // 检测自动填充
        setTimeout(() => {
            if (input.value) {
                input.classList.add('auto-filled');
                // 触发验证
                if (input.type === 'password') {
                    validatePassword(input);
                } else if (input.id === 'username') {
                    validateUsername(input);
                }
            }
        }, 100);
    });
}

// 检测自动填充
detectAutoFill();

// 导出函数供全局使用
window.togglePasswordVisibility = togglePasswordVisibility;
window.validateForm = validateForm;
window.showWarningAlert = showWarningAlert;
window.showErrorAlert = showErrorAlert;
window.showSuccessAlert = showSuccessAlert;
