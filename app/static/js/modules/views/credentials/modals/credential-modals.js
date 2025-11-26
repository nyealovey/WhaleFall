(function (window, document) {
  'use strict';

  /**
   * 创建凭据新建/编辑模态控制器。
   *
   * @param {Object} [options] - 配置选项
   * @param {Object} [options.http] - HTTP 请求工具
   * @param {Object} [options.FormValidator] - 表单验证器
   * @param {Object} [options.ValidationRules] - 验证规则
   * @param {Object} [options.toast] - Toast 通知工具
   * @param {Object} [options.DOMHelpers] - DOM 辅助工具
   * @return {Object} 控制器对象，包含 init、openCreate、openEdit 方法
   * @throws {Error} 当必需的依赖未初始化时抛出
   */
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

    /**
     * 初始化表单验证与事件。
     *
     * @param {void} 无参数。基于 credentialModalForm 自动绑定。
     * @returns {void}
     */
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

    /**
     * 处理凭据类型变化。
     *
     * @param {void} 无参数。直接读取 typeSelect 当前值。
     * @returns {void}
     */
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

    /**
     * 切换密码显示/隐藏。
     *
     * @param {Event} event - 点击事件
     * @return {void}
     */
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

    /**
     * 重置表单状态为创建模式。
     *
     * @param {void} 无参数。直接操作模态表单。
     * @returns {void}
     */
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

    /**
     * 打开新建模态。
     *
     * @param {void} 无参数。调用 resetForm 并展示模态。
     * @returns {void}
     */
    function openCreate() {
      resetForm();
      modal.show();
    }

    /**
     * 打开编辑模态并填充数据。
     *
     * @param {number|string} credentialId - 凭据 ID
     * @return {Promise<void>}
     */
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

    /**
     * 表单提交入口，按模式调用创建/更新。
     *
     * @param {Event} event - 提交事件
     * @return {void}
     */
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

    /**
     * 将表单值组装为 payload。
     *
     * @param {void} 无参数。直接读取 credentialModalForm。
     * @returns {Object|null} 表单数据对象
     */
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

    /**
     * 调用后端创建凭据。
     *
     * @param {Object} payload - 凭据数据
     * @return {void}
     */
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

    /**
     * 调用后端更新凭据。
     *
     * @param {Object} payload - 凭据数据
     * @return {void}
     */
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

    /**
     * 切换提交按钮 loading 状态。
     *
     * @param {boolean} loading - 是否显示加载状态
     * @return {void}
     */
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
