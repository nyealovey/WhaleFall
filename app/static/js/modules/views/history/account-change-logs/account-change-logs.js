/**
 * 账户变更历史页面模块。
 *
 * 提供变更日志列表展示、筛选、统计和详情查看功能。
 */
(function (global) {
  "use strict";

  const FILTER_FORM_ID = "account-change-logs-filter-form";

  let helpers = null;
  let store = null;
  let gridPage = null;
  let GridPage = null;
  let GridPlugins = null;
  let escapeHtml = null;
  let rowMeta = null;

  let detailModal = null;
  let detailContent = null;

  function mount() {
    helpers = global.DOMHelpers;
    if (!helpers) {
      console.error("DOMHelpers 未初始化，无法加载账户变更历史页面脚本");
      return;
    }
    if (!global.gridjs || !global.GridWrapper) {
      console.error("Grid.js 或 GridWrapper 未加载");
      return;
    }
    GridPage = global.Views?.GridPage;
    GridPlugins = global.Views?.GridPlugins;
    if (!GridPage?.mount || !GridPlugins) {
      console.error("Views.GridPage 或 Views.GridPlugins 未加载");
      return;
    }
    escapeHtml = global.UI?.escapeHtml;
    rowMeta = global.GridRowMeta;
    if (typeof escapeHtml !== "function" || typeof rowMeta?.get !== "function") {
      console.error("UI helpers 或 GridRowMeta 未加载");
      return;
    }
    if (!global.AccountChangeLogsService) {
      console.error("AccountChangeLogsService 未加载");
      return;
    }
    if (typeof global.createAccountChangeLogsStore !== "function") {
      console.error("createAccountChangeLogsStore 未加载");
      return;
    }
    try {
      store = global.createAccountChangeLogsStore({
        service: new global.AccountChangeLogsService(),
        emitter: global.mitt ? global.mitt() : null,
      });
    } catch (error) {
      console.error("初始化 AccountChangeLogsStore 失败:", error);
      return;
    }

    const pageRoot = document.getElementById("account-change-logs-page-root");
    if (!pageRoot) {
      console.warn("未找到账户变更历史页面根元素");
      return;
    }

    helpers.ready(() => {
      setDefaultTimeRange();
      initializeDetailModal();
      subscribeToStoreEvents();
      initializeGridPage(pageRoot);
      store?.actions?.loadStats(gridPage?.getFilters?.() || resolveFilters()).catch((error) => {
        console.error("加载账户变更统计失败:", error);
      });
    });
  }

  function subscribeToStoreEvents() {
    if (!store?.subscribe) {
      return;
    }
    store.subscribe("accountChangeLogs:statsUpdated", (payload) => {
      const stats = payload?.stats || payload?.state?.stats || {};
      const windowHours = payload?.windowHours || payload?.state?.windowHours || 24;
      updateStats(stats, windowHours);
    });
    store.subscribe("accountChangeLogs:statsError", (payload) => {
      console.error("加载账户变更统计失败:", payload?.error);
    });
  }

  function initializeGridPage(pageRoot) {
    const container = pageRoot.querySelector("#account-change-logs-grid");
    if (!container) {
      console.warn("未找到账户变更日志列表容器");
      return;
    }

    const statsPlugin = {
      name: "accountChangeLogsStats",
      onFiltersChanged: (_ctx, { filters }) => {
        store?.actions?.loadStats(filters).catch((error) => {
          console.error("加载账户变更统计失败:", error);
        });
      },
    };

    gridPage = GridPage.mount({
      root: pageRoot,
      grid: "#account-change-logs-grid",
      filterForm: `#${FILTER_FORM_ID}`,
      gridOptions: {
        sort: false,
        columns: buildColumns(),
        server: {
          url: store?.gridUrl || "",
          headers: { "X-Requested-With": "XMLHttpRequest" },
          then: handleServerResponse,
          total: (response) => {
            const payload = response?.data || response || {};
            return payload.total || 0;
          },
        },
      },
      filters: {
        allowedKeys: ["search", "instance_id", "db_type", "change_type", "hours"],
        resolve: (values) => resolveFilters(values),
        normalize: (filters) => normalizeGridFilters(filters),
      },
      plugins: [
        statsPlugin,
        GridPlugins.filterCard({ autoSubmitOnChange: true }),
        GridPlugins.actionDelegation({
          actions: {
            "open-change-log-detail": ({ event, el }) => {
              event.preventDefault();
              openDetail(el.getAttribute("data-log-id"));
            },
          },
        }),
      ],
    });
  }

  function getRowMeta(row) {
    try {
      return rowMeta.get(row) || {};
    } catch {
      return {};
    }
  }

  function handleServerResponse(response) {
    const payload = response?.data || response || {};
    const items = Array.isArray(payload.items) ? payload.items : [];
    const normalizedItems = store?.actions?.ingestGridItems ? store.actions.ingestGridItems(items) : [];
    return normalizedItems.map((normalized) => {
      return [
        normalized.change_time || "-",
        normalized.db_type || "",
        normalized.instance_name || "-",
        normalized.username || "-",
        normalized.change_type || "-",
        normalized.message || "",
        "",
        normalized,
      ];
    });
  }

  function buildColumns() {
    const gridHtml = global.gridjs?.html;
    return [
      {
        name: "时间",
        id: "time",
        width: "170px",
        formatter: (cell, row) => {
          const meta = getRowMeta(row);
          const text = meta.change_time || cell || "-";
          return gridHtml ? gridHtml(`<span class="text-nowrap">${escapeHtml(text)}</span>`) : text;
        },
      },
      {
        name: "数据库类型",
        id: "db_type",
        width: "120px",
        formatter: (_cell, row) => renderDbTypeCell(getRowMeta(row), gridHtml),
      },
      {
        name: "实例",
        id: "instance",
        formatter: (_cell, row) => renderInstanceCell(getRowMeta(row), gridHtml),
      },
      {
        name: "账号",
        id: "username",
        width: "180px",
        formatter: (_cell, row) => renderAccountCell(getRowMeta(row), gridHtml),
      },
      {
        name: "类型",
        id: "change_type",
        width: "130px",
        formatter: (_cell, row) => renderChangeTypeCell(getRowMeta(row), gridHtml),
      },
      {
        name: "摘要",
        id: "message",
        formatter: (cell, row) => {
          const meta = getRowMeta(row);
          const text = meta.message || cell || "";
          if (!gridHtml) {
            return text;
          }
          const escaped = escapeHtml(text);
          return gridHtml(`<div class="change-log-message-cell" title="${escaped}">${escaped}</div>`);
        },
      },
      {
        name: "操作",
        id: "actions",
        width: "90px",
        sort: false,
        formatter: (_cell, row) => {
          const meta = getRowMeta(row);
          if (!meta.id) {
            return "";
          }
          return gridHtml ? renderActionButton(meta.id) : "详情";
        },
      },
      { id: "__meta__", hidden: true },
    ];
  }

  function renderDbTypeCell(meta, gridHtml) {
    const dbType = meta.db_type ? String(meta.db_type).toUpperCase() : "-";
    if (!gridHtml) {
      return dbType;
    }
    return gridHtml(`<span class="status-pill status-pill--muted">${escapeHtml(dbType)}</span>`);
  }

  function renderInstanceCell(meta, gridHtml) {
    const name = meta.instance_name ? String(meta.instance_name) : "-";
    if (!gridHtml) {
      return name;
    }
    return gridHtml(
      `<div class="d-flex flex-wrap align-items-center gap-2">
        <span class="fw-semibold">${escapeHtml(name)}</span>
      </div>`,
    );
  }

  function renderAccountCell(meta, gridHtml) {
    const username = meta.username ? String(meta.username) : "-";
    if (!gridHtml) {
      return username;
    }
    return gridHtml(
      `<div class="d-flex flex-wrap align-items-center gap-2">
        <span class="fw-semibold">${escapeHtml(username)}</span>
      </div>`,
    );
  }

  function renderChangeTypeCell(meta, gridHtml) {
    const resolver = global.ChangeHistoryRenderer?.resolveChangeTypeInfo;
    const info = typeof resolver === "function" ? resolver(meta.change_type) : { label: meta.change_type || "-", pill: "status-pill--muted" };
    if (!gridHtml) {
      return info.label;
    }
    return gridHtml(`<span class="status-pill ${escapeHtml(info.pill)}">${escapeHtml(info.label)}</span>`);
  }

  function renderActionButton(id) {
    if (!global.gridjs?.html) {
      return "详情";
    }
    return global.gridjs.html(`
      <button type="button" class="btn btn-outline-primary btn-sm" data-action="open-change-log-detail" data-log-id="${escapeHtml(String(id))}">
        <i class="fas fa-eye me-1"></i>详情
      </button>
    `);
  }

  function resolveFilters(rawValues) {
    const source = rawValues && Object.keys(rawValues || {}).length ? rawValues : collectFormValues();
    const timeRangeValue = source?.time_range || "";
    const derivedHours = getHoursFromTimeRange(timeRangeValue);
    const hoursValue = source?.hours || derivedHours;

    const filters = {
      search: sanitizeText(source?.search || source?.q),
      instance_id: sanitizeText(source?.instance_id || source?.instance),
      db_type: sanitizeText(source?.db_type),
      change_type: sanitizeText(source?.change_type),
      hours: derivedHours === null ? null : Number.isFinite(Number(hoursValue)) ? Number(hoursValue) : 24,
    };
    if (filters.hours !== null && (!filters.hours || filters.hours <= 0)) {
      filters.hours = 24;
    }
    return filters;
  }

  function normalizeGridFilters(filters) {
    const source = filters && typeof filters === "object" ? filters : {};
    const normalized = {};

    const search = sanitizeText(source.search || source.q);
    if (search) {
      normalized.search = search;
    }

    const dbType = sanitizeText(source.db_type);
    if (dbType && dbType !== "all") {
      normalized.db_type = dbType;
    }

    const instanceIdRaw = Number(source.instance_id || source.instance);
    if (Number.isFinite(instanceIdRaw) && instanceIdRaw > 0) {
      normalized.instance_id = Math.floor(instanceIdRaw);
    }

    const changeType = sanitizeText(source.change_type);
    if (changeType && changeType !== "all") {
      normalized.change_type = changeType;
    }

    if (source.hours === null || source.hours === undefined || source.hours === "") {
      return normalized;
    }
    const hoursRaw = Number(source.hours);
    normalized.hours = Number.isFinite(hoursRaw) && hoursRaw > 0 ? Math.floor(hoursRaw) : 24;
    return normalized;
  }

  function sanitizeText(value) {
    if (typeof value !== "string") {
      return "";
    }
    const trimmed = value.trim();
    return trimmed === "" ? "" : trimmed;
  }

  function collectFormValues() {
    const form = document.getElementById(FILTER_FORM_ID);
    if (!form) {
      return {};
    }
    const serializer = global.UI?.serializeForm;
    if (serializer) {
      return serializer(form);
    }
    const formData = new FormData(form);
    const result = Object.create(null);
    const search = formData.get("search");
    if (search !== null && search !== undefined) {
      result.search = search;
    }
    const dbType = formData.get("db_type");
    if (dbType !== null && dbType !== undefined) {
      result.db_type = dbType;
    }
    const instanceId = formData.get("instance_id");
    if (instanceId !== null && instanceId !== undefined) {
      result.instance_id = instanceId;
    }
    const changeType = formData.get("change_type");
    if (changeType !== null && changeType !== undefined) {
      result.change_type = changeType;
    }
    const timeRange = formData.get("time_range");
    if (timeRange !== null && timeRange !== undefined) {
      result.time_range = timeRange;
    }
    return result;
  }

  function setDefaultTimeRange() {
    const selectWrapper = helpers.selectOne("#time_range");
    if (!selectWrapper.length) {
      return;
    }
    const el = selectWrapper.first();
    if (el && !el.value) {
      el.value = "all";
    }
  }

  function getHoursFromTimeRange(timeRange) {
    const value = (timeRange || "").toString().trim();
    if (!value) {
      return 24;
    }
    if (value === "all") {
      return null;
    }
    if (value === "1h") {
      return 1;
    }
    if (value === "1d") {
      return 24;
    }
    if (value === "1w") {
      return 24 * 7;
    }
    if (value === "1m") {
      return 24 * 30;
    }
    return 24;
  }

  function updateStats(payload, windowHoursRaw) {
    if (!payload || typeof payload !== "object") {
      return;
    }
    const total = Number(payload.total_changes ?? 0) || 0;
    const success = Number(payload.success_count ?? 0) || 0;
    const failed = Number(payload.failed_count ?? 0) || 0;
    const affectedAccounts = Number(payload.affected_accounts ?? 0) || 0;
    const windowHours = Number(windowHoursRaw) > 0 ? Number(windowHoursRaw) : 24;

    const setText = (id, value) => {
      const element = document.getElementById(id);
      if (!element) {
        return;
      }
      element.textContent = String(value);
    };

    setText("totalChanges", total);
    setText("failedChanges", failed);
    setText("affectedAccounts", affectedAccounts);

    const formatPercent = global.NumberFormat.formatPercent;
    const successRatio = total > 0 ? success / total : 0;
    const failedRatio = total > 0 ? failed / total : 0;
    setText(
      "successRate",
      formatPercent(successRatio, { precision: 1, trimZero: true, inputType: "ratio", fallback: "0%" }),
    );
    setText(
      "changeLogsMetaFailedRate",
      formatPercent(failedRatio, { precision: 1, trimZero: true, inputType: "ratio", fallback: "0%" }),
    );

    const avgPerAccount = affectedAccounts > 0 ? total / affectedAccounts : 0;
    setText(
      "changeLogsMetaAvgPerAccount",
      global.NumberFormat.formatDecimal(avgPerAccount, { precision: 1, trimZero: true, fallback: "0" }),
    );

    setText("changeLogsMetaWindowHours", `${windowHours}h`);

    const successPerAccount = affectedAccounts > 0 ? success / affectedAccounts : 0;
    setText(
      "changeLogsMetaSuccessPerAccount",
      global.NumberFormat.formatDecimal(successPerAccount, { precision: 1, trimZero: true, fallback: "0" }),
    );

    const failedPerAccount = affectedAccounts > 0 ? failed / affectedAccounts : 0;
    setText(
      "changeLogsMetaFailedPerAccount",
      global.NumberFormat.formatDecimal(failedPerAccount, { precision: 1, trimZero: true, fallback: "0" }),
    );

    const changesPerHour = windowHours > 0 ? total / windowHours : 0;
    setText(
      "changeLogsMetaChangesPerHour",
      global.NumberFormat.formatDecimal(changesPerHour, { precision: 1, trimZero: true, fallback: "0" }),
    );
  }

  function initializeDetailModal() {
    const factory = global.UI?.createModal;
    if (typeof factory !== "function") {
      console.error("UI.createModal 未加载，无法初始化详情模态框");
      return;
    }
    const modalSelector = "#accountChangeLogDetailModal";
    const content = document.getElementById("accountChangeLogDetailContent");
    if (!content) {
      console.error("未找到变更详情容器");
      return;
    }
    detailContent = content;
    detailModal = factory({
      modalSelector,
      onClose: () => {
        if (detailContent) {
          detailContent.innerHTML = global.ChangeHistoryRenderer?.renderHistoryLoading
            ? global.ChangeHistoryRenderer.renderHistoryLoading()
            : "";
        }
        const metaEl = document.getElementById("accountChangeLogDetailMeta");
        if (metaEl) {
          metaEl.textContent = "加载中...";
        }
      },
    });
  }

  function openDetail(logId) {
    if (!store?.actions?.loadDetail) {
      return;
    }
    if (!detailModal || typeof detailModal.open !== "function") {
      global.toast?.error?.("详情模态框未初始化");
      return;
    }
    const id = (logId || "").toString();
    const cached = store.getCachedMeta ? store.getCachedMeta(id) : null;

    const metaEl = document.getElementById("accountChangeLogDetailMeta");
    if (metaEl) {
      const pieces = [];
      if (cached?.username) pieces.push(cached.username);
      if (cached?.db_type) pieces.push(String(cached.db_type).toUpperCase());
      metaEl.textContent = pieces.length ? pieces.join(" · ") : `变更 #${id}`;
    }

    if (detailContent && global.ChangeHistoryRenderer?.renderHistoryLoading) {
      detailContent.innerHTML = global.ChangeHistoryRenderer.renderHistoryLoading();
    }

    store.actions
      .loadDetail(id)
      .then((log) => {
        if (!detailContent) {
          return;
        }
        if (!log) {
          detailContent.innerHTML = `<div class="change-history-modal__empty"><span class="status-pill status-pill--danger">获取详情失败</span></div>`;
          detailModal.open({ logId: id });
          return;
        }
        const renderer = global.ChangeHistoryRenderer?.renderChangeHistoryCard;
        if (typeof renderer !== "function") {
          detailContent.innerHTML = `<pre class="bg-light p-3 rounded">${escapeHtml(JSON.stringify(log, null, 2))}</pre>`;
          detailModal.open({ logId: id });
          return;
        }
        detailContent.innerHTML = renderer(log, { collapsible: false, open: true });
        detailModal.open({ logId: id });
      })
      .catch((error) => {
        console.error("获取变更详情失败:", error);
        if (!detailContent) {
          return;
        }
        detailContent.innerHTML = `<div class="change-history-modal__empty"><span class="status-pill status-pill--danger">${escapeHtml(error?.message || "获取详情失败")}</span></div>`;
        detailModal.open({ logId: id });
      });
  }

  global.AccountChangeLogsPage = {
    mount,
  };
})(window);
