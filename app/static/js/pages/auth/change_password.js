/**
 * 修改密码页面：统一使用 Umbrella JS 封装的 DOMHelpers。
 */
(function (global) {
    'use strict';

    const helpers = global.DOMHelpers;
    if (!helpers) {
        console.error('DOMHelpers 未初始化，无法加载修改密码页面脚本');
        return;
    }

    const { ready, selectOne, from, value } = helpers;

    let changePasswordValidator = null;
    let changePasswordController = null;

    ready(initializeChangePasswordPage);

    function initializeChangePasswordPage() {
        const form = selectOne('#changePasswordForm');
        if (!form.length) {
            return;
        }

        if (global.ResourceFormController) {
            changePasswordController = new global.ResourceFormController(form.first(), {
                loadingText: '更新中...',
            });
        }

        initializePasswordToggles();
        initializePasswordStrength();
        initializeFormValidation();
    }

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
                changePasswordController?.toggleLoading(true);
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

    global.togglePasswordVisibility = togglePasswordVisibility;
    global.getPasswordStrength = getPasswordStrength;
    global.updatePasswordStrength = updatePasswordStrength;
    global.updatePasswordRequirements = updatePasswordRequirements;
})(window);
