(function (window, document) {
  'use strict';

  function createController(options) {
    const {
      http = window.httpU,
      FormValidator = window.FormValidator,
      ValidationRules = window.ValidationRules,
      toast = window.toast,
      DOMHelpers = window.DOMHelpers,
    } = options || {};

    if (!http) {
      throw new Error('CredentialModals: httpU 未初始化');
    }
    if (!DOMHelpers) {
      throw new Error('CredentialModals: DOMHelpers 未加载');
    }
    const { selectOne, from } = DOMHelpers;

    const modalEl = document.getElementById('credentialModal');
    if (!modalEl) {
      throw new Error('CredentialModals: 找不到 #credentialModal');
    }
    const modal = new bootstrap.Modal(modalEl);
    const form = document.getElementById('credentialModalForm');
    const submitBtn = document.getElementById('credentialModalSubmit');
    const titleEl = document.getElementById('credentialModalTitle');
    const passwordInput = document.getElementById('credentialPassword');
    const typeSelect = document.getElementById('credentialType');
    const dbTypeField = document.getElementById('credentialDbTypeField');
    const dbTypeSelect = document.getElementById('credentialDbType');
    const togglePasswordBtn = document.getElementById('credentialTogglePassword');

    let validator = null;
    let mode = 'create';

    function init() {
      if (!FormValidator || !ValidationRules) {
        console.warn('CredentialModals: FormValidator 或 ValidationRules 未加载');
        return;
      }
      validator = FormValidator.create('#credentialModalForm');
      validator
        .useRules('#credentialName', ValidationRules.credential.name)
        .useRules('#credentialType', ValidationRules.credential.credentialType)
        .useRules('#credentialUsername', ValidationRules.credential.username)
        .useRules('#credentialDbType', ValidationRules.credential.dbType)
        .useRules('#credentialPassword', ValidationRules.credential.password)
        .onSuccess(handleSubmit)
        .onFail(() => toast?.error?.('请检查凭据信息填写'));

      typeSelect?.addEventListener('change', handleCredentialTypeChange);
      togglePasswordBtn?.addEventListener('click', handleTogglePassword);
      modalEl.addEventListener('hidden.bs.modal', resetForm);
      handleCredentialTypeChange();
    }

    function handleCredentialTypeChange() {
      if (!typeSelect || !dbTypeField || !dbTypeSelect) {
        return;
      }
      const type = typeSelect.value;
      if (type === 'database') {
        dbTypeField.style.display = '';
        dbTypeSelect.required = true;
      } else {
        dbTypeField.style.display = 'none';
        dbTypeSelect.required = false;
        dbTypeSelect.value = '';
      }
      validator?.revalidateField('#credentialDbType');
    }

    function handleTogglePassword(event) {
      if (!passwordInput) {
        return;
      }
      const newType = passwordInput.type === 'password' ? 'text' : 'password';
      passwordInput.type = newType;
      const icon = event.currentTarget.querySelector('i');
      if (icon) {
        icon.classList.toggle('fa-eye');
        icon.classList.toggle('fa-eye-slash');
      }
    }

    function resetForm() {
      form.reset();
      form.dataset.formMode = 'create';
      mode = 'create';
      passwordInput.required = true;
      passwordInput.placeholder = '请输入密码';
      titleEl.textContent = '添加凭据';
      submitBtn.textContent = '添加凭据';
      handleCredentialTypeChange();
      validator?.instance?.refresh?.();
    }

    function openCreate() {
      resetForm();
      modal.show();
    }

    async function openEdit(credentialId) {
      if (!credentialId) {
        return;
      }
      try {
        mode = 'edit';
        form.dataset.formMode = 'edit';
        passwordInput.required = false;
        passwordInput.placeholder = '留空表示保持原密码';
        titleEl.textContent = '编辑凭据';
        submitBtn.textContent = '保存';
        const response = await http.get(`/credentials/api/credentials/${credentialId}`);
        if (!response?.success || !response?.data) {
          throw new Error(response?.message || '获取凭据失败');
        }
        const credential = response.data?.credential || response.data;
        form.credential_id.value = credential.id;
        form.name.value = credential.name || '';
        form.credential_type.value = credential.credential_type || '';
        form.username.value = credential.username || '';
        form.description.value = credential.description || '';
        form.is_active.checked = Boolean(credential.is_active);
        form.db_type.value = (credential.db_type || '').toString().toLowerCase();
        handleCredentialTypeChange();
        modal.show();
      } catch (error) {
        console.error('加载凭据失败', error);
        toast?.error?.(error?.message || '加载凭据失败');
      }
    }

    function handleSubmit(event) {
      event?.preventDefault?.();
      const payload = buildPayload();
      if (!payload) {
        return;
      }
      toggleLoading(true);
      if (mode === 'edit') {
        submitUpdate(payload);
      } else {
        submitCreate(payload);
      }
    }

    function buildPayload() {
      const data = new FormData(form);
      const payload = {
        name: data.get('name'),
        credential_type: data.get('credential_type'),
        username: data.get('username'),
        description: data.get('description') || '',
        is_active: form.is_active.checked,
        db_type: data.get('db_type') || '',
      };
      const password = data.get('password');
      if (mode === 'create' || (password && password.trim() !== '')) {
        payload.password = password;
      }
      if (mode === 'edit') {
        payload.id = data.get('credential_id');
      }
      return payload;
    }

    function submitCreate(payload) {
      http.post('/credentials/api/create', payload)
        .then((resp) => {
          if (!resp?.success) {
            throw new Error(resp?.message || '添加凭据失败');
          }
          toast?.success?.(resp?.message || '添加凭据成功');
          modal.hide();
          window.location.reload();
        })
        .catch((error) => {
          console.error('添加凭据失败', error);
          toast?.error?.(error?.message || '添加凭据失败');
        })
        .finally(() => toggleLoading(false));
    }

    function submitUpdate(payload) {
      const credentialId = payload.id;
      if (!credentialId) {
        toast?.error?.('缺少凭据ID');
        toggleLoading(false);
        return;
      }
      http.post(`/credentials/api/${credentialId}/edit`, payload)
        .then((resp) => {
          if (!resp?.success) {
            throw new Error(resp?.message || '保存凭据失败');
          }
          toast?.success?.(resp?.message || '保存成功');
          modal.hide();
          window.location.reload();
        })
        .catch((error) => {
          console.error('保存凭据失败', error);
          toast?.error?.(error?.message || '保存凭据失败');
        })
        .finally(() => toggleLoading(false));
    }

    function toggleLoading(loading) {
      if (!submitBtn) {
        return;
      }
      submitBtn.disabled = loading;
      if (loading) {
        submitBtn.innerHTML = '<span class=\"spinner-border spinner-border-sm me-2\"></span>处理中';
      } else {
        submitBtn.textContent = mode === 'edit' ? '保存' : '添加凭据';
      }
    }

    return {
      init,
      openCreate,
      openEdit,
    };
  }

  window.CredentialModals = {
    createController,
  };
})(window, document);
