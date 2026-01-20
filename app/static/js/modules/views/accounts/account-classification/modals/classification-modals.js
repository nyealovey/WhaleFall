(function (global) {
  "use strict";

  /**
   * 创建账户分类新建/编辑模态控制器。
   *
   * @param {Object} [options] - 配置选项
   * @param {Object} [options.document] - Document 对象
   * @param {Object} [options.UI] - UI 工具对象
   * @param {Object} [options.toast] - Toast 通知工具
   * @param {Object} [options.FormValidator] - 表单验证器
   * @param {Object} [options.ValidationRules] - 验证规则
   * @param {Object} [options.api] - API 服务对象
   * @param {Function} [options.debugLog] - 调试日志函数
   * @param {Function} [options.handleRequestError] - 请求错误处理函数
   * @param {Function} [options.onMutated] - 数据变更回调
   * @return {Object} 控制器对象
   * @throws {Error} 当必需的依赖未初始化时抛出
   */
  function createController(options) {
    const {
      document,
      UI,
      toast,
      FormValidator,
      ValidationRules,
      api,
      debugLog,
      handleRequestError,
      onMutated,
    } = options || {};

    if (!document) {
      throw new Error("classification-modals: document is required");
    }
    if (!api) {
      throw new Error("classification-modals: api is required");
    }

    const validators = {
      create: null,
      edit: null,
    };
    const modals = {
      create: null,
      edit: null,
    };

    /**
     * 初始化模态与表单验证。
     *
     * @param {Object} [config={}] 自定义初始化参数。
     * @param {Object} [config.validatorOptions] 表单校验配置。
     * @returns {void}
     * @throws {Error} 当 UI.createModal 未加载时抛出
     */
    function init(config = {}) {
      if (!UI?.createModal) {
        throw new Error("classification-modals: UI.createModal 未加载");
      }
      debug("初始化分类模态控制器");
      modals.create = UI.createModal({
        modalSelector: "#createClassificationModal",
        onConfirm: event => triggerCreate(event),
        onClose: resetCreateForm,
      });
      modals.edit = UI.createModal({
        modalSelector: "#editClassificationModal",
        onConfirm: event => triggerUpdate(event),
        onClose: resetEditForm,
      });
      initFormValidators(config.validatorOptions);
    }

    /**
     * 打开新建分类模态框。
     *
     * @param {Event} [event] - 触发事件
     * @return {void}
     */
    function openCreate(event) {
      event?.preventDefault?.();
      resetCreateForm();
      modals.create?.open();
    }

    /**
     * 根据 ID 打开编辑分类模态框。
     *
     * @param {number|string} id - 分类 ID
     * @param {Event} [event] - 触发事件
     * @return {Promise<void>}
     */
    async function openEditById(id, event) {
      event?.preventDefault?.();
      if (!id) {
        toast?.error?.("未找到分类 ID");
        return;
      }
      try {
        const response = await api.detail(id);
        const classification = response?.data?.classification ?? response?.classification;
        if (!classification) {
          toast?.error?.("未获取到分类信息");
          return;
        }
        resetEditForm();
        fillEditForm(classification);
        modals.edit?.open();
      } catch (error) {
        handleRequestError?.(error, "获取分类信息失败", "edit_classification");
      }
    }

    /**
     * 触发创建分类操作。
     *
     * @param {Event} [event] 触发 onConfirm 的事件。
     * @returns {void}
     */
    function triggerCreate(event) {
      event?.preventDefault?.();
      const form = document.getElementById("createClassificationForm");
      if (form && validators.create?.instance) {
        submitViaForm(form);
        return;
      }
      if (form) {
        submitCreate(form);
      }
    }

    /**
     * 触发更新分类操作。
     *
     * @param {Event} [event] 触发 onConfirm 的事件。
     * @returns {void}
     */
    function triggerUpdate(event) {
      event?.preventDefault?.();
      const form = document.getElementById("editClassificationForm");
      if (form && validators.edit?.instance) {
        submitViaForm(form);
        return;
      }
      if (form) {
        submitUpdate(form);
      }
    }

    function submitViaForm(form) {
      if (!form) return;
      if (typeof form.requestSubmit === "function") {
        form.requestSubmit();
      } else {
        const event = new Event("submit", { bubbles: true, cancelable: true });
        form.dispatchEvent(event);
      }
    }

    /**
     * 提交创建分类请求。
     *
     * @param {HTMLFormElement} form - 表单元素
     * @return {Promise<void>}
     */
    async function submitCreate(form) {
      const payload = collectCreatePayload(form);

      if (!payload) {
        toast?.error?.("请填写完整的分类信息");
        return;
      }

      try {
        const response = await api.create(payload);
        toast?.success?.(response?.message || "分类创建成功");
        modals.create?.close();
        form.reset();
        refreshValidator(validators.create);
        await onMutated?.("created");
      } catch (error) {
        handleRequestError?.(error, "创建分类失败", "create_classification");
      }
    }

    /**
     * 提交更新分类请求。
     *
     * @param {HTMLFormElement} form - 表单元素
     * @return {Promise<void>}
     */
    async function submitUpdate(form) {
      const payload = collectUpdatePayload(form);
      const id = form.querySelector("#editClassificationId")?.value;

      if (!payload || !id) {
        toast?.error?.("请填写完整的分类信息");
        return;
      }

      try {
        const response = await api.update(id, payload);
        toast?.success?.(response?.message || "分类更新成功");
        modals.edit?.close();
        refreshValidator(validators.edit);
        await onMutated?.("updated");
      } catch (error) {
        handleRequestError?.(error, "更新分类失败", "update_classification");
      }
    }

    /**
     * 获取输入值并去除首尾空格。
     *
     * @param {HTMLFormElement} form 表单元素
     * @param {string} selector 元素选择器
     * @return {string} 处理后的字符串
     */
    function getTrimmedValue(form, selector) {
      const element = form.querySelector(selector);
      if (!element) {
        return "";
      }
      return String(element.value || "").trim();
    }

    function parseRiskLevel(value, fallback) {
      const resolvedFallback = Number.isInteger(fallback) ? fallback : 4;
      const raw = Number(value);
      if (!Number.isInteger(raw)) {
        return resolvedFallback;
      }
      if (raw < 1) {
        return 1;
      }
      if (raw > 6) {
        return 6;
      }
      return raw;
    }

    function collectCreatePayload(form) {
      const code = getTrimmedValue(form, "#classificationCode").toLowerCase();
      const displayName = getTrimmedValue(form, "#classificationDisplayName");
      const description = getTrimmedValue(form, "#classificationDescription");
      const riskLevel = parseRiskLevel(getTrimmedValue(form, "#riskLevel"), 4);
      const priority = parsePriority(getTrimmedValue(form, "#priority"));
      const iconRadio = form.querySelector('input[name="classificationIcon"]:checked');

      if (!code) {
        return null;
      }

      const payload = {
        code,
        display_name: displayName,
        description,
        risk_level: riskLevel,
        icon_name: iconRadio ? iconRadio.value : "fa-tag",
        priority,
      };

      if (!payload.display_name) {
        delete payload.display_name;
      }

      return payload;
    }

    function collectUpdatePayload(form) {
      const displayName = getTrimmedValue(form, "#editClassificationName");
      const description = getTrimmedValue(form, "#editClassificationDescription");
      const priority = parsePriority(getTrimmedValue(form, "#editClassificationPriority"));
      const isSystem = getTrimmedValue(form, "#editClassificationIsSystem") === "true";

      if (!displayName) {
        return null;
      }

      const payload = {
        display_name: displayName,
        description,
        priority,
      };

      if (isSystem) {
        return payload;
      }

      payload.risk_level = parseRiskLevel(getTrimmedValue(form, "#editClassificationRiskLevel"), 4);
      const iconRadio = form.querySelector('input[name="editClassificationIcon"]:checked');
      payload.icon_name = iconRadio ? iconRadio.value : "fa-tag";

      return payload;
    }

    /**
     * 解析优先级值。
     *
     * @param {string|number} value - 优先级值
     * @return {number} 解析后的优先级（0-100）
     */
    function parsePriority(value) {
      const parsed = Number(value);
      if (Number.isNaN(parsed) || parsed < 0) {
        return 0;
      }
      if (parsed > 100) {
        return 100;
      }
      return parsed;
    }

    /**
     * 填充编辑表单数据。
     *
     * @param {Object} classification - 分类对象
     * @return {void}
     */
    function fillEditForm(classification) {
      document.getElementById("editClassificationId").value = classification.id;
      document.getElementById("editClassificationIsSystem").value = classification.is_system ? "true" : "false";
      document.getElementById("editClassificationCode").value = classification.code || "";
      document.getElementById("editClassificationName").value = classification.display_name || classification.name || "";
      document.getElementById("editClassificationDescription").value = classification.description || "";
      document.getElementById("editClassificationRiskLevel").value = String(classification.risk_level || 4);
      document.getElementById("editClassificationPriority").value = classification.priority ?? 0;

      const iconName = classification.icon_name || "fa-tag";
      const radio = document.querySelector(`input[name="editClassificationIcon"][value="${iconName}"]`);
      if (radio) {
        radio.checked = true;
      } else {
        const fallback = document.querySelector('input[name="editClassificationIcon"][value="fa-tag"]');
        if (fallback) {
          fallback.checked = true;
        }
      }
      applyEditSystemLock(Boolean(classification.is_system));
    }

    function applyEditSystemLock(isSystem) {
      const riskLevelSelect = document.getElementById("editClassificationRiskLevel");
      if (riskLevelSelect) {
        riskLevelSelect.disabled = Boolean(isSystem);
      }
      document.querySelectorAll('input[name="editClassificationIcon"]').forEach(function (input) {
        input.disabled = Boolean(isSystem);
      });
    }

    /**
     * 初始化表单验证器。
     *
     * @param {Object} [options={}] 自定义表单选择器。
     * @param {string} [options.createFormSelector="#createClassificationForm"] 新建表单。
     * @param {string} [options.editFormSelector="#editClassificationForm"] 编辑表单。
     * @returns {void}
     */
    function initFormValidators(options = {}) {
      const {
        createFormSelector = "#createClassificationForm",
        editFormSelector = "#editClassificationForm",
      } = options;
      const validatorFactory = FormValidator || global.FormValidator;
      const rules = ValidationRules || global.ValidationRules;

      if (!validatorFactory || !rules) {
        console.error("classification-modals: 表单校验模块未正确加载");
        return;
      }

      const createForm = document.querySelector(createFormSelector);
      if (createForm) {
        validators.create = validatorFactory.create(createFormSelector);
        if (validators.create) {
          validators.create
            .useRules("#classificationCode", rules.classification.code)
            .useRules("#classificationDisplayName", rules.classification.displayNameOptional)
            .useRules("#priority", rules.classification.priority)
            .onSuccess(event => submitCreate(event.target))
            .onFail(() => toast?.error?.("请检查分类信息填写"));

          bindRevalidate(createForm, "#classificationCode", validators.create);
          bindRevalidate(createForm, "#classificationDisplayName", validators.create);
          bindRevalidate(createForm, "#priority", validators.create, "input");
        }
      }

      const editForm = document.querySelector(editFormSelector);
      if (editForm) {
        validators.edit = validatorFactory.create(editFormSelector);
        if (validators.edit) {
          validators.edit
            .useRules("#editClassificationName", rules.classification.displayNameRequired)
            .useRules("#editClassificationPriority", rules.classification.priority)
            .onSuccess(event => submitUpdate(event.target))
            .onFail(() => toast?.error?.("请检查分类信息填写"));

          bindRevalidate(editForm, "#editClassificationName", validators.edit);
          bindRevalidate(editForm, "#editClassificationPriority", validators.edit, "input");
        }
      }
    }

    /**
     * 绑定字段重新验证。
     *
     * @param {HTMLFormElement} form - 表单元素
     * @param {string} selector - 字段选择器
     * @param {Object} validator - 验证器对象
     * @param {string} [eventName] - 事件名称
     * @returns {void}
     */
    function bindRevalidate(form, selector, validator, eventName) {
      const field = form.querySelector(selector);
      if (!field || !validator) {
        return;
      }
      const evt = eventName || "blur";
      field.addEventListener(evt, function () {
        if (typeof validator.revalidateField === "function") {
          validator.revalidateField(selector);
        }
      });
    }

    /**
     * 重置创建表单。
     *
     * @param {HTMLFormElement} [formElement] 可选表单。
     * @returns {void}
     */
    function resolveFormArg(formElement, fallbackId) {
      if (!formElement || formElement instanceof HTMLFormElement) {
        return formElement || document.getElementById(fallbackId);
      }
      if (formElement?.event instanceof Event) {
        return document.getElementById(fallbackId);
      }
      return document.getElementById(fallbackId);
    }

    function resetCreateForm(formElement) {
      const form = resolveFormArg(formElement, "createClassificationForm");
      if (form) {
        form.reset();
      }
      refreshValidator(validators.create);
    }

    /**
     * 重置编辑表单。
     *
     * @param {HTMLFormElement} [formElement] 可选表单。
     * @returns {void}
     */
    function resetEditForm(formElement) {
      const form = resolveFormArg(formElement, "editClassificationForm");
      if (form) {
        form.reset();
      }
      const isSystemInput = document.getElementById("editClassificationIsSystem");
      if (isSystemInput) {
        isSystemInput.value = "";
      }
      applyEditSystemLock(false);
      refreshValidator(validators.edit);
    }

    /**
     * 刷新验证器。
     *
     * @param {Object} validator 验证器对象。
     * @returns {void}
     */
    function refreshValidator(validator) {
      if (validator?.instance?.refresh) {
        validator.instance.refresh();
      }
    }

    /**
     * 输出调试信息。
     *
     * @param {string} message 调试消息。
     * @param {*} [payload] 附加数据。
     * @returns {void}
     */
    function debug(message, payload) {
      if (typeof debugLog === "function") {
        debugLog(message, payload);
      }
    }

    return {
      init,
      openCreate,
      openEditById,
      triggerCreate,
      triggerUpdate,
      resetCreateForm,
      resetEditForm,
    };
  }

  global.AccountClassificationModals = {
    createController,
  };
})(window);
