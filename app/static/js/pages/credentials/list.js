/**
 * 凭据列表页面脚本
 * 处理筛选、搜索、导出、批量操作等功能
 */

const CREDENTIAL_FILTER_FORM_ID = "credential-filter-form";
const AUTO_APPLY_FILTER_CHANGE = true;

let deleteCredentialId = null;
let credentialFilterEventHandler = null;

document.addEventListener("DOMContentLoaded", () => {
  initializeCredentialsListPage();
});

function initializeCredentialsListPage() {
  initializeDeleteConfirmation();
  registerCredentialFilterForm();
  subscribeCredentialFilters();
  initializeRealTimeSearch();
}

function initializeDeleteConfirmation() {
  const confirmDeleteBtn = document.getElementById("confirmDelete");
  if (confirmDeleteBtn) {
    confirmDeleteBtn.addEventListener("click", handleDeleteConfirmation);
  }
}

function handleDeleteConfirmation() {
  if (!deleteCredentialId) {
    return;
  }
  showLoadingState("confirmDelete", "删除中...");
  http
    .post(`/credentials/api/credentials/${deleteCredentialId}/delete`)
    .then((data) => {
      if (data.message) {
        toast.success(data.message);
        setTimeout(() => location.reload(), 1000);
      } else if (data.error) {
        toast.error(data.error);
      }
    })
    .catch((error) => {
      console.error("删除凭据失败:", error);
      toast.error("删除失败，请稍后重试");
    })
    .finally(() => {
      hideLoadingState("confirmDelete", "确认删除");
    });
}

function deleteCredential(credentialId, credentialName) {
  deleteCredentialId = credentialId;
  const deleteModal = document.getElementById("deleteModal");
  const credentialNameElement = document.getElementById("deleteCredentialName");
  if (credentialNameElement) {
    credentialNameElement.textContent = credentialName;
  }
  if (deleteModal) {
    new bootstrap.Modal(deleteModal).show();
  }
}

function showLoadingState(element, text) {
  const target = typeof element === "string" ? document.getElementById(element) : element;
  if (target) {
    target.innerHTML = `<i class="fas fa-spinner fa-spin me-2"></i>${text}`;
    target.disabled = true;
  }
}

function hideLoadingState(element, originalText) {
  const target = typeof element === "string" ? document.getElementById(element) : element;
  if (target) {
    target.innerHTML = originalText;
    target.disabled = false;
  }
}

function exportCredentials(format = "csv") {
  const searchParams = new URLSearchParams(window.location.search);
  searchParams.append("export", format);
  const url = `${window.location.pathname}?${searchParams.toString()}`;
  window.open(url, "_blank");
}

function sortTable(column, direction = "asc") {
  const table = document.querySelector(".credentials-table .table");
  if (!table) {
    return;
  }
  const tbody = table.querySelector("tbody");
  const rows = Array.from(tbody.querySelectorAll("tr"));
  rows.sort((a, b) => {
    const aValue = a.querySelector(`td:nth-child(${column})`).textContent.trim();
    const bValue = b.querySelector(`td:nth-child(${column})`).textContent.trim();
    return direction === "asc" ? aValue.localeCompare(bValue) : bValue.localeCompare(aValue);
  });
  rows.forEach((row) => tbody.appendChild(row));
}

function filterTable(filterValue) {
  const table = document.querySelector(".credentials-table .table");
  if (!table) {
    return;
  }
  const rows = table.querySelectorAll("tbody tr");
  rows.forEach((row) => {
    const text = row.textContent.toLowerCase();
    const shouldShow = text.includes(filterValue.toLowerCase());
    row.style.display = shouldShow ? "" : "none";
  });
}

function initializeRealTimeSearch() {
  const searchInput = document.querySelector('input[name="search"]');
  if (!searchInput) {
    return;
  }

  let searchTimeout;
  searchInput.addEventListener("input", function () {
    clearTimeout(searchTimeout);
    searchTimeout = setTimeout(() => {
      filterTable(this.value.trim());
    }, 300);
  });
}

function registerCredentialFilterForm() {
  if (!window.FilterUtils) {
    console.warn("FilterUtils 未加载，跳过凭据筛选初始化");
    return;
  }
  const selector = `#${CREDENTIAL_FILTER_FORM_ID}`;
  const form = document.querySelector(selector);
  if (!form) {
    return;
  }
  window.FilterUtils.registerFilterForm(selector, {
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
  if (!window.EventBus) {
    return;
  }
  const form = document.getElementById(CREDENTIAL_FILTER_FORM_ID);
  if (!form) {
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
        resetCredentialFilters(form);
        break;
      case "change":
        if (AUTO_APPLY_FILTER_CHANGE) {
          applyCredentialFilters(form, detail.values);
        }
        break;
      case "submit":
        applyCredentialFilters(form, detail.values);
        break;
      default:
        break;
    }
  };
  ["change", "submit", "clear"].forEach((action) => {
    EventBus.on(`filters:${action}`, handler);
  });
  credentialFilterEventHandler = handler;
  window.addEventListener("beforeunload", cleanupCredentialFilters, { once: true });
}

function cleanupCredentialFilters() {
  if (!window.EventBus || !credentialFilterEventHandler) {
    return;
  }
  ["change", "submit", "clear"].forEach((action) => {
    EventBus.off(`filters:${action}`, credentialFilterEventHandler);
  });
  credentialFilterEventHandler = null;
}

function applyCredentialFilters(form, values) {
  const targetForm = form || document.getElementById(CREDENTIAL_FILTER_FORM_ID);
  if (!targetForm) {
    return;
  }
  const data =
    values && Object.keys(values || {}).length ? values : collectFormValues(targetForm);
  const searchTerm = (data.search || "").trim();
  if (searchTerm && searchTerm.length < 2) {
    toast.warning("搜索关键词至少需要2个字符");
    return;
  }

  const params = new URLSearchParams();
  Object.entries(data || {}).forEach(([key, value]) => {
    if (key === "csrf_token") {
      return;
    }
    if (value === undefined || value === null) {
      return;
    }
    if (Array.isArray(value)) {
      value
        .filter((item) => item !== "" && item !== null)
        .forEach((item) => params.append(key, item));
    } else if (String(value).trim() !== "") {
      params.append(key, value);
    }
  });
  const action = targetForm.getAttribute("action") || window.location.pathname;
  const query = params.toString();
  window.location.href = query ? `${action}?${query}` : action;
}

function resetCredentialFilters(form) {
  const targetForm = form || document.getElementById(CREDENTIAL_FILTER_FORM_ID);
  if (targetForm) {
    targetForm.reset();
  }
  applyCredentialFilters(targetForm, {});
}

function collectFormValues(form) {
  if (!form) {
    return {};
  }
  if (window.FilterUtils && typeof window.FilterUtils.serializeForm === "function") {
    return window.FilterUtils.serializeForm(form);
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

window.deleteCredential = deleteCredential;
window.exportCredentials = exportCredentials;
window.sortTable = sortTable;
window.filterTable = filterTable;
