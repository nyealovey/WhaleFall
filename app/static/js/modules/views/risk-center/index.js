(function (global) {
  "use strict";

  const escapeHtml = global.UI?.escapeHtml || ((value) => String(value ?? ""));

  function severityText(severity) {
    if (severity === "critical") return "严重";
    if (severity === "warning") return "警告";
    if (severity === "info") return "提示";
    if (severity === "ok") return "正常";
    return "未知";
  }

  function pillClass(severity) {
    if (severity === "critical") return "status-pill--danger";
    if (severity === "warning") return "status-pill--warning";
    if (severity === "info") return "status-pill--info";
    if (severity === "ok") return "status-pill--success";
    return "status-pill--muted";
  }

  function iconForTone(tone) {
    if (tone === "danger") return "times";
    if (tone === "warning") return "exclamation";
    if (tone === "muted") return "question";
    return "check";
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

  function renderFlags(flags) {
    if (!Array.isArray(flags) || flags.length === 0) {
      return '<span class="status-pill status-pill--success">当前无风险</span>';
    }
    return flags
      .slice(0, 3)
      .map((risk) => `<span class="status-pill ${pillClass(risk?.severity)}">${escapeHtml(risk?.label || "风险")}</span>`)
      .join("");
  }

  function renderCard(card) {
    const links = card?.links || {};
    const statusBand = card?.status_band || {};
    return `
      <article class="risk-instance-card risk-instance-card--${escapeHtml(card?.overall_severity || "unknown")}" data-risk-card>
        <div class="risk-instance-card__body">
          <div class="risk-instance-card__masthead">
            <a class="risk-instance-card__identity" href="${escapeHtml(links.detail || "#")}" aria-label="查看 ${escapeHtml(card?.name || "实例")} 详情">
              <span class="risk-instance-card__icon"><i class="fas fa-database"></i></span>
              <span class="risk-instance-card__copy">
                <strong class="risk-instance-card__name">${escapeHtml(card?.name || "-")}</strong>
                <span class="risk-instance-card__subtitle">${escapeHtml(card?.subtitle || "")}</span>
              </span>
            </a>
            <div class="dropdown">
              <button class="btn btn-sm btn-icon" type="button" data-bs-toggle="dropdown" aria-expanded="false" aria-label="打开实例操作">
                <i class="fas fa-ellipsis-v"></i>
              </button>
              <ul class="dropdown-menu dropdown-menu-end">
                <li><a class="dropdown-item" href="${escapeHtml(links.detail || "#")}"><i class="fas fa-server me-2"></i>实例详情</a></li>
                <li><a class="dropdown-item" href="${escapeHtml(links.backup || "#")}"><i class="fas fa-shield-alt me-2"></i>备份信息</a></li>
                <li><a class="dropdown-item" href="${escapeHtml(links.capacity || "#")}"><i class="fas fa-chart-line me-2"></i>容量趋势</a></li>
                <li><a class="dropdown-item" href="${escapeHtml(links.accounts || "#")}"><i class="fas fa-users me-2"></i>账户台账</a></li>
                <li><a class="dropdown-item" href="${escapeHtml(links.tasks || "#")}"><i class="fas fa-tasks me-2"></i>任务记录</a></li>
              </ul>
            </div>
          </div>
          <div class="risk-instance-card__metrics">
            ${renderMetric(card?.backup, "Backup")}
            ${renderMetric(card?.capacity, "Capacity")}
            ${renderMetric(card?.access, "Access")}
          </div>
          <div class="risk-instance-card__flags">${renderFlags(card?.risk_flags)}</div>
        </div>
        <a class="risk-instance-card__status risk-instance-card__status--${escapeHtml(statusBand.tone || "muted")}" href="${escapeHtml(links.detail || "#")}">
          <span class="risk-instance-card__status-icon"><i class="fas fa-${iconForTone(statusBand.tone)}"></i></span>
          <span>${escapeHtml(statusBand.label || `${severityText(card?.overall_severity)} · 缺少状态`)}</span>
        </a>
      </article>
    `;
  }

  function updateSummary(root, summary) {
    const counts = summary?.severity_counts || {};
    const values = {
      critical: counts.critical || 0,
      warning: counts.warning || 0,
      ok: counts.ok || 0,
      unknown: counts.unknown || 0,
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
