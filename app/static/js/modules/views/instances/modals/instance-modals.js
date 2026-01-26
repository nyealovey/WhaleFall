(function (window, document) {
  'use strict';

  /**
   * 创建实例新建/编辑模态控制器。
   *
   * @param {Object} [options] - 配置选项
   * @param {Object} options.store - InstanceCrudStore（由 Page Entry 注入）
   * @param {Function} [options.onSaved] - 保存成功后的回调（由 Page Entry 决定刷新策略）
   * @param {Object} [options.FormValidator] - 表单验证器
   * @param {Object} [options.ValidationRules] - 验证规则
   * @param {Object} [options.toast] - Toast 通知工具
   * @param {Object} [options.DOMHelpers] - DOM 辅助工具
   * @return {Object} 控制器对象，包含 init、openCreate、openEdit 方法
   * @throws {Error} 当必需的依赖未初始化时抛出
   */
  function createController(options) {
    const {
      store = null,
      onSaved = null,
      FormValidator = window.FormValidator,
      ValidationRules = window.ValidationRules,
      toast = window.toast,
      DOMHelpers = window.DOMHelpers,
    } = options || {};

    if (!DOMHelpers) throw new Error('InstanceModals: DOMHelpers 未加载');
    if (
      !store ||
      !store.actions ||
      typeof store.actions.load !== 'function' ||
      typeof store.actions.create !== 'function' ||
      typeof store.actions.update !== 'function'
    ) {
      throw new Error('InstanceModals: store 未初始化');
    }

    const modalEl = document.getElementById('instanceModal');
    if (!modalEl) throw new Error('InstanceModals: 找不到 #instanceModal');
    const bootstrapLib = window.bootstrap;
    if (!bootstrapLib) throw new Error('InstanceModals: bootstrap 未加载');
    const modal = new bootstrapLib.Modal(modalEl);
    const form = document.getElementById('instanceModalForm');
    const submitBtn = document.getElementById('instanceModalSubmit');
    const titleEl = document.getElementById('instanceModalTitle');
    const instanceIdInput = document.getElementById('instanceIdInput');
    const isActiveInput = document.getElementById('instanceIsActive');
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
      if (isActiveInput) {
        isActiveInput.checked = true;
      }
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
        const instance = await store.actions.load(instanceId);
        if (!instance) {
          throw new Error('加载实例失败');
        }
        fillForm(instance);
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
      if (isActiveInput) {
        isActiveInput.checked = Boolean(instance.is_active);
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
        is_active: isActiveInput ? isActiveInput.checked : false,
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
      store.actions.create(payload)
        .then((resp) => {
          toast?.success?.(resp?.message || '添加实例成功');
          modal.hide();
          if (typeof onSaved === 'function') {
            onSaved({ mode: 'create', response: resp });
          }
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
      store.actions.update(id, payload)
        .then((resp) => {
          toast?.success?.(resp?.message || '保存成功');
          modal.hide();
          if (typeof onSaved === 'function') {
            onSaved({ mode: 'edit', response: resp });
          }
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
      const resolver = window.UI?.resolveErrorMessage;
      if (typeof resolver === 'function') {
        return resolver(error, fallback);
      }
      if (!error) return fallback;
      if (typeof error === 'string') return error;
      return error.message || fallback;
    }

    return {
      init,
      openCreate,
      openEdit,
    };
  }

  window.InstanceModals = { createController };
})(window, document);
