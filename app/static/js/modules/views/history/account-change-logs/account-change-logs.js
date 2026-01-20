/**
 * 账户变更历史页面模块。
 *
 * 提供变更日志列表展示、筛选、统计和详情查看功能。
 */
(function (global) {
  "use strict";

  const FILTER_FORM_ID = "account-change-logs-filter-form";

  let helpers = null;
  let service = null;
  let gridPage = null;
  let GridPage = null;
  let GridPlugins = null;
  let escapeHtml = null;
  let rowMeta = null;
  const cache = new Map();

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
    GridPage = global.Views?.GridPage || null;
    GridPlugins = global.Views?.GridPlugins || null;
    if (!GridPage?.mount || !GridPlugins) {
      console.error("Views.GridPage 或 Views.GridPlugins 未加载");
      return;
    }
    escapeHtml = global.UI?.escapeHtml || null;
    rowMeta = global.GridRowMeta || null;
    if (typeof escapeHtml !== "function" || typeof rowMeta?.get !== "function") {
      console.error("UI helpers 或 GridRowMeta 未加载");
      return;
    }
    if (!global.AccountChangeLogsService) {
      console.error("AccountChangeLogsService 未加载");
      return;
    }
    service = new global.AccountChangeLogsService();

    const pageRoot = document.getElementById("account-change-logs-page-root");
    if (!pageRoot) {
      console.warn("未找到账户变更历史页面根元素");
      return;
    }

    helpers.ready(() => {
      setDefaultTimeRange();
      initializeDetailModal();
      initializeGridPage(pageRoot);
      refreshStats(gridPage?.getFilters?.() || resolveFilters());
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
        refreshStats(filters);
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
          url: service.getGridUrl(),
          headers: { "X-Requested-With": "XMLHttpRequest" },
          then: handleServerResponse,
          total: (response) => {
            const payload = response?.data || response || {};
            return payload.total || 0;
          },
        },
      },
      filters: {
        allowedKeys: ["search", "instance_id", "db_type", "change_type", "status", "hours"],
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
    cache.clear();
    return items.map((item) => {
      const normalized = normalizeItem(item);
      cache.set(String(normalized.id), normalized);
      return [
        normalized.change_time || "-",
        normalized.instance_name || "-",
        normalized.username || "-",
        normalized.change_type || "-",
        normalized.status || "-",
        normalized.message || "",
        "",
        normalized,
      ];
    });
  }

  function normalizeItem(item) {
    return {
      id: item?.id,
      account_id: item?.account_id ?? null,
      instance_id: item?.instance_id ?? null,
      instance_name: item?.instance_name || "",
      db_type: item?.db_type || "",
      username: item?.username || "",
      change_type: item?.change_type || "",
      status: item?.status || "",
      message: item?.message || "",
      change_time: item?.change_time || "",
      session_id: item?.session_id ?? null,
      privilege_diff_count: item?.privilege_diff_count ?? 0,
      other_diff_count: item?.other_diff_count ?? 0,
    };
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
        name: "状态",
        id: "status",
        width: "110px",
        formatter: (_cell, row) => renderStatusCell(getRowMeta(row), gridHtml),
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

  function renderInstanceCell(meta, gridHtml) {
    const name = meta.instance_name ? String(meta.instance_name) : "-";
    const dbType = meta.db_type ? String(meta.db_type).toUpperCase() : "";
    if (!gridHtml) {
      return dbType ? `${name} (${dbType})` : name;
    }
    const dbChip = dbType ? `<span class="status-pill status-pill--muted">${escapeHtml(dbType)}</span>` : "";
    return gridHtml(
      `<div class="d-flex flex-wrap align-items-center gap-2">
        <span class="fw-semibold">${escapeHtml(name)}</span>
        ${dbChip}
      </div>`,
    );
  }

  function renderAccountCell(meta, gridHtml) {
    const username = meta.username ? String(meta.username) : "-";
    const accountId = meta.account_id ? `#${meta.account_id}` : "";
    if (!gridHtml) {
      return accountId ? `${username} ${accountId}` : username;
    }
    const idChip = accountId ? `<span class="status-pill status-pill--muted">${escapeHtml(accountId)}</span>` : "";
    return gridHtml(
      `<div class="d-flex flex-wrap align-items-center gap-2">
        <span class="fw-semibold">${escapeHtml(username)}</span>
        ${idChip}
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

  function renderStatusCell(meta, gridHtml) {
    const resolver = global.ChangeHistoryRenderer?.resolveStatusInfo;
    const info = typeof resolver === "function" ? resolver(meta.status) : { label: meta.status || "-", pill: "status-pill--muted" };
    if (!gridHtml) {
      return info.label;
    }
    return gridHtml(`<span class="status-pill ${escapeHtml(info.pill)}">${escapeHtml(info.label)}</span>`);
  }

  function renderActionButton(id) {
    return `
      <button type="button" class="btn btn-outline-primary btn-sm" data-action="open-change-log-detail" data-log-id="${escapeHtml(String(id))}">
        <i class="fas fa-eye me-1"></i>详情
      </button>
    `;
  }

  function resolveFilters(rawValues) {
    const source = rawValues && Object.keys(rawValues || {}).length ? rawValues : collectFormValues();
    const timeRangeValue = source?.time_range || "";
    const hoursValue = source?.hours || getHoursFromTimeRange(timeRangeValue);

    const filters = {
      search: sanitizeText(source?.search || source?.q),
      instance_id: sanitizeText(source?.instance_id || source?.instance),
      db_type: sanitizeText(source?.db_type),
      change_type: sanitizeText(source?.change_type),
      status: sanitizeText(source?.status),
      hours: Number.isFinite(Number(hoursValue)) ? Number(hoursValue) : 24,
    };
    if (!filters.hours || filters.hours <= 0) {
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

    const status = sanitizeText(source.status);
    if (status && status !== "all") {
      normalized.status = status;
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
    const status = formData.get("status");
    if (status !== null && status !== undefined) {
      result.status = status;
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
      el.value = "1d";
    }
  }

  function getHoursFromTimeRange(timeRange) {
    const value = (timeRange || "").toString().trim();
    if (!value) {
      return 24;
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

  function refreshStats(filters) {
    if (!service) {
      return;
    }
    const hours = filters?.hours;
    service
      .fetchStats({ hours })
      .then((resp) => {
        const payload = resp?.data || resp || {};
        if (resp && resp.success === false) {
          return;
        }
        updateStats(payload);
      })
      .catch((error) => {
        console.error("加载账户变更统计失败:", error);
      });
  }

  function updateStats(payload) {
    if (!payload || typeof payload !== "object") {
      return;
    }
    const totalEl = document.getElementById("totalChanges");
    const successEl = document.getElementById("successChanges");
    const failedEl = document.getElementById("failedChanges");
    const accountsEl = document.getElementById("affectedAccounts");

    if (totalEl) totalEl.textContent = String(payload.total_changes ?? 0);
    if (successEl) successEl.textContent = String(payload.success_count ?? 0);
    if (failedEl) failedEl.textContent = String(payload.failed_count ?? 0);
    if (accountsEl) accountsEl.textContent = String(payload.affected_accounts ?? 0);
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
    if (!service) {
      return;
    }
    if (!detailModal || typeof detailModal.open !== "function") {
      global.toast?.error?.("详情模态框未初始化");
      return;
    }
    const id = (logId || "").toString();
    const cached = cache.get(id) || null;

    const metaEl = document.getElementById("accountChangeLogDetailMeta");
    if (metaEl) {
      const pieces = [];
      if (cached?.username) pieces.push(cached.username);
      if (cached?.db_type) pieces.push(String(cached.db_type).toUpperCase());
      if (cached?.account_id) pieces.push(`#${cached.account_id}`);
      metaEl.textContent = pieces.length ? pieces.join(" · ") : `变更 #${id}`;
    }

    if (detailContent && global.ChangeHistoryRenderer?.renderHistoryLoading) {
      detailContent.innerHTML = global.ChangeHistoryRenderer.renderHistoryLoading();
    }

    service
      .fetchDetail(id)
      .then((resp) => {
        if (!detailContent) {
          return;
        }
        if (!resp || resp.success === false) {
          const message = resp?.message || resp?.error || "获取详情失败";
          detailContent.innerHTML = `<div class="change-history-modal__empty"><span class="status-pill status-pill--danger">${escapeHtml(message)}</span></div>`;
          detailModal.open({ logId: id });
          return;
        }
        const payload = resp?.data || resp || {};
        const log = payload?.log || null;
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
