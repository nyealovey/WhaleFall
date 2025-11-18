function mountCredentialsListPage(global) {
  "use strict";

  const helpers = global.DOMHelpers;
  if (!helpers) {
    console.error("DOMHelpers 未初始化，无法加载凭据列表脚本");
    return;
  }

  const LodashUtils = global.LodashUtils;
  if (!LodashUtils) {
    throw new Error("LodashUtils 未初始化");
  }

  const { ready, select, selectOne, from } = helpers;
  const credentialModals = global.CredentialModals?.createController
    ? global.CredentialModals.createController({
        http: global.httpU,
        FormValidator: global.FormValidator,
        ValidationRules: global.ValidationRules,
        toast: global.toast,
        DOMHelpers: global.DOMHelpers,
      })
    : null;

  const CredentialsService = global.CredentialsService;
  const createCredentialsStore = global.createCredentialsStore;
  let credentialsService = null;
  let credentialsStore = null;
  try {
    if (!CredentialsService) {
      throw new Error('CredentialsService 未加载');
    }
    credentialsService = new CredentialsService(global.httpU);
    if (typeof createCredentialsStore === 'function') {
      credentialsStore = createCredentialsStore({
        service: credentialsService,
        emitter: global.mitt ? global.mitt() : null,
      });
    } else {
      throw new Error('createCredentialsStore 未加载');
    }
  } catch (error) {
    console.error('初始化 CredentialsService/CredentialsStore 失败:', error);
  }

  const CREDENTIAL_FILTER_FORM_ID = "credential-filter-form";
  const AUTO_APPLY_FILTER_CHANGE = true;

  let deleteCredentialId = null;
  let deleteModal = null;
  let confirmDeleteButton = null;
  let credentialFilterCard = null;
  let filterUnloadHandler = null;

  ready(initializeCredentialsListPage);

  /**
   * 页面入口：初始化模态、删除确认、筛选、实时搜索。
   */
  function initializeCredentialsListPage() {
    bindModalTriggers();
    initializeDeleteConfirmation();
    initializeCredentialFilterCard();
    initializeRealTimeSearch();
    bindCredentialsStoreEvents();
  }

  /**
   * 初始化新建/编辑凭据模态触发器。
   */
  function bindModalTriggers() {
    if (!credentialModals) {
      console.warn('CredentialModals 未加载，创建/编辑模态不可用');
      return;
    }
    const createBtn = document.querySelector('[data-action="create-credential"]');
    if (createBtn) {
      createBtn.addEventListener('click', (event) => {
        event.preventDefault();
        credentialModals.openCreate();
      });
    }
    select('[data-action="edit-credential"]').each((button) => {
      const wrapper = from(button);
      wrapper.on('click', (event) => {
        event.preventDefault();
        const row = button.closest('tr');
        const credentialId = row?.getAttribute('data-credential-id') || wrapper.attr('data-credential-id');
        if (credentialId) {
          credentialModals.openEdit(credentialId);
        }
      });
    });
    credentialModals.init?.();
  }

  function initializeDeleteConfirmation() {
    const factory = global.UI?.createModal;
    if (!factory) {
      console.error('UI.createModal 未加载，删除模态无法初始化');
      return;
    }
    deleteModal = factory({
      modalSelector: "#deleteModal",
      confirmSelector: "#confirmDelete",
      onConfirm: handleDeleteConfirmation,
      onClose: () => {
        deleteCredentialId = null;
      },
    });
    confirmDeleteButton = selectOne("#confirmDelete");
  }

  function handleDeleteConfirmation(event) {
    event?.preventDefault?.();
    if (!deleteCredentialId) {
      return;
    }
    if (!credentialsStore) {
      console.error('CredentialsStore 未初始化');
      return;
    }
    showLoadingState(confirmDeleteButton, "删除中...");
    credentialsStore.actions.deleteCredential(deleteCredentialId)
      .catch((error) => {
        console.error("删除凭据失败:", error);
        global.toast.error(error?.message || "删除失败，请稍后重试");
      })
      .finally(() => {
        hideLoadingState(confirmDeleteButton, "确认删除");
        deleteModal?.close?.();
      });
  }

  function deleteCredential(credentialId, credentialName) {
    if (!credentialId) {
      return;
    }
    deleteCredentialId = credentialId;
    const credentialNameElement = selectOne("#deleteCredentialName");
    if (credentialNameElement.length) {
      credentialNameElement.text(credentialName || "");
    }
    deleteModal?.open();
  }

  function showLoadingState(target, text) {
    const element = from(target);
    if (!element.length) {
      return;
    }
    element.attr("data-original-text", element.html());
    element.html(`<i class="fas fa-spinner fa-spin me-2"></i>${text}`);
    element.attr("disabled", "disabled");
  }

  function hideLoadingState(target, fallbackText) {
    const element = from(target);
    if (!element.length) {
      return;
    }
    const original = element.attr("data-original-text");
    element.html(original || fallbackText || "");
    element.attr("disabled", null);
    element.attr("data-original-text", null);
  }

  function exportCredentials(format = "csv") {
    const formElement = selectOne(`#${CREDENTIAL_FILTER_FORM_ID}`).first();
    const filters = resolveCredentialFilters(formElement);
    const params = buildCredentialQueryParams({ ...filters, export: format });
    const url = `${global.location.pathname}?${params.toString()}`;
    global.open(url, "_blank", "noopener");
  }

  function sortTable(column, direction = "asc") {
    const table = selectOne(".credentials-table .table");
    if (!table.length) {
      return;
    }
    const tbody = table.find("tbody").first();
    if (!tbody) {
      return;
    }
    const rows = from(tbody).find("tr").nodes;
    if (!rows.length) {
      return;
    }

    const normalizedDirection = direction === "desc" ? "desc" : "asc";
    const sortedRows = LodashUtils.orderBy(
      rows,
      [
        (row) => {
          const cell = from(row).find(`td:nth-child(${column})`).text();
          return normalizeText(cell);
        },
      ],
      [normalizedDirection],
    );

    sortedRows.forEach((row) => tbody.appendChild(row));
  }

  function filterTable(filterValue) {
    const table = selectOne(".credentials-table .table");
    if (!table.length) {
      return;
    }
    const rows = table.find("tbody tr");
    const normalizedFilter = normalizeText(filterValue || "");
    rows.each((row) => {
      const text = normalizeText(row.textContent || "");
      row.style.display = !normalizedFilter || text.includes(normalizedFilter) ? "" : "none";
    });
  }

  function initializeRealTimeSearch() {
    const searchInput = selectOne('input[name="search"]');
    if (!searchInput.length) {
      return;
    }

    const debouncedFilter = LodashUtils.debounce(
      (value) => {
        filterTable(value ? value.trim() : "");
      },
      300,
      { leading: false, trailing: true },
    );

    const handleInput = (event) => {
      debouncedFilter(event.target.value || "");
    };

    const handleBlur = () => {
      if (typeof debouncedFilter.flush === "function") {
        debouncedFilter.flush();
      }
    };

    const cleanup = () => {
      if (typeof debouncedFilter.cancel === "function") {
        debouncedFilter.cancel();
      }
      searchInput.off("input", handleInput);
      searchInput.off("blur", handleBlur);
      from(global).off("beforeunload", cleanup);
    };

    searchInput.on("input", handleInput);
    searchInput.on("blur", handleBlur);
    from(global).on("beforeunload", cleanup);
  }

  function initializeCredentialFilterCard() {
    const factory = global.UI?.createFilterCard;
    if (!factory) {
      console.error("UI.createFilterCard 未加载，凭据筛选无法初始化");
      return;
    }
    credentialFilterCard = factory({
      formSelector: `#${CREDENTIAL_FILTER_FORM_ID}`,
      autoSubmitOnChange: AUTO_APPLY_FILTER_CHANGE,
      onSubmit: ({ values }) => applyCredentialFilters(null, values),
      onClear: () => applyCredentialFilters(null, {}),
      onChange: ({ values }) => {
        if (AUTO_APPLY_FILTER_CHANGE) {
          applyCredentialFilters(null, values);
        }
      },
    });

    if (filterUnloadHandler) {
      from(global).off("beforeunload", filterUnloadHandler);
    }
    filterUnloadHandler = () => {
      destroyCredentialFilterCard();
      from(global).off("beforeunload", filterUnloadHandler);
      filterUnloadHandler = null;
    };
    from(global).on("beforeunload", filterUnloadHandler);
  }

  function destroyCredentialFilterCard() {
    if (credentialFilterCard?.destroy) {
      credentialFilterCard.destroy();
    }
    credentialFilterCard = null;
  }

  function applyCredentialFilters(form, values) {
    const targetForm = resolveFormElement(form);
    if (!targetForm) {
      return;
    }

    const filters = resolveCredentialFilters(targetForm, values);
    const searchTerm = filters.search || "";
    if (typeof searchTerm === "string" && searchTerm.trim().length > 0 && searchTerm.trim().length < 2) {
      global.toast.warning("搜索关键词至少需要2个字符");
      return;
    }

    const params = buildCredentialQueryParams(filters);
    const action = targetForm.getAttribute("action") || global.location.pathname;
    const query = params.toString();
    global.location.href = query ? `${action}?${query}` : action;
  }

  function resolveCredentialFilters(form, overrideValues) {
    const rawValues =
      overrideValues && Object.keys(overrideValues || {}).length ? overrideValues : collectFormValues(form);
    return Object.entries(rawValues || {}).reduce((result, [key, value]) => {
      if (key === "csrf_token") {
        return result;
      }
      const normalized = sanitizeFilterValue(value);
      if (normalized === null || normalized === undefined) {
        return result;
      }
      if (Array.isArray(normalized) && normalized.length === 0) {
        return result;
      }
      result[key] = normalized;
      return result;
    }, {});
  }

  function sanitizeFilterValue(value) {
    if (Array.isArray(value)) {
      return LodashUtils.compact(value.map((item) => sanitizePrimitiveValue(item)));
    }
    return sanitizePrimitiveValue(value);
  }

  function sanitizePrimitiveValue(value) {
    if (value instanceof File) {
      return value.name;
    }
    if (typeof value === "string") {
      const trimmed = value.trim();
      return trimmed === "" ? null : trimmed;
    }
    if (value === undefined || value === null) {
      return null;
    }
    return value;
  }

  function buildCredentialQueryParams(filters) {
    const params = new URLSearchParams();
    Object.entries(filters || {}).forEach(([key, value]) => {
      if (Array.isArray(value)) {
        value.forEach((item) => params.append(key, item));
      } else {
        params.append(key, value);
      }
    });
    return params;
  }

  function resetCredentialFilters(form) {
    const targetForm = resolveFormElement(form);
    if (targetForm) {
      targetForm.reset();
    }
    applyCredentialFilters(targetForm, {});
  }

  function resolveFormElement(form) {
    if (!form && credentialFilterCard?.form) {
      return credentialFilterCard.form;
    }
    if (!form) {
      return selectOne(`#${CREDENTIAL_FILTER_FORM_ID}`).first();
    }
    if (form instanceof Element) {
      return form;
    }
    if (form && typeof form.current === "function") {
      return form.current();
    }
    if (form && typeof form.first === "function") {
      return form.first();
    }
    return form;
  }

  function collectFormValues(form) {
    if (credentialFilterCard?.serialize) {
      return credentialFilterCard.serialize();
    }
    const serializer = global.UI?.serializeForm;
    if (serializer) {
      return serializer(form);
    }
    if (!form) {
      return {};
    }
    const formData = new FormData(form);
    const result = {};
    formData.forEach((value, key) => {
      const normalized = value instanceof File ? value.name : value;
      if (result[key] === undefined) {
        result[key] = normalized;
      } else if (Array.isArray(result[key])) {
        result[key].push(normalized);
      } else {
        result[key] = [result[key], normalized];
      }
    });
    return result;
  }

  function normalizeText(value) {
    const text = (value || "").toString().trim();
    if (typeof LodashUtils.toLower === "function") {
      return LodashUtils.toLower(text);
    }
    return text.toLowerCase();
  }

  function bindCredentialsStoreEvents() {
    if (!credentialsStore) {
      return;
    }
    credentialsStore.subscribe("credentials:deleted", ({ credentialId, response }) => {
      removeCredentialRow(credentialId);
      closeDeleteModal();
      deleteCredentialId = null;
      const message = response?.message || "凭据已删除";
      global.toast.success(message);
    });
    credentialsStore.subscribe("credentials:error", (payload) => {
      const message = payload?.error?.message || "凭据操作失败";
      global.toast.error(message);
    });
  }

  function removeCredentialRow(credentialId) {
    if (!credentialId && credentialId !== 0) {
      return;
    }
    const row = document.querySelector(`[data-credential-id="${credentialId}"]`);
    if (row && row.parentNode) {
      row.parentNode.removeChild(row);
    }
  }

  function closeDeleteModal() {
    deleteModal?.close?.();
  }

  global.deleteCredential = deleteCredential;
  global.exportCredentials = exportCredentials;
  global.sortTable = sortTable;
  global.filterTable = filterTable;
}

window.CredentialsListPage = {
  mount: function () {
    mountCredentialsListPage(window);
  },
};
