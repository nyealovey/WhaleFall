(function (global) {
  "use strict";

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
    if (!UI?.createModal) {
      throw new Error("classification-modals: UI.createModal 未加载");
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

    function init() {
      debug("初始化分类模态控制器");
      modals.create = UI.createModal({
        modalSelector: "#createClassificationModal",
        onConfirm: () => triggerCreate(),
        onClose: resetCreateForm,
      });
      modals.edit = UI.createModal({
        modalSelector: "#editClassificationModal",
        onConfirm: () => triggerUpdate(),
        onClose: resetEditForm,
      });
      setupColorPreviewListeners();
      initFormValidators();
    }

    function openCreate(event) {
      event?.preventDefault?.();
      resetCreateForm();
      modals.create?.open();
    }

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

    function triggerCreate() {
      if (validators.create?.revalidate) {
        validators.create.revalidate();
        return;
      }
      if (validators.create?.instance?.revalidate) {
        validators.create.instance.revalidate();
        return;
      }
      const form = document.getElementById("createClassificationForm");
      if (form) {
        submitCreate(form);
      }
    }

    function triggerUpdate() {
      if (validators.edit?.revalidate) {
        validators.edit.revalidate();
        return;
      }
      if (validators.edit?.instance?.revalidate) {
        validators.edit.instance.revalidate();
        return;
      }
      const form = document.getElementById("editClassificationForm");
      if (form) {
        submitUpdate(form);
      }
    }

    async function submitCreate(form) {
      const payload = collectPayload(form, {
        name: "#classificationName",
        description: "#classificationDescription",
        riskLevel: "#riskLevel",
        color: "#classificationColor",
        priority: "#priority",
        iconSelector: 'input[name="classificationIcon"]:checked',
      });

      if (!payload) {
        toast?.error?.("请填写完整的分类信息");
        return;
      }

      try {
        const response = await api.create(payload);
        toast?.success?.(response?.message || "分类创建成功");
        modals.create?.close();
        form.reset();
        resetColorPreview("colorPreview");
        refreshValidator(validators.create);
        await onMutated?.("created");
      } catch (error) {
        handleRequestError?.(error, "创建分类失败", "create_classification");
      }
    }

    async function submitUpdate(form) {
      const payload = collectPayload(form, {
        name: "#editClassificationName",
        description: "#editClassificationDescription",
        riskLevel: "#editClassificationRiskLevel",
        color: "#editClassificationColor",
        priority: "#editClassificationPriority",
        iconSelector: 'input[name="editClassificationIcon"]:checked',
      });
      const id = form.querySelector("#editClassificationId")?.value;

      if (!payload || !id) {
        toast?.error?.("请填写完整的分类信息");
        return;
      }

      try {
        const response = await api.update(id, payload);
        toast?.success?.(response?.message || "分类更新成功");
        modals.edit?.close();
        resetColorPreview("editColorPreview");
        refreshValidator(validators.edit);
        await onMutated?.("updated");
      } catch (error) {
        handleRequestError?.(error, "更新分类失败", "update_classification");
      }
    }

    function collectPayload(form, selectors) {
      const nameInput = form.querySelector(selectors.name);
      const colorSelect = form.querySelector(selectors.color);
      const priorityInput = form.querySelector(selectors.priority);
      const descriptionInput = form.querySelector(selectors.description);
      const riskLevelSelect = form.querySelector(selectors.riskLevel);
      const iconRadio = form.querySelector(selectors.iconSelector);

      const payload = {
        name: nameInput ? nameInput.value.trim() : "",
        description: descriptionInput ? descriptionInput.value.trim() : "",
        risk_level: riskLevelSelect ? riskLevelSelect.value : "medium",
        color_key: colorSelect ? colorSelect.value : "",
        priority: parsePriority(priorityInput?.value),
        icon_name: iconRadio ? iconRadio.value : "fa-tag",
      };

      if (!payload.name || !payload.color_key) {
        toast?.error?.("请填写完整的分类信息");
        return null;
      }

      return payload;
    }

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

    function fillEditForm(classification) {
      document.getElementById("editClassificationId").value = classification.id;
      document.getElementById("editClassificationName").value = classification.name || "";
      document.getElementById("editClassificationDescription").value = classification.description || "";
      document.getElementById("editClassificationRiskLevel").value = classification.risk_level || "medium";
      document.getElementById("editClassificationColor").value = classification.color_key || classification.color || "";
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

      updateColorPreview("editColorPreview", document.getElementById("editClassificationColor"));
    }

    function setupColorPreviewListeners() {
      const createColorSelect = document.getElementById("classificationColor");
      if (createColorSelect) {
        createColorSelect.addEventListener("change", function () {
          updateColorPreview("colorPreview", this);
        });
      }
      const editColorSelect = document.getElementById("editClassificationColor");
      if (editColorSelect) {
        editColorSelect.addEventListener("change", function () {
          updateColorPreview("editColorPreview", this);
        });
      }
    }

    function updateColorPreview(previewId, selectElement) {
      const preview = document.getElementById(previewId);
      if (!preview || !selectElement) {
        return;
      }
      const selectedOption = selectElement.options[selectElement.selectedIndex];
      const colorValue = selectedOption?.dataset?.color;
      const colorText = selectedOption?.text;

      if (colorValue && selectElement.value) {
        const dot = preview.querySelector(".color-preview-dot");
        const text = preview.querySelector(".color-preview-text");
        if (dot && text) {
          dot.style.backgroundColor = colorValue;
          text.textContent = colorText;
          preview.style.display = "flex";
        }
      } else {
        preview.style.display = "none";
      }
    }

    function resetColorPreview(previewId) {
      const preview = document.getElementById(previewId);
      if (preview) {
        preview.style.display = "none";
      }
    }

    function initFormValidators() {
      const validatorFactory = FormValidator || global.FormValidator;
      const rules = ValidationRules || global.ValidationRules;

      if (!validatorFactory || !rules) {
        console.error("classification-modals: 表单校验模块未正确加载");
        return;
      }

      const createForm = document.getElementById("createClassificationForm");
      if (createForm) {
        validators.create = validatorFactory.create("#createClassificationForm");
        if (validators.create) {
          validators.create
            .useRules("#classificationName", rules.classification.name)
            .useRules("#classificationColor", rules.classification.color)
            .useRules("#priority", rules.classification.priority)
            .onSuccess(event => submitCreate(event.target))
            .onFail(() => toast?.error?.("请检查分类信息填写"));

          bindRevalidate(createForm, "#classificationName", validators.create);
          bindRevalidate(createForm, "#classificationColor", validators.create, "change");
          bindRevalidate(createForm, "#priority", validators.create, "input");
        }
      }

      const editForm = document.getElementById("editClassificationForm");
      if (editForm) {
        validators.edit = validatorFactory.create("#editClassificationForm");
        if (validators.edit) {
          validators.edit
            .useRules("#editClassificationName", rules.classification.name)
            .useRules("#editClassificationColor", rules.classification.color)
            .useRules("#editClassificationPriority", rules.classification.priority)
            .onSuccess(event => submitUpdate(event.target))
            .onFail(() => toast?.error?.("请检查分类信息填写"));

          bindRevalidate(editForm, "#editClassificationName", validators.edit);
          bindRevalidate(editForm, "#editClassificationColor", validators.edit, "change");
          bindRevalidate(editForm, "#editClassificationPriority", validators.edit, "input");
        }
      }
    }

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

    function resetCreateForm() {
      const form = document.getElementById("createClassificationForm");
      if (form) {
        form.reset();
      }
      resetColorPreview("colorPreview");
      refreshValidator(validators.create);
    }

    function resetEditForm() {
      const form = document.getElementById("editClassificationForm");
      if (form) {
        form.reset();
      }
      resetColorPreview("editColorPreview");
      refreshValidator(validators.edit);
    }

    function refreshValidator(validator) {
      if (validator?.instance?.refresh) {
        validator.instance.refresh();
      }
    }

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
