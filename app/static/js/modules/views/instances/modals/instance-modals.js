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

    if (!http) throw new Error('InstanceModals: httpU 未初始化');
    if (!DOMHelpers) throw new Error('InstanceModals: DOMHelpers 未加载');
    const { selectOne, from } = DOMHelpers;

    const modalEl = document.getElementById('instanceModal');
    if (!modalEl) throw new Error('InstanceModals: 找不到 #instanceModal');
    const modal = new bootstrap.Modal(modalEl);
    const form = document.getElementById('instanceModalForm');
    const submitBtn = document.getElementById('instanceModalSubmit');
    const titleEl = document.getElementById('instanceModalTitle');

    let mode = 'create';
    let validator = null;

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

    function resetForm() {
      form.reset();
      form.dataset.formMode = 'create';
      mode = 'create';
      form.instance_id.value = '';
      titleEl.textContent = '添加实例';
      submitBtn.textContent = '保存';
      if (validator?.instance?.refresh) {
        validator.instance.refresh();
      }
    }

    function openCreate() {
      resetForm();
      modal.show();
    }

    async function openEdit(instanceId) {
      if (!instanceId) return;
      try {
        mode = 'edit';
        form.dataset.formMode = 'edit';
        titleEl.textContent = '编辑实例';
        submitBtn.textContent = '保存';
        const resp = await http.get(`/instances/api/${instanceId}`);
        const data = resp?.data?.instance || resp?.data;
        if (!resp?.success || !data) {
          throw new Error(resp?.message || '加载实例失败');
        }
        fillForm(data);
        modal.show();
      } catch (error) {
        console.error('加载实例失败', error);
        toast?.error?.(error?.message || '加载实例失败');
      }
    }

    function fillForm(instance) {
      form.instance_id.value = instance.id;
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

    function submitCreate(payload) {
      http.post('/instances/api/create', payload)
        .then((resp) => {
          if (!resp?.success) throw new Error(resp?.message || '添加实例失败');
          toast?.success?.(resp?.message || '添加实例成功');
          modal.hide();
          window.location.reload();
        })
        .catch((error) => {
          console.error('添加实例失败', error);
          toast?.error?.(error?.message || '添加实例失败');
        })
        .finally(() => toggleLoading(false));
    }

    function submitUpdate(payload) {
      const id = payload.id;
      if (!id) {
        toast?.error?.('缺少实例ID');
        toggleLoading(false);
        return;
      }
      http.post(`/instances/api/edit/${id}`, payload)
        .then((resp) => {
          if (!resp?.success) throw new Error(resp?.message || '保存实例失败');
          toast?.success?.(resp?.message || '保存成功');
          modal.hide();
          window.location.reload();
        })
        .catch((error) => {
          console.error('保存实例失败', error);
          toast?.error?.(error?.message || '保存实例失败');
        })
        .finally(() => toggleLoading(false));
    }

    function toggleLoading(loading) {
      if (!submitBtn) return;
      submitBtn.disabled = loading;
      submitBtn.innerHTML = loading
        ? '<span class="spinner-border spinner-border-sm me-2"></span>处理中'
        : '保存';
    }

    return {
      init,
      openCreate,
      openEdit,
    };
  }

  window.InstanceModals = { createController };
})(window, document);
