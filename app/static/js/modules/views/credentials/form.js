/**
 * 凭据表单（创建/编辑）
 */
function mountCredentialsForm(window) {
  'use strict';

  const helpers = window.DOMHelpers;
  if (!helpers) {
    console.error('DOMHelpers 未初始化，无法挂载凭据表单逻辑');
    return;
  }

  const { ready, selectOne, from, value } = helpers;
  let credentialValidator = null;
  let formController = null;

  ready(() => {
    const form = selectOne('#credentialForm');
    if (!form.length) {
      return;
    }

    const root = selectOne('#credential-form-root');
    const mode = root.length ? root.data('formMode') || root.attr('data-form-mode') || 'create' : 'create';

    if (window.ResourceFormController) {
      formController = new window.ResourceFormController(form.first(), {
        loadingText: mode === 'edit' ? '保存中...' : '创建中...',
      });
    }

    initializePasswordToggle();
    initializeCredentialTypeToggle();
    initializeFormValidation(mode);
    initializePasswordStrengthWatcher(mode);
  });

  function initializePasswordToggle() {
    const toggleButton = selectOne('#togglePassword');
    const passwordInput = selectOne('#password');
    if (!toggleButton.length || !passwordInput.length) {
      return;
    }
    toggleButton.on('click', (event) => {
      const current = passwordInput.attr('type') === 'password' ? 'text' : 'password';
      passwordInput.attr('type', current);
      from(event.currentTarget)
        .find('i')
        .each((icon) => {
          icon.classList.toggle('fa-eye');
          icon.classList.toggle('fa-eye-slash');
        });
      from(event.currentTarget).attr('title', current === 'password' ? '显示密码' : '隐藏密码');
    });
  }

  function initializeCredentialTypeToggle() {
    const credentialTypeSelect = selectOne('#credential_type');
    const dbTypeSelect = selectOne('#db_type');
    if (!credentialTypeSelect.length || !dbTypeSelect.length) {
      return;
    }

    const toggleDbField = () => {
      const container = dbTypeSelect.closest('.mb-3');
      if (!container.length) {
        return;
      }

      const dbNode = dbTypeSelect.first();
      if (!dbNode) {
        return;
      }

      if (value(credentialTypeSelect) === 'database') {
        container.first().style.display = 'block';
        dbNode.required = true;
      } else {
        container.first().style.display = 'none';
        dbNode.required = false;
        dbNode.value = '';
      }
      credentialValidator?.revalidateField('#db_type');
    };

    credentialTypeSelect.on('change', toggleDbField);
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
    const formWrapper = from(form);
    const checkbox = formWrapper.find('#is_active').first();
    if (!checkbox) {
      return;
    }
    let hidden = formWrapper.find('input[name="is_active"][type="hidden"].generated').first();
    if (!hidden) {
      hidden = document.createElement('input');
      hidden.type = 'hidden';
      hidden.name = 'is_active';
      hidden.classList.add('generated');
      formWrapper.first().appendChild(hidden);
    }
    hidden.value = checkbox.checked ? 'true' : 'false';
  }

  function initializePasswordStrengthWatcher(mode) {
    if (mode !== 'edit') {
      return;
    }
    const input = selectOne('#password');
    const bar = selectOne('#passwordStrength');
    const text = selectOne('#passwordStrengthText');
    if (!input.length || !bar.length || !text.length) {
      return;
    }

    const updateStrength = (password) => {
      const metrics = calculateStrength(password);
      const barNode = bar.first();
      if (barNode) {
        barNode.style.width = metrics.percent + '%';
        bar.attr('class', 'password-strength-fill ' + metrics.color);
      }
      text.text(metrics.feedback);
    };

    input.on('input', (event) => updateStrength(event.target.value));
    updateStrength(value(input) || '');
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
}

window.CredentialFormPage = {
  mount: function () {
    mountCredentialsForm(window);
  },
};
