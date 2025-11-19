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
  const gridjs = global.gridjs;
  const gridHtml = gridjs?.html;
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
  let credentialsGrid = null;
  let canManageCredentials = false;

  ready(initializeCredentialsListPage);

  /**
   * 页面入口：初始化模态、删除确认、筛选、实时搜索。
   */
  function initializeCredentialsListPage() {
    initializeCredentialsGrid();
    bindModalTriggers();
    initializeDeleteConfirmation();
    initializeCredentialFilterCard();
    bindCredentialsStoreEvents();
  }

  function initializeCredentialsGrid() {
    const container = document.getElementById("credentials-grid");
    if (!container) {
      return;
    }
    if (!global.GridWrapper || !gridjs) {
      console.error("Grid.js 或 GridWrapper 未加载，无法初始化凭据表格");
      return;
    }
    canManageCredentials = container.dataset.canManage === "true";
    credentialsGrid = new global.GridWrapper(container, {
      sort: false,
      columns: [
        {
          name: "ID",
          id: "id",
          formatter: (cell) =>
            gridHtml
              ? gridHtml(`<span class="badge bg-secondary">#${cell}</span>`)
              : `#${cell}`,
        },
        {
          name: "名称",
          id: "name",
          formatter: (cell, row) => {
            const meta = row?.cells?.[8]?.data || {};
            const description = meta.description
              ? `<br><small class="text-muted">${escapeHtmlValue(meta.description)}</small>`
              : "";
            const displayName = escapeHtmlValue(cell || "-");
            return gridHtml ? gridHtml(`<div class="fw-semibold">${displayName}</div>${description}`) : displayName;
          },
        },
        {
          name: "类型",
          id: "credential_type",
          formatter: (cell, row) => {
            const meta = row?.cells?.[row.cells.length - 1]?.data || {};
            const credentialType = (cell || meta.credential_type || "-").toString().toUpperCase();
            const dbBadgeMeta = getDbBadgeMeta(meta.db_type);
            const credentialBadgeMap = {
              database: "bg-success",
              api: "bg-primary",
              ssh: "bg-warning",
            };
            const credentialClass =
              credentialBadgeMap[(cell || "").toString().toLowerCase()] || "bg-secondary";
            if (!gridHtml) {
              return `${credentialType} - ${dbBadgeMeta.label}`;
            }
            return gridHtml(`
              <div class="credential-type-cell">
                <span class="badge ${credentialClass}">${escapeHtmlValue(credentialType)}</span>
                <span class="credential-db-badge ${dbBadgeMeta.className}">
                  <i class="${dbBadgeMeta.icon} me-1"></i>${dbBadgeMeta.label}
                </span>
              </div>
            `);
          },
        },
        { name: "用户名", id: "username" },
        {
          name: "绑定实例",
          id: "instance_count",
          formatter: (cell) => {
            const count = Number(cell) || 0;
            const suffix = count === 1 ? "个实例" : "个实例";
            if (!gridHtml) {
              return `${count} ${suffix}`;
            }
            return gridHtml(
              `<span class="badge bg-info instance-count-badge"><i class="fas fa-database me-1"></i>${count} ${suffix}</span>`,
            );
          },
        },
        {
          name: "状态",
          id: "is_active",
          formatter: (cell) => {
            const isActive = Boolean(cell);
            if (!gridHtml) {
              return isActive ? "启用" : "禁用";
            }
            const color = isActive ? "success" : "secondary";
            const text = isActive ? "启用" : "禁用";
            return gridHtml(`<span class="badge bg-${color}">${text}</span>`);
          },
        },
        {
          name: "创建时间",
          id: "created_at",
          formatter: (cell, row) => {
            const meta = row?.cells?.[row.cells.length - 1]?.data || {};
            return meta.created_at_display || cell || "-";
          },
        },
        {
          name: "操作",
          sort: false,
          formatter: (cell, row) => {
            const credentialId = row?.cells?.[0]?.data;
            const meta = row?.cells?.[8]?.data || {};
            if (!canManageCredentials) {
              return gridHtml ? gridHtml('<span class="text-muted small">只读</span>') : "";
            }
            const credentialNameLiteral = JSON.stringify(meta.name || "");
            return gridHtml
              ? gridHtml(`
                <div class="btn-group btn-group-sm" role="group">
                  <button type="button" class="btn btn-outline-warning" onclick="openCredentialEditor(${credentialId})" title="编辑">
                    <i class="fas fa-edit"></i>
                  </button>
                  <button type="button" class="btn btn-outline-danger" onclick="deleteCredential(${credentialId}, ${credentialNameLiteral})" title="删除">
                    <i class="fas fa-trash"></i>
                  </button>
                </div>
              `)
              : "";
          },
        },
      ],
      server: {
        url: "/credentials/api/credentials?sort=id&order=desc",
        headers: {
          "X-Requested-With": "XMLHttpRequest",
        },
        then: (response) => {
          const payload = response?.data || response || {};
          const items = payload.items || [];
          return items.map((item) => [
            item.id,
            item.name,
            item.credential_type,
            item.db_type,
            item.username,
            item.instance_count ?? 0,
            item.is_active,
            item.created_at_display || "",
            item,
          ]);
        },
        total: (response) => {
          const payload = response?.data || response || {};
          return payload.total || 0;
        },
      },
    });
    const initialFilters = normalizeGridFilters(resolveCredentialFilters(resolveFormElement()));
    credentialsGrid.setFilters(initialFilters || {}, { silent: true });
    credentialsGrid.init();
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

  function openCredentialEditor(credentialId) {
    if (!credentialModals || !credentialId) {
      return;
    }
    credentialModals.openEdit(credentialId);
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

    const filters = normalizeGridFilters(resolveCredentialFilters(targetForm, values));
    const searchTerm = filters.search || "";
    if (typeof searchTerm === "string" && searchTerm.trim().length > 0 && searchTerm.trim().length < 2) {
      global.toast.warning("搜索关键词至少需要2个字符");
      return;
    }
    if (credentialsGrid) {
      credentialsGrid.updateFilters(filters);
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

  function normalizeGridFilters(filters) {
    const normalized = { ...(filters || {}) };
    ["credential_type", "db_type", "status"].forEach((key) => {
      if (normalized[key] === "all") {
        delete normalized[key];
      }
    });
    if (Array.isArray(normalized.tags)) {
      const cleaned = normalized.tags.filter((item) => item && item.trim());
      if (cleaned.length === 0) {
        delete normalized.tags;
      } else {
        normalized.tags = cleaned;
      }
    } else if (typeof normalized.tags === "string" && normalized.tags.trim() === "") {
      delete normalized.tags;
    }
    return normalized;
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

  function escapeHtmlValue(value) {
    if (value === undefined || value === null) {
      return "";
    }
    return String(value)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#39;");
  }

  function getDbBadgeMeta(dbType) {
    const normalized = (dbType || "").toLowerCase();
    const map = {
      mysql: {
        className: "credential-db-badge--mysql",
        icon: "fas fa-database",
        label: "MySQL",
      },
      postgresql: {
        className: "credential-db-badge--postgresql",
        icon: "fas fa-database",
        label: "PostgreSQL",
      },
      pgsql: {
        className: "credential-db-badge--postgresql",
        icon: "fas fa-database",
        label: "PostgreSQL",
      },
      sqlserver: {
        className: "credential-db-badge--sqlserver",
        icon: "fas fa-server",
        label: "SQL Server",
      },
      oracle: {
        className: "credential-db-badge--oracle",
        icon: "fas fa-database",
        label: "Oracle",
      },
    };
    const fallbackLabel = normalized ? normalized.toUpperCase() : "未指定";
    const base = map[normalized];
    if (base) {
      return {
        ...base,
        className: `credential-db-badge ${base.className}`,
      };
    }
    return {
      className: "credential-db-badge credential-db-badge--default",
      icon: "fas fa-database",
      label: fallbackLabel,
    };
  }

  function bindCredentialsStoreEvents() {
    if (!credentialsStore) {
      return;
    }
    credentialsStore.subscribe("credentials:deleted", ({ credentialId, response }) => {
      closeDeleteModal();
      deleteCredentialId = null;
      const message = response?.message || "凭据已删除";
      global.toast.success(message);
      credentialsGrid?.refresh?.();
    });
    credentialsStore.subscribe("credentials:error", (payload) => {
      const message = payload?.error?.message || "凭据操作失败";
      global.toast.error(message);
    });
  }

  function closeDeleteModal() {
    deleteModal?.close?.();
  }

  global.deleteCredential = deleteCredential;
  global.openCredentialEditor = openCredentialEditor;
}

window.CredentialsListPage = {
  mount: function () {
    mountCredentialsListPage(window);
  },
};
