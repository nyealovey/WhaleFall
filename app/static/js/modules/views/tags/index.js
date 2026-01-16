/**
 * 挂载标签管理页面。
 *
 * 初始化标签管理页面的所有组件，包括标签列表表格、筛选器、
 * 创建/编辑/删除模态框和快捷操作。支持标签的 CRUD 操作。
 *
 * @param {Object} global - 全局 window 对象
 * @return {void}
 *
 * @example
 * // 在页面加载时调用
 * mountTagsIndexPage(window);
 */
function mountTagsIndexPage(global) {
  "use strict";

  const helpers = global.DOMHelpers;
  if (!helpers) {
    console.error("DOMHelpers 未初始化，无法加载标签管理页面");
    return;
  }
  const gridjs = global.gridjs;
  const GridWrapper = global.GridWrapper;
  if (!gridjs || !GridWrapper) {
    console.error("Grid.js 或 GridWrapper 未加载");
    return;
  }
  const LodashUtils = global.LodashUtils;
  if (!LodashUtils) {
    console.error("LodashUtils 未初始化");
    return;
  }

  const GridPage = global.Views?.GridPage;
  const GridPlugins = global.Views?.GridPlugins;
  if (!GridPage?.mount || !GridPlugins) {
    console.error("Views.GridPage 或 Views.GridPlugins 未加载");
    return;
  }

  const escapeHtml = global.UI?.escapeHtml;
  const resolveErrorMessage = global.UI?.resolveErrorMessage;
  const rowMeta = global.GridRowMeta;
  if (
    typeof escapeHtml !== "function" ||
    typeof resolveErrorMessage !== "function" ||
    typeof rowMeta?.get !== "function"
  ) {
    console.error("UI helpers 或 GridRowMeta 未加载");
    return;
  }

  const TagManagementService = global.TagManagementService;
  if (!TagManagementService) {
    console.error("TagManagementService 未初始化");
    return;
  }
  const tagService = new TagManagementService();

  const gridHtml = gridjs.html;
  const { ready, selectOne } = helpers;

  const pageRoot = document.getElementById("tags-page-root");
  if (!pageRoot) {
    console.warn("未找到标签管理页面根元素");
    return;
  }

  const TAG_FILTER_FORM_ID = "tag-filter-form";
  let statsContainer = null;
  let tagModals = null;
  let canManageTags = false;
  let gridPage = null;
  let tagsGrid = null;

  ready(() => {
    statsContainer = pageRoot.querySelector("#tagStatsContainer");
    initializeTagModals();
    initializeGridPage();
    bindQuickActions();
    exposeActions();
  });

  /**
   * 初始化标签列表 grid page skeleton。
   *
   * @returns {void} 无返回值，通过副作用创建 Views.GridPage controller。
   */
  function initializeGridPage() {
    const container = pageRoot.querySelector("#tags-grid");
    if (!container) {
      console.warn("找不到 #tags-grid 容器");
      return;
    }

    canManageTags = container.dataset.canManage === "true";

    gridPage = GridPage.mount({
      root: pageRoot,
      grid: "#tags-grid",
      filterForm: `#${TAG_FILTER_FORM_ID}`,
      gridOptions: {
        search: false,
        sort: false,
        columns: buildColumns(),
        server: {
          url: tagService.getGridUrl(),
          headers: { "X-Requested-With": "XMLHttpRequest" },
          then: handleServerResponse,
          total: (response) => {
            const payload = response?.data || response || {};
            return payload.total || 0;
          },
        },
      },
      filters: {
        allowedKeys: ["search", "category", "status"],
        resolve: (values, ctx) => resolveFilters(values, ctx),
        normalize: (filters) => normalizeGridFilters(filters),
      },
      plugins: [
        GridPlugins.filterCard({
          autoSubmitOnChange: true,
          autoSubmitDebounce: 400,
        }),
        GridPlugins.actionDelegation({
          actions: {
            "edit-tag": ({ event, el }) => {
              event.preventDefault();
              openTagEditor(el.getAttribute("data-tag-id"));
            },
            "delete-tag": ({ event, el }) => {
              event.preventDefault();
              const encodedName = el.getAttribute("data-tag-name") || "";
              const decodedName = encodedName ? decodeURIComponent(encodedName) : "";
              requestDeleteTag(el.getAttribute("data-tag-id"), decodedName, el);
            },
          },
        }),
      ],
    });

    tagsGrid = gridPage?.gridWrapper || null;
  }

  function resolveFilters(values, ctx) {
    const rawSearch = typeof values?.search === "string" ? values.search.trim() : "";
    if (rawSearch && rawSearch.length < 2) {
      ctx.toast?.warning?.("搜索关键词至少需要2个字符");
      return null;
    }
    return values || {};
  }

  /**
   * 规范化筛选对象，移除空值。
   *
   * @param {Object} filters 原始过滤条件。
   * @returns {Object} 去除空值后的过滤结果。
   */
  function normalizeGridFilters(filters) {
    const normalized = filters && typeof filters === "object" ? filters : {};
    const cleaned = {};

    const search = typeof normalized.search === "string" ? normalized.search.trim() : "";
    if (search) {
      cleaned.search = search;
    }

    const category = typeof normalized.category === "string" ? normalized.category.trim() : "";
    if (category && category !== "all") {
      cleaned.category = category;
    }

    const status = typeof normalized.status === "string" ? normalized.status.trim() : "";
    if (status && status !== "all") {
      cleaned.status = status;
    }

    return cleaned;
  }

  /**
   * 初始化标签创建/编辑模态。
   *
   * @returns {void} 成功时创建控制器并调用 init。
   */
  function initializeTagModals() {
    if (!global.TagModals?.createController) {
      console.warn("TagModals 未加载，创建/编辑模态不可用");
      return;
    }
    tagModals = global.TagModals.createController({
      tagService,
      FormValidator: global.FormValidator,
      ValidationRules: global.ValidationRules,
      toast: global.toast,
      DOMHelpers: global.DOMHelpers,
    });
    tagModals.init?.();
  }

  /**
   * 绑定工具栏快捷按钮。
   *
   * @returns {void} 将按钮事件与模态操作关联。
   */
  function bindQuickActions() {
    const createBtn = selectOne('[data-action="create-tag"]');
    if (createBtn.length && tagModals) {
      createBtn.on("click", (event) => {
        event.preventDefault();
        tagModals.openCreate();
      });
    }
  }

  /**
   * 提示确认并删除标签。
   *
   * @param {number|string} tagId 标签 ID。
   * @param {string} tagName 标签名称。
   * @param {Element} [trigger] 触发按钮。
   * @returns {Promise<void>} 完成删除流程。
   */
  async function requestDeleteTag(tagId, tagName, trigger) {
    if (!tagId || !canManageTags) {
      return;
    }
    if (typeof tagService.deleteTag !== "function") {
      console.error("tagService 未初始化，无法删除标签");
      return;
    }

    const confirmDanger = global.UI?.confirmDanger;
    if (typeof confirmDanger !== "function") {
      global.toast?.error?.("确认组件未初始化");
      return;
    }

    const displayName = tagName || `ID: ${tagId}`;
    const confirmed = await confirmDanger({
      title: "确认删除标签",
      message: "该操作不可撤销，请确认影响范围后继续。",
      details: [
        { label: "目标标签", value: displayName, tone: "danger" },
        { label: "不可撤销", value: "删除后将无法恢复", tone: "danger" },
      ],
      confirmText: "确认删除",
      confirmButtonClass: "btn-danger",
    });
    if (!confirmed) {
      return;
    }

    const setButtonLoading = global.UI?.setButtonLoading;
    const clearButtonLoading = global.UI?.clearButtonLoading;
    const hasLoadingApi = typeof setButtonLoading === "function" && typeof clearButtonLoading === "function";

    if (hasLoadingApi) {
      setButtonLoading(trigger, { loadingText: "删除中..." });
    } else if (trigger) {
      trigger.setAttribute("aria-busy", "true");
      trigger.setAttribute("aria-disabled", "true");
      if ("disabled" in trigger) {
        trigger.disabled = true;
      }
    }

    try {
      const resp = await tagService.deleteTag(tagId);
      if (!resp?.success) {
        throw new Error(resp?.message || "删除标签失败");
      }
      global.toast?.success?.(resp?.message || "删除标签成功");
      tagsGrid?.refresh?.();
    } catch (error) {
      console.error("删除标签失败", error);
      global.toast?.error?.(resolveErrorMessage(error, "删除标签失败"));
    } finally {
      if (hasLoadingApi) {
        clearButtonLoading(trigger);
      } else if (trigger) {
        trigger.removeAttribute("aria-busy");
        trigger.removeAttribute("aria-disabled");
        if ("disabled" in trigger) {
          trigger.disabled = false;
        }
      }
    }
  }

  /**
   * 打开标签编辑模态。
   *
   * @param {number|string} tagId 标签主键。
   * @returns {void} 调用标签模态打开编辑页。
   */
  function openTagEditor(tagId) {
    if (!tagModals || !tagId) {
      return;
    }
    tagModals.openEdit(tagId);
  }

  function buildColumns() {
    return [
      {
        name: "标签",
        id: "tag_name",
        formatter: (cell, row) => renderTagCell(resolveRowMeta(row)),
      },
      {
        name: "分类",
        id: "category",
        width: "110px",
        formatter: (cell, row) => renderCategoryChip(resolveRowMeta(row)),
      },
      {
        name: "颜色",
        id: "color",
        width: "110px",
        formatter: (cell, row) => renderColorChip(resolveRowMeta(row)),
      },
      {
        name: "状态",
        id: "is_active",
        width: "90px",
        formatter: (cell, row) => renderStatusPill(Boolean(resolveRowMeta(row).is_active)),
      },
      {
        name: "关联",
        id: "bindings",
        formatter: (cell, row) => renderBindings(resolveRowMeta(row)),
      },
      {
        name: "操作",
        id: "actions",
        width: "90px",
        sort: false,
        formatter: (cell, row) => renderActionButtons(resolveRowMeta(row)),
      },
      { id: "__meta__", hidden: true },
    ];
  }

  function handleServerResponse(response) {
    const payload = response?.data || response || {};
    updateTagStats(payload.stats);
    const items = payload.items || [];
    return items.map((item) => [
      item.display_name || item.name || "-",
      item.category || "-",
      item.color_name || item.color || "-",
      item.is_active,
      item.instance_count || 0,
      null,
      item,
    ]);
  }

  function resolveRowMeta(row) {
    return rowMeta.get(row);
  }

  function renderTagCell(meta) {
    const displayName = escapeHtml(meta.display_name || meta.name || "-");
    const code = meta.name ? `#${escapeHtml(meta.name)}` : "";
    if (!gridHtml) {
      return code ? `${displayName} (${code})` : displayName;
    }
    return gridHtml(`
      <div>
        <div class="fw-semibold">${displayName}</div>
        ${code ? `<div class="tags-name-cell__code">${code}</div>` : ""}
      </div>
    `);
  }

  function renderCategoryChip(meta) {
    const category = meta.category || "-";
    if (!gridHtml) {
      return category;
    }
    return gridHtml(buildChipOutlineHtml(category, "muted", "fas fa-bookmark"));
  }

  function renderColorChip(meta) {
    const colorName = meta.color_name || meta.color || "-";
    if (!gridHtml) {
      return colorName;
    }
    const tone = meta.color ? "brand" : "muted";
    return gridHtml(buildChipOutlineHtml(colorName, tone, "fas fa-fill-drip"));
  }

  function renderBindings(meta) {
    const instanceCount = Number(meta.instance_count) || 0;
    if (!gridHtml) {
      return instanceCount ? `实例 ${instanceCount}` : "无关联";
    }
    const chips = instanceCount
      ? [buildLedgerChipHtml(`<i class="fas fa-database"></i>实例 ${instanceCount}`)]
      : [buildLedgerChipHtml("<i class=\"fas fa-minus\"></i>无关联", true)];
    return gridHtml(`<div class="ledger-chip-stack">${chips.join("")}</div>`);
  }

  function renderActionButtons(meta) {
    if (!canManageTags) {
      return gridHtml ? gridHtml('<span class="text-muted small">只读</span>') : "只读";
    }
    const tagId = meta.id;
    if (!tagId) {
      return "";
    }
    const encodedName = encodeURIComponent(meta.display_name || meta.name || "");
    if (!gridHtml) {
      return "管理";
    }
    return gridHtml(`
      <div class="d-flex justify-content-center gap-2">
        <button type="button" class="btn btn-outline-secondary btn-icon" data-action="edit-tag" data-tag-id="${tagId}" title="编辑">
          <i class="fas fa-edit"></i>
        </button>
        <button type="button" class="btn btn-outline-danger btn-icon" data-action="delete-tag" data-tag-id="${tagId}" data-tag-name="${encodedName}" title="删除">
          <i class="fas fa-trash"></i>
        </button>
      </div>
    `);
  }

  function renderStatusPill(isActive) {
    const resolveText = global.UI?.Terms?.resolveActiveStatusText;
    const text = typeof resolveText === "function" ? resolveText(isActive) : isActive ? "启用" : "停用";
    if (!gridHtml) {
      return text;
    }
    const variant = isActive ? "success" : "muted";
    const icon = isActive ? "fas fa-check-circle" : "fas fa-ban";
    return gridHtml(buildStatusPillHtml(text, variant, icon));
  }

  function buildChipOutlineHtml(text, tone = "muted", iconClass) {
    const classes = ["chip-outline"];
    classes.push(tone === "brand" ? "chip-outline--brand" : "chip-outline--muted");
    const iconHtml = iconClass ? `<i class="${iconClass}" aria-hidden="true"></i>` : "";
    const safeText = text ? escapeHtml(text) : "-";
    return `<span class="${classes.join(" ")}">${iconHtml}${safeText}</span>`;
  }

  function buildStatusPillHtml(text, variant = "muted", iconClass) {
    const classes = ["status-pill"];
    if (variant) {
      classes.push(`status-pill--${variant}`);
    }
    const iconHtml = iconClass ? `<i class="${iconClass}" aria-hidden="true"></i>` : "";
    return `<span class="${classes.join(" ")}">${iconHtml}${escapeHtml(text || "-")}</span>`;
  }

  function buildLedgerChipHtml(content, muted = false) {
    const classes = ["ledger-chip"];
    if (muted) {
      classes.push("ledger-chip--muted");
    }
    return `<span class="${classes.join(" ")}">${content}</span>`;
  }

  function updateTagStats(stats) {
    if (!statsContainer || !stats) {
      return;
    }
    const mapping = {
      total: stats.total,
      active: stats.active,
      inactive: stats.inactive,
      category_count: stats.category_count,
    };
    Object.entries(mapping).forEach(([key, value]) => {
      if (typeof value === "undefined" || value === null) {
        return;
      }
      const card = statsContainer.querySelector(`[data-stat-key="${key}"]`);
      if (!card) {
        return;
      }
      const valueEl = card.querySelector(".tags-stat-card__value");
      if (valueEl) {
        valueEl.textContent = value;
      }
    });
  }

  function exposeActions() {
    global.TagsIndexActions = {
      openEditor: openTagEditor,
      confirmDelete: requestDeleteTag,
    };
  }
}

window.TagsIndexPage = {
  mount: function () {
    mountTagsIndexPage(window);
  },
};
