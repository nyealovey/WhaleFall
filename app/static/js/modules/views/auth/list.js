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
    console.error('DOMHelpers 未初始化，无法加载用户列表脚本');
    return;
  }
  const gridjs = global.gridjs;
  const GridWrapper = global.GridWrapper;
  if (!gridjs || !GridWrapper) {
    console.error('Grid.js 或 GridWrapper 未加载');
    return;
  }
  const LodashUtils = global.LodashUtils;
  if (!LodashUtils) {
    console.error('LodashUtils 未初始化');
    return;
  }
  const UNSAFE_KEYS = ['__proto__', 'prototype', 'constructor'];
  const isSafeKey = (key) => typeof key === 'string' && !UNSAFE_KEYS.includes(key);
  const FILTER_KEYS = ['username', 'email', 'role', 'status', 'source', 'search', 'page', 'page_size', 'pageSize', 'sort', 'direction'];
  const isAllowedFilterKey = (key) => isSafeKey(key) && FILTER_KEYS.includes(key);

  function assignFilterField(target, key, value) {
    switch (key) {
      case 'username':
        target.username = value;
        break;
      case 'email':
        target.email = value;
        break;
      case 'role':
        target.role = value;
        break;
      case 'status':
        target.status = value;
        break;
      case 'source':
        target.source = value;
        break;
      case 'search':
        target.search = value;
        break;
      case 'page':
        target.page = value;
        break;
      case 'page_size':
      case 'pageSize':
        target.page_size = value;
        break;
      case 'sort':
        target.sort = value;
        break;
      case 'direction':
        target.direction = value;
        break;
      default:
        break;
    }
  }

  function getFilterField(target, key) {
    switch (key) {
      case 'username':
        return target.username;
      case 'email':
        return target.email;
      case 'role':
        return target.role;
      case 'status':
        return target.status;
      case 'source':
        return target.source;
      case 'search':
        return target.search;
      case 'page':
        return target.page;
      case 'page_size':
      case 'pageSize':
        return target.page_size;
      case 'sort':
        return target.sort;
      case 'direction':
        return target.direction;
      default:
        return undefined;
    }
  }
  const UserService = global.UserService;
  if (!UserService) {
    console.error('UserService 未初始化');
    return;
  }

  const http = global.httpU;
  const gridHtml = gridjs.html;
  const { ready, selectOne, from } = helpers;

  const USER_FILTER_FORM_ID = 'user-filter-form';
  let usersGrid = null;
  let filterCard = null;
  let filterUnloadHandler = null;
  let userModals = null;
  let userService = null;
  let canManageUsers = false;
  let currentUserId = null;
  let gridActionDelegationBound = false;

  /**
   * 初始化用户创建/编辑模态控制器。
   *
   * @param {void} 无参数。依赖全局 UserModals。
   * @returns {void}
   */
  function initializeUserModals() {
    if (!global.UserModals?.createController) {
      console.warn('UserModals 未加载，创建/编辑模态不可用');
      return;
    }
    userModals = global.UserModals.createController({
      http: global.httpU,
      FormValidator: global.FormValidator,
      ValidationRules: global.ValidationRules,
      toast: global.toast,
      DOMHelpers: global.DOMHelpers,
    });
    userModals.init?.();
  }

  /**
   * 初始化用户列表 gridjs 表格。
   *
   * @param {void} 无参数。直接读取容器与初始数据。
   * @returns {void}
   */
  function initializeGrid() {
    const container = document.getElementById('users-grid');
    if (!container) {
      console.warn('找不到 #users-grid 容器');
      return;
    }
    canManageUsers = container.dataset.canManage === 'true';
    currentUserId = Number(container.dataset.currentUser || 0) || null;
    usersGrid = new GridWrapper(container, {
      search: false,
      sort: false,
      columns: [
        {
          name: 'ID',
          id: 'id',
          width: '90px',
          formatter: (cell) => renderIdChip(cell),
        },
        {
          name: '用户',
          id: 'username',
          formatter: (cell, row) => renderUserCell(cell, resolveRowMeta(row)),
        },
        {
          name: '角色',
          id: 'role',
          width: '110px',
          formatter: (cell) => renderRoleChip(cell),
        },
        {
          name: '状态',
          id: 'is_active',
          width: '70px',
          formatter: (cell) => renderStatusPill(Boolean(cell)),
        },
        {
          name: '创建时间',
          id: 'created_at',
          formatter: (cell, row) => renderTimestamp(resolveRowMeta(row), cell),
        },
        {
          name: '操作',
          id: 'actions',
          sort: false,
          formatter: (cell, row) => renderActionButtons(resolveRowMeta(row)),
        },
      ],
      server: {
        url: '/users/api/users?sort=created_at&order=desc',
        headers: {
          'X-Requested-With': 'XMLHttpRequest',
        },
        then: (response) => {
          const payload = response?.data || response || {};
          const items = payload.items || payload.users || [];
          return items.map((item) => [
            item.id,
            item.username || '-',
            item.role,
            item.is_active,
            item.created_at_display || item.created_at || '-',
            item,
          ]);
        },
        total: (response) => {
          const payload = response?.data || response || {};
          return payload.total || payload.pagination?.total || 0;
        },
      },
    });

    const initialFilters = normalizeGridFilters(resolveUserFilters(resolveFormElement()));
    usersGrid.init();
    bindGridActionDelegation(container);
    if (initialFilters && Object.keys(initialFilters).length > 0) {
      usersGrid.setFilters(initialFilters);
    }
  }

  /**
   * 绑定“新建用户”按钮事件。
   *
   * @param {void} 无参数。使用固定 data-action 选择器。
   * @returns {void}
   */
  function bindCreateButton() {
    const createBtn = selectOne('[data-action="create-user"]');
    if (createBtn.length && userModals) {
      createBtn.on('click', (event) => {
        event.preventDefault();
        userModals.openCreate();
      });
    }
  }

  /**
   * 初始化用户过滤器表单。
   *
   * @param {void} 无参数。查找 USER_FILTER_FORM_ID。
   * @returns {void}
   */
  function initializeFilterCard() {
    const form = document.getElementById(USER_FILTER_FORM_ID);
    if (!form) {
      return;
    }
    filterCard = { form };
    form.addEventListener('submit', (event) => {
      event.preventDefault();
      applyUserFilters(form);
    });
    const clearButton = form.querySelector('[data-filter-clear]');
    if (clearButton) {
      clearButton.addEventListener('click', (event) => {
        event.preventDefault();
        resetUserFilters(form);
      });
    }
    const autoInputs = form.querySelectorAll('[data-auto-submit]');
    if (autoInputs.length) {
      const debouncedSubmit = LodashUtils.debounce(() => applyUserFilters(form), 400);
      autoInputs.forEach((input) => {
        input.addEventListener('input', () => debouncedSubmit());
      });
    }
    form.querySelectorAll("select, input[type='checkbox'], input[type='radio']").forEach((element) => {
      element.addEventListener('change', () => applyUserFilters(form));
    });
    if (filterUnloadHandler) {
      from(global).off('beforeunload', filterUnloadHandler);
    }
    filterUnloadHandler = () => {
      destroyFilterCard();
      from(global).off('beforeunload', filterUnloadHandler);
      filterUnloadHandler = null;
    };
    from(global).on('beforeunload', filterUnloadHandler);
  }

  /**
   * 销毁过滤器相关资源。
   *
   * @param {void} 无参数。重置 filterCard 状态。
   * @returns {void}
   */
  function destroyFilterCard() {
    filterCard = null;
  }

  /**
   * 将筛选条件应用到 grid 或跳转到新 URL。
   *
   * @param {HTMLFormElement|string|EventTarget} form 源表单或选择器。
   * @param {Object} [overrideValues] 额外覆盖的过滤值。
   * @returns {void}
   */
  function applyUserFilters(form, overrideValues) {
    const targetForm = resolveFormElement(form);
    if (!targetForm) {
      return;
    }
    const filters = normalizeGridFilters(resolveUserFilters(targetForm, overrideValues));
    const searchTerm = filters.search || '';
    if (typeof searchTerm === 'string' && searchTerm.trim().length > 0 && searchTerm.trim().length < 2) {
      global.toast?.warning?.('搜索关键词至少需要2个字符');
      return;
    }
    if (usersGrid) {
      usersGrid.updateFilters(filters);
      return;
    }
    const params = buildQueryParams(filters);
    const action = targetForm.getAttribute('action') || global.location.pathname;
    const query = params.toString();
    global.location.href = query ? `${action}?${query}` : action;
  }

  /**
   * 重置表单并重新加载数据。
   *
   * @param {HTMLFormElement|string|EventTarget} form 需要重置的元素。
   * @returns {void}
   */
  function resetUserFilters(form) {
    const targetForm = resolveFormElement(form);
    if (targetForm) {
      targetForm.reset();
    }
    applyUserFilters(targetForm, {});
  }

  /**
   * 根据 FormData 解析过滤条件。
   *
   * @param {HTMLFormElement} form 当前筛选表单。
   * @param {Object} [overrideValues] 需要覆盖的键值对。
   * @returns {Object} 解析后的过滤对象。
   */
  function resolveUserFilters(form, overrideValues) {
    const rawValues = overrideValues && Object.keys(overrideValues || {}).length ? overrideValues : collectFormValues(form);
    const safeEntries = Object.entries(rawValues || {}).filter(
      ([key]) => isAllowedFilterKey(key),
    );
    return safeEntries.reduce((result, [key, value]) => {
      const normalized = sanitizeFilterValue(value);
      if (normalized === null || normalized === undefined) {
        return result;
      }
      if (Array.isArray(normalized) && !normalized.length) {
        return result;
      }
      assignFilterField(result, key, normalized);
      return result;
    }, {});
  }

  /**
   * 清理空值，保留有效过滤项。
   *
   * @param {Object} filters 原始过滤器。
   * @returns {Object} 过滤后的结果。
   */
  function normalizeGridFilters(filters) {
    const normalized = filters || {};
    const cleaned = {};
    const role = normalized.role;
    const status = normalized.status;
    if (role && role !== 'all') {
      cleaned.role = role;
    }
    if (status && status !== 'all') {
      cleaned.status = status;
    }
    if (normalized.username) {
      cleaned.username = normalized.username;
    }
    if (normalized.email) {
      cleaned.email = normalized.email;
    }
    if (normalized.search) {
      cleaned.search = normalized.search;
    }
    return cleaned;
  }

  /**
   * 过滤输入，转换空/默认值为 null。
   *
   * @param {*} value 表单原值。
   * @returns {*|null} 规范化后的结果。
   */
  function sanitizeFilterValue(value) {
    if (Array.isArray(value)) {
      return LodashUtils.compact(value.map((item) => sanitizePrimitiveValue(item)));
    }
    return sanitizePrimitiveValue(value);
  }

  /**
   * 规范化单个表单值。
   *
   * @param {*} value 原始输入值。
   * @returns {*|null} 处理后的结果。
   */
  function sanitizePrimitiveValue(value) {
    if (value instanceof File) {
      return value.name;
    }
    if (typeof value === 'string') {
      const trimmed = value.trim();
      return trimmed === '' ? null : trimmed;
    }
    if (value === undefined || value === null) {
      return null;
    }
    return value;
  }

  /**
   * 将过滤条件编码成 URLSearchParams。
   *
   * @param {Object} filters 经过 normalize 的过滤对象。
   * @returns {URLSearchParams} 查询参数实例。
   */
  function buildQueryParams(filters) {
    const params = new URLSearchParams();
    Object.entries(filters || {}).forEach(([key, value]) => {
      if (Array.isArray(value)) {
        value.forEach((item) => params.append(key, item));
      } else {
        params.append(key, value);
      }
    });
    return params;
  }

  /**
   * 接受 selector/元素，返回 DOM 表单。
   *
   * @param {HTMLFormElement|string|Object} form 选择器、元素或 Umbrella 集合。
   * @returns {HTMLFormElement|null} 匹配的表单。
   */
  function resolveFormElement(form) {
    if (!form && filterCard?.form) {
      return filterCard.form;
    }
    if (!form) {
      return selectOne(`#${USER_FILTER_FORM_ID}`).first();
    }
    if (form instanceof Element) {
      return form;
    }
    if (form && typeof form.current === 'function') {
      return form.current();
    }
    if (form && typeof form.first === 'function') {
      return form.first();
    }
    return form;
  }

  /**
   * 收集表单数据，兼容 serializeForm 缺失。
   *
   * @param {HTMLFormElement} form 目标表单。
   * @returns {Object} 键值形式的表单数据。
   */
  function collectFormValues(form) {
    const serializer = global.UI?.serializeForm;
    if (serializer) {
      return serializer(form);
    }
    if (!form) {
      return {};
    }
    const formData = new FormData(form);
    const result = Object.create(null);
    formData.forEach((value, key) => {
      if (!isAllowedFilterKey(key)) {
        return;
      }
      const normalized = value instanceof File ? value.name : value;
      const existing = getFilterField(result, key);
      if (existing === undefined) {
        assignFilterField(result, key, normalized);
        return;
      }
      if (Array.isArray(existing)) {
        existing.push(normalized);
        assignFilterField(result, key, existing);
        return;
      }
      assignFilterField(result, key, [existing, normalized]);
    });
    return result;
  }

  /**
   * 简单 HTML 转义。
   *
   * @param {*} value 需要转义的值。
   * @returns {string} 安全字符串。
   */
  function escapeHtmlValue(value) {
    if (value === undefined || value === null) {
      return '';
    }
    return String(value)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
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
   * @returns {void}
   */
  async function requestDeleteUser(userId, username) {
    if (!userService || !userId || !canManageUsers) {
      return;
    }
    if (Number(userId) === Number(currentUserId)) {
      global.toast?.warning?.('不能删除当前登录用户');
      return;
    }

    const confirmDanger = global.UI?.confirmDanger;
    if (typeof confirmDanger !== 'function') {
      global.toast?.error?.('确认组件未初始化');
      return;
    }

    const displayName = username || `ID: ${userId}`;
    const confirmed = await confirmDanger({
      title: '确认删除用户',
      message: '该操作不可撤销，请确认影响范围后继续。',
      details: [
        { label: '目标用户', value: displayName, tone: 'danger' },
        { label: '不可撤销', value: '删除后将无法恢复', tone: 'danger' },
      ],
      confirmText: '确认删除',
      confirmButtonClass: 'btn-danger',
    });
    if (!confirmed) {
      return;
    }
    const trigger = selectOne(`[data-action="delete-user"][data-user-id="${userId}"]`);
    showLoadingState(trigger, '删除中...');
    userService
      .deleteUser(userId)
      .then((data) => {
        if (data?.success) {
          global.toast?.success?.(data.message || '用户删除成功');
          usersGrid?.refresh?.();
        } else {
          throw new Error(data?.message || '删除用户失败');
        }
      })
      .catch((error) => {
        console.error('删除用户失败', error);
        global.toast?.error?.(error?.message || '删除用户失败');
      })
      .finally(() => hideLoadingState(trigger, '删除'));
  }

  /**
   * 在按钮上展示加载状态。
   *
   * @param {Element|string|Object} element 目标按钮或选择器。
   * @param {string} text 加载提示。
   * @returns {void}
   */
  function showLoadingState(element, text) {
    const target = from(element);
    if (!target.length) {
      return;
    }
    target.attr('data-original-text', target.html());
    target.html(`<i class="fas fa-spinner fa-spin me-2"></i>${text}`);
    target.attr('disabled', 'disabled');
  }

  /**
   * 恢复按钮原样。
   *
   * @param {Element|string|Object} element 目标按钮。
   * @param {string} [fallbackText] 当无缓存时使用的文案。
   * @returns {void}
   */
  function hideLoadingState(element, fallbackText) {
    const target = from(element);
    if (!target.length) {
      return;
    }
    const original = target.attr('data-original-text');
    target.html(original || fallbackText || '删除');
    target.attr('disabled', null);
    target.attr('data-original-text', null);
  }

  function resolveRowMeta(row) {
    if (!row?.cells?.length) {
      return {};
    }
    return row.cells[row.cells.length - 1]?.data || {};
  }

  function renderIdChip(value) {
    const text = value ? `#${value}` : '-';
    if (!gridHtml) {
      return text;
    }
    return gridHtml(buildChipOutlineHtml(text, 'muted'));
  }

  function renderUserCell(cell, meta) {
    const username = escapeHtmlValue(cell || '-');
    const emailChip = meta.email
      ? `<div class="ledger-chip-stack mt-1"><span class="ledger-chip ledger-chip--muted"><i class="fas fa-envelope me-1"></i>${escapeHtmlValue(meta.email)}</span></div>`
      : '';
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
    admin: { label: '管理员', icon: 'fas fa-shield-alt', tone: 'brand' },
    user: { label: '普通用户', icon: 'fas fa-user', tone: 'muted' },
    viewer: { label: '查看者', icon: 'fas fa-eye', tone: 'muted' },
  };

  function renderRoleChip(roleValue) {
    let meta;
    switch (roleValue) {
      case 'admin':
        meta = ROLE_META.admin;
        break;
      case 'user':
        meta = ROLE_META.user;
        break;
      case 'viewer':
        meta = ROLE_META.viewer;
        break;
      default:
        meta = { label: roleValue || '-', icon: 'fas fa-user-tag', tone: 'muted' };
        break;
    }
    if (!gridHtml) {
      return meta.label;
    }
    return gridHtml(buildChipOutlineHtml(meta.label, meta.tone === 'brand' ? 'brand' : 'muted', meta.icon));
  }

  function renderStatusPill(isActive) {
    const text = isActive ? '启用' : '停用';
    if (!gridHtml) {
      return text;
    }
    const icon = isActive ? 'fas fa-check-circle' : 'fas fa-ban';
    const variant = isActive ? 'success' : 'muted';
    return gridHtml(buildStatusPillHtml(text, variant, icon));
  }

  function renderTimestamp(meta, cell) {
    const value = meta.created_at_display || cell || '-';
    if (!gridHtml) {
      return value;
    }
    return gridHtml(`<span class="text-muted small">${escapeHtmlValue(value)}</span>`);
  }

  function renderActionButtons(meta) {
    if (!canManageUsers) {
      return gridHtml ? gridHtml('<span class="text-muted small">只读</span>') : '只读';
    }
    const userId = meta.id;
    if (!userId) {
      return '';
    }
    const isSelf = currentUserId && Number(userId) === Number(currentUserId);
    const deleteDisabled = isSelf ? 'disabled' : '';
    const encodedUsername = encodeURIComponent(meta.username || '');
    const deleteTitle = isSelf ? '不能删除当前登录用户' : '删除用户';
    if (!gridHtml) {
      return isSelf ? '编辑' : '编辑/删除';
    }
    return gridHtml(`
      <div class="d-flex justify-content-center gap-2">
        <button type="button" class="btn btn-outline-secondary btn-icon" data-action="edit-user" data-user-id="${userId}" title="编辑用户">
          <i class="fas fa-edit"></i>
        </button>
        <button type="button" class="btn btn-outline-secondary btn-icon text-danger" data-action="delete-user" data-user-id="${userId}" data-username="${encodedUsername}" ${deleteDisabled} title="${deleteTitle}">
          <i class="fas fa-trash"></i>
        </button>
      </div>
    `);
  }

  function buildChipOutlineHtml(text, tone = 'muted', iconClass) {
    const toneClass = tone === 'brand' ? 'chip-outline--brand' : 'chip-outline--muted';
    const iconHtml = iconClass ? `<i class="${iconClass}" aria-hidden="true"></i>` : '';
    return `<span class="chip-outline ${toneClass}">${iconHtml}${escapeHtmlValue(text)}</span>`;
  }

  function buildStatusPillHtml(text, variant = 'muted', iconClass) {
    const classes = ['status-pill'];
    if (variant) {
      classes.push(`status-pill--${variant}`);
    }
    const iconHtml = iconClass ? `<i class="${iconClass}" aria-hidden="true"></i>` : '';
    return `<span class="${classes.join(' ')}">${iconHtml}${escapeHtmlValue(text)}</span>`;
  }

  ready(() => {
    userService = new UserService(http);
    initializeUserModals();
    initializeGrid();
    initializeFilterCard();
    bindCreateButton();
  });

  /**
   * 统一处理表格内动作按钮，避免字符串 onclick。
   *
   * @param {HTMLElement} container grid 容器。
   * @returns {void}
   */
  function bindGridActionDelegation(container) {
    if (!container || gridActionDelegationBound) {
      return;
    }
    container.addEventListener('click', (event) => {
      const actionBtn = event.target.closest('[data-action]');
      if (!actionBtn || !container.contains(actionBtn)) {
        return;
      }
      const action = actionBtn.getAttribute('data-action');
      const userId = actionBtn.getAttribute('data-user-id');
      switch (action) {
        case 'edit-user':
          event.preventDefault();
          openUserEditor(userId);
          break;
        case 'delete-user': {
          event.preventDefault();
          const encoded = actionBtn.getAttribute('data-username') || '';
          const username = encoded ? decodeURIComponent(encoded) : '';
          requestDeleteUser(userId, username);
          break;
        }
        default:
          break;
      }
    });
    gridActionDelegationBound = true;
  }

  global.AuthListActions = {
    openEditor: openUserEditor,
    requestDelete: requestDeleteUser,
  };
}

window.AuthListPage = {
  mount: function () {
    mountAuthListPage(window);
  },
};
