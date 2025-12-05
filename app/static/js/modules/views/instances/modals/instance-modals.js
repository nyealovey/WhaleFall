(function (window, document) {
  'use strict';

  /**
   * 创建实例新建/编辑模态控制器。
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

    if (!http) throw new Error('InstanceModals: httpU 未初始化');
    if (!window.InstanceService) throw new Error('InstanceModals: InstanceService 未加载');
    if (!DOMHelpers) throw new Error('InstanceModals: DOMHelpers 未加载');
    const { selectOne, from } = DOMHelpers;
    const instanceService = new window.InstanceService(http);

    const modalEl = document.getElementById('instanceModal');
    if (!modalEl) throw new Error('InstanceModals: 找不到 #instanceModal');
    const modal = new bootstrap.Modal(modalEl);
    const form = document.getElementById('instanceModalForm');
    const submitBtn = document.getElementById('instanceModalSubmit');
    const titleEl = document.getElementById('instanceModalTitle');
    const instanceIdInput = document.getElementById('instanceIdInput');
    const metaTextEl = document.getElementById('instanceModalMeta');
    const metaPillEl = document.getElementById('instanceModalMetaPill');
    const metaVariants = ['status-pill--muted', 'status-pill--info', 'status-pill--danger'];

    let mode = 'create';
    let validator = null;

    /**
     * 初始化表单验证与事件。
     *
     * @return {void}
     */
    function init() {
      if (!FormValidator || !ValidationRules) {
        console.warn('InstanceModals: FormValidator/ValidationRules 未加载');
        return;
      }
      validator = FormValidator.create('#instanceModalForm');
      validator
        .useRules('#instanceName', ValidationRules.instance?.name)
        .useRules('#instanceDbType', ValidationRules.instance?.dbType)
        .useRules('#instanceHost', ValidationRules.instance?.host)
        .useRules('#instancePort', ValidationRules.instance?.port || [
          { rule: 'required', errorMessage: '请输入端口' },
        ])
        .onSuccess(handleSubmit)
        .onFail(() => toast?.error?.('请检查实例信息填写'));

      modalEl.addEventListener('hidden.bs.modal', resetForm);
    }

    /**
     * 重置表单状态为创建模式。
     *
     * @return {void}
     */
    function resetForm() {
      form.reset();
      form.dataset.formMode = 'create';
      mode = 'create';
      if (instanceIdInput) {
        instanceIdInput.value = '';
      } else if (form.instance_id) {
        form.instance_id.value = '';
      }
      titleEl.textContent = '添加实例';
      setMetaState('新建', 'status-pill--muted');
      updateSubmitButtonCopy();
      if (validator?.instance?.refresh) {
        validator.instance.refresh();
      }
    }

    /**
     * 打开新建模态。
     *
     * @return {void}
     */
    function openCreate() {
      resetForm();
      modal.show();
    }

    /**
     * 打开编辑模态并填充数据。
     *
     * @param {number|string} instanceId - 实例 ID
     * @return {Promise<void>}
     */
    async function openEdit(instanceId) {
      if (!instanceId) return;
      try {
        mode = 'edit';
        form.dataset.formMode = 'edit';
        titleEl.textContent = '编辑实例';
        updateSubmitButtonCopy();
        setMetaState('加载中', 'status-pill--muted');
        const resp = await instanceService.getInstance(instanceId);
        const data = resp?.data?.instance || resp?.data;
        if (!resp?.success || !data) {
          throw new Error(resp?.message || '加载实例失败');
        }
        fillForm(data);
        setMetaState('编辑', 'status-pill--info');
        modal.show();
      } catch (error) {
        console.error('加载实例失败', error);
        setMetaState('加载失败', 'status-pill--danger');
        toast?.error?.(resolveErrorMessage(error, '加载实例失败'));
      }
    }

    /**
     * 填充表单数据。
     *
     * @param {Object} instance - 实例对象
     * @return {void}
     */
    function fillForm(instance) {
      if (instanceIdInput) {
        instanceIdInput.value = instance.id;
      } else if (form.instance_id) {
        form.instance_id.value = instance.id;
      }
      form.name.value = instance.name || '';
      form.db_type.value = instance.db_type || '';
      form.host.value = instance.host || '';
      form.port.value = instance.port || '';
      form.database_name.value = instance.database_name || '';
      form.description.value = instance.description || '';
      const credSelect = form.querySelector('#instanceCredential');
      if (credSelect) {
        credSelect.value = instance.credential_id || '';
      }
      form.is_active.checked = Boolean(instance.is_active);
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
      if (!payload) return;
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
     * @return {Object|null} 表单数据对象
     */
    function buildPayload() {
      const data = new FormData(form);
      const payload = {
        name: data.get('name'),
        db_type: data.get('db_type'),
        host: data.get('host'),
        port: Number(data.get('port')),
        database_name: data.get('database_name') || '',
        credential_id: data.get('credential_id') || '',
        description: data.get('description') || '',
        is_active: form.is_active.checked,
      };
      if (mode === 'edit') {
        payload.id = data.get('instance_id');
      }
      return payload;
    }

    /**
     * 调用后端创建实例。
     *
     * @param {Object} payload - 实例数据
     * @return {void}
     */
    function submitCreate(payload) {
      instanceService.createInstance(payload)
        .then((resp) => {
          if (!resp?.success) throw new Error(resp?.message || '添加实例失败');
          toast?.success?.(resp?.message || '添加实例成功');
          modal.hide();
          window.location.reload();
        })
        .catch((error) => {
          console.error('添加实例失败', error);
          toast?.error?.(resolveErrorMessage(error, '添加实例失败'));
        })
        .finally(() => toggleLoading(false));
    }

    /**
     * 调用后端更新实例。
     *
     * @param {Object} payload - 实例数据
     * @return {void}
     */
    function submitUpdate(payload) {
      const id = payload.id;
      if (!id) {
        toast?.error?.('缺少实例ID');
        toggleLoading(false);
        return;
      }
      instanceService.updateInstance(id, payload)
        .then((resp) => {
          if (!resp?.success) throw new Error(resp?.message || '保存实例失败');
          toast?.success?.(resp?.message || '保存成功');
          modal.hide();
          window.location.reload();
        })
        .catch((error) => {
          console.error('保存实例失败', error);
          toast?.error?.(resolveErrorMessage(error, '保存实例失败'));
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
      if (!submitBtn) return;
      submitBtn.disabled = loading;
      if (loading) {
        submitBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>处理中';
      } else {
        updateSubmitButtonCopy();
      }
    }

    function updateSubmitButtonCopy() {
      if (!submitBtn) {
        return;
      }
      const text = mode === 'edit' ? '保存' : '创建实例';
      submitBtn.textContent = text;
      submitBtn.setAttribute('aria-label', mode === 'edit' ? '保存实例' : '提交新实例');
    }

    function setMetaState(label, variant) {
      if (metaTextEl) {
        metaTextEl.textContent = label;
      }
      if (metaPillEl) {
        metaPillEl.classList.remove(...metaVariants);
        metaPillEl.classList.add(variant || 'status-pill--muted');
      }
    }

    function resolveErrorMessage(error, fallback) {
      if (!error) return fallback;
      if (error.response?.message) return error.response.message;
      if (error.response?.data?.message) return error.response.data.message;
      if (error.message) return error.message;
      return fallback;
    }

    return {
      init,
      openCreate,
      openEdit,
    };
  }

  window.InstanceModals = { createController };
})(window, document);
