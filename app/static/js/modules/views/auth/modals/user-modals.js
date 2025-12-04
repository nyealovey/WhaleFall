(function (window, document) {
  'use strict';

  /**
   * 创建用户新建/编辑模态控制器。
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
      throw new Error('UserModals: httpU 未初始化');
    }
    if (!DOMHelpers) {
      throw new Error('UserModals: DOMHelpers 未加载');
    }
    const { selectOne, from } = DOMHelpers;

    const modalEl = document.getElementById('userModal');
    if (!modalEl) {
      throw new Error('UserModals: 找不到 #userModal');
    }
    const bootstrapModal = new bootstrap.Modal(modalEl);

    const form = document.getElementById('userModalForm');
    const submitBtn = document.getElementById('userModalSubmit');
    const titleEl = document.getElementById('userModalTitle');
    const metaEl = document.getElementById('userModalMeta');

    let mode = 'create';
    let validator = null;
    let validatorMode = 'create';
    let editingUserMeta = null;

    /**
     * 初始化表单验证与事件。
     *
     * @param {void} 无参数。函数直接操作 #userModalForm。
     * @returns {void}
     */
    function init() {
      if (!FormValidator || !ValidationRules) {
        console.warn('UserModals: FormValidator 或 ValidationRules 未加载');
        return;
      }
      setupValidator('create');
      modalEl.addEventListener('hidden.bs.modal', resetForm);
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
      validator = FormValidator.create('#userModalForm');
      if (!validator) {
        console.warn('UserModals: FormValidator 初始化失败');
        return;
      }
      const passwordRules = nextMode === 'edit'
        ? ValidationRules.user.passwordOptional
        : ValidationRules.user.passwordRequired;
      validator
        .useRules('#userUsername', ValidationRules.user.username)
        .useRules('#userRole', ValidationRules.user.role)
        .useRules('#userPassword', passwordRules)
        .onSuccess(handleSubmit)
        .onFail(() => toast?.error?.('请检查用户信息填写'));
    }

    /**
     * 重置表单状态为创建模式。
     *
     * @param {void} 无参数。内部重置当前模态表单。
     * @returns {void}
     */
    function resetForm() {
      form.reset();
      form.dataset.formMode = 'create';
      mode = 'create';
      editingUserMeta = null;
      setupValidator('create');
      selectOne('#userPassword').attr('required', true);
      selectOne('#userPassword').attr('placeholder', '至少 8 位，包含大小写字母和数字');
      titleEl.textContent = '新建用户';
      submitBtn.textContent = '创建用户';
      updateModeMeta('create');
      validator?.instance?.refresh?.();
    }

    /**
     * 打开新建模态。
     *
     * @param {void} 无参数。重置表单并显示模态。
     * @returns {void}
     */
    function openCreate() {
      resetForm();
      bootstrapModal.show();
    }

    /**
     * 打开编辑模态并填充数据。
     *
     * @param {number|string} userId - 用户 ID
     * @return {Promise<void>}
     */
    async function openEdit(userId) {
      if (!userId) {
        return;
      }
      try {
        setupValidator('edit');
        selectOne('#userModalForm').attr('data-form-mode', 'edit');
        mode = 'edit';
        selectOne('#userPassword').attr('required', false);
        selectOne('#userPassword').attr('placeholder', '留空则保持原密码');
        titleEl.textContent = '编辑用户';
        submitBtn.textContent = '保存';
        updateModeMeta('edit');

        const payload = await http.get(`/users/api/users/${userId}`);
        if (!payload?.success || !payload?.data?.user) {
          toast?.error?.(payload?.message || '获取用户信息失败');
          return;
        }
        const user = payload.data.user;
        form.user_id.value = user.id;
        form.username.value = user.username;
        form.role.value = user.role;
        form.is_active.checked = Boolean(user.is_active);
        editingUserMeta = {
          role: user.role,
          is_active: Boolean(user.is_active),
          username: user.username,
        };
        bootstrapModal.show();
      } catch (error) {
        console.error('加载用户信息失败', error);
        toast?.error?.(error?.message || '加载用户信息失败');
      }
    }

    /**
     * 表单提交入口，按模式调用创建/更新。
     *
     * @param {Event} event - 提交事件
     * @return {void}
     */
    function handleSubmit(event) {
      event.preventDefault();
      const payload = buildPayload();
      if (!payload) {
        return;
      }
      if (mode === 'edit' && shouldWarnAboutAdminChange(payload)) {
        const confirmed = window.confirm('此操作将使该管理员失去管理权限，继续可能导致系统无人可管理，是否确认？');
        if (!confirmed) {
          return;
        }
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
     * @param {void} 无参数。直接读取 userModalForm。
     * @returns {Object|null} 表单数据对象
     */
    function buildPayload() {
      const data = new FormData(form);
      const payload = {
        username: data.get('username'),
        role: data.get('role'),
        is_active: form.is_active.checked,
      };
      const password = data.get('password');
      if (mode === 'create' || (password && password.trim() !== '')) {
        payload.password = password;
      }
      if (mode === 'edit') {
        payload.id = data.get('user_id');
      }
      return payload;
    }

    function updateModeMeta(nextMode) {
      if (!metaEl) {
        return;
      }
      if (nextMode === 'edit') {
        metaEl.textContent = '编辑';
        metaEl.classList.remove('status-pill--muted');
        metaEl.classList.add('status-pill--info');
      } else {
        metaEl.textContent = '新建';
        metaEl.classList.remove('status-pill--info');
        metaEl.classList.add('status-pill--muted');
      }
    }

    /**
     * 调用后端创建用户。
     *
     * @param {Object} payload - 用户数据
     * @return {void}
     */
    function submitCreate(payload) {
      http.post('/users/api/users', payload)
        .then((resp) => {
          if (!resp?.success) {
            throw new Error(resp?.message || '创建用户失败');
          }
          toast?.success?.(resp?.message || '用户创建成功');
          bootstrapModal.hide();
          window.location.reload();
        })
        .catch((error) => {
          console.error('创建用户失败', error);
          toast?.error?.(resolveErrorMessage(error, '创建用户失败'));
        })
        .finally(() => toggleLoading(false));
    }

    /**
     * 调用后端更新用户。
     *
     * @param {Object} payload - 用户数据
     * @return {void}
     */
    function submitUpdate(payload) {
      const userId = payload.id;
      if (!userId) {
        toast?.error?.('缺少用户ID');
        toggleLoading(false);
        return;
      }
      http.put(`/users/api/users/${userId}`, payload)
        .then((resp) => {
          if (!resp?.success) {
            throw new Error(resp?.message || '更新用户失败');
          }
          toast?.success?.(resp?.message || '用户更新成功');
          bootstrapModal.hide();
          window.location.reload();
        })
        .catch((error) => {
          console.error('更新用户失败', error);
          toast?.error?.(resolveErrorMessage(error, '更新用户失败'));
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
        submitBtn.textContent = mode === 'edit' ? '保存' : '创建用户';
      }
    }

    function shouldWarnAboutAdminChange(payload) {
      if (!editingUserMeta) {
        return false;
      }
      const wasAdmin = editingUserMeta.role === 'admin' && editingUserMeta.is_active;
      const willBeAdmin = payload.role === 'admin' && payload.is_active;
      return wasAdmin && !willBeAdmin;
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

  window.UserModals = {
    createController,
  };
})(window, document);
