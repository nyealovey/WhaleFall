(function (global) {
  "use strict";

  const escapeHtml = global.UI?.escapeHtml || ((value) => String(value ?? ""));
  const FILTER_DEBOUNCE_MS = 300;
  const LIVE_TEXT_FILTER_NAMES = new Set(["search", "tag"]);
  const SELECT_FILTER_NAMES = new Set(["severity", "db_type", "status"]);
  const DB_TYPE_VISUALS = new Map([
    ["mysql", { fallbackIcon: "fa-database", tone: "primary" }],
    ["postgresql", { fallbackIcon: "fa-database", tone: "info" }],
    ["sqlserver", { fallbackIcon: "fa-server", tone: "warning" }],
    ["oracle", { fallbackIcon: "fa-circle", tone: "danger" }],
  ]);
  const SEVERITY_VISUALS = new Map([
    ["critical", { label: "严重", icon: "fa-triangle-exclamation" }],
    ["warning", { label: "警告", icon: "fa-circle-exclamation" }],
    ["ok", { label: "正常", icon: "fa-circle-check" }],
    ["info", { label: "关注", icon: "fa-circle-info" }],
    ["unknown", { label: "未知", icon: "fa-circle-question" }],
  ]);
  const RISK_SIGNALS = [
    { key: "backup", label: "备份", icon: "fa-hard-drive" },
    { key: "audit", label: "审计", icon: "fa-shield-halved" },
    { key: "managed", label: "托管", icon: "fa-sitemap" },
    { key: "tasks", label: "任务", icon: "fa-list-check" },
  ];
  let dbTypeMetaMap = new Map();

  function safeParseJSON(value, fallback) {
    try {
      return JSON.parse(value);
    } catch {
      return fallback;
    }
  }

  function debounce(fn, wait) {
    let timerId = null;
    function debounced(...args) {
      if (timerId !== null) {
        global.clearTimeout(timerId);
      }
      timerId = global.setTimeout(() => {
        timerId = null;
        fn(...args);
      }, wait);
    }
    debounced.cancel = () => {
      if (timerId !== null) {
        global.clearTimeout(timerId);
        timerId = null;
      }
    };
    return debounced;
  }

  function getFilterFieldName(event) {
    const target = event?.target;
    return typeof target?.name === "string" ? target.name : "";
  }

  function isLiveTextFilter(event) {
    return LIVE_TEXT_FILTER_NAMES.has(getFilterFieldName(event));
  }

  function isSelectFilter(event) {
    return SELECT_FILTER_NAMES.has(getFilterFieldName(event));
  }

  function readFilters(form) {
    const data = new FormData(form);
    const filters = {};
    const search = String(data.get("search") || "").trim();
    const severity = String(data.get("severity") || "").trim();
    const dbType = String(data.get("db_type") || "").trim();
    const status = String(data.get("status") || "").trim();
    const tag = String(data.get("tag") || "").trim();
    filters.limit = 0;
    if (search) filters.search = search;
    if (severity) filters.severity = severity;
    if (dbType) filters.db_type = dbType;
    if (status) filters.status = status;
    if (tag) filters.tag = tag;
    return filters;
  }

  function renderDbTypeIcon(card) {
    const typeStr = String(card?.db_type || "").trim();
    const normalizedType = typeStr.toLowerCase();
    const meta = dbTypeMetaMap.get(normalizedType) || dbTypeMetaMap.get(typeStr) || {};
    const visual = DB_TYPE_VISUALS.get(normalizedType) || {};
    const title = meta.display_name || typeStr.toUpperCase() || "数据库";
    const tone = visual.tone || meta.color || "muted";
    const assetUrl = meta.asset_url || "";
    const glyphHtml = assetUrl
      ? `<img class="risk-instance-card__db-type-asset" src="${escapeHtml(assetUrl)}" alt="" aria-hidden="true">`
      : `<i class="fas ${escapeHtml(visual.fallbackIcon || meta.icon || "fa-database")}" aria-hidden="true"></i>`;
    return `
      <span class="risk-instance-card__db-type risk-instance-card__db-type--${escapeHtml(tone)}"
            title="${escapeHtml(title)}"
            aria-label="数据库类型 ${escapeHtml(title)}"
            role="img">
        ${glyphHtml}
      </span>
    `;
  }

  function renderSeverityIcon(card) {
    const severity = String(card?.overall_severity || "unknown");
    const visual = SEVERITY_VISUALS.get(severity) || SEVERITY_VISUALS.get("unknown");
    return `
      <span class="risk-instance-card__severity risk-instance-card__severity--${escapeHtml(severity)}"
            title="风险等级：${escapeHtml(visual.label)}"
            aria-label="风险等级 ${escapeHtml(visual.label)}"
            role="img">
        <i class="fas ${escapeHtml(visual.icon)}" aria-hidden="true"></i>
      </span>
    `;
  }

  function renderSignal(metric, signal) {
    const safeMetric = metric || {};
    return `
      <span class="risk-signal risk-signal--${escapeHtml(safeMetric.tone || "muted")}"
            data-risk-signal="${escapeHtml(signal.key)}"
            title="${escapeHtml(signal.label)}：${escapeHtml(safeMetric.label || "-")}"
            aria-label="${escapeHtml(signal.label)}：${escapeHtml(safeMetric.label || "-")}"
            role="img">
        <i class="fas ${escapeHtml(signal.icon)} risk-signal__icon" aria-hidden="true"></i>
      </span>
    `;
  }

  function renderCard(card) {
    const links = card?.links || {};
    const subtitle = card?.subtitle || card?.name || "实例";
    return `
      <article class="card risk-instance-card risk-instance-card--${escapeHtml(card?.overall_severity || "unknown")}" data-risk-card>
        <div class="risk-instance-card__body">
          <div class="risk-instance-card__masthead">
            <a class="risk-instance-card__identity"
               href="${escapeHtml(links.detail || "#")}"
               title="${escapeHtml(subtitle)}"
               aria-label="查看 ${escapeHtml(card?.name || "实例")} 详情">
              ${renderDbTypeIcon(card)}
              <strong class="risk-instance-card__name">${escapeHtml(card?.name || "-")}</strong>
            </a>
            ${renderSeverityIcon(card)}
          </div>
          <div class="risk-instance-card__signals" aria-label="实例核心风险指标">
            ${RISK_SIGNALS.map((signal) => renderSignal(card?.[signal.key], signal)).join("")}
          </div>
        </div>
      </article>
    `;
  }

  function updateSummary(root, summary) {
    const counts = summary?.severity_counts || {};
    const values = {
      critical: counts.critical || 0,
      warning: counts.warning || 0,
      ok: counts.ok || 0,
      total: summary?.total_instances || 0,
    };
    Object.entries(values).forEach(([key, value]) => {
      const node = root.querySelector(`[data-stat-key="${key}"] .wf-metric-card__value`);
      if (node) {
        node.textContent = String(value);
      }
    });
  }

  function mount() {
    const root = document.querySelector("[data-risk-center-root]");
    if (!root || !global.RiskCenterService || typeof global.createRiskCenterStore !== "function") {
      return;
    }
    dbTypeMetaMap = new Map(Object.entries(safeParseJSON(root.dataset.dbTypeMap || "{}", {})));
    const form = root.querySelector("[data-risk-filter-form]");
    const grid = root.querySelector("[data-risk-card-grid]");
    const empty = root.querySelector("[data-risk-empty]");
    const feedback = root.querySelector("[data-risk-feedback]");
    const refreshButton = document.querySelector('[data-action="refresh-risk-center"]');
    const clearButton = root.querySelector('[data-action="clear-risk-filters"]');
    const store = global.createRiskCenterStore({ service: new global.RiskCenterService() });

    function setFeedback(message) {
      if (!feedback) return;
      feedback.textContent = message || "";
      feedback.classList.toggle("d-none", !message);
    }

    function refresh() {
      if (!form || !grid) return Promise.resolve();
      setFeedback("");
      return store.actions.refresh(readFilters(form)).catch((error) => {
        setFeedback(error?.message || "加载风险中心失败");
      });
    }
    const debouncedRefresh = debounce(refresh, FILTER_DEBOUNCE_MS);

    store.subscribe("risk-center:loading", (payload) => {
      if (refreshButton) {
        refreshButton.disabled = Boolean(payload?.loading);
      }
    });
    store.subscribe("risk-center:updated", (payload) => {
      const cards = Array.isArray(payload?.cards?.items) ? payload.cards.items : [];
      updateSummary(root, payload?.summary || {});
      if (grid) {
        grid.innerHTML = cards.map(renderCard).join("");
      }
      if (empty) {
        empty.classList.toggle("d-none", cards.length > 0);
      }
    });

    form?.addEventListener("submit", (event) => {
      event.preventDefault();
      debouncedRefresh.cancel();
      refresh();
    });
    form?.addEventListener("input", (event) => {
      if (isLiveTextFilter(event)) {
        debouncedRefresh();
      }
    });
    form?.addEventListener("change", (event) => {
      if (isSelectFilter(event)) {
        debouncedRefresh.cancel();
        refresh();
      }
    });
    refreshButton?.addEventListener("click", refresh);
    clearButton?.addEventListener("click", () => {
      form?.reset();
      debouncedRefresh.cancel();
      refresh();
    });
  }

  global.RiskCenterPage = { mount };
})(window);
