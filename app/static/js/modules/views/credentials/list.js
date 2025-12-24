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
  const UNSAFE_KEYS = ["__proto__", "prototype", "constructor"];
  const ALLOWED_FILTER_KEYS = [
    "name",
    "credential_type",
    "username",
    "db_type",
    "status",
    "tags",
    "search",
    "page",
    "page_size",
    "sort",
    "direction",
  ];
  const isSafeKey = (key) => typeof key === "string" && !UNSAFE_KEYS.includes(key);
  const isAllowedFilterKey = (key) => isSafeKey(key) && ALLOWED_FILTER_KEYS.includes(key);

  const { ready, selectOne, from } = helpers;
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
  let gridActionDelegationBound = false;
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

  let credentialFilterCard = null;
  let filterUnloadHandler = null;
  let credentialsGrid = null;
  let canManageCredentials = false;

  const credentialTypeMetaMap = {
    database: { label: "数据库凭据", icon: "fa-database", variant: "brand" },
    ssh: { label: "SSH", icon: "fa-terminal", variant: "muted" },
    api: { label: "API", icon: "fa-plug", variant: "muted" },
    windows: { label: "Windows", icon: "fa-desktop", variant: "muted" },
    kafka: { label: "Kafka", icon: "fa-broadcast-tower", variant: "muted" },
  };

  const dbTypeMetaMap = {
    mysql: { label: "MySQL", icon: "fa-database" },
    mariadb: { label: "MariaDB", icon: "fa-database" },
    postgresql: { label: "PostgreSQL", icon: "fa-database" },
    pgsql: { label: "PostgreSQL", icon: "fa-database" },
    sqlserver: { label: "SQL Server", icon: "fa-server" },
    oracle: { label: "Oracle", icon: "fa-database" },
    redis: { label: "Redis", icon: "fa-warehouse" },
    mongodb: { label: "MongoDB", icon: "fa-leaf" },
  };

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
          name: "凭据",
          id: "name",
          formatter: (cell, row) => {
            const meta = resolveRowMeta(row);
            const displayName = escapeHtmlValue(cell || meta.name || "-");
            const usernameLine = meta.username
              ? `<small class="text-muted d-block"><i class="fas fa-user me-1"></i>${escapeHtmlValue(meta.username)}</small>`
              : "";
            return gridHtml
              ? gridHtml(`<div class="fw-semibold">${displayName}</div>${usernameLine}`)
              : displayName;
          },
        },
        {
          name: "类型",
          id: "credential_type",
          formatter: (cell) => renderCredentialTypeBadge(cell),
        },
        {
          name: "数据库类型",
          id: "db_type",
          formatter: (cell) => renderDbTypeChip(cell),
        },
        {
          name: "状态",
          id: "is_active",
          formatter: (cell) => renderStatusBadge(cell),
        },
        {
          name: "绑定实例",
          id: "instance_count",
          formatter: (cell, row) => renderInstanceColumn(cell, row),
        },
        {
          name: "创建时间",
          id: "created_at",
          formatter: (cell, row) => renderCreatedAtColumn(cell, row),
        },
        {
          name: "操作",
          id: "actions",
          sort: false,
          formatter: (cell, row) => {
            if (!canManageCredentials) {
              return gridHtml ? gridHtml('<span class="text-muted small">只读</span>') : '';
            }
            const meta = resolveRowMeta(row);
            const credentialId = meta.id;
            const encodedName = encodeURIComponent(meta.name || "");
            if (!gridHtml) {
              return "管理";
            }
            return gridHtml(`
              <div class="btn-group" role="group">
                <button type="button" class="btn btn-outline-secondary btn-icon" data-action="edit-credential" data-credential-id="${credentialId}" title="编辑">
                  <i class="fas fa-pen"></i>
                </button>
                <button type="button" class="btn btn-outline-danger btn-icon" data-action="delete-credential" data-credential-id="${credentialId}" data-credential-name="${encodedName}" title="删除">
                  <i class="fas fa-trash"></i>
                </button>
              </div>
            `);
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
    credentialsGrid.init();
    bindGridActionDelegation(container);
    if (initialFilters && Object.keys(initialFilters).length > 0) {
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
    credentialModals.init?.();
  }

  /**
   * 提示确认并删除凭据。
   *
   * @param {number|string} credentialId 凭据 ID。
   * @param {string} credentialName 展示名称。
   * @param {Element} [trigger] 触发按钮。
   * @returns {Promise<void>} 完成删除流程。
   */
  async function deleteCredential(credentialId, credentialName, trigger) {
    if (!credentialId || !canManageCredentials) {
      return;
    }
    if (!credentialsStore?.actions?.deleteCredential) {
      console.error('CredentialsStore 未初始化');
      return;
    }

    const confirmDanger = global.UI?.confirmDanger;
    if (typeof confirmDanger !== 'function') {
      global.toast?.error?.('确认组件未初始化');
      return;
    }

    const displayName = credentialName || `ID: ${credentialId}`;
    const confirmed = await confirmDanger({
      title: '确认删除凭据',
      message: '该操作不可撤销，请确认影响范围后继续。',
      details: [
        { label: '目标凭据', value: displayName, tone: 'danger' },
        { label: '不可撤销', value: '删除后将无法恢复', tone: 'danger' },
      ],
      confirmText: '确认删除',
      confirmButtonClass: 'btn-danger',
    });
    if (!confirmed) {
      return;
    }

    const setButtonLoading = global.UI?.setButtonLoading;
    const clearButtonLoading = global.UI?.clearButtonLoading;
    const hasLoadingApi =
      typeof setButtonLoading === 'function' && typeof clearButtonLoading === 'function';

    if (hasLoadingApi) {
      setButtonLoading(trigger, { loadingText: '删除中...' });
    } else if (trigger) {
      trigger.setAttribute('aria-busy', 'true');
      trigger.setAttribute('aria-disabled', 'true');
      if ('disabled' in trigger) {
        trigger.disabled = true;
      }
    }

    try {
      await credentialsStore.actions.deleteCredential(credentialId);
    } catch (error) {
      console.error('删除凭据失败:', error);
    } finally {
      if (hasLoadingApi) {
        clearButtonLoading(trigger);
      } else if (trigger) {
        trigger.removeAttribute('aria-busy');
        trigger.removeAttribute('aria-disabled');
        if ('disabled' in trigger) {
          trigger.disabled = false;
        }
      }
    }
  }

  /**
   * 打开凭据编辑模态。
   *
   * @param {number|string} credentialId 凭据 ID。
   * @returns {void}
   */
  function openCredentialEditor(credentialId, trigger) {
    if (!credentialModals || !credentialId) {
      return;
    }
    const triggerElement = trigger ? from(trigger) : null;
    if (triggerElement?.length) {
      triggerElement.attr('data-loading', 'true');
      triggerElement.attr('disabled', 'disabled');
    }
    credentialModals.openEdit(credentialId);
    if (triggerElement?.length) {
      triggerElement.attr('disabled', null);
      triggerElement.attr('data-loading', null);
    }
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

  function assignFilterField(target, key, value) {
    switch (key) {
      case "name":
        target.name = value;
        break;
      case "credential_type":
        target.credential_type = value;
        break;
      case "username":
        target.username = value;
        break;
      case "db_type":
        target.db_type = value;
        break;
      case "status":
        target.status = value;
        break;
      case "tags":
        target.tags = value;
        break;
      case "search":
        target.search = value;
        break;
      case "page":
        target.page = value;
        break;
      case "page_size":
        target.page_size = value;
        break;
      case "sort":
        target.sort = value;
        break;
      case "direction":
        target.direction = value;
        break;
      default:
        break;
    }
  }

  function getFilterField(target, key) {
    switch (key) {
      case "name":
        return target.name;
      case "credential_type":
        return target.credential_type;
      case "username":
        return target.username;
      case "db_type":
        return target.db_type;
      case "status":
        return target.status;
      case "tags":
        return target.tags;
      case "search":
        return target.search;
      case "page":
        return target.page;
      case "page_size":
        return target.page_size;
      case "sort":
        return target.sort;
      case "direction":
        return target.direction;
      default:
        return undefined;
    }
  }

  function resolveCredentialFilters(form, overrideValues) {
    const rawValues =
      overrideValues && Object.keys(overrideValues || {}).length ? overrideValues : collectFormValues(form);
    const safeEntries = Object.entries(rawValues || {}).filter(
      ([key]) => isAllowedFilterKey(key),
    );
    return safeEntries.reduce((result, [key, value]) => {
      const normalized = sanitizeFilterValue(value);
      if (normalized === null || normalized === undefined) {
        return result;
      }
      if (Array.isArray(normalized) && normalized.length === 0) {
        return result;
      }
      assignFilterField(result, key, normalized);
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
    const normalized = filters || {};
    const cleaned = {};
    if (normalized.name) cleaned.name = normalized.name;
    if (normalized.credential_type && normalized.credential_type !== "all") cleaned.credential_type = normalized.credential_type;
    if (normalized.db_type && normalized.db_type !== "all") cleaned.db_type = normalized.db_type;
    if (normalized.status && normalized.status !== "all") cleaned.status = normalized.status;
    if (normalized.search) cleaned.search = normalized.search;
    if (Array.isArray(normalized.tags)) {
      const tagsClean = normalized.tags.filter((item) => item && item.trim());
      if (tagsClean.length > 0) {
        cleaned.tags = tagsClean.map((tag) => sanitizeText(tag));
      }
    } else if (typeof normalized.tags === "string" && normalized.tags.trim() !== "") {
      cleaned.tags = sanitizeText(normalized.tags);
    }
    return cleaned;
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
    const result = Object.create(null);
    formData.forEach((value, key) => {
      if (!isAllowedFilterKey(key)) {
        return;
      }
      const normalized = value instanceof File ? value.name : value;
      const existing = getFilterField(result, key);
      if (existing === undefined) {
        assignFilterField(result, key, normalized);
      } else if (Array.isArray(existing)) {
        existing.push(normalized);
        assignFilterField(result, key, existing);
      } else {
        assignFilterField(result, key, [existing, normalized]);
      }
    });
    return result;
  }

  function sanitizeText(value) {
    if (value === undefined || value === null) {
      return "";
    }
    return String(value).trim();
  }

  /**
   * 去除文本值的多余空格。
   *
   * @param {string} value 待处理的字符串。
   * @returns {string} 规范化文本。
   */
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
   * 渲染凭据类型 chip。
   *
   * @param {string} rawType 凭据类型。
   * @returns {import('gridjs').Html|string} chip 片段。
   */
  function renderCredentialTypeBadge(rawType) {
    const normalized = (rawType || "").toString().trim().toLowerCase();
    let meta = {};
    if (isSafeKey(normalized)) {
      switch (normalized) {
        case "database":
          meta = credentialTypeMetaMap.database;
          break;
        case "ssh":
          meta = credentialTypeMetaMap.ssh;
          break;
        case "api":
          meta = credentialTypeMetaMap.api;
          break;
        case "windows":
          meta = credentialTypeMetaMap.windows;
          break;
        case "kafka":
          meta = credentialTypeMetaMap.kafka;
          break;
        default:
          break;
      }
    }
    const label = meta.label || (normalized ? normalized.toUpperCase() : "未分类");
    const icon = meta.icon || "fa-key";
    if (!gridHtml) {
      return label;
    }
    const toneClass = meta.variant === "brand" ? "chip-outline--brand" : "chip-outline--muted";
    return gridHtml(
      `<span class="chip-outline ${toneClass}"><i class="fas ${icon}" aria-hidden="true"></i>${escapeHtmlValue(label)}</span>`,
    );
  }

  /**
   * 渲染数据库类型 chip。
   *
   * @param {string} dbType 数据库类型。
   * @returns {import('gridjs').Html|string} chip 片段。
   */
  function renderDbTypeChip(dbType) {
    const normalized = (dbType || "").toString().trim().toLowerCase();
    let meta = {};
    if (isSafeKey(normalized)) {
      switch (normalized) {
        case "mysql":
          meta = dbTypeMetaMap.mysql;
          break;
        case "mariadb":
          meta = dbTypeMetaMap.mariadb;
          break;
        case "postgresql":
        case "pgsql":
          meta = dbTypeMetaMap.postgresql;
          break;
        case "sqlserver":
          meta = dbTypeMetaMap.sqlserver;
          break;
        case "oracle":
          meta = dbTypeMetaMap.oracle;
          break;
        case "redis":
          meta = dbTypeMetaMap.redis;
          break;
        case "mongodb":
          meta = dbTypeMetaMap.mongodb;
          break;
        default:
          break;
      }
    }
    const label = meta.label || (normalized ? normalized.toUpperCase() : "未指定");
    const icon = meta.icon || "fa-database";
    if (!gridHtml) {
      return label;
    }
    const variantClass = meta.label ? "chip-outline--brand" : "chip-outline--muted";
    return gridHtml(
      `<span class="chip-outline ${variantClass}"><i class="fas ${icon}" aria-hidden="true"></i>${escapeHtmlValue(label)}</span>`,
    );
  }

  /**
   * 渲染启用状态。
   *
   * @param {boolean} value 原始状态值。
   * @returns {import('gridjs').Html|string} 状态 pill。
   */
  function renderStatusBadge(value) {
    const isActive = Boolean(value);
    const text = isActive ? "启用" : "停用";
    const variant = isActive ? "success" : "danger";
    const icon = isActive ? "fa-lock-open" : "fa-lock";
    return renderStatusPill(text, variant, icon);
  }

  /**
   * 渲染绑定实例列。
   *
   * @param {number} count 数据库绑定数量。
   * @param {import('gridjs').Row} row 当前行。
   * @returns {import('gridjs').Html|string} 栈式展示。
   */
  function renderInstanceColumn(count, row) {
    const meta = resolveRowMeta(row);
    const resolvedCount = Number.isFinite(Number(count)) ? Number(count) : Number(meta.instance_count ?? 0);
    if (!gridHtml) {
      return `${resolvedCount} 个实例`;
    }
    return gridHtml(
      `<div class="instance-count-stack">
        ${buildStatusPillMarkup(`${resolvedCount} 个实例`, resolvedCount ? 'info' : 'muted', 'fa-database')}
      </div>`,
    );
  }

  /**
   * 渲染创建时间列。
   *
   * @param {string} value 原始时间。
   * @param {import('gridjs').Row} row 当前行。
   * @returns {import('gridjs').Html|string} 文本内容。
   */
  function renderCreatedAtColumn(value, row) {
    const meta = resolveRowMeta(row);
    const display = value || meta.created_at_display || '-';
    if (!gridHtml) {
      return display;
    }
    return gridHtml(`<span class="text-muted">${escapeHtmlValue(display || '-')}</span>`);
  }

  /**
   * 渲染状态 pill。
   *
   * @param {string} text 文案。
   * @param {string} variant 颜色风格。
   * @param {string} icon FontAwesome 图标类。
   * @returns {import('gridjs').Html|string} pill 片段。
   */
  function renderStatusPill(text, variant = 'muted', icon) {
    if (!gridHtml) {
      return text;
    }
    return gridHtml(buildStatusPillMarkup(text, variant, icon));
  }

  /**
   * 构建 status-pill HTML。
   *
   * @param {string} text pill 文案。
   * @param {string} variant 样式。
   * @param {string} icon 图标类。
   * @returns {string} HTML 字符串。
   */
  function buildStatusPillMarkup(text, variant = 'muted', icon) {
    const classes = ['status-pill'];
    if (variant) {
      classes.push(`status-pill--${variant}`);
    }
    const iconHtml = icon ? `<i class="fas ${icon}" aria-hidden="true"></i>` : '';
    return `<span class="${classes.join(' ')}">${iconHtml}${escapeHtmlValue(text || '')}</span>`;
  }

  /**
   * 解析行附带的元数据。
   *
   * @param {import('gridjs').Row} row gridjs 行。
   * @returns {Object} 行末附加元信息。
   */
  function resolveRowMeta(row) {
    return row?.cells?.[row.cells.length - 1]?.data || {};
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
    credentialsStore.subscribe("credentials:deleted", ({ response }) => {
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
   * 绑定 Grid 内动作按钮事件，替代字符串 onclick。
   *
   * @param {HTMLElement} container grid 容器。
   * @returns {void}
   */
  function bindGridActionDelegation(container) {
    if (!container || gridActionDelegationBound) {
      return;
    }
    container.addEventListener("click", (event) => {
      const actionBtn = event.target.closest("[data-action]");
      if (!actionBtn || !container.contains(actionBtn)) {
        return;
      }
      const action = actionBtn.getAttribute("data-action");
      const credentialId = actionBtn.getAttribute("data-credential-id");
      switch (action) {
        case "edit-credential":
          event.preventDefault();
          openCredentialEditor(credentialId, actionBtn);
          break;
        case "delete-credential": {
          event.preventDefault();
          const encodedName = actionBtn.getAttribute("data-credential-name") || "";
          const decodedName = encodedName ? decodeURIComponent(encodedName) : "";
          deleteCredential(credentialId, decodedName, actionBtn);
          break;
        }
        default:
          break;
      }
    });
    gridActionDelegationBound = true;
  }

  global.deleteCredential = deleteCredential;
  global.openCredentialEditor = openCredentialEditor;
}

window.CredentialsListPage = {
  mount: function () {
    mountCredentialsListPage(window);
  },
};
