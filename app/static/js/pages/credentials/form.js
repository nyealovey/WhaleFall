/**
 * 凭据表单（创建/编辑）
 */
(function (window, document) {
  'use strict';

  let credentialValidator = null;
  let formController = null;

  document.addEventListener('DOMContentLoaded', () => {
    const form = document.getElementById('credentialForm');
    if (!form) {
      return;
    }

    const root = document.getElementById('credential-form-root');
    const mode = root?.dataset.formMode || 'create';

    if (window.ResourceFormController) {
      formController = new window.ResourceFormController(form, {
        loadingText: mode === 'edit' ? '保存中...' : '创建中...',
      });
    }

    initializePasswordToggle();
    initializeCredentialTypeToggle();
    initializeFormValidation(mode);
    initializePasswordStrengthWatcher(mode);
  });

  function initializePasswordToggle() {
    const toggleButton = document.getElementById('togglePassword');
    const passwordInput = document.getElementById('password');
    if (!toggleButton || !passwordInput) {
      return;
    }
    toggleButton.addEventListener('click', () => {
      const current = passwordInput.getAttribute('type') === 'password' ? 'text' : 'password';
      passwordInput.setAttribute('type', current);
      const icon = toggleButton.querySelector('i');
      if (icon) {
        icon.classList.toggle('fa-eye');
        icon.classList.toggle('fa-eye-slash');
      }
      toggleButton.setAttribute('title', current === 'password' ? '显示密码' : '隐藏密码');
    });
  }

  function initializeCredentialTypeToggle() {
    const credentialTypeSelect = document.getElementById('credential_type');
    const dbTypeSelect = document.getElementById('db_type');
    if (!credentialTypeSelect || !dbTypeSelect) {
      return;
    }

    const toggleDbField = () => {
      const container = dbTypeSelect.closest('.mb-3');
      if (!container) {
        return;
      }
      if (credentialTypeSelect.value === 'database') {
        container.style.display = 'block';
        dbTypeSelect.required = true;
      } else {
        container.style.display = 'none';
        dbTypeSelect.required = false;
        dbTypeSelect.value = '';
      }
      credentialValidator?.revalidateField('#db_type');
    };

    credentialTypeSelect.addEventListener('change', toggleDbField);
    toggleDbField();
  }

  function initializeFormValidation(mode) {
    if (!window.FormValidator || !window.ValidationRules) {
      console.warn('表单校验模块未加载');
      return;
    }
    credentialValidator = window.FormValidator.create('#credentialForm');
    if (!credentialValidator) {
      return;
    }

    credentialValidator
      .useRules('#name', window.ValidationRules.credential.name)
      .useRules('#credential_type', window.ValidationRules.credential.credentialType)
      .useRules('#db_type', window.ValidationRules.credential.dbType)
      .useRules('#username', window.ValidationRules.credential.username);

    if (mode === 'edit') {
      credentialValidator.useRules('#password', [
        {
          validator: function (value) {
            if (!value || value.trim() === '') {
              return true;
            }
            return value.length >= 6;
          },
          errorMessage: '密码至少需要 6 个字符',
        },
      ]);
    } else {
      credentialValidator.useRules('#password', window.ValidationRules.credential.password);
    }

    credentialValidator
      .onSuccess((event) => {
        formController?.toggleLoading(true);
        if (mode === 'edit') {
          normalizeIsActive(event.target);
        }
        event.target.submit();
      })
      .onFail(() => {
        window.toast.error('请检查表单填写');
      });
  }

  function normalizeIsActive(form) {
    const checkbox = form.querySelector('#is_active');
    if (!checkbox) {
      return;
    }
    let hidden = form.querySelector('input[name="is_active"][type="hidden"].generated');
    if (!hidden) {
      hidden = document.createElement('input');
      hidden.type = 'hidden';
      hidden.name = 'is_active';
      hidden.classList.add('generated');
      form.appendChild(hidden);
    }
    hidden.value = checkbox.checked ? 'true' : 'false';
  }

  function initializePasswordStrengthWatcher(mode) {
    if (mode !== 'edit') {
      return;
    }
    const input = document.getElementById('password');
    const bar = document.getElementById('passwordStrength');
    const text = document.getElementById('passwordStrengthText');
    if (!input || !bar || !text) {
      return;
    }

    const updateStrength = (password) => {
      const metrics = calculateStrength(password);
      bar.style.width = metrics.percent + '%';
      bar.className = 'password-strength-fill ' + metrics.color;
      text.textContent = metrics.feedback;
    };

    input.addEventListener('input', (event) => updateStrength(event.target.value));
    updateStrength(input.value || '');
  }

  function calculateStrength(password) {
    let score = 0;
    if (password.length >= 6) score++;
    if (password.length >= 8) score++;
    if (/[a-z]/.test(password)) score++;
    if (/[A-Z]/.test(password)) score++;
    if (/[0-9]/.test(password)) score++;
    if (/[^A-Za-z0-9]/.test(password)) score++;

    if (score === 0) {
      return { percent: 0, color: 'bg-secondary', feedback: '请输入密码以检测强度' };
    }
    if (score <= 2) {
      return { percent: 30, color: 'bg-danger', feedback: '密码强度：弱' };
    }
    if (score <= 4) {
      return { percent: 60, color: 'bg-warning', feedback: '密码强度：中等' };
    }
    return { percent: 100, color: 'bg-success', feedback: '密码强度：强' };
  }
})(window, document);
