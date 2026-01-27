(function (global) {
  "use strict";

  const escapeHtml = global.UI?.escapeHtml;
  if (typeof escapeHtml !== "function") {
    throw new Error("ChangeHistoryRenderer: UI.escapeHtml 未初始化");
  }

  function normalizeText(value) {
    if (value === undefined || value === null) {
      return "";
    }
    return String(value).trim();
  }

  function resolveChangeTypeInfo(rawType) {
    const type = normalizeText(rawType).toLowerCase();
    switch (type) {
      case "add":
        return { label: "新增", icon: "fas fa-user-plus", pill: "status-pill--success" };
      case "modify_privilege":
        return { label: "权限变更", icon: "fas fa-key", pill: "status-pill--info" };
      case "modify_other":
        return { label: "属性变更", icon: "fas fa-sliders-h", pill: "status-pill--info" };
      case "delete":
        return { label: "删除", icon: "fas fa-user-times", pill: "status-pill--danger" };
      case "none":
        return { label: "无变更", icon: "fas fa-minus-circle", pill: "status-pill--muted" };
      default:
        return { label: rawType ? normalizeText(rawType) : "变更", icon: "fas fa-history", pill: "status-pill--muted" };
    }
  }

  function resolveStatusInfo(rawStatus) {
    const status = normalizeText(rawStatus).toLowerCase();
    if (!status) {
      return { label: "未知", pill: "status-pill--muted", icon: "fas fa-question-circle" };
    }
    if (status === "success" || status === "ok") {
      return { label: "成功", pill: "status-pill--success", icon: "fas fa-check-circle" };
    }
    if (status === "failed" || status === "error") {
      return { label: "失败", pill: "status-pill--danger", icon: "fas fa-times-circle" };
    }
    return { label: status, pill: "status-pill--muted", icon: "fas fa-info-circle" };
  }

  function renderPill(text, variant = "status-pill--muted", icon) {
    const iconHtml = icon ? `<i class="${icon} me-1"></i>` : "";
    return `<span class="status-pill ${variant}">${iconHtml}${escapeHtml(text)}</span>`;
  }

  function renderChip(text, variant = "chip-outline--muted", icon) {
    const iconHtml = icon ? `<i class="${icon} me-2"></i>` : "";
    return `<span class="chip-outline ${variant}">${iconHtml}${escapeHtml(text)}</span>`;
  }

  function renderLedgerChips(values, emptyLabel) {
    if (!values || (Array.isArray(values) && values.length === 0)) {
      return `<span class="ledger-chip ledger-chip--muted">${escapeHtml(emptyLabel)}</span>`;
    }
    const list = Array.isArray(values) ? values : [values];
    const chips = list
      .filter((value) => value !== undefined && value !== null && value !== "")
      .map((value) => `<span class="ledger-chip">${escapeHtml(value)}</span>`)
      .join("");
    return chips || `<span class="ledger-chip ledger-chip--muted">${escapeHtml(emptyLabel)}</span>`;
  }

  function resolvePrivilegeActionVariant(action) {
    const value = normalizeText(action).toUpperCase();
    switch (value) {
      case "GRANT":
        return { text: "授权", variant: "status-pill--success" };
      case "REVOKE":
        return { text: "撤销", variant: "status-pill--danger" };
      case "ALTER":
        return { text: "更新", variant: "status-pill--info" };
      default:
        return { text: "变更", variant: "status-pill--muted" };
    }
  }

  function renderPrivilegeDiffEntries(diffEntries) {
    if (!Array.isArray(diffEntries) || diffEntries.length === 0) {
      return "";
    }

    const items = diffEntries.map((entry) => {
      const actionInfo = resolvePrivilegeActionVariant(entry?.action);
      const target = entry?.object || entry?.label || entry?.field || "权限";
      return `
        <li class="change-history-permission">
          <span class="status-pill ${actionInfo.variant}">${actionInfo.text}</span>
          <div class="change-history-permission__body">
            ${renderChip(target, "chip-outline--muted")}
            <div class="ledger-chip-stack">
              ${renderLedgerChips(entry?.permissions, "无权限")}
            </div>
          </div>
        </li>
      `;
    });

    return `
      <section class="change-history-section">
        <div class="change-history-section__title">
          ${renderChip("权限变更", "chip-outline--brand", "fas fa-key")}
          ${renderPill(`${diffEntries.length} 项`, "status-pill--muted")}
        </div>
        <ul class="change-history-permission-list">
          ${items.join("")}
        </ul>
      </section>
    `;
  }

  function parseKeyValuePairs(text) {
    const source = normalizeText(text);
    if (!source || !source.includes(":")) {
      return null;
    }
    const result = new Map();
    source.split(";").forEach((raw) => {
      const segment = raw.trim();
      if (!segment) {
        return;
      }
      const idx = segment.indexOf(":");
      if (idx <= 0) {
        return;
      }
      const key = segment.slice(0, idx).trim();
      if (!key) {
        return;
      }
      result.set(key, segment.slice(idx + 1).trim());
    });
    return result.size ? result : null;
  }

  function buildTypeSpecificDiffRows(entry) {
    if (!entry || entry.field !== "type_specific") {
      return null;
    }
    const beforeMap = parseKeyValuePairs(entry.before);
    const afterMap = parseKeyValuePairs(entry.after);
    if (!beforeMap && !afterMap) {
      return null;
    }
    const baseLabel = entry?.label || entry?.field || "数据库特性";
    const keySet = new Set();
    if (beforeMap) {
      Array.from(beforeMap.keys()).forEach((key) => keySet.add(key));
    }
    if (afterMap) {
      Array.from(afterMap.keys()).forEach((key) => keySet.add(key));
    }
    const keys = Array.from(keySet).sort();
    const rows = keys.map((key) => {
      const before = beforeMap?.get(key) || "";
      const after = afterMap?.get(key) || "";
      if (before === after) {
        return null;
      }
      return {
        label: `${baseLabel} · ${key}`,
        before,
        after,
        description: "",
      };
    }).filter(Boolean);
    return rows.length ? rows : null;
  }

  function computeOtherDisplayCount(diffEntries) {
    if (!Array.isArray(diffEntries) || diffEntries.length === 0) {
      return 0;
    }
    let count = 0;
    diffEntries.forEach((entry) => {
      const rows = buildTypeSpecificDiffRows(entry);
      count += rows ? rows.length : 1;
    });
    return count;
  }

  function renderOtherDiffRow(entry) {
    const label = entry?.label || entry?.field || "其他字段";
    const before = entry?.before ? `<span class="ledger-chip ledger-chip--muted">${escapeHtml(entry.before)}</span>` : '<span class="ledger-chip ledger-chip--muted">未设置</span>';
    const after = entry?.after ? `<span class="ledger-chip">${escapeHtml(entry.after)}</span>` : '<span class="ledger-chip">未设置</span>';
    const desc = entry?.description ? `<p class="change-history-stack-desc">${escapeHtml(entry.description)}</p>` : "";

    return `
      <div class="change-history-stack-row">
        ${renderChip(label, "chip-outline--muted")}
        <div class="change-history-stack-value">
          ${renderPill("原", "status-pill--muted")}
          ${before}
          ${renderPill("现", "status-pill--info")}
          ${after}
        </div>
        ${desc}
      </div>
    `;
  }

  function renderOtherDiffEntries(diffEntries) {
    if (!Array.isArray(diffEntries) || diffEntries.length === 0) {
      return "";
    }

    const rows = [];
    diffEntries.forEach((entry) => {
      const typeSpecificRows = buildTypeSpecificDiffRows(entry);
      if (typeSpecificRows) {
        typeSpecificRows.forEach((row) => {
          rows.push(renderOtherDiffRow(row));
        });
        return;
      }
      rows.push(renderOtherDiffRow(entry));
    });
    const displayCount = computeOtherDisplayCount(diffEntries);

    return `
      <section class="change-history-section">
        <div class="change-history-section__title">
          ${renderChip("其他属性", "chip-outline--brand", "fas fa-sliders-h")}
          ${renderPill(`${displayCount} 项`, "status-pill--muted")}
        </div>
        <div class="change-history-stack">
          ${rows.join("")}
        </div>
      </section>
    `;
  }

  function renderHistoryLoading() {
    return `
      <div class="change-history-modal__loading text-center py-4">
        <div class="spinner-border text-primary" role="status">
          <span class="visually-hidden">加载中...</span>
        </div>
        <p class="mt-2 text-muted">正在加载变更记录...</p>
      </div>
    `;
  }

  function buildSummaryPills(change) {
    const changeType = normalizeText(change?.change_type).toLowerCase();
    if (changeType === "add") {
      return "";
    }
    const privilegeCount = Array.isArray(change?.privilege_diff) ? change.privilege_diff.length : 0;
    const otherCount = computeOtherDisplayCount(change?.other_diff);
    const pills = [];
    if (privilegeCount) {
      pills.push(renderPill(`权限 ${privilegeCount} 项`, "status-pill--muted", "fas fa-key"));
    }
    if (otherCount) {
      pills.push(renderPill(`属性 ${otherCount} 项`, "status-pill--muted", "fas fa-sliders-h"));
    }
    return pills.join("");
  }

  function renderChangeHistoryCard(change, options = {}) {
    const { collapsible = true, open = false } = options || {};
    const typeInfo = resolveChangeTypeInfo(change?.change_type);
    const statusInfo = resolveStatusInfo(change?.status);
    const timeText = normalizeText(change?.change_time) || "未知时间";
    const changeType = normalizeText(change?.change_type).toLowerCase();
    const isAdd = changeType === "add";
    const rawStatus = normalizeText(change?.status).toLowerCase();
    const isSuccess = rawStatus === "success" || rawStatus === "ok";
    const privilegeCount = Array.isArray(change?.privilege_diff) ? change.privilege_diff.length : 0;
    const otherCount = computeOtherDisplayCount(change?.other_diff);
    const hasDiffs = Boolean(privilegeCount || otherCount);
    const messageText = isAdd ? "新增账户" : normalizeText(change?.message);
    const shouldShowMessage = isAdd ? true : (!isSuccess || !hasDiffs);

    const privilegeHtml = isAdd ? "" : renderPrivilegeDiffEntries(change?.privilege_diff);
    const otherHtml = isAdd ? "" : renderOtherDiffEntries(change?.other_diff);
    const sections = isAdd
      ? ""
      : (privilegeHtml || otherHtml
        ? `${privilegeHtml}${otherHtml}`
        : `<section class="change-history-section">${renderPill("无具体字段变更", "status-pill--muted")}</section>`);

    const containerTag = collapsible ? "details" : "article";
    const openAttr = collapsible && open ? " open" : "";
    const summaryTagStart = collapsible ? `<summary class="change-history-card__summary">` : `<div class="change-history-card__header">`;
    const summaryTagEnd = collapsible ? `</summary>` : `</div>`;

    const headerHtml = `
      ${summaryTagStart}
        <div class="change-history-card__summary-left">
          ${renderChip(typeInfo.label, "chip-outline--brand", typeInfo.icon)}
          ${buildSummaryPills(change)}
        </div>
        <div class="change-history-card__summary-right">
          ${renderPill(timeText, "status-pill--muted", "fas fa-clock")}
          ${renderPill(statusInfo.label, statusInfo.pill, statusInfo.icon)}
        </div>
      ${summaryTagEnd}
    `;

    const bodyHtml = `
      <div class="change-history-card__body">
        ${shouldShowMessage ? `<p class="change-history-card__message">${escapeHtml(messageText || "无摘要")}</p>` : ""}
        ${sections}
      </div>
    `;

    return `
      <${containerTag} class="change-history-card change-history-card--timeline"${openAttr}>
        ${headerHtml}
        ${bodyHtml}
      </${containerTag}>
    `;
  }

  global.ChangeHistoryRenderer = {
    renderHistoryLoading,
    renderChangeHistoryCard,
    resolveChangeTypeInfo,
    resolveStatusInfo,
  };
})(window);
