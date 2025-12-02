(function (global) {
  "use strict";

  const PARTITION_GRID_REFRESH_EVENT = "partitionList:refresh";
  let partitionGrid = null;
  let refreshHandlerBound = false;
  let initialized = false;

  /**
   * 挂载分区列表组件。
   *
   * @param {Window} [context=global] 自定义上下文。
   * @returns {void}
   */
  function mount(context) {
    const host = context || global;
    const helpers = global.DOMHelpers;
    if (!helpers) {
      console.error("DOMHelpers 未初始化，无法挂载分区列表");
      return;
    }
    if (initialized) {
      return;
    }
    initialized = true;
    const { ready } = helpers;
    ready(() => {
      initializeGrid({ windowRef: host });
      bindRefreshEvent(host);
    });
  }

  /**
   * 初始化分区列表表格。
   *
   * @return {void}
   */
  /**
   * 初始化分区列表表格。
   *
   * @param {Object} [options={}] 配置项。
   * @param {Document} [options.document=document] DOM 文档。
   * @param {string} [options.containerSelector="#partitions-grid"] 容器选择器。
   * @param {Window} [options.windowRef=global] 自定义上下文。
   * @returns {void}
   */
  function initializeGrid(options = {}) {
    const rootDoc = options.document || document;
    const container = rootDoc.getElementById(options.containerSelector || "partitions-grid");
    if (!container) {
      console.warn("未找到分区列表容器，跳过 Grid 初始化");
      return;
    }
    if (!global.GridWrapper || !global.gridjs) {
      console.error("Grid.js 或 GridWrapper 未加载，无法初始化分区列表");
      return;
    }
    partitionGrid = new global.GridWrapper(container, {
      sort: false,
      columns: buildColumns(global.gridjs?.html),
      server: {
        url: "/partition/api/partitions?sort=name&order=asc",
        headers: {
          "X-Requested-With": "XMLHttpRequest",
        },
        then: (response) => {
          const payload = response?.data || response || {};
          const items = payload.items || [];
          updateGridMeta(payload.total || items.length);
          return items.map((item) => [
            item.table_type || "unknown",
            item.name || "-",
            item.size || "0 B",
            item.record_count ?? 0,
            item.date || "-",
            item.status || "unknown",
            item,
          ]);
        },
        total: (response) => {
          const payload = response?.data || response || {};
          return payload.total || 0;
        },
      },
    });
    partitionGrid.init();
  }

  /**
   * 构建表格列配置。
   *
   * @return {Array<Object>} 列配置数组
   */
  /**
   * 构建表格列配置。
   *
   * @param {Function} [gridHtml] gridjs 的 html 帮助函数。
   * @returns {Array<Object>} 列配置数组。
   */
  function buildColumns(gridHtml) {
    return [
      {
        name: "表类型",
        id: "table_type",
        width: "220px",
        formatter: (cell, row) => renderTableTypeChip(resolveRowMeta(row), cell, gridHtml),
      },
      {
        name: "分区名称",
        id: "name",
        formatter: (cell, row) => renderPartitionName(resolveRowMeta(row), cell, gridHtml),
      },
      {
        name: "大小",
        id: "size",
        width: "160px",
        formatter: (cell, row) => renderSizeCell(resolveRowMeta(row), cell, gridHtml),
      },
      {
        name: "记录数",
        id: "record_count",
        width: "160px",
        formatter: (cell) => renderRecordCount(cell, gridHtml),
      },
      {
        name: "分区月份",
        id: "date",
        width: "160px",
        formatter: (cell) => renderDateCell(cell, gridHtml),
      },
      {
        name: "状态",
        id: "status",
        width: "90px",
        formatter: (cell) => renderStatusPill(cell, gridHtml),
      },
      {
        id: "__meta__",
        hidden: true,
      },
    ];
  }

  /**
   * 解析行元数据。
   *
   * @param {Object} row - 表格行对象
   * @return {Object} 元数据对象
   */
  function resolveRowMeta(row) {
    return row?.cells?.[row.cells.length - 1]?.data || {};
  }

  /**
   * 渲染状态徽章。
   *
   * @param {string} status - 状态值
   * @param {Function} gridHtml - Grid.js HTML 函数
   * @return {string|Object} 徽章 HTML 或文本
   */
  function renderTableTypeChip(meta, fallback, gridHtml) {
    const label = meta.display_name || fallback || "-";
    if (!gridHtml) {
      return label;
    }
    return gridHtml(`<span class="ledger-chip">${escapeHtml(label)}</span>`);
  }

  function renderPartitionName(meta, cell, gridHtml) {
    const name = escapeHtml(cell || "-");
    const subtitle = meta.table || meta.table_type || "";
    if (!gridHtml) {
      return subtitle ? `${name} (${subtitle})` : name;
    }
    const subtitleHtml = subtitle
      ? `<span class="text-muted d-block partition-name__meta">${escapeHtml(subtitle)}</span>`
      : "";
    return gridHtml(`<div class="partition-name">${name}${subtitleHtml}</div>`);
  }

  function renderSizeCell(meta, cell, gridHtml) {
    const formatted = escapeHtml(cell || meta.size || "0 B");
    if (!gridHtml) {
      return formatted;
    }
    return gridHtml(
      `<span class="status-pill status-pill--muted"><i class="fas fa-database"></i>${formatted}</span>`
    );
  }

  function renderRecordCount(cell, gridHtml) {
    const count = Number(cell) || 0;
    const formatted = count.toLocaleString();
    const tone = count > 1000000 ? "warning" : "muted";
    if (!gridHtml) {
      return formatted;
    }
    return gridHtml(
      `<span class="status-pill status-pill--${tone}"><i class="fas fa-hashtag"></i>${formatted}</span>`
    );
  }

  function renderDateCell(cell, gridHtml) {
    const label = cell ? String(cell) : "-";
    if (!gridHtml) {
      return label;
    }
    return gridHtml(`<span class="chip-outline chip-outline--muted">${escapeHtml(label)}</span>`);
  }

  function renderStatusPill(status, gridHtml) {
    const normalized = (status || "unknown").toLowerCase();
    const meta = {
      current: { text: "当前", tone: "success", icon: "fa-check-circle" },
      past: { text: "历史", tone: "muted", icon: "fa-history" },
      future: { text: "未来", tone: "info", icon: "fa-clock" },
      warning: { text: "告警", tone: "danger", icon: "fa-exclamation-triangle" },
      unknown: { text: "未知", tone: "muted", icon: "fa-question-circle" },
    };
    const resolved = meta[normalized] || meta.unknown;
    if (!gridHtml) {
      return resolved.text;
    }
    return gridHtml(
      `<span class="status-pill status-pill--${resolved.tone}"><i class="fas ${resolved.icon}"></i>${resolved.text}</span>`
    );
  }

  function updateGridMeta(total) {
    const metaEl = document.getElementById("partitionGridMeta");
    if (!metaEl) {
      return;
    }
    metaEl.textContent = `共 ${Number(total || 0).toLocaleString()} 条记录`;
  }

  /**
   * 转义 HTML 特殊字符。
   *
   * @param {*} value - 要转义的值
   * @return {string} 转义后的字符串
   */
  function escapeHtml(value) {
    if (value === undefined || value === null) {
      return "";
    }
    return String(value)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#39;");
  }

  /**
   * 绑定刷新事件监听器。
   *
   * @return {void}
   */
  /**
   * 绑定刷新事件监听器。
   *
   * @param {Window|EventTarget} [target=global] 事件目标。
   * @returns {void}
   */
  function bindRefreshEvent(target = global) {
    if (refreshHandlerBound) {
      return;
    }
    /**
     * 触发分区 grid 刷新。
     *
     * @param {void} 无参数。处理逻辑直接依赖 partitionGrid 实例。
     * @returns {void}
     */
    const handler = () => {
      if (!partitionGrid) {
        return;
      }
      partitionGrid.refresh?.();
    };
    target.addEventListener(PARTITION_GRID_REFRESH_EVENT, handler);
    refreshHandlerBound = true;
  }

  /**
   * 刷新分区列表。
   *
   * @return {void}
   */
  /**
   * 刷新分区列表。
   *
   * @param {Window|EventTarget} [target=global] 事件目标。
   * @returns {void}
   */
  function refresh(target = global) {
    if (partitionGrid) {
      partitionGrid.refresh?.();
      return;
    }
    target.dispatchEvent?.(new CustomEvent(PARTITION_GRID_REFRESH_EVENT));
  }

  global.PartitionsListGrid = {
    mount,
    refresh,
  };
})(window);
