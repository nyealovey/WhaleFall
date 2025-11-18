(function (global) {
  "use strict";

  /**
   * 规则模态控制器，负责新建/编辑/查看。
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

    /**
     * 初始化所有模态与验证器。
     */
    function init() {
      if (!UI?.createModal) {
        throw new Error("rule-modals: UI.createModal 未加载");
      }
      debug("初始化规则模态控制器");
      state.modals.create = UI.createModal({
        modalSelector: "#createRuleModal",
        onConfirm: () => triggerCreate(),
        onClose: resetCreateForm,
        size: "lg",
      });
      state.modals.edit = UI.createModal({
        modalSelector: "#editRuleModal",
        onConfirm: () => submitUpdate(),
        onClose: resetEditForm,
        size: "lg",
      });
      state.modals.view = UI.createModal({
        modalSelector: "#viewRuleModal",
        onClose: resetViewModal,
        size: "lg",
      });
      initFormValidators();
      syncClassificationOptions();
    }

    /**
     * 同步分类下拉选项，来自外部 state 或内部缓存。
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
     */
    function populateClassificationSelect(elementId, classifications) {
      const select = document.getElementById(elementId);
      if (!select) {
        return;
      }
      select.innerHTML = '<option value="">请选择分类</option>';
      (classifications || []).forEach(classification => {
        const option = document.createElement("option");
        option.value = classification.id;
        option.textContent = classification.name;
        select.appendChild(option);
      });
    }

    /**
     * 打开新建模态。
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

        document.getElementById("viewRuleName").textContent = rule.rule_name || "-";
        document.getElementById("viewRuleClassification").textContent = rule.classification_name || "未分类";
        document.getElementById("viewRuleDbType").textContent = (rule.db_type || "").toUpperCase();

        const operator =
          rule.rule_expression?.operator === "AND"
            ? "AND (所有条件都必须满足)"
            : "OR (任一条件满足即可)";
        document.getElementById("viewRuleOperator").textContent = operator;

        document.getElementById("viewRuleStatus").innerHTML = rule.is_active
          ? '<span class="badge bg-success">启用</span>'
          : '<span class="badge bg-secondary">禁用</span>';

        if (global.timeUtils && typeof global.timeUtils.formatDateTime === "function") {
          document.getElementById("viewRuleCreatedAt").textContent = rule.created_at
            ? global.timeUtils.formatDateTime(rule.created_at)
            : "-";
          document.getElementById("viewRuleUpdatedAt").textContent = rule.updated_at
            ? global.timeUtils.formatDateTime(rule.updated_at)
            : "-";
        }

        const permissionsContainer = document.getElementById("viewPermissionsConfig");
        if (permissionsContainer) {
          permissionsContainer.innerHTML =
            permissionView?.renderDisplay?.(rule.db_type, rule.rule_expression) ||
            '<div class="text-center text-muted">未加载权限配置</div>';
        }

        state.modals.view?.open();
      } catch (error) {
        handleRequestError?.(error, "获取规则信息失败", "view_rule");
      }
    }

    function triggerCreate() {
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

    async function submitCreate(form) {
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

    async function submitUpdate() {
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
        rule_expression: ruleExpression,
      };
    }

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

    function resetCreateForm() {
      const form = document.getElementById("createRuleForm");
      if (form) {
        form.reset();
      }
      permissionView?.reset?.("permissionsConfig");
    }

    function resetEditForm() {
      const form = document.getElementById("editRuleForm");
      if (form) {
        form.reset();
        const hiddenDbType = form.querySelector("#editRuleDbTypeHidden");
        if (hiddenDbType) {
          hiddenDbType.value = "";
        }
      }
      permissionView?.reset?.("editPermissionsConfig", "edit");
    }

    function resetViewModal() {
      const modal = document.getElementById("viewRuleModal");
      if (modal?.dataset) {
        delete modal.dataset.ruleId;
      }
      const fields = [
        "viewRuleName",
        "viewRuleClassification",
        "viewRuleDbType",
        "viewRuleOperator",
        "viewRuleCreatedAt",
        "viewRuleUpdatedAt",
      ];
      fields.forEach(id => {
        const node = document.getElementById(id);
        if (node) {
          node.textContent = "-";
        }
      });
      const status = document.getElementById("viewRuleStatus");
      if (status) {
        status.innerHTML = "-";
      }
      const permissionsContainer = document.getElementById("viewPermissionsConfig");
      if (permissionsContainer) {
        permissionsContainer.innerHTML = '<div class="text-center text-muted">未加载权限配置</div>';
      }
    }

    function initFormValidators() {
      const validatorFactory = FormValidator || global.FormValidator;
      const rules = ValidationRules || global.ValidationRules;

      if (!validatorFactory || !rules) {
        console.error("rule-modals: 表单校验模块未正确加载");
        return;
      }

      const ruleForm = document.getElementById("createRuleForm");
      if (ruleForm) {
        state.validators.create = validatorFactory.create("#createRuleForm");
        if (state.validators.create) {
          state.validators.create
            .useRules("#ruleClassification", rules.classificationRule.classification)
            .useRules("#ruleName", rules.classificationRule.name)
            .useRules("#ruleDbType", rules.classificationRule.dbType)
            .useRules("#ruleOperator", rules.classificationRule.operator)
            .onSuccess(event => submitCreate(event.target))
            .onFail(() => toast?.error?.("请检查规则信息填写"));
        }
      }
    }

    function loadPermissions(prefix = "") {
      return permissionView?.loadByPrefix
        ? permissionView.loadByPrefix(prefix)
        : Promise.resolve();
    }

    /**
     * 独立页面表单挂载
     * @param {{form?: HTMLFormElement, mode?: 'create'|'edit', redirectUrl?: string}} opts
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
