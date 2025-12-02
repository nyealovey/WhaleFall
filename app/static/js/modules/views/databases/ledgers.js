(function (global) {
  "use strict";

  function mount() {
    const helpers = global.DOMHelpers;
    if (!helpers) {
      console.error("DOMHelpers 未初始化，无法加载数据库台账页面");
      return;
    }
    const gridjs = global.gridjs;
    const GridWrapper = global.GridWrapper;
    if (!gridjs || !GridWrapper) {
      console.error("Grid.js 未就绪");
      return;
    }

    const { ready } = helpers;
    const gridHtml = gridjs.html;
    const CHIP_COLUMN_WIDTH = '220px';
    const TYPE_COLUMN_WIDTH = '110px';
    const ACTION_COLUMN_WIDTH = '90px';
    const root = document.getElementById("database-ledger-root");
    if (!root) {
      return;
    }

    const apiUrl = root.dataset.apiUrl;
    const exportUrl = root.dataset.exportUrl || "";
    const capacityStatsUrl = root.dataset.capacityStatsUrl || "";
    let currentDbType = root.dataset.currentDbType || "all";
    const FILTER_FORM_ID = "database-ledger-filter-form";
    const TAG_INPUT_SELECTOR = "#selected-tag-names";
    const TAG_PREVIEW_SELECTOR = "#selected-tags-preview";
    const TAG_CHIPS_SELECTOR = "#selected-tags-chips";

    let ledgerGrid = null;

    ready(() => {
      initializeGrid();
      bindFilterForm();
      bindTypeButtons();
      bindExportButton();
      initializeTagFilter();
    });

    function initializeGrid() {
      const container = document.getElementById("database-ledger-grid");
      if (!container) {
        return;
      }
      ledgerGrid = new GridWrapper(container, {
        search: false,
        sort: false,
        columns: buildColumns(),
        server: {
          url: apiUrl,
          headers: { "X-Requested-With": "XMLHttpRequest" },
          then: handleServerResponse,
          total: (response) => {
            const payload = response?.data || response || {};
            const total = payload.total || 0;
            updateTotalCount(total);
            return total;
          },
        },
      });
      const initialFilters = resolveFilters();
      initialFilters.db_type = currentDbType;
      ledgerGrid.setFilters(initialFilters, { silent: true });
      ledgerGrid.init();
    }

    function buildColumns() {
        return [
            {
                id: "database_name",
                name: "数据库/实例",
                formatter: (cell, row) => renderNameCell(resolveRowMeta(row)),
            },
            {
                id: "db_type",
                name: "类型",
                width: TYPE_COLUMN_WIDTH,
                formatter: (cell, row) => renderDbTypeBadge(resolveRowMeta(row)?.db_type),
            },
        {
          id: "capacity",
          name: "数据库大小",
          formatter: (cell, row) => renderCapacityCell(resolveRowMeta(row)?.capacity),
        },
            {
                id: "tags",
                name: "标签",
                width: CHIP_COLUMN_WIDTH,
                formatter: (cell, row) => renderTags(resolveRowMeta(row)?.tags || []),
            },
            {
                id: "actions",
                name: "操作",
                width: ACTION_COLUMN_WIDTH,
                formatter: (cell, row) => renderActions(resolveRowMeta(row)),
            },
        { id: "__meta__", hidden: true },
      ];
    }

    function handleServerResponse(response) {
      const payload = response?.data || response || {};
      const items = payload.items || [];
      return items.map((item) => [item.database_name, item.db_type, item.capacity, item.tags || [], null, item]);
    }

    function resolveRowMeta(row) {
      return row?.cells?.[row.cells.length - 1]?.data || {};
    }

    function renderNameCell(meta) {
      if (!gridHtml) {
        return meta.database_name || "-";
      }
      const instanceName = meta.instance?.name || "未知实例";
      const host = meta.instance?.host || "-";
      return gridHtml(`
        <div>
            <strong>${escapeHtml(meta.database_name || "-")}</strong>
            <div class="small account-instance-meta">
                <i class="fas fa-server account-instance-icon me-1" aria-hidden="true"></i>${escapeHtml(instanceName)} · ${escapeHtml(host)}
            </div>
        </div>
      `);
    }

    function renderDbTypeBadge(dbType) {
      if (!gridHtml) {
        return dbType || "-";
      }
      const labelMap = {
        mysql: "MySQL",
        postgresql: "PostgreSQL",
        sqlserver: "SQL Server",
        oracle: "Oracle",
      };
      const iconMap = {
        mysql: "fa-database",
        postgresql: "fa-database",
        sqlserver: "fa-server",
        oracle: "fa-database",
      };
      const label = labelMap[dbType] || (dbType || "未知");
      const icon = iconMap[dbType] || "fa-database";
      return gridHtml(`<span class="chip-outline chip-outline--brand"><i class="fas ${icon}" aria-hidden="true"></i>${escapeHtml(label)}</span>`);
    }

    function renderCapacityCell(capacity) {
      if (!gridHtml) {
        return capacity?.label || "未采集";
      }
      const sizeLabel = capacity?.label ? escapeHtml(capacity.label) : null;
      const collectedAt = capacity?.collected_at ? formatDate(capacity.collected_at) : "无采集记录";
      if (!sizeLabel) {
        return gridHtml(`
          <div class="d-flex flex-column gap-1">
            <span class="status-pill status-pill--muted">未采集</span>
            <small>${escapeHtml(collectedAt)}</small>
          </div>
        `);
      }
      return gridHtml(`
        <div>
            <div class="fw-bold">${sizeLabel}</div>
            <small>${escapeHtml(collectedAt)}</small>
        </div>
      `);
    }

    function renderTags(tagList) {
      const tags = Array.isArray(tagList) ? tagList : [];
      if (!gridHtml) {
        return tags.map((tag) => tag.display_name || tag.name).join(", ") || "无标签";
      }
      if (!tags.length) {
        return gridHtml('<span class="text-muted">无标签</span>');
      }
      const names = tags
        .map((tag) => tag?.display_name || tag?.name)
        .filter((name) => typeof name === "string" && name.trim().length > 0);
      return renderChipStack(names, {
        baseClass: 'ledger-chip',
        counterClass: 'ledger-chip ledger-chip--counter',
        emptyText: '无标签',
        maxItems: Number.POSITIVE_INFINITY,
      });
    }

    function renderActions(meta) {
      if (!gridHtml) {
        return "";
      }
      const params = new URLSearchParams();
      if (meta?.database_name) {
        // database_aggregations 页面只识别 database/database_id，两者都写入可兼容旧逻辑
        params.set("database", meta.database_name);
      }
      if (meta?.id) {
        params.set("database_id", String(meta.id));
      }
      if (meta?.instance?.id) {
        params.set("instance", String(meta.instance.id));
      }
      const dbTypeParam = meta?.db_type || meta?.instance?.db_type;
      if (dbTypeParam) {
        params.set("db_type", dbTypeParam);
      }
      const queryString = params.toString();
      const separator = capacityStatsUrl.includes("?") ? "&" : "?";
      const capacityHref = capacityStatsUrl
        ? queryString
          ? `${capacityStatsUrl}${separator}${queryString}`
          : capacityStatsUrl
        : "#";
      return gridHtml(`
        <div class="btn-group btn-group-sm" role="group">
            <a class="btn btn-outline-secondary btn-icon" href="${capacityHref}" target="_blank" rel="noreferrer" title="查看容量趋势">
                <i class="fas fa-external-link-alt"></i>
            </a>
        </div>
      `);
    }

    function initializeTagFilter() {
      if (!global.TagSelectorHelper) {
        console.warn("TagSelectorHelper 未加载，跳过标签筛选");
        return;
      }
      const hiddenInput = document.querySelector(TAG_INPUT_SELECTOR);
      const initialValues = parseInitialTagValues(hiddenInput?.value || "");
      global.TagSelectorHelper.setupForForm({
        modalSelector: "#tagSelectorModal",
        rootSelector: "[data-tag-selector]",
        openButtonSelector: "#open-tag-filter-btn",
        previewSelector: TAG_PREVIEW_SELECTOR,
        chipsSelector: TAG_CHIPS_SELECTOR,
        hiddenInputSelector: TAG_INPUT_SELECTOR,
        initialValues,
        onConfirm: () => {
          if (!ledgerGrid) {
            return;
          }
          const filters = resolveFilters();
          currentDbType = filters.db_type || "all";
          ledgerGrid.setFilters(filters);
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

    function resetTagFilterDisplay() {
      const previewEl = document.querySelector(TAG_PREVIEW_SELECTOR);
      if (previewEl) {
        previewEl.style.display = "none";
      }
      const chipsEl = document.querySelector(TAG_CHIPS_SELECTOR);
      if (chipsEl) {
        chipsEl.innerHTML = "";
      }
      const hiddenInput = document.querySelector(TAG_INPUT_SELECTOR);
      if (hiddenInput) {
        hiddenInput.value = "";
      }
      if (global.TagSelectorHelper?.clearSelection) {
        global.TagSelectorHelper.clearSelection({
          hiddenInputSelector: TAG_INPUT_SELECTOR,
        });
      }
    }

    function bindTypeButtons() {
      const buttons = root.querySelectorAll("[data-db-type-btn]");
      buttons.forEach((button) => {
        button.addEventListener("click", () => {
          currentDbType = button.dataset.dbType || "all";
          buttons.forEach((btn) => btn.classList.remove("btn-primary"));
          buttons.forEach((btn) => btn.classList.add("btn-outline-primary", "border-2", "fw-bold"));
          button.classList.add("btn-primary");
          button.classList.remove("btn-outline-primary", "border-2", "fw-bold");
          const filters = ledgerGrid ? { ...(ledgerGrid.currentFilters || {}) } : {};
          filters.db_type = currentDbType;
          setDbTypeFieldValue(currentDbType);
          if (ledgerGrid) {
            ledgerGrid.setFilters(filters);
          }
        });
      });
    }

    function bindFilterForm() {
      const form = document.getElementById(FILTER_FORM_ID);
      if (!form) {
        return;
      }
      form.addEventListener("submit", (event) => {
        event.preventDefault();
        const filters = resolveFilters();
        currentDbType = filters.db_type || "all";
        if (ledgerGrid) {
          ledgerGrid.setFilters(filters);
        }
      });
      const clearButton = form.querySelector("[data-filter-clear]");
      if (clearButton) {
        clearButton.addEventListener("click", () => {
          form.reset();
          currentDbType = "all";
          setDbTypeFieldValue("all");
          resetTagFilterDisplay();
          if (ledgerGrid) {
            ledgerGrid.setFilters({ db_type: "all", search: "", tags: "" });
          }
        });
      }
    }

    function resolveFilters() {
      const form = document.getElementById(FILTER_FORM_ID);
      if (!form) {
        return { db_type: currentDbType, search: "" };
      }
      const formData = new FormData(form);
      return {
        search: (formData.get("search") || "").trim(),
        db_type: (formData.get("db_type") || currentDbType || "all").trim() || "all",
        tags: (formData.get("tags") || "").trim(),
      };
    }

    function setDbTypeFieldValue(value) {
      const form = document.getElementById(FILTER_FORM_ID);
      if (!form) {
        return;
      }
      const select = form.querySelector('[name="db_type"]');
      if (select) {
        select.value = value || "all";
      }
    }

    function bindExportButton() {
      const exportBtn = root.querySelector("[data-export-ledger]");
      if (!exportBtn) {
        return;
      }
      exportBtn.addEventListener("click", () => {
        if (!exportUrl) {
          return;
        }
        const params = new URLSearchParams(ledgerGrid?.currentFilters || {});
        const query = params.toString();
        const downloadUrl = query ? `${exportUrl}?${query}` : exportUrl;
        global.open(downloadUrl, "_blank", "noreferrer");
      });
    }

    function formatDate(value) {
      if (!value) {
        return "未采集";
      }
      const date = new Date(value);
      if (Number.isNaN(date.getTime())) {
        return value;
      }
      return date.toLocaleString("zh-CN", {
        month: "2-digit",
        day: "2-digit",
        hour: "2-digit",
        minute: "2-digit",
      });
    }

    function updateTotalCount(total) {
      const target = document.getElementById("database-ledger-total");
      if (target) {
        target.textContent = `共 ${total} 条记录`;
      }
    }

    function escapeHtml(str) {
      if (typeof str !== "string") {
        return str ?? "";
      }
      return str
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#39;");
    }

    function renderChipStack(names, options = {}) {
      const {
        emptyText = '无数据',
        baseClass = 'ledger-chip',
        baseModifier = '',
        counterClass = 'ledger-chip ledger-chip--counter',
        maxItems = 2,
      } = options;
      const sanitized = (names || [])
        .filter((name) => typeof name === 'string' && name.trim().length > 0)
        .map((name) => escapeHtml(name.trim()));
      if (!sanitized.length) {
        return gridHtml ? gridHtml(`<span class="text-muted">${emptyText}</span>`) : emptyText;
      }
      if (!gridHtml) {
        return sanitized.join(', ');
      }
      const limit = Number.isFinite(maxItems) ? maxItems : sanitized.length;
      const visible = sanitized.slice(0, limit).join(' · ');
      const baseClasses = [baseClass, baseModifier].filter(Boolean).join(' ').trim();
      const chips = [`<span class="${baseClasses}">${visible}</span>`];
      if (sanitized.length > limit) {
        const rest = sanitized.length - limit;
        chips.push(`<span class="${counterClass}">+${rest}</span>`);
      }
      return gridHtml(`<div class="ledger-chip-stack">${chips.join('')}</div>`);
    }
  }

  global.DatabaseLedgerPage = {
    mount,
  };
})(window);
