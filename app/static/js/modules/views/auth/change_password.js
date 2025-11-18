/**
 * 修改密码页面：统一使用 Umbrella JS 封装的 DOMHelpers。
 */
function mountChangePasswordPage(global) {
    'use strict';

    const helpers = global.DOMHelpers;
    if (!helpers) {
        console.error('DOMHelpers 未初始化，无法加载修改密码页面脚本');
        return;
    }

    const { ready, selectOne, from, value } = helpers;

    let changePasswordValidator = null;
    let submitButton = null;

    ready(initializeChangePasswordPage);

    /**
     * 页面入口：绑定事件、校验与强度提示。
     */
    function initializeChangePasswordPage() {
        const form = selectOne('#changePasswordForm');
        if (!form.length) {
            return;
        }

        submitButton = form.find('[type="submit"]').first();

        initializePasswordToggles();
        initializePasswordStrength();
        initializeFormValidation();
    }

    /**
     * 绑定密码显示/隐藏切换。
     */
    function initializePasswordToggles() {
        const toggles = [
            { button: '#toggleOldPassword', input: '#old_password' },
            { button: '#toggleNewPassword', input: '#new_password' },
            { button: '#toggleConfirmPassword', input: '#confirm_password' },
        ];

        toggles.forEach(({ button, input }) => {
            const toggleButton = selectOne(button);
            const inputElement = selectOne(input);
            if (!toggleButton.length || !inputElement.length) {
                return;
            }

            toggleButton.on('click', (event) => {
                togglePasswordVisibility(inputElement, from(event.currentTarget));
            });
        });
    }

    /**
     * 切换 input type 并同步图标提示。
     */
    function togglePasswordVisibility(inputElement, toggleButton) {
        const currentType = inputElement.attr('type') === 'password' ? 'text' : 'password';
        inputElement.attr('type', currentType);

        toggleButton.find('i').each((icon) => {
            icon.classList.toggle('fa-eye');
            icon.classList.toggle('fa-eye-slash');
        });

        const title = currentType === 'password' ? '显示密码' : '隐藏密码';
        toggleButton.attr('title', title);
    }

    /**
     * 监听新密码输入，实时显示强度与要求。
     */
    function initializePasswordStrength() {
        const newPasswordInput = selectOne('#new_password');
        if (!newPasswordInput.length) {
            return;
        }

        newPasswordInput.on('input', (event) => {
            const password = event.target.value;
            const strength = getPasswordStrength(password);
            updatePasswordStrength(strength);
            updatePasswordRequirements(password);

            if (changePasswordValidator) {
                changePasswordValidator.revalidateField('#new_password');
                changePasswordValidator.revalidateField('#confirm_password');
            }
        });

        updatePasswordRequirements(value(newPasswordInput) || '');
    }

    /**
     * 计算复杂度评分与提示文字。
     */
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

    /**
     * 渲染强度进度条与提示文案。
     */
    function updatePasswordStrength(strengthData) {
        const strengthBar = selectOne('#passwordStrength');
        const strengthText = selectOne('#passwordStrengthText');
        if (!strengthBar.length || !strengthText.length) {
            return;
        }

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

        const barNode = strengthBar.first();
        if (barNode) {
            barNode.style.width = percentage + '%';
        }
        strengthBar.attr('class', 'password-strength-fill ' + colorClass);
        strengthText.text(feedback);
    }

    function updatePasswordRequirements(password) {
        const requirementsContainer = selectOne('#passwordRequirements');
        if (!requirementsContainer.length) {
            return;
        }

        const requirements = checkPasswordRequirements(password);
        let html = '<h6>密码要求:</h6><ul>';
        requirements.forEach((req) => {
            const statusClass = req.met ? 'requirement-met' : 'requirement-not-met';
            const icon = req.met ? '✓' : '✗';
            html += `<li class="${statusClass}">${icon} ${req.text}</li>`;
        });
        html += '</ul>';

        requirementsContainer.html(html);
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
        if (!global.FormValidator || !global.ValidationRules) {
            console.error('表单校验模块未正确加载');
            return;
        }

        changePasswordValidator = global.FormValidator.create('#changePasswordForm');
        if (!changePasswordValidator) {
            return;
        }

        const newPasswordRules = global.ValidationRules.auth.changePassword.newPassword.slice();
        newPasswordRules.push({
            validator(value, fields) {
                const oldPasswordField = fields['#old_password'];
                const oldPassword = oldPasswordField ? oldPasswordField.elem.value : '';
                return value !== oldPassword;
            },
            errorMessage: '新密码不能与当前密码相同',
        });
        newPasswordRules.push({
            validator(value) {
                return getPasswordStrength(value).strength >= 2;
            },
            errorMessage: '密码强度太弱，请使用更复杂的密码',
        });

        changePasswordValidator
            .useRules('#old_password', global.ValidationRules.auth.changePassword.oldPassword)
            .useRules('#new_password', newPasswordRules)
            .useRules('#confirm_password', global.ValidationRules.auth.changePassword.confirmPassword)
            .onSuccess((event) => {
                const form = event.target;
                toggleSubmitLoading(true);
                form.submit();
            })
            .onFail(() => {
                global.toast.error('请检查密码修改表单填写');
            });

        const oldPasswordInput = selectOne('#old_password');
        if (oldPasswordInput.length) {
            oldPasswordInput.on('blur', () => {
                changePasswordValidator.revalidateField('#old_password');
                changePasswordValidator.revalidateField('#new_password');
            });
        }

        const confirmPasswordInput = selectOne('#confirm_password');
        if (confirmPasswordInput.length) {
            confirmPasswordInput.on('input', () => {
                changePasswordValidator.revalidateField('#confirm_password');
            });
        }
    }

    function toggleSubmitLoading(loading) {
        if (!submitButton) {
            return;
        }
        if (loading) {
            submitButton.dataset.originalText = submitButton.innerHTML;
            submitButton.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>更新中...';
            submitButton.disabled = true;
        } else {
            submitButton.innerHTML = submitButton.dataset.originalText || '<i class="fas fa-save me-2"></i>更新密码';
            submitButton.disabled = false;
        }
    }

    global.togglePasswordVisibility = togglePasswordVisibility;
    global.getPasswordStrength = getPasswordStrength;
    global.updatePasswordStrength = updatePasswordStrength;
    global.updatePasswordRequirements = updatePasswordRequirements;
}

window.ChangePasswordPage = {
    mount: function () {
        mountChangePasswordPage(window);
    },
};
