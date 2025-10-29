/**
 * 修改密码页面JavaScript
 * 处理密码显示/隐藏、密码强度检查、表单验证、密码修改提交等功能
 */

// 页面加载完成后初始化
document.addEventListener('DOMContentLoaded', function() {
    initializeChangePasswordPage();
});

// 初始化修改密码页面
function initializeChangePasswordPage() {
    initializePasswordToggles();
    initializePasswordStrength();
    initializeFormValidation();
    initializeFormSubmission();
}

// 初始化密码显示/隐藏切换
function initializePasswordToggles() {
    const toggles = [
        { button: 'toggleOldPassword', input: 'old_password' },
        { button: 'toggleNewPassword', input: 'new_password' },
        { button: 'toggleConfirmPassword', input: 'confirm_password' }
    ];

    toggles.forEach(({ button, input }) => {
        const toggleButton = document.getElementById(button);
        const inputElement = document.getElementById(input);
        
        if (toggleButton && inputElement) {
            toggleButton.addEventListener('click', function() {
                togglePasswordVisibility(inputElement, this);
            });
        }
    });
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

// 初始化密码强度检查
function initializePasswordStrength() {
    const newPasswordInput = document.getElementById('new_password');
    
    if (newPasswordInput) {
        newPasswordInput.addEventListener('input', function() {
            const password = this.value;
            const strength = getPasswordStrength(password);
            updatePasswordStrength(strength);
        });
    }
}

// 获取密码强度
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

// 更新密码强度显示
function updatePasswordStrength(strengthData) {
    const strengthBar = document.getElementById('passwordStrength');
    const strengthText = document.getElementById('passwordStrengthText');

    if (!strengthBar || !strengthText) return;

    const { strength, feedback } = strengthData;
    
    let percentage = 0;
    let colorClass = 'bg-secondary';
    let textClass = '';

    if (strength >= 1) {
        percentage = 20;
        colorClass = 'bg-danger';
        textClass = 'weak';
    }
    if (strength >= 3) {
        percentage = 40;
        colorClass = 'bg-warning';
        textClass = 'fair';
    }
    if (strength >= 4) {
        percentage = 60;
        colorClass = 'bg-info';
        textClass = 'good';
    }
    if (strength >= 5) {
        percentage = 80;
        colorClass = 'bg-success';
        textClass = 'strong';
    }
    if (strength >= 6) {
        percentage = 100;
        colorClass = 'bg-success';
        textClass = 'very-strong';
    }

    // 更新强度条
    strengthBar.style.width = percentage + '%';
    strengthBar.className = 'password-strength-fill ' + colorClass;
    
    // 更新强度文本
    strengthText.textContent = feedback;
    strengthText.className = 'password-strength-text ' + textClass;
}

// 初始化表单验证
function initializeFormValidation() {
    const newPasswordInput = document.getElementById('new_password');
    const confirmPasswordInput = document.getElementById('confirm_password');

    if (newPasswordInput) {
        newPasswordInput.addEventListener('blur', function() {
            validateNewPassword(this);
        });
    }

    if (confirmPasswordInput) {
        confirmPasswordInput.addEventListener('input', function() {
            validatePasswordMatch();
        });
    }
}

// 验证新密码
function validateNewPassword(input) {
    const value = input.value;
    const isValid = value.length >= 6;

    updateFieldValidation(input, isValid, '密码至少需要6个字符');
    return isValid;
}

// 验证密码匹配
function validatePasswordMatch() {
    const newPassword = document.getElementById('new_password').value;
    const confirmPassword = document.getElementById('confirm_password').value;
    const confirmInput = document.getElementById('confirm_password');
    
    if (confirmPassword && newPassword !== confirmPassword) {
        updateFieldValidation(confirmInput, false, '两次输入的密码不一致');
        return false;
    } else if (confirmPassword && newPassword === confirmPassword) {
        updateFieldValidation(confirmInput, true, '密码匹配');
        return true;
    }
    
    return true;
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
    const changePasswordForm = document.getElementById('changePasswordForm');
    
    if (changePasswordForm) {
        changePasswordForm.addEventListener('submit', function(e) {
            handleFormSubmission(e, this);
        });
    }
}

// 处理表单提交
function handleFormSubmission(event, form) {
    const oldPassword = document.getElementById('old_password').value;
    const newPassword = document.getElementById('new_password').value;
    const confirmPassword = document.getElementById('confirm_password').value;

    // 验证表单
    if (!validateForm(oldPassword, newPassword, confirmPassword)) {
        event.preventDefault();
        return false;
    }

    // 显示加载状态
    showLoadingState(form);
    
    // 如果更新失败，恢复按钮状态
    setTimeout(() => {
        hideLoadingState(form);
    }, 3000);
}

// 验证表单
function validateForm(oldPassword, newPassword, confirmPassword) {
    // 基本验证
    if (!oldPassword || !newPassword || !confirmPassword) {
        toast.warning('所有字段都不能为空', { title: '验证失败' });
        return false;
    }

    if (newPassword.length < 6) {
        toast.warning('新密码至少需要6个字符', { title: '密码强度不足' });
        return false;
    }

    if (newPassword !== confirmPassword) {
        toast.warning('两次输入的新密码不一致', { title: '密码不匹配' });
        return false;
    }

    if (oldPassword === newPassword) {
        toast.warning('新密码不能与当前密码相同', { title: '密码重复' });
        return false;
    }

    // 密码强度验证
    const strength = getPasswordStrength(newPassword);
    if (strength.strength < 2) {
        toast.warning('密码强度太弱，请使用更复杂的密码', { title: '密码强度不足' });
        return false;
    }

    return true;
}

// 显示加载状态
function showLoadingState(form) {
    const submitBtn = form.querySelector('button[type="submit"]');
    if (submitBtn) {
        submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>更新中...';
        submitBtn.disabled = true;
    }
}

// 隐藏加载状态
function hideLoadingState(form) {
    const submitBtn = form.querySelector('button[type="submit"]');
    if (submitBtn) {
        submitBtn.innerHTML = '<i class="fas fa-key me-2"></i>更新密码';
        submitBtn.disabled = false;
    }
}

// 密码要求检查
function checkPasswordRequirements(password) {
    const requirements = [
        { text: '至少6个字符', met: password.length >= 6 },
        { text: '至少8个字符', met: password.length >= 8 },
        { text: '包含小写字母', met: /[a-z]/.test(password) },
        { text: '包含大写字母', met: /[A-Z]/.test(password) },
        { text: '包含数字', met: /[0-9]/.test(password) },
        { text: '包含特殊字符', met: /[^A-Za-z0-9]/.test(password) }
    ];

    return requirements;
}

// 更新密码要求显示
function updatePasswordRequirements(password) {
    const requirementsContainer = document.getElementById('passwordRequirements');
    if (!requirementsContainer) return;

    const requirements = checkPasswordRequirements(password);
    
    let html = '<h6>密码要求:</h6><ul>';
    requirements.forEach(req => {
        const statusClass = req.met ? 'requirement-met' : 'requirement-not-met';
        const icon = req.met ? '✓' : '✗';
        html += `<li class="${statusClass}">${icon} ${req.text}</li>`;
    });
    html += '</ul>';
    
    requirementsContainer.innerHTML = html;
}

// 导出函数供全局使用
window.togglePasswordVisibility = togglePasswordVisibility;
window.validateForm = validateForm;
