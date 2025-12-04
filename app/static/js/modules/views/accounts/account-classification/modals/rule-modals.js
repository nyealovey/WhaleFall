(function (global) {
  "use strict";

  /**
   * 规则模态控制器，负责新建/编辑/查看。
   *
   * @param {Object} [options={}] 依赖集合。
   * @param {Document} options.document DOM Document。
   * @param {Object} options.UI UI 工具对象。
   * @param {Object} options.toast Toast 工具。
   * @param {Object} options.FormValidator 表单验证工厂。
   * @param {Object} options.ValidationRules 校验规则集合。
   * @param {Object} options.api 规则 API（detail/create/update）。
   * @param {Object} [options.permissionView] 权限渲染器。
   * @param {Function} [options.debugLog] 调试输出。
   * @param {Function} [options.handleRequestError] 错误处理。
   * @param {Function} [options.onMutated] 成功回调。
   * @param {Function} [options.getClassificationOptions] 获取分类列表函数。
   * @returns {Object} 暴露 init/open/trigger API 的控制器。
   */
  function createController(options) {
    const {
      document,
      UI,
      toast,
      FormValidator,
      ValidationRules,
      api,
      permissionView,
      debugLog,
      handleRequestError,
      onMutated,
      getClassificationOptions,
    } = options || {};

    if (!document) {
      throw new Error("rule-modals: document is required");
    }
    if (!api) {
      throw new Error("rule-modals: api is required");
    }

    const state = {
      modals: {
        create: null,
        edit: null,
        view: null,
      },
      validators: {
        create: null,
      },
      classifications: [],
    };

    const statusVariants = {
      active: { text: "启用", variant: "status-pill--success" },
      inactive: { text: "禁用", variant: "status-pill--muted" },
    };

    const dbTypeLabels = {
      mysql: "MySQL",
      postgresql: "PostgreSQL",
      sqlserver: "SQL Server",
      oracle: "Oracle",
      redis: "Redis",
    };

    function renderStatusPill(isActive) {
      const config = isActive ? statusVariants.active : statusVariants.inactive;
      return `<span class="status-pill ${config.variant}">${config.text}</span>`;
    }

    function summarizeRulePermissions(expression) {
      if (!expression || typeof expression !== "object") {
        return null;
      }
      let total = 0;
      Object.values(expression).forEach(value => {
        if (Array.isArray(value)) {
          total += value.length;
        }
      });
      return total > 0 ? `共 ${total} 项权限` : null;
    }

    function formatDbType(dbType) {
      if (!dbType) {
        return "-";
      }
      const key = String(dbType).toLowerCase();
      return dbTypeLabels[key] || dbType.toString();
    }

    /**
     * 初始化所有模态与验证器。
     *
     * @param {Object} [config={}] 自定义初始化参数。
     * @param {Object} [config.modalOptions] createModal 额外配置。
     * @param {Object} [config.validatorOptions] 校验配置。
     * @returns {void}
     */
    function init(config = {}) {
      if (!UI?.createModal) {
        throw new Error("rule-modals: UI.createModal 未加载");
      }
      debug("初始化规则模态控制器");
      const modalOptions = config.modalOptions || {};
      state.modals.create = UI.createModal({
        modalSelector: "#createRuleModal",
        onConfirm: event => triggerCreate(event),
        onClose: resetCreateForm,
        size: "lg",
        ...(modalOptions.create || {}),
      });
      state.modals.edit = UI.createModal({
        modalSelector: "#editRuleModal",
        onConfirm: event => submitUpdate(event),
        onClose: resetEditForm,
        size: "lg",
        ...(modalOptions.edit || {}),
      });
      state.modals.view = UI.createModal({
        modalSelector: "#viewRuleModal",
        onClose: resetViewModal,
        size: "lg",
        ...(modalOptions.view || {}),
      });
      initFormValidators(config.validatorOptions);
      syncClassificationOptions();
    }

    /**
     * 同步分类下拉选项，来自外部 state 或内部缓存。
     *
     * @param {Array<Object>} [list] 可选的分类数组。
     * @returns {void}
     */
    function syncClassificationOptions(list) {
      if (Array.isArray(list)) {
        state.classifications = list.slice();
      } else if (typeof getClassificationOptions === "function") {
        const provided = getClassificationOptions();
        if (Array.isArray(provided)) {
          state.classifications = provided.slice();
        }
      }
      populateClassificationSelect("ruleClassification", state.classifications);
      populateClassificationSelect("editRuleClassification", state.classifications);
    }

    /**
     * 渲染分类下拉列表。
     *
     * @param {string} elementId select 元素 ID。
     * @param {Array<Object>} classifications 分类列表。
     * @returns {HTMLSelectElement|null} 渲染完成的 select。
     */
    function populateClassificationSelect(elementId, classifications) {
      const select = document.getElementById(elementId);
      if (!select) {
        return null;
      }
      select.innerHTML = '<option value="">请选择分类</option>';
      (classifications || []).forEach(classification => {
        const option = document.createElement("option");
        option.value = classification.id;
        option.textContent = classification.name;
        select.appendChild(option);
      });
      return select;
    }

    /**
     * 打开新建模态。
     *
     * @param {Event} [event] 触发事件。
     * @returns {void}
     */
    function openCreate(event) {
      event?.preventDefault?.();
      syncClassificationOptions();
      resetCreateForm();
      state.modals.create?.open();
    }

    /**
     * 打开编辑模态并填充数据。
     */
    async function openEditById(id, event) {
      event?.preventDefault?.();
      if (!id) {
        toast?.error?.("未找到规则 ID");
        return;
      }
      try {
        const response = await api.detail(id);
        const rule = response?.data?.rule ?? response?.rule;
        if (!rule) {
          toast?.error?.("未获取到规则信息");
          return;
        }

        syncClassificationOptions();
        resetEditForm();

        document.getElementById("editRuleId").value = rule.id;
        document.getElementById("editRuleName").value = rule.rule_name || "";
        document.getElementById("editRuleClassification").value = rule.classification_id || "";
        document.getElementById("editRuleDbType").value = rule.db_type || "";
        document.getElementById("editRuleDbTypeHidden").value = rule.db_type || "";
        document.getElementById("editRuleOperator").value =
          (rule.rule_expression && rule.rule_expression.operator) || "OR";

        state.modals.edit?.open();
        loadPermissions("edit").then(() => {
          permissionView?.setSelected?.(
            rule.db_type,
            rule.rule_expression,
            "editPermissionsConfig",
            "edit",
          );
        });
      } catch (error) {
        handleRequestError?.(error, "获取规则信息失败", "edit_rule");
      }
    }

    /**
     * 打开查看模态，展示详细信息。
     *
     * @param {number|string} id 规则 ID。
     * @param {Event} [event] 触发事件。
     * @returns {Promise<void>} 完成后 resolve。
     */
    async function openViewById(id, event) {
      event?.preventDefault?.();
      if (!id) {
        toast?.error?.("未找到规则 ID");
        return;
      }
      try {
        const response = await api.detail(id);
        const rule = response?.data?.rule ?? response?.rule;
        if (!rule) {
          toast?.error?.("未获取到规则信息");
          return;
        }

        const modalEl = document.getElementById("viewRuleModal");
        if (modalEl) {
          modalEl.dataset.ruleId = rule.id;
        }

        const modalMeta = document.getElementById("viewRuleModalMeta");
        if (modalMeta) {
          modalMeta.textContent = rule.rule_name || "规则信息";
        }

        const operator =
          rule.rule_expression?.operator === "AND"
            ? "AND (所有条件都必须满足)"
            : "OR (任一条件满足即可)";
        document.getElementById("viewRuleOperator").textContent = operator;

        const classification = rule.classification_name || rule.classification?.name;
        const classificationEl = document.getElementById("viewRuleClassification");
        if (classificationEl) {
          classificationEl.textContent = classification || "未分类";
        }
        const dbTypeEl = document.getElementById("viewRuleDbType");
        if (dbTypeEl) {
          dbTypeEl.textContent = formatDbType(rule.db_type);
        }

        const permissionsContainer = document.getElementById("viewPermissionsConfig");
        if (permissionsContainer) {
          permissionsContainer.innerHTML =
            permissionView?.renderDisplay?.(rule.db_type, rule.rule_expression) ||
            '<div class="rule-detail-empty">无权限配置</div>';
        }
        const permissionsMeta = document.getElementById("viewRulePermissionsMeta");
        if (permissionsMeta) {
          const summary = summarizeRulePermissions(rule.rule_expression);
          permissionsMeta.textContent = summary || "无权限配置";
          permissionsMeta.className = `status-pill ${summary ? "status-pill--info" : "status-pill--muted"}`;
        }

        state.modals.view?.open();
      } catch (error) {
        handleRequestError?.(error, "获取规则信息失败", "view_rule");
      }
    }

    /**
     * 触发表单校验并在校验通过后提交创建。
     *
     * @param {Event} [event] onConfirm 事件。
     * @returns {void}
     */
    function triggerCreate(event) {
      event?.preventDefault?.();
      if (state.validators.create?.revalidate) {
        state.validators.create.revalidate();
        return;
      }
      if (state.validators.create?.instance?.revalidate) {
        state.validators.create.instance.revalidate();
        return;
      }
      const form = document.getElementById("createRuleForm");
      if (form) {
        submitCreate(form);
      }
    }

    /**
     * 提交创建请求。
     *
     * @param {HTMLFormElement} form 规则创建表单。
     * @returns {Promise<void>} 创建完成后 resolve。
     */
    async function submitCreate(form) {
      if (!(form instanceof HTMLFormElement)) {
        return;
      }
      const payload = collectRulePayload(form, {
        idField: "#ruleId",
        classification: "#ruleClassification",
        name: "#ruleName",
        dbType: "#ruleDbType",
        operator: "#ruleOperator",
        permissionsContainer: "permissionsConfig",
        prefix: "",
      });

      if (!payload) {
        return;
      }

      try {
        const response = await api.create(payload);
        toast?.success?.(response?.message || "规则创建成功");
        state.modals.create?.close();
        form.reset();
        permissionView?.reset?.("permissionsConfig");
        await onMutated?.("created");
      } catch (error) {
        handleRequestError?.(error, "创建规则失败", "create_rule");
      }
    }

    /**
     * 提交更新请求。
     *
     * @param {Event} [event] onConfirm 事件。
     * @returns {Promise<void>} 更新完成后 resolve。
     */
    async function submitUpdate(event) {
      event?.preventDefault?.();
      const form = document.getElementById("editRuleForm");
      if (!form) {
        return;
      }

      const payload = collectRulePayload(form, {
        idField: "#editRuleId",
        classification: "#editRuleClassification",
        name: "#editRuleName",
        dbType: "#editRuleDbTypeHidden",
        operator: "#editRuleOperator",
        permissionsContainer: "editPermissionsConfig",
        prefix: "edit",
      });

      if (!payload) {
        return;
      }

      const ruleId = form.querySelector("#editRuleId")?.value;

      try {
        const response = await api.update(ruleId, payload);
        toast?.success?.(response?.message || "规则更新成功");
        state.modals.edit?.close();
        await onMutated?.("updated");
      } catch (error) {
        handleRequestError?.(error, "更新规则失败", "update_rule");
      }
    }

    /**
     * 从表单控件收集规则配置。
     *
     * @param {HTMLFormElement} form 表单元素。
     * @param {Object} options 字段选择器合集。
     * @returns {Object|null} 标准化 payload。
     */
    function collectRulePayload(form, options) {
      if (!permissionView) {
        toast?.error?.("权限配置模块未加载");
        return null;
      }

      const classificationId = form.querySelector(options.classification)?.value;
      const ruleName = form.querySelector(options.name)?.value;
      const dbType = form.querySelector(options.dbType)?.value;
      const operator = form.querySelector(options.operator)?.value || "OR";

      const selected = permissionView.collectSelected?.(
        dbType,
        options.permissionsContainer,
        options.prefix || "",
      );
      if (!permissionView.hasSelection?.(selected)) {
        toast?.warning?.("请至少选择一个权限");
        return null;
      }

      const ruleExpression = permissionView.buildExpression?.(dbType, selected, operator);

      return {
        classification_id: parseInt(classificationId, 10),
        rule_name: ruleName,
        db_type: dbType,
        operator,
        rule_expression: ruleExpression,
      };
    }

    /**
     * 删除规则后刷新数据。
     *
     * @param {number|string} id 规则 ID。
     * @returns {Promise<void>} 删除完成后 resolve。
     */
    async function deleteRule(id) {
      if (!confirm("确定要删除这个规则吗？")) {
        return;
      }
      try {
        const response = await api.remove(id);
        toast?.success?.(response?.message || "规则删除成功");
        await onMutated?.("deleted");
      } catch (error) {
        handleRequestError?.(error, "删除规则失败", "delete_rule");
      }
    }

    /**
     * 重置创建表单并清理权限配置。
     *
     * @param {HTMLFormElement} [formElement] 可选外部表单。
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
      const form = resolveFormArg(formElement, "createRuleForm");
      if (form) {
        form.reset();
      }
      permissionView?.reset?.("permissionsConfig");
    }

    /**
     * 重置编辑表单状态。
     *
     * @param {HTMLFormElement} [formElement] 可选外部表单。
     * @returns {void}
     */
    function resetEditForm(formElement) {
      const form = resolveFormArg(formElement, "editRuleForm");
      if (form) {
        form.reset();
        const hiddenDbType = form.querySelector("#editRuleDbTypeHidden");
        if (hiddenDbType) {
          hiddenDbType.value = "";
        }
      }
      permissionView?.reset?.("editPermissionsConfig", "edit");
    }

    /**
     * 重置查看模态数据字段。
     *
     * @param {Document} [doc=document] 自定义文档对象。
     * @returns {void}
     */
    function resolveDocumentArg(doc) {
      if (!doc) {
        return document;
      }
      if (doc instanceof Document) {
        return doc;
      }
      if (doc?.document instanceof Document) {
        return doc.document;
      }
      if (doc?.event instanceof Event) {
        return doc.event.target?.ownerDocument || document;
      }
      return document;
    }

    function resetViewModal(doc) {
      const targetDoc = resolveDocumentArg(doc);
      const modal = targetDoc.getElementById("viewRuleModal");
      if (modal?.dataset) {
        delete modal.dataset.ruleId;
      }
      const fields = ["viewRuleOperator", "viewRuleClassification", "viewRuleDbType"];
      fields.forEach(id => {
        const node = targetDoc.getElementById(id);
        if (node) {
          node.textContent = "-";
        }
      });
      const permissionsContainer = targetDoc.getElementById("viewPermissionsConfig");
      if (permissionsContainer) {
        permissionsContainer.innerHTML = '<div class="rule-detail-empty">未加载权限配置</div>';
      }
      const permissionsMeta = targetDoc.getElementById("viewRulePermissionsMeta");
      if (permissionsMeta) {
        permissionsMeta.textContent = "未加载";
        permissionsMeta.className = "status-pill status-pill--muted";
      }
      const modalMeta = targetDoc.getElementById("viewRuleModalMeta");
      if (modalMeta) {
        modalMeta.textContent = "规则信息";
      }
    }

    /**
     * 初始化创建/编辑规则的表单校验。
     *
     * @param {Object} [options={}] 自定义校验配置。
     * @param {string} [options.createFormSelector="#createRuleForm"] 新建表单。
     * @returns {void}
     */
    function initFormValidators(options = {}) {
      const { createFormSelector = "#createRuleForm" } = options;
      const validatorFactory = FormValidator || global.FormValidator;
      const rules = ValidationRules || global.ValidationRules;

      if (!validatorFactory || !rules) {
        console.error("rule-modals: 表单校验模块未正确加载");
        return;
      }

      const ruleForm = document.querySelector(createFormSelector);
      if (ruleForm) {
        state.validators.create = validatorFactory.create(createFormSelector);
        if (state.validators.create) {
          state.validators.create
            .useRules("#ruleClassification", rules.classificationRule.classification)
            .useRules("#ruleName", rules.classificationRule.name)
            .useRules("#ruleDbType", rules.classificationRule.dbType)
            .useRules("#ruleOperator", rules.classificationRule.operator)
            .onSuccess(event => submitCreate(resolveFormElement(event?.target, createFormSelector)))
            .onFail(() => toast?.error?.("请检查规则信息填写"));
        }
      }
    }

    function resolveFormElement(source, selector) {
      if (source instanceof HTMLFormElement) {
        return source;
      }
      if (source && source.form) {
        return source.form;
      }
      const fallback = document.querySelector(selector || '#createRuleForm');
      return fallback instanceof HTMLFormElement ? fallback : null;
    }

    /**
     * 根据前缀加载权限配置。
     *
     * @param {"create"|"edit"|string} [prefix=""] 权限面板前缀。
     * @returns {Promise<void>} 完成后 resolve。
     */
    function loadPermissions(prefix = "") {
      return permissionView?.loadByPrefix
        ? permissionView.loadByPrefix(prefix)
        : Promise.resolve();
    }

    /**
     * 输出调试日志。
     *
     * @param {string} message 日志文本。
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
      openViewById,
      deleteRule,
      triggerCreate,
      submitUpdate,
      loadPermissions,
      resetCreateForm,
      resetEditForm,
      resetViewModal,
      updateClassificationOptions: syncClassificationOptions,
    };
  }

  global.AccountClassificationRuleModals = {
    createController,
  };
})(window);
