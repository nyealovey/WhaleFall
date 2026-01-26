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

  const gridjs = global.gridjs;
  const GridWrapper = global.GridWrapper;
  if (!gridjs || !GridWrapper) {
    console.error("Grid.js 或 GridWrapper 未加载");
    return;
  }

  const GridPage = global.Views?.GridPage;
  const GridPlugins = global.Views?.GridPlugins;
  if (!GridPage?.mount || !GridPlugins) {
    console.error("Views.GridPage 或 Views.GridPlugins 未加载");
    return;
  }

  const escapeHtml = global.UI?.escapeHtml;
  const resolveErrorMessage = global.UI?.resolveErrorMessage;
  const rowMeta = global.GridRowMeta;
  if (
    typeof escapeHtml !== "function" ||
    typeof resolveErrorMessage !== "function" ||
    typeof rowMeta?.get !== "function"
  ) {
    console.error("UI helpers 或 GridRowMeta 未加载");
    return;
  }

  const pageRoot = document.getElementById("credentials-list-page-root");
  if (!pageRoot) {
    console.warn("未找到凭据管理页面根元素");
    return;
  }

  const gridHtml = gridjs.html;
  const { ready, selectOne } = helpers;

  const CredentialsService = global.CredentialsService;
  if (!CredentialsService) {
    console.error("CredentialsService 未加载");
    return;
  }
  const createCredentialsStore = global.createCredentialsStore;
  if (typeof createCredentialsStore !== "function") {
    console.error("createCredentialsStore 未加载");
    return;
  }

  let credentialsStore = null;
  let credentialModals = null;

  const CREDENTIAL_FILTER_FORM_ID = "credential-filter-form";
  let credentialsGrid = null;
  let canManageCredentials = false;

  const credentialTypeMetaMap = new Map([
    ["database", { label: "数据库凭据", icon: "fa-database", tone: "brand" }],
    ["ssh", { label: "SSH", icon: "fa-terminal", tone: "muted" }],
    ["api", { label: "API", icon: "fa-plug", tone: "muted" }],
    ["windows", { label: "Windows", icon: "fa-desktop", tone: "muted" }],
    ["kafka", { label: "Kafka", icon: "fa-broadcast-tower", tone: "muted" }],
  ]);

  const dbTypeMetaMap = new Map([
    ["mysql", { label: "MySQL", icon: "fa-database" }],
    ["mariadb", { label: "MariaDB", icon: "fa-database" }],
    ["postgresql", { label: "PostgreSQL", icon: "fa-database" }],
    ["pgsql", { label: "PostgreSQL", icon: "fa-database" }],
    ["sqlserver", { label: "SQL Server", icon: "fa-server" }],
    ["oracle", { label: "Oracle", icon: "fa-database" }],
    ["redis", { label: "Redis", icon: "fa-warehouse" }],
    ["mongodb", { label: "MongoDB", icon: "fa-leaf" }],
  ]);

  ready(() => {
    try {
      credentialsStore = createCredentialsStore({
        service: new CredentialsService(),
        emitter: global.mitt ? global.mitt() : null,
      });
    } catch (error) {
      console.error("初始化 CredentialsStore 失败:", error);
      return;
    }

    credentialModals = initializeCredentialModals();
    initializeGridPage();
    bindCreateCredentialButton();
    exposeActions();
  });

  function initializeCredentialModals() {
    if (!global.CredentialModals?.createController) {
      console.warn("CredentialModals 未加载，创建/编辑模态不可用");
      return null;
    }
    const controller = global.CredentialModals.createController({
      store: credentialsStore,
      FormValidator: global.FormValidator,
      ValidationRules: global.ValidationRules,
      toast: global.toast,
      DOMHelpers: global.DOMHelpers,
      onSaved: () => {
        credentialsGrid?.refresh?.();
      },
    });
    controller.init?.();
    return controller;
  }

  function initializeGridPage() {
    const container = pageRoot.querySelector("#credentials-grid");
    if (!container) {
      return;
    }
    canManageCredentials = container.dataset.canManage === "true";

    const gridPage = GridPage.mount({
      root: pageRoot,
      grid: "#credentials-grid",
      filterForm: `#${CREDENTIAL_FILTER_FORM_ID}`,
      gridOptions: {
        sort: false,
        columns: buildColumns(),
        server: {
          url: credentialsStore?.gridUrl || "",
          headers: { "X-Requested-With": "XMLHttpRequest" },
          then: handleServerResponse,
          total: (response) => {
            const payload = response?.data || response || {};
            return payload.total || 0;
          },
        },
      },
      filters: {
        allowedKeys: ["search", "credential_type", "db_type", "status"],
        resolve: (values, ctx) => resolveFilters(values, ctx),
        normalize: (filters) => normalizeGridFilters(filters),
      },
      plugins: [
        GridPlugins.filterCard({
          autoSubmitOnChange: true,
          autoSubmitDebounce: 400,
        }),
        GridPlugins.actionDelegation({
          actions: {
            "edit-credential": ({ event, el }) => {
              event.preventDefault();
              openCredentialEditor(el.getAttribute("data-credential-id"), el);
            },
            "delete-credential": ({ event, el }) => {
              event.preventDefault();
              const encodedName = el.getAttribute("data-credential-name") || "";
              const decodedName = encodedName ? decodeURIComponent(encodedName) : "";
              deleteCredential(el.getAttribute("data-credential-id"), decodedName, el);
            },
          },
        }),
      ],
    });

    credentialsGrid = gridPage?.gridWrapper || null;
  }

  function resolveFilters(values, ctx) {
    const search = typeof values?.search === "string" ? values.search.trim() : "";
    if (search && search.length < 2) {
      ctx.toast?.warning?.("搜索关键词至少需要2个字符");
      return null;
    }
    return values || {};
  }

  function normalizeGridFilters(filters) {
    const normalized = filters && typeof filters === "object" ? filters : {};
    const cleaned = {};

    const search = typeof normalized.search === "string" ? normalized.search.trim() : "";
    if (search) {
      cleaned.search = search;
    }

    const credentialType =
      typeof normalized.credential_type === "string" ? normalized.credential_type.trim() : "";
    if (credentialType && credentialType !== "all") {
      cleaned.credential_type = credentialType;
    }

    const dbType = typeof normalized.db_type === "string" ? normalized.db_type.trim() : "";
    if (dbType && dbType !== "all") {
      cleaned.db_type = dbType;
    }

    const status = typeof normalized.status === "string" ? normalized.status.trim() : "";
    if (status && status !== "all") {
      cleaned.status = status;
    }

    return cleaned;
  }

  function buildColumns() {
    return [
      {
        name: "凭据",
        id: "name",
        formatter: (cell, row) => {
          const meta = rowMeta.get(row);
          const displayName = escapeHtml(cell || meta.name || "-");
          const usernameLine = meta.username
            ? `<small class="text-muted d-block"><i class="fas fa-user me-1"></i>${escapeHtml(meta.username)}</small>`
            : "";
          return gridHtml ? gridHtml(`<div class="fw-semibold">${displayName}</div>${usernameLine}`) : displayName;
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
        formatter: (cell, row) => renderActionButtons(rowMeta.get(row)),
      },
      { id: "__meta__", hidden: true },
    ];
  }

  function handleServerResponse(response) {
    const payload = response?.data || response || {};
    const items = payload.items || [];
    return items.map((item) => [
      item.name,
      item.credential_type,
      item.db_type,
      item.is_active,
      item.instance_count ?? 0,
      item.created_at_display || "",
      null,
      item,
    ]);
  }

  function renderCredentialTypeBadge(rawType) {
    const normalized = (rawType || "").toString().trim().toLowerCase();
    const meta = credentialTypeMetaMap.get(normalized) || null;
    const label = meta?.label || (normalized ? normalized.toUpperCase() : "未分类");
    const icon = meta?.icon || "fa-key";
    if (!gridHtml) {
      return label;
    }
    const toneClass = meta?.tone === "brand" ? "chip-outline--brand" : "chip-outline--muted";
    return gridHtml(`<span class="chip-outline ${toneClass}"><i class="fas ${icon}" aria-hidden="true"></i>${escapeHtml(label)}</span>`);
  }

  function renderDbTypeChip(dbType) {
    const normalized = (dbType || "").toString().trim().toLowerCase();
    const meta = dbTypeMetaMap.get(normalized) || null;
    const label = meta?.label || (normalized ? normalized.toUpperCase() : "未指定");
    const icon = meta?.icon || "fa-database";
    if (!gridHtml) {
      return label;
    }
    const variantClass = meta ? "chip-outline--brand" : "chip-outline--muted";
    return gridHtml(`<span class="chip-outline ${variantClass}"><i class="fas ${icon}" aria-hidden="true"></i>${escapeHtml(label)}</span>`);
  }

  function renderStatusBadge(value) {
    const isActive = Boolean(value);
    const resolveText = global.UI?.Terms?.resolveActiveStatusText;
    const text = typeof resolveText === "function" ? resolveText(isActive) : isActive ? "启用" : "停用";
    const variant = isActive ? "success" : "muted";
    const icon = isActive ? "fa-lock-open" : "fa-lock";
    return renderStatusPill(text, variant, icon);
  }

  function renderInstanceColumn(count, row) {
    const meta = rowMeta.get(row);
    const resolvedCount = Number.isFinite(Number(count)) ? Number(count) : Number(meta.instance_count ?? 0);
    if (!gridHtml) {
      return `${resolvedCount}`;
    }
    const variant = resolvedCount ? "info" : "muted";
    return gridHtml(
      `<div class="instance-count-stack">
        <span class="status-pill status-pill--${variant}" title="绑定实例数" aria-label="绑定实例数 ${resolvedCount}">
          <i class="fas fa-database" aria-hidden="true"></i><span aria-hidden="true">${resolvedCount}</span>
        </span>
      </div>`,
    );
  }

  function renderCreatedAtColumn(value, row) {
    const meta = rowMeta.get(row);
    const display = value || meta.created_at_display || "-";
    if (!gridHtml) {
      return display;
    }
    return gridHtml(`<span class="text-muted">${escapeHtml(display || "-")}</span>`);
  }

  function renderActionButtons(meta) {
    if (!canManageCredentials) {
      return gridHtml ? gridHtml('<span class="text-muted small">只读</span>') : "";
    }
    const credentialId = meta.id;
    const encodedName = encodeURIComponent(meta.name || "");
    if (!credentialId) {
      return "";
    }
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
  }

  function renderStatusPill(text, variant = "muted", icon) {
    if (!gridHtml) {
      return text;
    }
    return gridHtml(buildStatusPillMarkup(text, variant, icon));
  }

  function buildStatusPillMarkup(text, variant = "muted", icon) {
    const classes = ["status-pill"];
    if (variant) {
      classes.push(`status-pill--${variant}`);
    }
    const iconHtml = icon ? `<i class="fas ${icon}" aria-hidden="true"></i>` : "";
    return `<span class="${classes.join(" ")}">${iconHtml}${escapeHtml(text || "")}</span>`;
  }

  function bindCreateCredentialButton() {
    if (!credentialModals) {
      return;
    }
    const createBtn = selectOne('[data-action="create-credential"]');
    if (createBtn.length) {
      createBtn.on("click", (event) => {
        event.preventDefault();
        credentialModals.openCreate();
      });
    }
  }

  async function deleteCredential(credentialId, credentialName, trigger) {
    if (!credentialId || !canManageCredentials) {
      return;
    }
    if (!credentialsStore?.actions?.deleteCredential) {
      console.error("CredentialsStore 未初始化");
      global.toast?.error?.("凭据删除不可用");
      return;
    }

    const confirmDanger = global.UI?.confirmDanger;
    if (typeof confirmDanger !== "function") {
      global.toast?.error?.("确认组件未初始化");
      return;
    }

    const displayName = credentialName || `ID: ${credentialId}`;
    const confirmed = await confirmDanger({
      title: "确认删除凭据",
      message: "该操作不可撤销，请确认影响范围后继续。",
      details: [
        { label: "目标凭据", value: displayName, tone: "danger" },
        { label: "不可撤销", value: "删除后将无法恢复", tone: "danger" },
      ],
      confirmText: "确认删除",
      confirmButtonClass: "btn-danger",
    });
    if (!confirmed) {
      return;
    }

    const setButtonLoading = global.UI?.setButtonLoading;
    const clearButtonLoading = global.UI?.clearButtonLoading;
    const hasLoadingApi = typeof setButtonLoading === "function" && typeof clearButtonLoading === "function";

    if (hasLoadingApi) {
      setButtonLoading(trigger, { loadingText: "删除中..." });
    } else if (trigger) {
      trigger.setAttribute("aria-busy", "true");
      trigger.setAttribute("aria-disabled", "true");
      if ("disabled" in trigger) {
        trigger.disabled = true;
      }
    }

    try {
      const resp = await credentialsStore.actions.deleteCredential(credentialId);
      global.toast?.success?.(resp?.message || "凭据已删除");
      credentialsGrid?.refresh?.();
    } catch (error) {
      console.error("删除凭据失败:", error);
      global.toast?.error?.(resolveErrorMessage(error, "删除凭据失败"));
    } finally {
      if (hasLoadingApi) {
        clearButtonLoading(trigger);
      } else if (trigger) {
        trigger.removeAttribute("aria-busy");
        trigger.removeAttribute("aria-disabled");
        if ("disabled" in trigger) {
          trigger.disabled = false;
        }
      }
    }
  }

  function openCredentialEditor(credentialId) {
    if (!credentialModals || !credentialId) {
      return;
    }
    credentialModals.openEdit(credentialId);
  }

  function exposeActions() {
    global.deleteCredential = deleteCredential;
    global.openCredentialEditor = openCredentialEditor;
  }
}

window.CredentialsListPage = {
  mount: function () {
    mountCredentialsListPage(window);
  },
};
