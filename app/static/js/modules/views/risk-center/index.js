(function (global) {
  "use strict";

  const escapeHtml = global.UI?.escapeHtml || ((value) => String(value ?? ""));
  const DB_TYPE_VISUALS = new Map([
    ["mysql", { fallbackIcon: "fa-database", tone: "primary" }],
    ["postgresql", { fallbackIcon: "fa-database", tone: "info" }],
    ["sqlserver", { fallbackIcon: "fa-server", tone: "warning" }],
    ["oracle", { fallbackIcon: "fa-circle", tone: "danger" }],
  ]);
  let dbTypeMetaMap = new Map();

  function safeParseJSON(value, fallback) {
    try {
      return JSON.parse(value);
    } catch {
      return fallback;
    }
  }

  function readFilters(form) {
    const data = new FormData(form);
    const filters = {};
    const search = String(data.get("search") || "").trim();
    const severity = String(data.get("severity") || "").trim();
    const dbType = String(data.get("db_type") || "").trim();
    const status = String(data.get("status") || "").trim();
    const tag = String(data.get("tag") || "").trim();
    if (search) filters.search = search;
    if (severity) filters.severity = severity;
    if (dbType) filters.db_type = dbType;
    if (status) filters.status = status;
    if (tag) filters.tag = tag;
    return filters;
  }

  function renderMetric(metric, fallbackDetail) {
    const safeMetric = metric || {};
    return `
      <div class="risk-signal risk-signal--${escapeHtml(safeMetric.tone || "muted")}">
        <strong>${escapeHtml(safeMetric.label || "-")}</strong>
        <span>${escapeHtml(safeMetric.detail || fallbackDetail)}</span>
      </div>
    `;
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

  function renderCard(card) {
    const links = card?.links || {};
    return `
      <article class="card risk-instance-card risk-instance-card--${escapeHtml(card?.overall_severity || "unknown")}" data-risk-card>
        <div class="risk-instance-card__body">
          <div class="risk-instance-card__masthead">
            <a class="risk-instance-card__identity" href="${escapeHtml(links.detail || "#")}" aria-label="查看 ${escapeHtml(card?.name || "实例")} 详情">
              ${renderDbTypeIcon(card)}
              <span class="risk-instance-card__copy">
                <strong class="risk-instance-card__name">${escapeHtml(card?.name || "-")}</strong>
                <span class="risk-instance-card__subtitle">${escapeHtml(card?.subtitle || "")}</span>
              </span>
            </a>
          </div>
          <div class="risk-instance-card__metrics">
            ${renderMetric(card?.backup, "备份")}
            ${renderMetric(card?.audit, "审计")}
            ${renderMetric(card?.managed, "托管")}
            ${renderMetric(card?.tasks, "任务")}
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
      refresh();
    });
    refreshButton?.addEventListener("click", refresh);
    clearButton?.addEventListener("click", () => {
      form?.reset();
      refresh();
    });
  }

  global.RiskCenterPage = { mount };
})(window);
