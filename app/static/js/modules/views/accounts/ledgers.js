/**
 * 挂载账户台账页面。
 *
 * 初始化账户台账页面的所有组件，包括 Grid 列表、筛选器、标签选择器、
 * 数据库类型切换、导出与账户权限查看。
 *
 * @param {Window} global - 全局 window 对象
 * @returns {void}
 */
function mountAccountsListPage(global) {
  "use strict";

  const helpers = global.DOMHelpers;
  if (!helpers) {
    console.error("DOMHelpers 未初始化，无法加载账户台账页面");
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
  const renderChipStack = global.UI?.renderChipStack;
  const rowMeta = global.GridRowMeta;
  if (
    typeof escapeHtml !== "function" ||
    typeof renderChipStack !== "function" ||
    typeof rowMeta?.get !== "function"
  ) {
    console.error("UI helpers 或 GridRowMeta 未加载");
    return;
  }

  const AccountsLedgersService = global.AccountsLedgersService;
  if (!AccountsLedgersService) {
    console.error("AccountsLedgersService 未初始化");
    return;
  }
  const accountsLedgersService = new AccountsLedgersService();

  const pageRoot = document.getElementById("accounts-page-root");
  if (!pageRoot) {
    console.warn("未找到账户台账页面根元素");
    return;
  }

  const gridHtml = gridjs.html;
  const { ready, selectOne } = helpers;

  const ACCOUNT_FILTER_FORM_ID = "account-filter-form";
  const TAG_SELECTOR_SCOPE = "account-tag-selector";
  const resolveExportEndpoint = () =>
    pageRoot.dataset.exportUrl ?? accountsLedgersService.getExportUrl();
  const currentDbType = pageRoot.dataset.currentDbType || "all";
  const includeDbTypeColumn = !currentDbType || currentDbType === "all";
  const basePath = resolveBasePath(currentDbType);

  let gridPage = null;
  let accountsGrid = null;
  let instanceService = null;
  let instanceStore = null;

  ready(() => {
    configurePermissionViewer();
    initializeInstanceService();
    initializeInstanceStore();
    initializeGridPage();
    initializeTagFilter();
    bindDatabaseTypeButtons();
    bindSyncAllAccountsAction();
  });

  function configurePermissionViewer() {
    const viewer = global.PermissionViewer;
    const PermissionService = global.PermissionService;
    if (!viewer?.configure || typeof PermissionService !== "function") {
      console.error("PermissionViewer/PermissionService 未加载，权限查看功能不可用");
      return;
    }
    if (typeof global.showPermissionsModal !== "function") {
      console.error("showPermissionsModal 未加载，权限查看功能不可用");
      return;
    }
    let service = null;
    try {
      service = new PermissionService();
    } catch (error) {
      console.error("初始化 PermissionService 失败:", error);
      return;
    }
    try {
      viewer.configure({
        fetchPermissions: ({ accountId, apiUrl }) => {
          return apiUrl
            ? service.fetchByUrl(apiUrl)
            : service.fetchAccountPermissions(accountId);
        },
        showPermissionsModal: global.showPermissionsModal,
        toast: global.toast,
      });
    } catch (error) {
      console.error("配置 PermissionViewer 失败:", error);
    }
  }

  function resolveBasePath(dbType) {
    const normalized = typeof dbType === "string" ? dbType.trim() : "";
    if (normalized && normalized !== "all") {
      return `/accounts/ledgers/${encodeURIComponent(normalized)}`;
    }
    return "/accounts/ledgers";
  }

  function initializeInstanceService() {
    const Service = global.InstanceManagementService;
    if (!Service) {
      return;
    }
    try {
      instanceService = new Service();
    } catch (error) {
      console.error("初始化 InstanceManagementService 失败:", error);
      instanceService = null;
    }
  }

  function initializeInstanceStore() {
    const createInstanceStore = global.createInstanceStore;
    if (typeof createInstanceStore !== "function" || !instanceService) {
      return;
    }
    try {
      instanceStore = createInstanceStore({
        service: instanceService,
        emitter: global.mitt ? global.mitt() : null,
      });
      instanceStore.init?.({})?.catch?.((error) => {
        console.warn("InstanceStore 初始化失败", error);
      });
    } catch (error) {
      console.error("初始化 InstanceStore 失败:", error);
      instanceStore = null;
    }
  }

  function initializeGridPage() {
    gridPage = GridPage.mount({
      root: pageRoot,
      grid: "#accounts-grid",
      filterForm: `#${ACCOUNT_FILTER_FORM_ID}`,
      gridOptions: {
        search: false,
        sort: false,
        columns: buildColumns({ includeDbTypeColumn }),
        server: {
          url: accountsLedgersService.getGridUrl(),
          headers: { "X-Requested-With": "XMLHttpRequest" },
          then: handleServerResponse({ includeDbTypeColumn }),
          total: (response) => {
            const payload = response?.data || response || {};
            const total = payload.total || 0;
            updateTotalCount(total);
            return total;
          },
        },
      },
      filters: {
        allowedKeys: [
          "search",
          "classification",
          "tags",
          "instance_id",
          "is_locked",
          "is_superuser",
          "plugin",
        ],
        normalize: (filters) => normalizeGridFilters(filters),
      },
      plugins: [
        GridPlugins.filterCard({
          autoSubmitOnChange: true,
          onClear: () => {
            clearTagSelectorPreview(TAG_SELECTOR_SCOPE);
            global.location.href = basePath;
          },
        }),
        GridPlugins.urlSync({
          basePath: () => basePath,
        }),
        GridPlugins.exportButton({
          selector: '[data-action="export-accounts-csv"]',
          endpoint: resolveExportEndpoint,
        }),
        GridPlugins.actionDelegation({
          actions: {
            "view-permissions": ({ event, el }) => {
              event.preventDefault();
              handleViewPermissions(el.getAttribute("data-account-id"), el);
            },
          },
        }),
      ],
    });

    accountsGrid = gridPage?.gridWrapper || null;
  }

  function normalizeGridFilters(filters) {
    const source = filters && typeof filters === "object" ? filters : {};
    const cleaned = {};

    const search = sanitizeText(source.search || source.q);
    if (search) {
      cleaned.search = search;
    }

    const classification = sanitizeText(source.classification);
    if (classification && classification !== "all") {
      cleaned.classification = classification;
    }

    const tags = normalizeArrayValue(source.tags);
    if (tags.length) {
      cleaned.tags = tags;
    }

    const instanceId = sanitizeText(source.instance_id);
    if (instanceId) {
      cleaned.instance_id = instanceId;
    }

    const isLocked = sanitizeFlag(source.is_locked);
    if (isLocked) {
      cleaned.is_locked = isLocked;
    }

    const isSuperuser = sanitizeFlag(source.is_superuser);
    if (isSuperuser) {
      cleaned.is_superuser = isSuperuser;
    }

    const plugin = sanitizeText(source.plugin);
    if (plugin) {
      cleaned.plugin = plugin;
    }

    if (currentDbType && currentDbType !== "all") {
      cleaned.db_type = currentDbType;
    }

    return cleaned;
  }

  function sanitizeText(value) {
    if (typeof value !== "string") {
      return "";
    }
    const trimmed = value.trim();
    return trimmed || "";
  }

  function sanitizeFlag(value) {
    if (value === "true" || value === "false") {
      return value;
    }
    return "";
  }

  function normalizeArrayValue(value) {
    if (!value) {
      return [];
    }
    if (Array.isArray(value)) {
      return value.map((item) => (typeof item === "string" ? item.trim() : "")).filter(Boolean);
    }
    if (typeof value === "string") {
      return value
        .split(",")
        .map((item) => item.trim())
        .filter(Boolean);
    }
    return [];
  }

  function buildColumns({ includeDbTypeColumn }) {
    const CHIP_COLUMN_WIDTH = "220px";

    const columns = [
      {
        name: "账户/实例",
        id: "username",
        formatter: (cell, row) => renderAccountCell(rowMeta.get(row)),
      },
      {
        name: "可用性",
        id: "is_locked",
        width: "70px",
        formatter: (cell) => renderStatusBadge(Boolean(cell)),
      },
      {
        name: "是否删除",
        id: "is_deleted",
        width: "70px",
        formatter: (cell) => renderDeletionBadge(Boolean(cell)),
      },
      {
        name: "是否超极",
        id: "is_superuser",
        width: "70px",
        formatter: (cell) => renderSuperuserBadge(Boolean(cell)),
      },
      {
        name: "分类",
        id: "classifications",
        sort: false,
        width: CHIP_COLUMN_WIDTH,
        formatter: (cell) => renderClassifications(Array.isArray(cell) ? cell : []),
      },
    ];

    if (includeDbTypeColumn) {
      columns.push({
        name: "数据库类型",
        id: "db_type",
        width: "120px",
        formatter: (cell) => renderDbTypeBadge(cell),
      });
    }

    columns.push(
      {
        name: "标签",
        id: "tags",
        sort: false,
        width: CHIP_COLUMN_WIDTH,
        formatter: (cell) => renderTags(Array.isArray(cell) ? cell : []),
      },
      {
        name: "操作",
        id: "actions",
        sort: false,
        width: "70px",
        formatter: (cell, row) => renderActions(rowMeta.get(row)),
      },
      { id: "__meta__", hidden: true },
    );

    return columns;
  }

  function handleServerResponse({ includeDbTypeColumn }) {
    return (response) => {
      const payload = response?.data || response || {};
      const items = payload.items || [];
      return items.map((item) => {
        const row = [
          item.username || "-",
          item.is_locked,
          item.is_deleted,
          item.is_superuser,
          item.classifications || [],
        ];
        if (includeDbTypeColumn) {
          row.push(item.db_type || "-");
        }
        row.push(item.tags || [], null, item);
        return row;
      });
    };
  }

  function renderTags(tags) {
    if (!gridHtml) {
      return tags.map((tag) => tag?.display_name || tag?.name).filter(Boolean).join(", ") || "无标签";
    }
    const names = tags
      .map((tag) => tag?.display_name || tag?.name)
      .filter((name) => typeof name === "string" && name.trim().length > 0);
    return renderChipStack(names, {
      gridHtml,
      emptyText: "无标签",
      baseClass: "ledger-chip",
      counterClass: "ledger-chip ledger-chip--counter",
      maxItems: Number.POSITIVE_INFINITY,
    });
  }

  function renderAccountCell(meta = {}) {
    if (!gridHtml) {
      return meta.username || "-";
    }
    const username = escapeHtml(meta.username || "-");
    const instanceName = escapeHtml(meta.instance_name || "未知实例");
    const host = escapeHtml(meta.instance_host || "-");
    return gridHtml(`
      <div>
        <strong>${username}</strong>
        <div class="small account-instance-meta">
          <i class="fas fa-database account-instance-icon me-1" aria-hidden="true"></i>${instanceName} · ${host}
        </div>
      </div>
    `);
  }

  function renderClassifications(list) {
    if (!gridHtml) {
      return list.map((item) => item?.name).filter(Boolean).join(", ") || "未分类";
    }
    const names = list
      .map((item) => item?.name)
      .filter((name) => typeof name === "string" && name.trim().length > 0);
    return renderChipStack(names, {
      gridHtml,
      emptyText: "未分类",
      baseClass: "chip-outline",
      baseModifier: "chip-outline--muted",
      counterClass: "chip-outline chip-outline--muted chip-outline--ghost",
    });
  }

  function renderDbTypeBadge(dbType) {
    const typeStr = typeof dbType === "string" ? dbType : String(dbType || "");
    const normalized = typeStr.toLowerCase();
    let meta;
    switch (normalized) {
      case "mysql":
        meta = { label: "MySQL", icon: "fa-database" };
        break;
      case "postgresql":
        meta = { label: "PostgreSQL", icon: "fa-database" };
        break;
      case "sqlserver":
        meta = { label: "SQL Server", icon: "fa-server" };
        break;
      case "oracle":
        meta = { label: "Oracle", icon: "fa-database" };
        break;
      default:
        meta = null;
        break;
    }
    const label = meta?.label || (typeStr ? typeStr.toUpperCase() : "-");
    const icon = meta?.icon || "fa-database";
    if (!gridHtml) {
      return label;
    }
    return gridHtml(
      `<span class="chip-outline chip-outline--brand" data-db-type="${escapeHtml(normalized)}"><i class="fas ${icon} me-1" aria-hidden="true"></i>${escapeHtml(label)}</span>`,
    );
  }

  function renderStatusBadge(isLocked) {
    const resolveText = global.UI?.Terms?.resolveLockStatusText;
    const text = typeof resolveText === "function" ? resolveText(isLocked) : isLocked ? "已锁定" : "正常";
    const variant = isLocked ? "danger" : "success";
    const icon = isLocked ? "fa-lock" : "fa-check";
    return renderStatusPill(text, variant, icon);
  }

  function renderDeletionBadge(isDeleted) {
    const resolveText = global.UI?.Terms?.resolveDeletionStatusText;
    const text = typeof resolveText === "function" ? resolveText(isDeleted) : isDeleted ? "已删除" : "正常";
    const variant = isDeleted ? "danger" : "muted";
    const icon = isDeleted ? "fa-trash" : "fa-check";
    return renderStatusPill(text, variant, icon);
  }

  function renderSuperuserBadge(isSuperuser) {
    const text = isSuperuser ? "是" : "否";
    const variant = isSuperuser ? "warning" : "muted";
    const icon = isSuperuser ? "fa-crown" : null;
    return renderStatusPill(text, variant, icon);
  }

  function renderStatusPill(text, variant = "muted", icon) {
    if (!gridHtml) {
      return text;
    }
    const classes = ["status-pill"];
    if (variant) {
      classes.push(`status-pill--${variant}`);
    }
    const iconHtml = icon ? `<i class="fas ${icon}" aria-hidden="true"></i>` : "";
    return gridHtml(`<span class="${classes.join(" ")}">${iconHtml}${escapeHtml(text || "")}</span>`);
  }

  function renderActions(meta) {
    if (!meta?.id) {
      return "";
    }
    if (!gridHtml) {
      return "详情";
    }
    return gridHtml(`
      <button type="button" class="btn btn-outline-primary btn-sm" data-action="view-permissions" data-account-id="${meta.id}" title="查看权限">
        <i class="fas fa-eye"></i>
      </button>
    `);
  }

  function updateTotalCount(total) {
    const element = document.getElementById("accounts-total");
    if (element) {
      element.textContent = `共 ${Number(total) || 0} 个账户`;
    }
  }

  function clearTagSelectorPreview(scope) {
    const filterContainer = document.querySelector(`[data-tag-selector-scope="${scope}"]`);
    const hiddenInput = filterContainer?.querySelector(`#${scope}-selected`);
    if (hiddenInput) {
      hiddenInput.value = "";
    }
    const chipsContainer = filterContainer?.querySelector(`#${scope}-chips`);
    if (chipsContainer) {
      chipsContainer.innerHTML = "";
    }
    const previewElement = filterContainer?.querySelector(`#${scope}-preview`);
    if (previewElement) {
      previewElement.style.display = "none";
    }
  }

  function initializeTagFilter() {
    if (!global.TagSelectorHelper) {
      console.warn("TagSelectorHelper 未加载，跳过标签筛选初始化");
      return;
    }
	    const filterContainer = document.querySelector(`[data-tag-selector-scope="${TAG_SELECTOR_SCOPE}"]`);
	    const hiddenInput = filterContainer?.querySelector(`#${TAG_SELECTOR_SCOPE}-selected`);
	    const initialValues = parseInitialTagValues(hiddenInput?.value || null);
	    global.TagSelectorHelper.setupForForm({
	      modalSelector: `#${TAG_SELECTOR_SCOPE}-modal`,
	      rootSelector: "[data-tag-selector]",
	      scope: TAG_SELECTOR_SCOPE,
	      container: filterContainer,
	      hiddenValueKey: "name",
      initialValues,
      onConfirm: () => {
        if (gridPage?.filterCard?.emit) {
          gridPage.filterCard.emit("change", { source: "account-tag-selector" });
          return;
        }
        gridPage?.applyFiltersFromForm?.({ source: "account-tag-selector" });
      },
    });
  }

  function parseInitialTagValues(raw) {
    if (!raw) {
      return [];
    }
    return raw
      .split(",")
      .map((item) => item.trim())
      .filter(Boolean);
  }

  function bindDatabaseTypeButtons() {
    const buttons = pageRoot.querySelectorAll("[data-db-type-btn]");
    buttons.forEach((button) => {
      button.addEventListener("click", (event) => {
        event.preventDefault();
        const dbType = button.getAttribute("data-db-type") || "all";
        switchDatabaseType(dbType);
      });
    });
  }

  function switchDatabaseType(dbType) {
    const normalized = typeof dbType === "string" ? dbType.trim() : "";
    const nextDbType = normalized || "all";
    const nextBasePath = resolveBasePath(nextDbType);

    const filters = Object.assign({}, gridPage?.getFilters?.() || {});
    if (nextDbType && nextDbType !== "all") {
      filters.db_type = nextDbType;
    } else {
      delete filters.db_type;
    }

    const params = global.TableQueryParams?.buildSearchParams
      ? global.TableQueryParams.buildSearchParams(filters)
      : buildSearchParamsFallback(filters);
    const query = params.toString();
    global.location.href = query ? `${nextBasePath}?${query}` : nextBasePath;
  }

  function buildSearchParamsFallback(filters) {
    const params = new URLSearchParams();
    Object.entries(filters || {}).forEach(([key, value]) => {
      if (value === undefined || value === null || value === "") {
        return;
      }
      if (Array.isArray(value)) {
        value.forEach((item) => {
          if (item !== undefined && item !== null && item !== "") {
            params.append(key, item);
          }
        });
        return;
      }
      params.append(key, value);
    });
    return params;
  }

  function bindSyncAllAccountsAction() {
    const syncButton = selectOne('[data-action="sync-all-accounts"]').first();
    if (!syncButton) {
      return;
    }
    syncButton.addEventListener("click", async (event) => {
      event?.preventDefault?.();
      const confirmDanger = global.UI?.confirmDanger;
      if (typeof confirmDanger !== "function") {
        global.toast?.error?.("确认组件未初始化");
        return;
      }

      const confirmed = await confirmDanger({
        title: "确认同步所有账户",
        message: "该操作将触发全量账户同步任务，请确认影响范围与资源消耗后继续。",
        details: [
          { label: "影响范围", value: "对全部实例执行账户同步", tone: "warning" },
          { label: "资源消耗", value: "可能占用较多数据库资源，建议低峰期执行", tone: "warning" },
        ],
        confirmText: "开始同步",
        confirmButtonClass: "btn-warning",
        resultUrl: "/history/sessions",
        resultText: "前往会话中心查看同步进度",
      });
      if (!confirmed) {
        return;
      }
      await syncAllAccounts(syncButton);
    });
  }

  async function syncAllAccounts(trigger) {
    const request =
      instanceStore?.actions?.syncAllAccounts?.() || instanceService?.syncAllAccounts?.();
    if (!request) {
      global.toast?.error?.("同步能力未初始化");
      return;
    }

    const setButtonLoading = global.UI?.setButtonLoading;
    const clearButtonLoading = global.UI?.clearButtonLoading;
    const hasLoadingApi = typeof setButtonLoading === "function" && typeof clearButtonLoading === "function";

    if (hasLoadingApi) {
      setButtonLoading(trigger, { loadingText: "同步中..." });
    } else if (trigger) {
      trigger.setAttribute("aria-busy", "true");
      trigger.setAttribute("aria-disabled", "true");
      trigger.setAttribute("disabled", "disabled");
    }

    try {
      const result = await Promise.resolve(request);
      const resolver = global.UI?.resolveAsyncActionOutcome;
      const outcome =
        typeof resolver === "function"
          ? resolver(result, {
              action: "accounts:syncAllAccounts",
              startedMessage: "批量同步任务已启动",
              failedMessage: "批量同步失败",
              unknownMessage: "批量同步未完成，请稍后在会话中心确认",
              resultUrl: "/history/sessions",
              resultText: "前往会话中心查看同步进度",
            })
          : null;

      const fallbackStatus =
        result?.success === true
          ? "started"
          : result?.success === false || result?.error === true
            ? "failed"
            : "unknown";
      const fallbackOutcome = {
        status: fallbackStatus,
        tone: fallbackStatus === "started" ? "success" : fallbackStatus === "failed" ? "error" : "warning",
        message:
          fallbackStatus === "started"
            ? result?.message || "批量同步任务已启动"
            : fallbackStatus === "failed"
              ? result?.message || "批量同步失败"
              : result?.message || "批量同步未完成，请稍后在会话中心确认",
      };

      const resolved = outcome || fallbackOutcome;
      const toast = global.toast;
      const warnOrInfo = toast?.warning || toast?.info;
      const notifier =
        resolved.tone === "success" ? toast?.success : resolved.tone === "error" ? toast?.error : warnOrInfo;
      notifier?.call(toast, resolved.message);

      if (resolved.status === "started") {
        global.setTimeout(() => {
          accountsGrid?.refresh?.();
        }, 1500);
      }
    } catch (error) {
      console.error("账户同步失败:", error);
      global.toast?.error?.("同步失败");
    } finally {
      if (hasLoadingApi) {
        clearButtonLoading(trigger);
      } else if (trigger) {
        trigger.removeAttribute("aria-busy");
        trigger.removeAttribute("aria-disabled");
        trigger.removeAttribute("disabled");
      }
    }
  }

  function handleViewPermissions(accountId, trigger) {
    const viewer = global.PermissionViewer?.viewAccountPermissions;
    if (typeof viewer !== "function") {
      console.error("PermissionViewer 未注册");
      return;
    }
	    viewer(accountId, {
	      apiUrl: `/api/v1/accounts/ledgers/${accountId}/permissions`,
	      scope: "accounts-permission",
	      trigger,
	    });
	  }
}

window.AccountsListPage = {
  mount: function () {
    mountAccountsListPage(window);
  },
};
