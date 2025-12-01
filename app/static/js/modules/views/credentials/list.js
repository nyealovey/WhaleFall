/**
 * 挂载凭据列表页面。
 *
 * 初始化凭据列表页面的所有组件，包括服务、Store、Grid、筛选器、
 * 模态框和事件订阅。负责页面的完整生命周期管理。
 *
 * @param {Object} global - 全局 window 对象
 * @return {void}
 *
 * @example
 * // 在页面加载时调用
 * mountCredentialsListPage(window);
 */
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
   *
   * 按顺序初始化页面的各个组件，包括表格、模态框、删除确认、
   * 筛选器和 Store 事件订阅。
   *
   * @param {void} 无参数。直接读取页面依赖。
   * @returns {void}
   */
  function initializeCredentialsListPage() {
    initializeCredentialsGrid();
    bindModalTriggers();
    initializeDeleteConfirmation();
    initializeCredentialFilterCard();
    bindCredentialsStoreEvents();
  }

  /**
   * 初始化凭据表格。
   *
   * 创建 Grid.js 表格实例，配置列定义、服务端分页、排序和筛选。
   * 根据用户权限动态显示操作列。
   *
   * @param {void} 无参数。依赖页面 DOM。
   * @returns {void}
   */
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
          name: "名称",
          id: "name",
          formatter: (cell, row) => {
            const meta = row?.cells?.[row.cells.length - 1]?.data || {};
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
            const credentialTypeRaw = (cell || meta.credential_type || "-").toString();
            const credentialType = credentialTypeRaw.toUpperCase();
            const credentialBadgeMap = {
              database: "bg-success",
              api: "bg-primary",
              ssh: "bg-warning",
            };
            const credentialClass =
              credentialBadgeMap[credentialTypeRaw.toLowerCase()] || "bg-secondary";
            if (!gridHtml) {
              return credentialType;
            }
            return gridHtml(
              `<span class="badge credential-type-badge ${credentialClass}">${escapeHtmlValue(credentialType)}</span>`,
            );
          },
        },
        {
          name: "子类型",
          id: "db_type",
          formatter: (cell, row) => {
            const meta = row?.cells?.[row.cells.length - 1]?.data || {};
            const dbTypeRaw = cell || meta.db_type;
            if (!dbTypeRaw) {
              return gridHtml ? gridHtml('<span class="text-muted">-</span>') : "-";
            }
            const dbBadgeMeta = getDbBadgeMeta(dbTypeRaw);
            if (!gridHtml) {
              return dbBadgeMeta.label;
            }
            return gridHtml(`
              <span class="${dbBadgeMeta.className}">
                <i class="${dbBadgeMeta.icon} me-1"></i>${dbBadgeMeta.label}
              </span>
            `);
          },
        },
        { name: "用户名", id: "username" },
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
          name: "绑定实例",
          id: "instance_count",
          formatter: (cell) => {
            const count = Number(cell) || 0;
            const suffix = "个实例";
            if (!gridHtml) {
              return `${count} ${suffix}`;
            }
            return gridHtml(
              `<span class="badge bg-info instance-count-badge"><i class="fas fa-database me-1"></i>${count} ${suffix}</span>`,
            );
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
            const meta = row?.cells?.[row.cells.length - 1]?.data || {};
            const credentialId = meta.id;
            if (!canManageCredentials) {
              return gridHtml ? gridHtml('<span class="text-muted small">只读</span>') : "";
            }
            const encodedName = encodeURIComponent(meta.name || "");
            return gridHtml
              ? gridHtml(`
                <div class="btn-group btn-group-sm" role="group">
                  <button type="button" class="btn btn-outline-warning" data-action="edit-credential" data-credential-id="${credentialId}" onclick="openCredentialEditor(${credentialId})" title="编辑">
                    <i class="fas fa-edit"></i>
                  </button>
                  <button type="button" class="btn btn-outline-danger" data-action="delete-credential" data-credential-id="${credentialId}" onclick="deleteCredential(${credentialId}, decodeURIComponent('${encodedName}'))" title="删除">
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
            item.name,
            item.credential_type,
            item.db_type,
            item.username,
            item.is_active,
            item.instance_count ?? 0,
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
    console.log('[Credentials] 初始筛选条件:', initialFilters);
    credentialsGrid.init();
    if (initialFilters && Object.keys(initialFilters).length > 0) {
      console.log('[Credentials] 应用初始筛选条件');
      credentialsGrid.setFilters(initialFilters);
    }
  }
  /**
   * 初始化新建/编辑凭据模态触发器。
   *
   * @param {void} 无参数。绑定固定 data-action。
   * @returns {void}
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

  /**
   * 初始化删除确认模态框。
   *
   * @param {void} 无参数。调用 UI.createModal。
   * @returns {void}
   */
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

  /**
   * 处理删除模态确认按钮点击。
   *
   * @param {Event} event 点击事件。
   * @returns {void}
   */
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

  /**
   * 打开删除确认模态。
   *
   * @param {number|string} credentialId 凭据 ID。
   * @param {string} credentialName 展示名称。
   * @returns {void}
   */
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

  /**
   * 打开凭据编辑模态。
   *
   * @param {number|string} credentialId 凭据 ID。
   * @returns {void}
   */
  function openCredentialEditor(credentialId) {
    if (!credentialModals || !credentialId) {
      return;
    }
    credentialModals.openEdit(credentialId);
  }

  /**
   * 显示按钮 loading 状态。
   *
   * @param {Element|string|Object} target 目标按钮或选择器。
   * @param {string} text 展示的加载文案。
   * @returns {void}
   */
  function showLoadingState(target, text) {
    const element = from(target);
    if (!element.length) {
      return;
    }
    element.attr("data-original-text", element.html());
    element.html(`<i class="fas fa-spinner fa-spin me-2"></i>${text}`);
    element.attr("disabled", "disabled");
  }

  /**
   * 恢复按钮默认状态。
   *
   * @param {Element|string|Object} target 目标按钮或选择器。
   * @param {string} fallbackText 找不到原文案时使用的文本。
   * @returns {void}
   */
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

  /**
   * 初始化筛选表单及自动提交逻辑。
   *
   * @param {void} 无参数。绑定表单事件。
   * @returns {void}
   */
  function initializeCredentialFilterCard() {
    const form = document.getElementById(CREDENTIAL_FILTER_FORM_ID);
    if (!form) {
      console.warn("凭据筛选表单缺失，搜索无法初始化");
      return;
    }

    credentialFilterCard = { form };

    form.addEventListener("submit", (event) => {
      event.preventDefault();
      applyCredentialFilters(form);
    });

    const clearButton = form.querySelector("[data-filter-clear]");
    if (clearButton) {
      clearButton.addEventListener("click", (event) => {
        event.preventDefault();
        resetCredentialFilters(form);
      });
    }

    const autoInputs = form.querySelectorAll("[data-auto-submit]");
    if (autoInputs.length) {
      const debouncedSubmit =
        typeof LodashUtils.debounce === "function"
          ? LodashUtils.debounce(() => applyCredentialFilters(form), 400)
          : null;
      autoInputs.forEach((input) => {
        input.addEventListener("input", () => {
          if (debouncedSubmit) {
            debouncedSubmit();
          } else {
            applyCredentialFilters(form);
          }
        });
      });
    }

    if (AUTO_APPLY_FILTER_CHANGE) {
      form.querySelectorAll("select, input[type='checkbox'], input[type='radio']").forEach((element) => {
        element.addEventListener("change", () => applyCredentialFilters(form));
      });
    }

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

  /**
   * 销毁筛选表单引用，移除事件。
   *
   * @param {void} 无参数。重置局部状态。
   * @returns {void}
   */
  function destroyCredentialFilterCard() {
    credentialFilterCard = null;
  }

  /**
   * 应用筛选条件并刷新 grid 或跳转。
   *
   * @param {HTMLFormElement|string|EventTarget} form 筛选表单。
   * @param {Object} [values] 额外覆盖的值。
   * @returns {void}
   */
  function applyCredentialFilters(form, values) {
    const targetForm = resolveFormElement(form);
    if (!targetForm) {
      console.warn('[Credentials] 未找到筛选表单');
      return;
    }

    const filters = normalizeGridFilters(resolveCredentialFilters(targetForm, values));
    console.log('[Credentials] 应用筛选条件:', filters);
    const searchTerm = filters.search || "";
    if (typeof searchTerm === "string" && searchTerm.trim().length > 0 && searchTerm.trim().length < 2) {
      global.toast.warning("搜索关键词至少需要2个字符");
      return;
    }
    if (credentialsGrid) {
      console.log('[Credentials] 调用 updateFilters');
      credentialsGrid.updateFilters(filters);
      return;
    }
    const params = buildCredentialQueryParams(filters);
    const action = targetForm.getAttribute("action") || global.location.pathname;
    const query = params.toString();
    global.location.href = query ? `${action}?${query}` : action;
  }

  /**
   * 解析表单字段并规范化值。
   *
   * @param {HTMLFormElement} form 筛选表单。
   * @param {Object} [overrideValues] 覆盖的 key/value。
   * @returns {Object} 过滤对象。
   */
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

  /**
   * 清理空值，返回有效过滤条件。
   *
   * @param {Object} filters 原始过滤条件。
   * @returns {Object} 处理后的过滤结果。
   */
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

  /**
   * 将表单值转换为接口可用格式。
   *
   * @param {*} value 原始表单值。
   * @returns {*|null} 清洗后的结果。
   */
  function sanitizeFilterValue(value) {
    if (Array.isArray(value)) {
      return LodashUtils.compact(value.map((item) => sanitizePrimitiveValue(item)));
    }
    return sanitizePrimitiveValue(value);
  }

  /**
   * 规范化单个字段的原始值。
   *
   * @param {*} value 输入值。
   * @returns {*|null} 处理后的结果。
   */
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

  /**
   * 将过滤条件编码为查询参数。
   *
   * @param {Object} filters 筛选对象。
   * @returns {URLSearchParams} 查询参数实例。
   */
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

  /**
   * 重置筛选表单并应用空过滤。
   *
   * @param {HTMLFormElement|string|EventTarget} form 目标表单。
   * @returns {void}
   */
  function resetCredentialFilters(form) {
    const targetForm = resolveFormElement(form);
    if (targetForm) {
      targetForm.reset();
    }
    applyCredentialFilters(targetForm, {});
  }

  /**
   * 接受 selector/DOM，统一为表单元素。
   *
   * @param {HTMLFormElement|string|Object} form 输入引用或选择器。
   * @returns {HTMLFormElement|null} 解析后的表单。
   */
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

  /**
   * 收集表单字段，如果存在 serializeForm 则优先使用。
   *
   * @param {HTMLFormElement} form 目标表单。
   * @returns {Object} 键值数据。
   */
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

  /**
   * 去除文本值的多余空格。
   *
   * @param {string} value 待处理的字符串。
   * @returns {string} 规范化文本。
   */
  function normalizeText(value) {
    const text = (value || "").toString().trim();
    if (typeof LodashUtils.toLower === "function") {
      return LodashUtils.toLower(text);
    }
    return text.toLowerCase();
  }

  /**
   * 简单 HTML 转义。
   *
   * @param {*} value 待转义的值。
   * @returns {string} 安全字符串。
   */
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

  /**
   * 根据数据库类型返回徽章元信息。
   *
   * @param {string} dbType 数据库类型标识。
   * @returns {Object} 包含 className/icon/label 的描述。
   */
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

  /**
   * 订阅凭据 store 的事件。
   *
   * @param {void} 无参数。依赖 credentialsStore。
   * @returns {void}
   */
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

  /**
   * 关闭删除凭据模态。
   *
   * @param {void} 无参数。调用 deleteModal.close。
   * @returns {void}
   */
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
