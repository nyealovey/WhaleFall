(function (global) {
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

  const CredentialsService = global.CredentialsService;
  let credentialsService = null;
  try {
    if (CredentialsService) {
      credentialsService = new CredentialsService(global.httpU);
    } else {
      throw new Error('CredentialsService 未加载');
    }
  } catch (error) {
    console.error('初始化 CredentialsService 失败:', error);
  }

  const CREDENTIAL_FILTER_FORM_ID = "credential-filter-form";
  const AUTO_APPLY_FILTER_CHANGE = true;

  let deleteCredentialId = null;
  let credentialFilterEventHandler = null;
  let confirmDeleteButton = null;

  ready(initializeCredentialsListPage);

  function initializeCredentialsListPage() {
    initializeDeleteConfirmation();
    registerCredentialFilterForm();
    subscribeCredentialFilters();
    initializeRealTimeSearch();
  }

  function initializeDeleteConfirmation() {
    confirmDeleteButton = selectOne("#confirmDelete");
    if (!confirmDeleteButton.length) {
      return;
    }
    confirmDeleteButton.on("click", handleDeleteConfirmation);
  }

  function handleDeleteConfirmation(event) {
    event.preventDefault();
    if (!deleteCredentialId) {
      return;
    }
    showLoadingState(confirmDeleteButton, "删除中...");
    if (!credentialsService) {
      console.error('CredentialsService 未初始化');
      hideLoadingState(confirmDeleteButton, "确认删除");
      return;
    }
    credentialsService
      .deleteCredential(deleteCredentialId)
      .then((data) => {
        if (data.message) {
          global.toast.success(data.message);
          global.setTimeout(() => global.location.reload(), 1000);
        } else if (data.error) {
          global.toast.error(data.error);
        }
      })
      .catch((error) => {
        console.error("删除凭据失败:", error);
        global.toast.error("删除失败，请稍后重试");
      })
      .finally(() => {
        hideLoadingState(confirmDeleteButton, "确认删除");
      });
  }

  function deleteCredential(credentialId, credentialName) {
    deleteCredentialId = credentialId;
    const credentialNameElement = selectOne("#deleteCredentialName");
    if (credentialNameElement.length) {
      credentialNameElement.text(credentialName || "");
    }
    const modalElement = selectOne("#deleteModal").first();
    if (modalElement && global.bootstrap?.Modal) {
      const instance = global.bootstrap.Modal.getOrCreateInstance(modalElement);
      instance.show();
    }
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

  function registerCredentialFilterForm() {
    if (!global.FilterUtils) {
      console.warn("FilterUtils 未加载，跳过凭据筛选初始化");
      return;
    }
    const selector = `#${CREDENTIAL_FILTER_FORM_ID}`;
    const form = selectOne(selector);
    if (!form.length) {
      return;
    }
    global.FilterUtils.registerFilterForm(selector, {
      onSubmit: ({ form, event }) => {
        event?.preventDefault?.();
        applyCredentialFilters(form);
      },
      onClear: ({ form, event }) => {
        event?.preventDefault?.();
        resetCredentialFilters(form);
      },
      autoSubmitOnChange: true,
    });
  }

  function subscribeCredentialFilters() {
    if (!global.EventBus) {
      return;
    }
    const formElement = selectOne(`#${CREDENTIAL_FILTER_FORM_ID}`).first();
    if (!formElement) {
      return;
    }

    const handler = (detail) => {
      if (!detail) {
        return;
      }
      const incoming = (detail.formId || "").replace(/^#/, "");
      if (incoming !== CREDENTIAL_FILTER_FORM_ID) {
        return;
      }
      switch (detail.action) {
        case "clear":
          resetCredentialFilters(formElement);
          break;
        case "change":
          if (AUTO_APPLY_FILTER_CHANGE) {
            applyCredentialFilters(formElement, detail.values);
          }
          break;
        case "submit":
          applyCredentialFilters(formElement, detail.values);
          break;
        default:
          break;
      }
    };

    ["change", "submit", "clear"].forEach((action) => {
      global.EventBus.on(`filters:${action}`, handler);
    });
    credentialFilterEventHandler = handler;

    const unloadHandler = () => {
      cleanupCredentialFilters();
      from(global).off("beforeunload", unloadHandler);
    };
    from(global).on("beforeunload", unloadHandler);
  }

  function cleanupCredentialFilters() {
    if (!global.EventBus || !credentialFilterEventHandler) {
      return;
    }
    ["change", "submit", "clear"].forEach((action) => {
      global.EventBus.off(`filters:${action}`, credentialFilterEventHandler);
    });
    credentialFilterEventHandler = null;
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
    if (!form) {
      return {};
    }
    if (global.FilterUtils && typeof global.FilterUtils.serializeForm === "function") {
      return global.FilterUtils.serializeForm(form);
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

  global.deleteCredential = deleteCredential;
  global.exportCredentials = exportCredentials;
  global.sortTable = sortTable;
  global.filterTable = filterTable;
})(window);
