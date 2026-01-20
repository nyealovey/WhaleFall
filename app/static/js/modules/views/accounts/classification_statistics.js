/**
 * 挂载账户分类统计页面。
 *
 * 页面目标：
 * - 选择分类/周期/db_type/实例/窗口后，展示分类趋势（去重账号数）
 * - 选择规则后，展示该规则趋势（命中账号数）；未选规则时展示规则贡献（TopN）
 */
function mountAccountClassificationStatisticsPage(global) {
  "use strict";

  const DEFAULT_PERIODS = 7;

  const document = global.document;
  if (!document) {
    return;
  }

  const ServiceCtor = global.AccountClassificationStatisticsService;
  if (typeof ServiceCtor !== "function") {
    console.error("AccountClassificationStatisticsService 未初始化");
    return;
  }

  let service = null;
  try {
    service = new ServiceCtor();
  } catch (error) {
    console.error("初始化 AccountClassificationStatisticsService 失败:", error);
    return;
  }

  const form = document.getElementById("account-classification-statistics-filter");
  if (!form) {
    return;
  }

  const elements = {
    refresh: document.querySelector('[data-action="refresh-stats"]'),
    submit: form.querySelector('[data-filter-submit]'),
    clear: form.querySelector('[data-filter-clear]'),
    classificationId: document.getElementById("classification_id"),
    periodType: document.getElementById("period_type"),
    dbType: document.getElementById("db_type"),
    instanceId: document.getElementById("instance_id"),
    ruleId: document.getElementById("rule_id"),
    ruleSearch: document.getElementById("acs-rule-search"),
    ruleStatus: document.getElementById("acs-rule-status"),
    rulesList: document.querySelector('[data-role="rules-list"]'),
    rulesEmpty: document.querySelector('[data-role="rules-empty"]'),
    rulesWindowLabel: document.getElementById("acs-rules-window-label"),
    classificationCoverage: document.getElementById("acs-classification-coverage"),
    secondaryCoverage: document.getElementById("acs-secondary-coverage"),
    secondaryTitle: document.getElementById("acs-secondary-title"),
    classificationCanvas: document.getElementById("acs-classification-trend"),
    secondaryCanvas: document.getElementById("acs-rule-secondary"),
  };

  const state = readStateFromForm(elements);
  let rulesCache = [];
  let selectedRuleMeta = null;
  let classificationChart = null;
  let secondaryChart = null;

  bindEvents();
  refreshAll({ silent: true });

  function bindEvents() {
    form.addEventListener("submit", (event) => {
      event.preventDefault();
      applyFilters();
    });

    elements.submit?.addEventListener("click", (event) => {
      event.preventDefault();
      applyFilters();
    });

    elements.clear?.addEventListener("click", (event) => {
      event.preventDefault();
      resetFilters();
    });

    elements.refresh?.addEventListener("click", (event) => {
      event.preventDefault();
      refreshAll({ silent: false });
    });

    elements.classificationId?.addEventListener("change", () => {
      state.classificationId = normalizeInt(elements.classificationId.value);
      // 切换分类默认清空选中规则，避免跨分类 rule_id 误导
      state.ruleId = null;
      if (elements.ruleId) {
        elements.ruleId.value = "";
      }
      syncUrl();
      refreshAll({ silent: true });
    });

    elements.periodType?.addEventListener("change", () => {
      state.periodType = normalizePeriodType(elements.periodType.value);
      syncUrl();
      refreshAll({ silent: true });
    });

    elements.dbType?.addEventListener("change", () => {
      state.dbType = normalizeString(elements.dbType.value);
      state.instanceId = null;
      if (elements.instanceId) {
        elements.instanceId.value = "";
      }
      syncUrl();
      refreshInstanceOptions().then(() => refreshAll({ silent: true }));
    });

    elements.instanceId?.addEventListener("change", () => {
      state.instanceId = normalizeInt(elements.instanceId.value);
      syncUrl();
      refreshAll({ silent: true });
    });

    elements.ruleStatus?.addEventListener("change", () => {
      state.ruleStatus = normalizeRuleStatus(elements.ruleStatus.value);
      syncUrl();
      refreshRulesList({ silent: true });
    });

    elements.ruleSearch?.addEventListener("input", () => {
      applyRuleSearch();
    });
  }

  function applyFilters() {
    const next = readStateFromForm(elements);
    state.classificationId = next.classificationId;
    state.periodType = next.periodType;
    state.dbType = next.dbType;
    state.instanceId = next.instanceId;
    state.ruleId = next.ruleId;
    state.ruleStatus = next.ruleStatus;

    syncUrl();
    refreshAll({ silent: false });
  }

  function resetFilters() {
    form.reset();
    state.classificationId = null;
    state.periodType = "daily";
    state.dbType = null;
    state.instanceId = null;
    state.ruleId = null;
    state.ruleStatus = "active";

    if (elements.ruleId) {
      elements.ruleId.value = "";
    }
    if (elements.instanceId) {
      elements.instanceId.setAttribute("disabled", "disabled");
      elements.instanceId.value = "";
    }
    if (elements.ruleSearch) {
      elements.ruleSearch.value = "";
    }

    syncUrl();
    refreshAll({ silent: true });
  }

  function readStateFromForm(refs) {
    return {
      classificationId: normalizeInt(refs.classificationId?.value),
      periodType: normalizePeriodType(refs.periodType?.value),
      dbType: normalizeString(refs.dbType?.value),
      instanceId: normalizeInt(refs.instanceId?.value),
      ruleId: normalizeInt(refs.ruleId?.value),
      ruleStatus: normalizeRuleStatus(refs.ruleStatus?.value),
    };
  }

  function refreshAll({ silent }) {
    if (!state.classificationId) {
      renderEmptyState();
      return;
    }
    refreshRulesList({ silent: true })
      .then(() => refreshCharts({ silent }))
      .catch((error) => {
        console.error("刷新失败:", error);
        notify("刷新失败，请稍后再试", "error", { silent });
      });
  }

  function refreshRulesList({ silent }) {
    if (!state.classificationId) {
      rulesCache = [];
      renderRulesList([]);
      return Promise.resolve();
    }

    setRulesLoading(true);
    return service
      .fetchRulesOverview({
        classificationId: state.classificationId,
        periodType: state.periodType,
        periods: DEFAULT_PERIODS,
        dbType: state.dbType,
        instanceId: state.instanceId,
        status: state.ruleStatus,
      })
      .then((payload) => {
        const data = payload?.data ?? payload ?? {};
        const rules = Array.isArray(data.rules) ? data.rules : data.data?.rules || [];
        const windowStart = data.window_start || data.data?.window_start || null;
        const windowEnd = data.window_end || data.data?.window_end || null;
        rulesCache = Array.isArray(rules) ? rules : [];
        selectedRuleMeta = resolveSelectedRule(rulesCache, state.ruleId);
        renderRulesWindowLabel(windowStart, windowEnd);
        renderRulesList(rulesCache);
        applyRuleSearch();
      })
      .catch((error) => {
        console.error("加载规则列表失败:", error);
        rulesCache = [];
        renderRulesList([]);
        notify("规则列表加载失败", "error", { silent });
      })
      .finally(() => setRulesLoading(false));
  }

  function refreshCharts({ silent }) {
    return service
      .fetchClassificationTrend({
        classificationId: state.classificationId,
        periodType: state.periodType,
        periods: DEFAULT_PERIODS,
        dbType: state.dbType,
        instanceId: state.instanceId,
      })
      .then((payload) => {
        const trend = payload?.data?.trend ?? payload?.trend ?? [];
        renderClassificationTrend(trend);
      })
      .then(() => {
        if (state.ruleId) {
          return service
            .fetchRuleTrend({
              ruleId: state.ruleId,
              periodType: state.periodType,
              periods: DEFAULT_PERIODS,
              dbType: state.dbType,
              instanceId: state.instanceId,
            })
            .then((payload) => {
              const trend = payload?.data?.trend ?? payload?.trend ?? [];
              renderRuleTrend(trend);
            });
        }
        return service
          .fetchRuleContributions({
            classificationId: state.classificationId,
            periodType: state.periodType,
            dbType: state.dbType,
            instanceId: state.instanceId,
            limit: 10,
          })
          .then((payload) => {
            const data = payload?.data ?? payload ?? {};
            renderRuleContributions(data);
          });
      })
      .catch((error) => {
        console.error("加载趋势失败:", error);
        notify("趋势数据加载失败", "error", { silent });
      });
  }

  function refreshInstanceOptions() {
    if (!elements.instanceId) {
      return Promise.resolve();
    }
    if (!state.dbType) {
      elements.instanceId.setAttribute("disabled", "disabled");
      elements.instanceId.innerHTML = '<option value="">所有实例</option>';
      return Promise.resolve();
    }

    elements.instanceId.removeAttribute("disabled");
    elements.instanceId.innerHTML = '<option value="">加载中...</option>';

    const http = global.httpU || global.http;
    if (!http || typeof http.get !== "function") {
      return Promise.resolve();
    }

    return http
      .get("/api/v1/instances/options", {
        params: { db_type: state.dbType },
        headers: { Accept: "application/json" },
      })
      .then((payload) => {
        const items = payload?.data?.instances ?? payload?.instances ?? [];
        const options = Array.isArray(items) ? items : [];
        renderInstanceOptions(options);
      })
      .catch((error) => {
        console.error("加载实例选项失败:", error);
        elements.instanceId.innerHTML = '<option value="">所有实例</option>';
      });
  }

  function renderInstanceOptions(items) {
    if (!elements.instanceId) {
      return;
    }
    const options = ['<option value="">所有实例</option>'];
    items.forEach((item) => {
      const id = item?.id;
      const name = item?.name;
      const label = item?.display_name || name || `实例 ${id}`;
      if (!id) {
        return;
      }
      const selected = state.instanceId && String(state.instanceId) === String(id) ? " selected" : "";
      options.push(`<option value="${escapeHtml(String(id))}"${selected}>${escapeHtml(String(label))}</option>`);
    });
    elements.instanceId.innerHTML = options.join("");
  }

  function renderRulesWindowLabel(windowStart, windowEnd) {
    if (!elements.rulesWindowLabel) {
      return;
    }
    const range = windowStart && windowEnd ? `${windowStart} ~ ${windowEnd}` : "窗口累计";
    elements.rulesWindowLabel.textContent = range;
  }

  function renderRulesList(rules) {
    if (!elements.rulesList) {
      return;
    }
    if (!Array.isArray(rules) || !rules.length) {
      if (elements.rulesEmpty) {
        elements.rulesEmpty.style.display = "block";
      }
      elements.rulesList.querySelectorAll(".acs-rule-item").forEach((node) => node.remove());
      return;
    }

    if (elements.rulesEmpty) {
      elements.rulesEmpty.style.display = "none";
    }

    elements.rulesList.querySelectorAll(".acs-rule-item").forEach((node) => node.remove());

    const fragment = document.createDocumentFragment();
    rules.forEach((rule) => {
      const ruleId = rule?.rule_id;
      const name = rule?.rule_name || `规则 #${ruleId}`;
      const dbType = rule?.db_type || "";
      const version = rule?.rule_version;
      const isActive = Boolean(rule?.is_active);
      const sum = Number(rule?.window_value_sum) || 0;
      const selected = state.ruleId && String(state.ruleId) === String(ruleId);

      const button = document.createElement("button");
      button.type = "button";
      button.className = `acs-rule-item${selected ? " acs-rule-item--selected" : ""}`;
      button.dataset.ruleId = String(ruleId || "");
      button.dataset.ruleName = String(name || "");
      button.dataset.ruleDbType = String(dbType || "");
      button.dataset.ruleVersion = String(version || "");
      button.dataset.ruleActive = isActive ? "1" : "0";
      button.dataset.ruleSum = String(sum);

      button.innerHTML = `
        <div class="acs-rule-item__main">
          <div class="acs-rule-item__name">${escapeHtml(String(name))}</div>
          <div class="acs-rule-item__meta">
            ${dbType ? `<span class="chip-outline chip-outline--muted">${escapeHtml(dbType)}</span>` : ""}
            ${version ? `<span class="chip-outline chip-outline--muted">v${escapeHtml(String(version))}</span>` : ""}
            <span class="status-pill ${isActive ? "status-pill--success" : "status-pill--muted"}">
              ${isActive ? "启用" : "归档"}
            </span>
          </div>
        </div>
        <div class="acs-rule-item__count" title="窗口累计命中账号数">${formatInteger(sum)}</div>
      `;

      button.addEventListener("click", () => handleRuleSelect(rule));
      fragment.appendChild(button);
    });

    elements.rulesList.appendChild(fragment);
  }

  function handleRuleSelect(rule) {
    const nextRuleId = normalizeInt(rule?.rule_id);
    if (!nextRuleId) {
      return;
    }
    state.ruleId = nextRuleId;
    if (elements.ruleId) {
      elements.ruleId.value = String(nextRuleId);
    }
    selectedRuleMeta = resolveSelectedRule(rulesCache, nextRuleId);
    syncUrl();
    highlightSelectedRule(nextRuleId);
    refreshCharts({ silent: true });
  }

  function highlightSelectedRule(ruleId) {
    if (!elements.rulesList) {
      return;
    }
    const id = String(ruleId || "");
    elements.rulesList.querySelectorAll(".acs-rule-item").forEach((node) => {
      const selected = node.dataset.ruleId === id;
      node.classList.toggle("acs-rule-item--selected", selected);
    });
  }

  function renderClassificationTrend(trend) {
    if (!elements.classificationCanvas || !global.Chart) {
      return;
    }
    const points = Array.isArray(trend) ? trend : [];
    const labels = points.map((item) => formatBucketLabel(item?.period_start, state.periodType));
    const values = points.map((item) => Number(item?.value_avg) || 0);
    const last = points.length ? points[points.length - 1] : null;
    setCoverage(elements.classificationCoverage, last);

    const ctx = elements.classificationCanvas.getContext("2d");
    if (classificationChart) {
      classificationChart.destroy();
    }
    classificationChart = new global.Chart(ctx, buildLineChartConfig({
      title: "分类趋势",
      label: "去重账号数",
      labels,
      values,
      points,
      periodType: state.periodType,
    }));
  }

  function renderRuleTrend(trend) {
    if (!elements.secondaryCanvas || !global.Chart) {
      return;
    }
    const points = Array.isArray(trend) ? trend : [];
    const labels = points.map((item) => formatBucketLabel(item?.period_start, state.periodType));
    const values = points.map((item) => Number(item?.value_avg) || 0);
    const last = points.length ? points[points.length - 1] : null;
    setCoverage(elements.secondaryCoverage, last);

    const title = resolveRuleTitle(selectedRuleMeta, state.ruleId);
    if (elements.secondaryTitle) {
      elements.secondaryTitle.textContent = title;
    }

    const ctx = elements.secondaryCanvas.getContext("2d");
    if (secondaryChart) {
      secondaryChart.destroy();
    }
    secondaryChart = new global.Chart(ctx, buildLineChartConfig({
      title,
      label: "命中账号数",
      labels,
      values,
      points,
      periodType: state.periodType,
    }));
  }

  function renderRuleContributions(payload) {
    if (!elements.secondaryCanvas || !global.Chart) {
      return;
    }
    const contributions = payload?.contributions ?? payload?.data?.contributions ?? [];
    const items = Array.isArray(contributions) ? contributions : [];

    if (elements.secondaryTitle) {
      elements.secondaryTitle.textContent = "规则贡献（当前周期）";
    }
    setCoverageText(elements.secondaryCoverage, payload?.coverage_days, payload?.expected_days);

    const labels = items.map((item) => item?.rule_name || `规则#${item?.rule_id}`);
    const values = items.map((item) => Number(item?.value_avg) || 0);

    const ctx = elements.secondaryCanvas.getContext("2d");
    if (secondaryChart) {
      secondaryChart.destroy();
    }
    secondaryChart = new global.Chart(ctx, buildBarChartConfig({
      title: "规则贡献（当前周期）",
      labels,
      values,
      items,
      periodType: state.periodType,
    }));
  }

  function buildLineChartConfig({ label, labels, values, points, periodType }) {
    const contrast = resolveCssVar("--surface-contrast") || "#2c3e50";
    const line = resolveCssVar("--status-info") || "#3498db";
    const fill = withAlpha(line, 0.18);
    const grid = withAlpha(contrast, 0.08);

    return {
      type: "line",
      data: {
        labels,
        datasets: [
          {
            label,
            data: values,
            borderColor: line,
            backgroundColor: fill,
            fill: true,
            pointRadius: 2,
            pointHoverRadius: 4,
            tension: 0.35,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        interaction: { mode: "nearest", axis: "x", intersect: false },
        plugins: {
          legend: { display: false },
          tooltip: {
            callbacks: {
              label(context) {
                const idx = context.dataIndex;
                const meta = (Array.isArray(points) ? points.at(idx) : null) || {};
                const avg = meta?.value_avg;
                const sum = meta?.value_sum;
                const cov = meta?.coverage_days;
                const exp = meta?.expected_days;
                const prefix = periodType === "daily" ? "值" : "均值";
                const avgText = `${prefix}: ${formatNumber(avg, periodType === "daily" ? 0 : 1)}`;
                const sumText = periodType === "daily" ? "" : `，累计: ${formatInteger(sum)}`;
                const covText = `，覆盖: ${formatInteger(cov)}/${formatInteger(exp)} 天`;
                return `${avgText}${sumText}${covText}`;
              },
            },
          },
        },
        scales: {
          x: {
            grid: { display: false },
            ticks: { color: withAlpha(contrast, 0.7) },
          },
          y: {
            beginAtZero: true,
            grid: { color: grid },
            ticks: {
              color: withAlpha(contrast, 0.7),
              callback(value) {
                return formatInteger(value);
              },
            },
          },
        },
      },
    };
  }

  function buildBarChartConfig({ title, labels, values, items, periodType }) {
    const contrast = resolveCssVar("--surface-contrast") || "#2c3e50";
    const bar = resolveCssVar("--status-warning") || "#f39c12";
    const grid = withAlpha(contrast, 0.08);

    return {
      type: "bar",
      data: {
        labels,
        datasets: [
          {
            label: title,
            data: values,
            backgroundColor: withAlpha(bar, 0.45),
            borderColor: withAlpha(bar, 0.9),
            borderWidth: 1,
            borderRadius: 8,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { display: false },
          tooltip: {
            callbacks: {
              label(context) {
                const idx = context.dataIndex;
                const meta = (Array.isArray(items) ? items.at(idx) : null) || {};
                const avg = meta?.value_avg;
                const sum = meta?.value_sum;
                const cov = meta?.coverage_days;
                const exp = meta?.expected_days;
                const prefix = periodType === "daily" ? "值" : "均值";
                const avgText = `${prefix}: ${formatNumber(avg, periodType === "daily" ? 0 : 1)}`;
                const sumText = periodType === "daily" ? "" : `，累计: ${formatInteger(sum)}`;
                const covText = `，覆盖: ${formatInteger(cov)}/${formatInteger(exp)} 天`;
                return `${avgText}${sumText}${covText}`;
              },
            },
          },
        },
        scales: {
          x: { grid: { display: false }, ticks: { color: withAlpha(contrast, 0.7) } },
          y: {
            beginAtZero: true,
            grid: { color: grid },
            ticks: {
              color: withAlpha(contrast, 0.7),
              callback(value) {
                return formatInteger(value);
              },
            },
          },
        },
      },
    };
  }

  function renderEmptyState() {
    if (elements.rulesEmpty) {
      elements.rulesEmpty.style.display = "block";
    }
    elements.rulesList?.querySelectorAll(".acs-rule-item").forEach((node) => node.remove());
    setCoverageText(elements.classificationCoverage, 0, 0);
    setCoverageText(elements.secondaryCoverage, 0, 0);
    if (elements.secondaryTitle) {
      elements.secondaryTitle.textContent = "规则贡献（当前周期）";
    }
    destroyCharts();
  }

  function destroyCharts() {
    if (classificationChart) {
      classificationChart.destroy();
      classificationChart = null;
    }
    if (secondaryChart) {
      secondaryChart.destroy();
      secondaryChart = null;
    }
  }

  function setRulesLoading(loading) {
    if (!elements.rulesList) {
      return;
    }
    elements.rulesList.dataset.loading = loading ? "1" : "0";
  }

  function applyRuleSearch() {
    if (!elements.rulesList || !elements.ruleSearch) {
      return;
    }
    const keyword = normalizeString(elements.ruleSearch.value)?.toLowerCase() || "";
    const nodes = elements.rulesList.querySelectorAll(".acs-rule-item");
    nodes.forEach((node) => {
      const name = String(node.dataset.ruleName || "").toLowerCase();
      const visible = !keyword || name.includes(keyword);
      node.style.display = visible ? "" : "none";
    });
  }

  function resolveSelectedRule(rules, ruleId) {
    if (!ruleId) {
      return null;
    }
    const id = String(ruleId);
    return (rules || []).find((rule) => String(rule?.rule_id) === id) || null;
  }

  function resolveRuleTitle(ruleMeta, ruleId) {
    if (!ruleId) {
      return "规则趋势（命中账号数）";
    }
    const name = ruleMeta?.rule_name || `规则 #${ruleId}`;
    const version = ruleMeta?.rule_version ? ` v${ruleMeta.rule_version}` : "";
    return `${name}${version}（命中账号数）`;
  }

  function setCoverage(node, lastPoint) {
    if (!node) {
      return;
    }
    const cov = lastPoint?.coverage_days ?? 0;
    const exp = lastPoint?.expected_days ?? 0;
    setCoverageText(node, cov, exp);
  }

  function setCoverageText(node, cov, exp) {
    if (!node) {
      return;
    }
    node.textContent = `覆盖 ${formatInteger(cov)}/${formatInteger(exp)} 天`;
  }

  function syncUrl() {
    const params = new URLSearchParams();
    if (state.classificationId) {
      params.set("classification_id", String(state.classificationId));
    }
    params.set("period_type", state.periodType);
    if (state.dbType) {
      params.set("db_type", state.dbType);
    }
    if (state.instanceId) {
      params.set("instance_id", String(state.instanceId));
    }
    if (state.ruleId) {
      params.set("rule_id", String(state.ruleId));
    }
    if (state.ruleStatus && state.ruleStatus !== "active") {
      params.set("status", state.ruleStatus);
    }

    const next = `${global.location.pathname}${params.toString() ? `?${params.toString()}` : ""}`;
    try {
      global.history.replaceState(null, "", next);
    } catch {
      // ignore
    }
  }

  function normalizeString(value) {
    const cleaned = String(value || "").trim();
    return cleaned || null;
  }

  function normalizeInt(value) {
    const cleaned = String(value || "").trim();
    if (!cleaned) {
      return null;
    }
    const parsed = Number(cleaned);
    if (!Number.isFinite(parsed) || parsed <= 0) {
      return null;
    }
    return Math.trunc(parsed);
  }

  function normalizePeriodType(value) {
    const raw = normalizeString(value) || "daily";
    const normalized = raw.toLowerCase();
    if (["daily", "weekly", "monthly", "quarterly"].includes(normalized)) {
      return normalized;
    }
    return "daily";
  }

  function normalizeRuleStatus(value) {
    const raw = (normalizeString(value) || "active").toLowerCase();
    if (["active", "archived", "all"].includes(raw)) {
      return raw;
    }
    return "active";
  }

  function formatBucketLabel(periodStart, periodType) {
    const raw = String(periodStart || "");
    if (!raw) {
      return "-";
    }
    if (global.dayjs) {
      const parsed = global.dayjs(raw);
      if (parsed?.isValid?.()) {
        if (periodType === "daily") {
          return parsed.format("MM-DD");
        }
        if (periodType === "monthly") {
          return parsed.format("YYYY-MM");
        }
        return parsed.format("MM-DD");
      }
    }
    return raw;
  }

  function notify(message, tone, { silent } = {}) {
    if (silent) {
      return;
    }
    if (!message) {
      return;
    }
    if (global.toast) {
      if (tone === "success" && global.toast.success) {
        global.toast.success(message);
        return;
      }
      if (tone === "error" && global.toast.error) {
        global.toast.error(message);
        return;
      }
      if (global.toast.info) {
        global.toast.info(message);
        return;
      }
    }
    if (tone === "error") {
      console.error(message);
    } else {
      console.info(message);
    }
  }

  function formatInteger(value) {
    if (value === null || value === undefined) {
      return "0";
    }
    if (global.NumberFormat?.formatInteger) {
      return global.NumberFormat.formatInteger(value, { fallback: value });
    }
    const n = Number(value) || 0;
    return n.toLocaleString();
  }

  function formatNumber(value, precision) {
    const n = Number(value);
    if (!Number.isFinite(n)) {
      return "0";
    }
    const digits = Number.isFinite(Number(precision)) ? Math.max(0, Number(precision)) : 0;
    return n.toFixed(digits);
  }

  function escapeHtml(value) {
    const str = String(value ?? "");
    return str
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#039;");
  }

  function resolveCssVar(name) {
    try {
      return getComputedStyle(document.documentElement).getPropertyValue(name).trim();
    } catch {
      return "";
    }
  }

  function withAlpha(color, alpha) {
    if (!color) {
      return color;
    }
    const a = Math.max(0, Math.min(1, Number(alpha)));
    if (color.startsWith("rgb(")) {
      return color.replace("rgb(", "rgba(").replace(")", `, ${a})`);
    }
    if (color.startsWith("rgba(")) {
      return color.replace(/rgba\\((.*?),\\s*([0-9\\.]+)\\)$/, `rgba($1, ${a})`);
    }
    return color;
  }
}

window.AccountClassificationStatisticsPage = {
  mount: function () {
    mountAccountClassificationStatisticsPage(window);
  },
};
