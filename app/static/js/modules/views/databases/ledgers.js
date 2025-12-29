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

    const GridPage = global.Views?.GridPage;
    const GridPlugins = global.Views?.GridPlugins;
    if (!GridPage?.mount || !GridPlugins) {
      console.error("Views.GridPage 或 Views.GridPlugins 未加载");
      return;
    }

    const escapeHtml = global.UI?.escapeHtml;
    const renderChipStack = global.UI?.renderChipStack;
    const rowMeta = global.GridRowMeta;
    if (typeof escapeHtml !== "function" || typeof renderChipStack !== "function" || typeof rowMeta?.get !== "function") {
      console.error("UI helpers 或 GridRowMeta 未加载");
      return;
    }

    const { ready } = helpers;
    const gridHtml = gridjs.html;
    const CHIP_COLUMN_WIDTH = "220px";
    const TYPE_COLUMN_WIDTH = "110px";
    const ACTION_COLUMN_WIDTH = "90px";
    const root = document.getElementById("database-ledger-root");
    if (!root) {
      return;
    }

    const apiUrl = root.dataset.apiUrl;
    const exportUrl = root.dataset.exportUrl || "";
    const capacityStatsUrl = root.dataset.capacityStatsUrl || "";
    let currentDbType = root.dataset.currentDbType || "all";
    const FILTER_FORM_ID = "database-ledger-filter-form";
    const TAG_FILTER_SCOPE = "database-tag-selector";

    let gridPage = null;

    ready(() => {
      initializeGridPage();
      bindTypeButtons();
      initializeTagFilter();
    });

    function initializeGridPage() {
      if (!apiUrl) {
        console.warn("database-ledger apiUrl 未配置");
        return;
      }

      gridPage = GridPage.mount({
        root,
        grid: "#database-ledger-grid",
        filterForm: `#${FILTER_FORM_ID}`,
        gridOptions: {
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
        },
        filters: {
          allowedKeys: ["search", "db_type", "tags"],
          normalize: (filters) => normalizeFilters(filters),
        },
        plugins: [
          GridPlugins.filterCard({
            autoSubmitOnChange: false,
            onClear: (ctx) => {
              currentDbType = "all";
              setDbTypeFieldValue("all");
              resetTagFilterDisplay();
              const searchInput = ctx.filterFormEl?.querySelector?.('[name="search"]');
              if (searchInput) {
                searchInput.value = "";
              }
              ctx.applyFiltersFromValues({ db_type: "all", search: "", tags: "" }, { source: "filter-clear" });
            },
          }),
          GridPlugins.exportButton({
            selector: "[data-export-ledger]",
            endpoint: exportUrl,
            navigate: "open",
          }),
        ],
      });
    }

    function normalizeFilters(filters) {
      const normalized = filters && typeof filters === "object" ? filters : {};
      const cleaned = {};

      const search = typeof normalized.search === "string" ? normalized.search.trim() : "";
      if (search) {
        cleaned.search = search;
      }

      const tags = typeof normalized.tags === "string" ? normalized.tags.trim() : "";
      if (tags) {
        cleaned.tags = tags;
      }

      const dbType = typeof normalized.db_type === "string" ? normalized.db_type.trim() : "";
      cleaned.db_type = dbType || currentDbType || "all";
      currentDbType = cleaned.db_type;

      return cleaned;
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
      return rowMeta.get(row);
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
      let label = dbType || "未知";
      let icon = "fa-database";
      switch (dbType) {
        case "mysql":
          label = "MySQL";
          icon = "fa-database";
          break;
        case "postgresql":
          label = "PostgreSQL";
          icon = "fa-database";
          break;
        case "sqlserver":
          label = "SQL Server";
          icon = "fa-server";
          break;
        case "oracle":
          label = "Oracle";
          icon = "fa-database";
          break;
        default:
          break;
      }
      return gridHtml(
        `<span class="chip-outline chip-outline--brand"><i class="fas ${icon}" aria-hidden="true"></i>${escapeHtml(label)}</span>`,
      );
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
      const names = tags
        .map((tag) => tag?.display_name || tag?.name)
        .filter((name) => typeof name === "string" && name.trim().length > 0);
      return renderChipStack(names, {
        gridHtml,
        emptyText: "无标签",
        maxItems: Number.POSITIVE_INFINITY,
      });
    }

    function renderActions(meta) {
      if (!gridHtml) {
        return "";
      }
      const params = new URLSearchParams();
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
      const scope = TAG_FILTER_SCOPE;
      const filterContainer = document.querySelector(`[data-tag-selector-scope="${scope}"]`);
      const hiddenInput = filterContainer?.querySelector(`#${scope}-selected`);
      const initialValues = parseInitialTagValues(hiddenInput?.value || "");
      global.TagSelectorHelper.setupForForm({
        modalSelector: "#tagSelectorModal",
        rootSelector: "[data-tag-selector]",
        scope,
        container: filterContainer,
        initialValues,
        onConfirm: () => {
          if (!gridPage) {
            return;
          }
          gridPage.applyFiltersFromForm({ source: "tag-selector" });
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
      const scope = TAG_FILTER_SCOPE;
      const filterContainer = document.querySelector(`[data-tag-selector-scope="${scope}"]`);
      const previewEl = filterContainer?.querySelector(`#${scope}-preview`);
      if (previewEl) {
        previewEl.style.display = "none";
      }
      const chipsEl = filterContainer?.querySelector(`#${scope}-chips`);
      if (chipsEl) {
        chipsEl.innerHTML = "";
      }
      const hiddenInput = filterContainer?.querySelector(`#${scope}-selected`);
      if (hiddenInput) {
        hiddenInput.value = "";
      }
      if (global.TagSelectorHelper?.clearSelection) {
        global.TagSelectorHelper.clearSelection({
          scope,
          container: filterContainer,
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
          setDbTypeFieldValue(currentDbType);
          gridPage?.applyFiltersFromForm?.({ source: "type-button" });
        });
      });
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
  }

  global.DatabaseLedgerPage = {
    mount,
  };
})(window);
