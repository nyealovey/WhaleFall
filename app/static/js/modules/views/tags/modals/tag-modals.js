(function (window, document) {
  'use strict';

  /**
   * 创建标签新建/编辑模态控制器。
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
      throw new Error('TagModals: httpU 未初始化');
    }
    if (!DOMHelpers) {
      throw new Error('TagModals: DOMHelpers 未加载');
    }

    const modalEl = document.getElementById('tagModal');
    if (!modalEl) {
      throw new Error('TagModals: 找不到 #tagModal');
    }
    const bootstrapLib = window.bootstrap;
    if (!bootstrapLib) {
      throw new Error('TagModals: bootstrap 未加载');
    }
    const modal = new bootstrapLib.Modal(modalEl);
    const form = document.getElementById('tagModalForm');
    const submitBtn = document.getElementById('tagModalSubmit');
    const titleEl = document.getElementById('tagModalTitle');
    const metaTextEl = document.getElementById('tagModalMeta');
    const metaPillEl = document.getElementById('tagModalMetaPill');
    const colorSelect = document.getElementById('tagColor');
    const colorPreview = document.getElementById('tagColorPreview');

    let mode = 'create';
    let validator = null;
    let submitIntent = false;

    function markSubmitIntent() {
      submitIntent = true;
    }

    function clearSubmitIntent() {
      submitIntent = false;
    }

    function shouldHandleSubmit(event) {
      if (!submitBtn) {
        return true;
      }
      if (event?.submitter) {
        return event.submitter === submitBtn;
      }
      return submitIntent;
    }

    /**
     * 初始化表单验证与颜色预览。
     *
     * @return {void}
     */
    function init() {
      if (!FormValidator || !ValidationRules) {
        console.warn('TagModals: FormValidator 或 ValidationRules 未加载');
        return;
      }
      validator = FormValidator.create('#tagModalForm');
      validator
        .useRules('#tagName', ValidationRules.tag?.name)
        .useRules('#tagDisplayName', ValidationRules.tag?.displayName)
        .useRules('#tagCategory', ValidationRules.tag?.category)
        .onSuccess(handleSubmit)
        .onFail(() => toast?.error?.('请检查标签信息填写'));

      modalEl.addEventListener('hidden.bs.modal', resetForm);
      submitBtn?.addEventListener('click', markSubmitIntent);
      form?.addEventListener('keydown', (event) => {
        if (event.key === 'Enter' && event.target?.tagName !== 'TEXTAREA') {
          markSubmitIntent();
        }
      });
      colorSelect?.addEventListener('change', updateColorPreview);
      updateColorPreview();
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
      form.tag_id.value = '';
      titleEl.textContent = '添加标签';
      updateSubmitButtonCopy();
      setMetaState('新建', 'status-pill--muted');
      updateColorPreview();
      validator?.revalidate?.();
      validator?.instance?.refresh?.();
      clearSubmitIntent();
    }

    /**
     * 更新颜色预览。
     *
     * @return {void}
     */
    function updateColorPreview() {
      if (!colorSelect || !colorPreview) {
        return;
      }
      const value = colorSelect.value || 'primary';
      colorPreview.className = `badge bg-${value}`;
      colorPreview.textContent = '示例';
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
     * @param {number|string} tagId - 标签 ID
     * @return {Promise<void>}
     */
    async function openEdit(tagId) {
      if (!tagId) {
        return;
      }
      try {
        mode = 'edit';
        form.dataset.formMode = 'edit';
        titleEl.textContent = '编辑标签';
        updateSubmitButtonCopy();
        setMetaState('加载中', 'status-pill--muted');
        const payload = await http.get(`/api/v1/tags/${tagId}`);
        if (!payload?.success || !payload?.data?.tag) {
          throw new Error(payload?.message || '加载标签失败');
        }
        const tag = payload.data.tag;
        form.tag_id.value = tag.id;
        form.name.value = tag.name || '';
        form.display_name.value = tag.display_name || '';
        form.category.value = tag.category || '';
        form.color.value = tag.color || 'primary';
        form.is_active.checked = Boolean(tag.is_active);
        updateColorPreview();
        setMetaState('编辑', 'status-pill--info');
        modal.show();
      } catch (error) {
        console.error('加载标签失败', error);
        setMetaState('加载失败', 'status-pill--danger');
        toast?.error?.(error?.message || '加载标签失败');
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
      if (!shouldHandleSubmit(event)) {
        clearSubmitIntent();
        return;
      }
      clearSubmitIntent();
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
     * @return {Object|null} 表单数据对象
     */
    function buildPayload() {
      const data = new FormData(form);
      const payload = {
        name: data.get('name'),
        display_name: data.get('display_name'),
        category: data.get('category'),
        color: data.get('color') || 'primary',
        is_active: form.is_active.checked,
      };
      if (mode === 'edit') {
        payload.id = data.get('tag_id');
      }
      return payload;
    }

    /**
     * 调用后端创建标签。
     *
     * @param {Object} payload - 标签数据
     * @return {void}
     */
    function submitCreate(payload) {
      http.post('/api/v1/tags', payload)
        .then((resp) => {
          if (!resp?.success) {
            throw new Error(resp?.message || '添加标签失败');
          }
          toast?.success?.(resp?.message || '添加标签成功');
          modal.hide();
          window.location.reload();
        })
        .catch((error) => {
          console.error('添加标签失败', error);
          toast?.error?.(error?.message || '添加标签失败');
        })
        .finally(() => toggleLoading(false));
    }

    /**
     * 调用后端更新标签。
     *
     * @param {Object} payload - 标签数据
     * @return {void}
     */
    function submitUpdate(payload) {
      const tagId = payload.id;
      if (!tagId) {
        toast?.error?.('缺少标签ID');
        toggleLoading(false);
        return;
      }
      http.put(`/api/v1/tags/${tagId}`, payload)
        .then((resp) => {
          if (!resp?.success) {
            throw new Error(resp?.message || '保存标签失败');
          }
          toast?.success?.(resp?.message || '保存成功');
          modal.hide();
          window.location.reload();
        })
        .catch((error) => {
          console.error('保存标签失败', error);
          toast?.error?.(error?.message || '保存标签失败');
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
        submitBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>处理中';
      } else {
        updateSubmitButtonCopy();
      }
    }

    function updateSubmitButtonCopy() {
      if (!submitBtn) {
        return;
      }
      const nextText = mode === 'edit' ? '保存' : '添加标签';
      submitBtn.textContent = nextText;
      submitBtn.setAttribute('aria-label', mode === 'edit' ? '保存标签' : '提交新标签');
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

    return {
      init,
      openCreate,
      openEdit,
    };
  }

  window.TagModals = {
    createController,
  };
})(window, document);
