/**
 * 挂载用户管理页面。
 *
 * 初始化用户管理页面的所有组件，包括用户列表表格、筛选器、
 * 创建/编辑/删除模态框等功能。支持用户的 CRUD 操作和角色管理。
 *
 * @param {Object} global - 全局 window 对象
 * @return {void}
 *
 * @example
 * // 在页面加载时调用
 * mountAuthListPage(window);
 */
function mountAuthListPage(global) {
  "use strict";

  const helpers = global.DOMHelpers;
  if (!helpers) {
    console.error("DOMHelpers 未初始化，无法加载用户列表脚本");
    return;
  }
  const gridjs = global.gridjs;
  const GridWrapper = global.GridWrapper;
  if (!gridjs || !GridWrapper) {
    console.error("Grid.js 或 GridWrapper 未加载");
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

  const UserService = global.UserService;
  if (!UserService) {
    console.error("UserService 未初始化");
    return;
  }
  const createUsersStore = global.createUsersStore;
  if (typeof createUsersStore !== "function") {
    console.error("createUsersStore 未初始化");
    return;
  }

  const gridHtml = gridjs.html;
  const { ready, selectOne } = helpers;

  const pageRoot = document.getElementById("auth-list-page-root");
  if (!pageRoot) {
    console.warn("未找到用户管理页面根元素");
    return;
  }

  const USER_FILTER_FORM_ID = "user-filter-form";
  let gridPage = null;
  let usersGrid = null;
  let userModals = null;
  let usersStore = null;
  let canManageUsers = false;
  let currentUserId = null;

  ready(() => {
    try {
      usersStore = createUsersStore({
        service: new UserService(),
        emitter: global.mitt ? global.mitt() : null,
      });
    } catch (error) {
      console.error("初始化 UsersStore 失败:", error);
      return;
    }
    initializeUserModals();
    initializeGridPage();
    bindCreateButton();
    exposeActions();
  });

  /**
   * 初始化用户创建/编辑模态控制器。
   *
   * @returns {void} 成功时创建控制器并调用 init。
   */
  function initializeUserModals() {
    if (!global.UserModals?.createController) {
      console.warn("UserModals 未加载，创建/编辑模态不可用");
      return;
    }
    userModals = global.UserModals.createController({
      store: usersStore,
      FormValidator: global.FormValidator,
      ValidationRules: global.ValidationRules,
      toast: global.toast,
      DOMHelpers: global.DOMHelpers,
      onSaved: () => {
        usersGrid?.refresh?.();
      },
    });
    userModals.init?.();
  }

  /**
   * 初始化用户列表 grid page skeleton。
   *
   * @returns {void} 无返回值，通过副作用创建 Views.GridPage controller。
   */
  function initializeGridPage() {
    const container = pageRoot.querySelector("#users-grid");
    if (!container) {
      console.warn("找不到 #users-grid 容器");
      return;
    }

    canManageUsers = container.dataset.canManage === "true";
    currentUserId = Number(container.dataset.currentUser || 0) || null;

    gridPage = GridPage.mount({
      root: pageRoot,
      grid: "#users-grid",
      filterForm: `#${USER_FILTER_FORM_ID}`,
      gridOptions: {
        search: false,
        sort: false,
        columns: buildColumns(),
        server: {
          url: usersStore?.gridUrl || "",
          headers: {
            "X-Requested-With": "XMLHttpRequest",
          },
          then: handleServerResponse,
          total: (response) => {
            const payload = response?.data || response || {};
            return payload.total || payload.pagination?.total || 0;
          },
        },
      },
      filters: {
        allowedKeys: ["search", "role", "status"],
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
            "edit-user": ({ event, el }) => {
              event.preventDefault();
              openUserEditor(el.getAttribute("data-user-id"));
            },
            "delete-user": ({ event, el }) => {
              event.preventDefault();
              const encoded = el.getAttribute("data-username") || "";
              const username = encoded ? decodeURIComponent(encoded) : "";
              requestDeleteUser(el.getAttribute("data-user-id"), username, el);
            },
          },
        }),
      ],
    });

    usersGrid = gridPage?.gridWrapper || null;
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

    const role = typeof normalized.role === "string" ? normalized.role.trim() : "";
    if (role && role !== "all") {
      cleaned.role = role;
    }

    const status = typeof normalized.status === "string" ? normalized.status.trim() : "";
    if (status && status !== "all") {
      cleaned.status = status;
    }

    const search = typeof normalized.search === "string" ? normalized.search.trim() : "";
    if (search) {
      cleaned.search = search;
    }

    return cleaned;
  }

  /**
   * 绑定“新建用户”按钮事件。
   *
   * @returns {void} 将按钮事件与模态操作关联。
   */
  function bindCreateButton() {
    const createBtn = selectOne('[data-action="create-user"]');
    if (createBtn.length && userModals) {
      createBtn.on("click", (event) => {
        event.preventDefault();
        userModals.openCreate();
      });
    }
  }

  /**
   * 打开用户编辑模态。
   *
   * @param {number|string} userId 目标用户 ID。
   * @returns {void}
   */
  function openUserEditor(userId) {
    if (!userModals || !userId) {
      return;
    }
    userModals.openEdit(userId);
  }

  /**
   * 提示确认并请求删除用户。
   *
   * @param {number|string} userId 待删除用户 ID。
   * @param {string} username 用户名展示文案。
   * @param {Element} [trigger] 触发按钮。
   * @returns {Promise<void>} 删除流程。
   */
  async function requestDeleteUser(userId, username, trigger) {
    if (!usersStore || !usersStore.actions?.remove || !userId || !canManageUsers) {
      return;
    }
    if (Number(userId) === Number(currentUserId)) {
      global.toast?.warning?.("不能删除当前登录用户");
      return;
    }

    const confirmDanger = global.UI?.confirmDanger;
    if (typeof confirmDanger !== "function") {
      global.toast?.error?.("确认组件未初始化");
      return;
    }

    const displayName = username || `ID: ${userId}`;
    const confirmed = await confirmDanger({
      title: "确认删除用户",
      message: "该操作不可撤销，请确认影响范围后继续。",
      details: [
        { label: "目标用户", value: displayName, tone: "danger" },
        { label: "不可撤销", value: "删除后将无法恢复", tone: "danger" },
      ],
      confirmText: "确认删除",
      confirmButtonClass: "btn-danger",
    });
    if (!confirmed) {
      return;
    }

    showLoadingState(trigger, "删除中...");

    try {
      const resp = await usersStore.actions.remove(userId);
      global.toast?.success?.(resp?.message || "用户删除成功");
      usersGrid?.refresh?.();
    } catch (error) {
      console.error("删除用户失败", error);
      global.toast?.error?.(resolveErrorMessage(error, "删除用户失败"));
    } finally {
      hideLoadingState(trigger);
    }
  }

  /**
   * 在按钮上展示加载状态。
   *
   * @param {Element|string|Object} element 目标按钮或选择器。
   * @param {string} text 加载提示。
   * @returns {void}
   */
  function showLoadingState(element, text) {
    const setButtonLoading = global.UI?.setButtonLoading;
    if (typeof setButtonLoading === "function") {
      setButtonLoading(element, { loadingText: text });
      return;
    }
    const node = element instanceof Element ? element : null;
    if (!node) {
      return;
    }
    node.setAttribute("aria-busy", "true");
    node.setAttribute("aria-disabled", "true");
    if ("disabled" in node) {
      node.disabled = true;
    }
  }

  /**
   * 恢复按钮原样。
   *
   * @param {Element|string|Object} element 目标按钮。
   * @returns {void}
   */
  function hideLoadingState(element) {
    const clearButtonLoading = global.UI?.clearButtonLoading;
    if (typeof clearButtonLoading === "function") {
      clearButtonLoading(element);
      return;
    }
    const node = element instanceof Element ? element : null;
    if (!node) {
      return;
    }
    node.removeAttribute("aria-busy");
    node.removeAttribute("aria-disabled");
    if ("disabled" in node) {
      node.disabled = false;
    }
  }

  function buildColumns() {
    return [
      {
        name: "ID",
        id: "id",
        width: "90px",
        formatter: (cell) => renderIdChip(cell),
      },
      {
        name: "用户",
        id: "username",
        formatter: (cell, row) => renderUserCell(cell, resolveRowMeta(row)),
      },
      {
        name: "角色",
        id: "role",
        width: "110px",
        formatter: (cell) => renderRoleChip(cell),
      },
      {
        name: "状态",
        id: "is_active",
        width: "70px",
        formatter: (cell) => renderStatusPill(Boolean(cell)),
      },
      {
        name: "创建时间",
        id: "created_at",
        formatter: (cell, row) => renderTimestamp(resolveRowMeta(row), cell),
      },
      {
        name: "操作",
        id: "actions",
        sort: false,
        formatter: (cell, row) => renderActionButtons(resolveRowMeta(row)),
      },
      { id: "__meta__", hidden: true },
    ];
  }

  function handleServerResponse(response) {
    const payload = response?.data || response || {};
    const items = payload.items || payload.users || [];
    return items.map((item) => [
      item.id,
      item.username || "-",
      item.role,
      item.is_active,
      item.created_at_display || item.created_at || "-",
      null,
      item,
    ]);
  }

  function resolveRowMeta(row) {
    return rowMeta.get(row);
  }

  function renderIdChip(value) {
    const text = value ? `#${value}` : "-";
    if (!gridHtml) {
      return text;
    }
    return gridHtml(buildChipOutlineHtml(text, "muted"));
  }

  function renderUserCell(cell, meta) {
    const username = escapeHtml(cell || "-");
    const emailChip = meta.email
      ? `<div class="ledger-chip-stack mt-1"><span class="ledger-chip ledger-chip--muted"><i class="fas fa-envelope me-1"></i>${escapeHtml(meta.email)}</span></div>`
      : "";
    if (!gridHtml) {
      return meta.email ? `${username} (${meta.email})` : username;
    }
    return gridHtml(`
      <div class="d-flex flex-column">
        <strong>${username}</strong>
        ${emailChip}
      </div>
    `);
  }

  const ROLE_META = {
    admin: { label: "管理员", icon: "fas fa-shield-alt", tone: "brand" },
    user: { label: "普通用户", icon: "fas fa-user", tone: "muted" },
    viewer: { label: "查看者", icon: "fas fa-eye", tone: "muted" },
  };

  function renderRoleChip(roleValue) {
    let meta;
    switch (roleValue) {
      case "admin":
        meta = ROLE_META.admin;
        break;
      case "user":
        meta = ROLE_META.user;
        break;
      case "viewer":
        meta = ROLE_META.viewer;
        break;
      default:
        meta = { label: roleValue || "-", icon: "fas fa-user-tag", tone: "muted" };
        break;
    }
    if (!gridHtml) {
      return meta.label;
    }
    return gridHtml(buildChipOutlineHtml(meta.label, meta.tone === "brand" ? "brand" : "muted", meta.icon));
  }

  function renderStatusPill(isActive) {
    const resolveText = global.UI?.Terms?.resolveActiveStatusText;
    const text = typeof resolveText === "function" ? resolveText(isActive) : isActive ? "启用" : "停用";
    if (!gridHtml) {
      return text;
    }
    const icon = isActive ? "fas fa-check-circle" : "fas fa-ban";
    const variant = isActive ? "success" : "muted";
    return gridHtml(buildStatusPillHtml(text, variant, icon));
  }

  function renderTimestamp(meta, cell) {
    const value = meta.created_at_display || cell || "-";
    if (!gridHtml) {
      return value;
    }
    return gridHtml(`<span class="text-muted small">${escapeHtml(value)}</span>`);
  }

  function renderActionButtons(meta) {
    if (!canManageUsers) {
      return gridHtml ? gridHtml('<span class="text-muted small">只读</span>') : "只读";
    }
    const userId = meta.id;
    if (!userId) {
      return "";
    }
    const isSelf = currentUserId && Number(userId) === Number(currentUserId);
    const deleteDisabled = isSelf ? "disabled" : "";
    const encodedUsername = encodeURIComponent(meta.username || "");
    const deleteTitle = isSelf ? "不能删除当前登录用户" : "删除用户";
    if (!gridHtml) {
      return isSelf ? "编辑" : "编辑/删除";
    }
    return gridHtml(`
      <div class="d-flex justify-content-center gap-2">
        <button type="button" class="btn btn-outline-secondary btn-icon" data-action="edit-user" data-user-id="${userId}" title="编辑用户">
          <i class="fas fa-edit"></i>
        </button>
        <button type="button" class="btn btn-outline-danger btn-icon" data-action="delete-user" data-user-id="${userId}" data-username="${encodedUsername}" ${deleteDisabled} title="${deleteTitle}">
          <i class="fas fa-trash"></i>
        </button>
      </div>
    `);
  }

  function buildChipOutlineHtml(text, tone = "muted", iconClass) {
    const toneClass = tone === "brand" ? "chip-outline--brand" : "chip-outline--muted";
    const iconHtml = iconClass ? `<i class="${iconClass}" aria-hidden="true"></i>` : "";
    return `<span class="chip-outline ${toneClass}">${iconHtml}${escapeHtml(text)}</span>`;
  }

  function buildStatusPillHtml(text, variant = "muted", iconClass) {
    const classes = ["status-pill"];
    if (variant) {
      classes.push(`status-pill--${variant}`);
    }
    const iconHtml = iconClass ? `<i class="${iconClass}" aria-hidden="true"></i>` : "";
    return `<span class="${classes.join(" ")}">${iconHtml}${escapeHtml(text)}</span>`;
  }

  function exposeActions() {
    global.AuthListActions = {
      openEditor: openUserEditor,
      requestDelete: requestDeleteUser,
    };
  }
}

window.AuthListPage = {
  mount: function () {
    mountAuthListPage(window);
  },
};
