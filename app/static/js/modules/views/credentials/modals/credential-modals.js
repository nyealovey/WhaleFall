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
    if (!window.CredentialsService) {
      throw new Error('CredentialModals: CredentialsService 未加载');
    }
    if (!DOMHelpers) {
      throw new Error('CredentialModals: DOMHelpers 未加载');
    }
    const { selectOne, from } = DOMHelpers;
    const credentialService = new window.CredentialsService(http);

    const modalEl = document.getElementById('credentialModal');
    if (!modalEl) {
      throw new Error('CredentialModals: 找不到 #credentialModal');
    }
    const modal = new bootstrap.Modal(modalEl);
    const form = document.getElementById('credentialModalForm');
    const submitBtn = document.getElementById('credentialModalSubmit');
    const titleEl = document.getElementById('credentialModalTitle');
    const metaTextEl = document.getElementById('credentialModalMeta');
    const metaPillEl = document.getElementById('credentialModalMetaPill');
    const isActiveInput = document.getElementById('credentialIsActive');
    const passwordInput = document.getElementById('credentialPassword');
    const typeSelect = document.getElementById('credentialType');
    const dbTypeField = document.getElementById('credentialDbTypeField');
    const dbTypeSelect = document.getElementById('credentialDbType');
    const togglePasswordBtn = document.getElementById('credentialTogglePassword');

    let validator = null;
    let validatorMode = 'create';
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
      setupValidator('create');
      typeSelect?.addEventListener('change', handleCredentialTypeChange);
      togglePasswordBtn?.addEventListener('click', handleTogglePassword);
      modalEl.addEventListener('hidden.bs.modal', resetForm);
      handleCredentialTypeChange();
    }

    function setupValidator(targetMode) {
      if (!FormValidator || !ValidationRules) {
        return;
      }
      const nextMode = targetMode === 'edit' ? 'edit' : 'create';
      if (validator && validatorMode === nextMode) {
        return;
      }
      if (validator?.destroy) {
        validator.destroy();
      }
      validatorMode = nextMode;
      validator = FormValidator.create('#credentialModalForm');
      if (!validator) {
        console.warn('CredentialModals: 表单校验初始化失败');
        return;
      }
      const passwordRules = nextMode === 'edit'
        ? ValidationRules.credential.passwordOptional
        : ValidationRules.credential.password;
      validator
        .useRules('#credentialName', ValidationRules.credential.name)
        .useRules('#credentialType', ValidationRules.credential.credentialType)
        .useRules('#credentialUsername', ValidationRules.credential.username)
        .useRules('#credentialDbType', ValidationRules.credential.dbType)
        .useRules('#credentialPassword', passwordRules)
        .onSuccess(handleSubmit)
        .onFail(() => toast?.error?.('请检查凭据信息填写'));
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
      if (isActiveInput) {
        isActiveInput.checked = true;
      }
      form.dataset.formMode = 'create';
      mode = 'create';
      setupValidator('create');
      passwordInput.required = true;
      passwordInput.placeholder = '请输入密码';
      titleEl.textContent = '添加凭据';
      updateSubmitButtonCopy();
      setMetaState('新建', 'status-pill--muted');
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
        setupValidator('edit');
        form.dataset.formMode = 'edit';
        passwordInput.required = false;
        passwordInput.placeholder = '留空表示保持原密码';
        titleEl.textContent = '编辑凭据';
        updateSubmitButtonCopy();
        setMetaState('加载中', 'status-pill--muted');
        const response = await credentialService.getCredential(credentialId);
        if (!response?.success || !response?.data) {
          throw new Error(response?.message || '获取凭据失败');
        }
        const credential = response.data?.credential || response.data;
        form.credential_id.value = credential.id;
        form.name.value = credential.name || '';
        form.credential_type.value = credential.credential_type || '';
        form.username.value = credential.username || '';
        form.description.value = credential.description || '';
        if (isActiveInput) {
          isActiveInput.checked = normalizeActiveFlag(credential.is_active);
        }
        form.db_type.value = (credential.db_type || '').toString().toLowerCase();
        handleCredentialTypeChange();
        setMetaState('编辑', 'status-pill--info');
        updateSubmitButtonCopy();
        modal.show();
      } catch (error) {
        console.error('加载凭据失败', error);
        setMetaState('加载失败', 'status-pill--danger');
        toast?.error?.(resolveErrorMessage(error, '加载凭据失败'));
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
        is_active: isActiveInput ? isActiveInput.checked : false,
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
      credentialService.createCredential(payload)
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
          toast?.error?.(resolveErrorMessage(error, '添加凭据失败'));
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
      credentialService.updateCredential(credentialId, payload)
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
          toast?.error?.(resolveErrorMessage(error, '保存凭据失败'));
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
        updateSubmitButtonCopy();
      }
    }

    function updateSubmitButtonCopy() {
      if (!submitBtn) {
        return;
      }
      const text = mode === 'edit' ? '保存' : '添加凭据';
      submitBtn.textContent = text;
      submitBtn.setAttribute('aria-label', mode === 'edit' ? '保存凭据' : '提交新凭据');
    }

    function setMetaState(label, variant) {
      if (!metaTextEl || !metaPillEl) {
        return;
      }
      metaTextEl.textContent = label;
      const variants = ['status-pill--muted', 'status-pill--info', 'status-pill--danger'];
      metaPillEl.classList.remove(...variants);
      metaPillEl.classList.add(variant || 'status-pill--muted');
    }

    function resolveErrorMessage(error, fallback) {
      if (!error) {
        return fallback;
      }
      if (error.response?.message) {
        return error.response.message;
      }
      if (error.response?.data?.message) {
        return error.response.data.message;
      }
      if (error.message) {
        return error.message;
      }
      return fallback;
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
    function normalizeActiveFlag(value) {
      if (typeof value === 'boolean') {
        return value;
      }
      if (typeof value === 'number') {
        return value === 1;
      }
      if (typeof value === 'string') {
        const normalized = value.trim().toLowerCase();
        return normalized === '1' || normalized === 'true' || normalized === 'yes';
      }
      return false;
    }
