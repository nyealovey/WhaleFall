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

    let mode = 'create';
    let validator = null;

    function init() {
      if (!FormValidator || !ValidationRules) {
        console.warn('UserModals: FormValidator 或 ValidationRules 未加载');
        return;
      }
      validator = FormValidator.create('#userModalForm');
      validator
        .useRules('#userUsername', ValidationRules.user.username)
        .useRules('#userRole', ValidationRules.user.role)
        .useRules('#userPassword', ValidationRules.user.passwordRequired)
        .onSuccess(handleSubmit)
        .onFail(() => toast?.error?.('请检查用户信息填写'));

      modalEl.addEventListener('hidden.bs.modal', resetForm);
    }

    function resetForm() {
      form.reset();
      form.dataset.formMode = 'create';
      mode = 'create';
        selectOne('#userPassword').attr('required', true);
        selectOne('#userPassword').attr('placeholder', '至少 8 位，包含大小写字母和数字');
      titleEl.textContent = '新建用户';
      submitBtn.textContent = '创建用户';
      validator?.revalidate?.();
      validator?.instance?.refresh?.();
    }

    function openCreate() {
      resetForm();
      bootstrapModal.show();
    }

    async function openEdit(userId) {
      if (!userId) {
        return;
      }
      try {
        selectOne('#userModalForm').attr('data-form-mode', 'edit');
        mode = 'edit';
        selectOne('#userPassword').attr('required', false);
        selectOne('#userPassword').attr('placeholder', '留空则保持原密码');
        titleEl.textContent = '编辑用户';
        submitBtn.textContent = '保存';

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
        bootstrapModal.show();
      } catch (error) {
        console.error('加载用户信息失败', error);
        toast?.error?.(error?.message || '加载用户信息失败');
      }
    }

    function handleSubmit(event) {
      event.preventDefault();
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
          toast?.error?.(error?.message || '创建用户失败');
        })
        .finally(() => toggleLoading(false));
    }

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
          toast?.error?.(error?.message || '更新用户失败');
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
        submitBtn.textContent = mode === 'edit' ? '保存' : '创建用户';
      }
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
