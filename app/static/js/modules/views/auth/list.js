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

  ready(() => {
    userService = new UserService(http);
    initializeUserModals();
    initializeGrid();
    initializeFilterCard();
    bindCreateButton();
  });

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
          formatter: (cell) => (gridHtml ? gridHtml(`<span class="badge bg-secondary">#${cell}</span>`) : cell),
        },
        {
          name: '用户',
          id: 'username',
          formatter: (cell, row) => {
            const meta = row?.cells?.[row.cells.length - 1]?.data || {};
            const username = escapeHtmlValue(cell || '-');
            const initial = username ? username.charAt(0).toUpperCase() : '-';
            const email = meta.email ? `<br><small class="text-muted">${escapeHtmlValue(meta.email)}</small>` : '';
            if (!gridHtml) {
              return `${username} ${meta.email || ''}`;
            }
            return gridHtml(`
              <div class="d-flex align-items-center">
                <div class="user-avatar me-3">${initial}</div>
                <div><strong>${username}</strong>${email}</div>
              </div>
            `);
          },
        },
        {
          name: '角色',
          id: 'role',
          formatter: (cell) => {
            const isAdmin = cell === 'admin';
            if (!gridHtml) {
              return isAdmin ? '管理员' : '普通用户';
            }
            const icon = isAdmin ? 'crown' : 'user';
            const color = isAdmin ? 'primary' : 'info';
            const text = isAdmin ? '管理员' : '普通用户';
            return gridHtml(`<span class="badge bg-${color}"><i class="fas fa-${icon} me-1"></i>${text}</span>`);
          },
        },
        {
          name: '状态',
          id: 'is_active',
          formatter: (cell) => {
            const isActive = Boolean(cell);
            if (!gridHtml) {
              return isActive ? '活跃' : '停用';
            }
            const color = isActive ? 'success' : 'secondary';
            const icon = isActive ? 'check-circle' : 'times-circle';
            const text = isActive ? '活跃' : '停用';
            return gridHtml(`<span class="badge bg-${color}"><i class="fas fa-${icon} me-1"></i>${text}</span>`);
          },
        },
        {
          name: '创建时间',
          id: 'created_at',
          formatter: (cell, row) => {
            const meta = row?.cells?.[row.cells.length - 1]?.data || {};
            return meta.created_at_display || cell || '-';
          },
        },
        {
          name: '操作',
          sort: false,
          formatter: (cell, row) => {
            const meta = row?.cells?.[row.cells.length - 1]?.data || {};
            if (!canManageUsers) {
              return gridHtml ? gridHtml('<span class="text-muted small">只读</span>') : '';
            }
            const userId = meta.id;
            const usernameLiteral = JSON.stringify(meta.username || '');
            const isSelf = currentUserId && Number(userId) === Number(currentUserId);
            const deleteDisabled = isSelf ? 'disabled' : '';
            return gridHtml
              ? gridHtml(`
                <div class="btn-group btn-group-sm" role="group">
                  <button type="button" class="btn btn-outline-primary" onclick="AuthListActions.openEditor(${userId})" title="编辑用户">
                    <i class="fas fa-edit"></i>
                  </button>
                  <button type="button" class="btn btn-outline-danger" ${deleteDisabled} onclick="AuthListActions.requestDelete(${userId}, ${usernameLiteral})" title="${isSelf ? '不能删除当前登录用户' : '删除用户'}">
                    <i class="fas fa-trash"></i>
                  </button>
                </div>
              `)
              : '';
          },
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
    if (initialFilters && Object.keys(initialFilters).length > 0) {
      usersGrid.setFilters(initialFilters);
    }
  }

  function bindCreateButton() {
    const createBtn = selectOne('[data-action="create-user"]');
    if (createBtn.length && userModals) {
      createBtn.on('click', (event) => {
        event.preventDefault();
        userModals.openCreate();
      });
    }
  }

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

  function destroyFilterCard() {
    filterCard = null;
  }

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

  function resetUserFilters(form) {
    const targetForm = resolveFormElement(form);
    if (targetForm) {
      targetForm.reset();
    }
    applyUserFilters(targetForm, {});
  }

  function resolveUserFilters(form, overrideValues) {
    const rawValues = overrideValues && Object.keys(overrideValues || {}).length ? overrideValues : collectFormValues(form);
    return Object.entries(rawValues || {}).reduce((result, [key, value]) => {
      if (key === 'csrf_token') {
        return result;
      }
      const normalized = sanitizeFilterValue(value);
      if (normalized === null || normalized === undefined) {
        return result;
      }
      if (Array.isArray(normalized) && !normalized.length) {
        return result;
      }
      result[key] = normalized;
      return result;
    }, {});
  }

  function normalizeGridFilters(filters) {
    const normalized = { ...(filters || {}) };
    ['role', 'status'].forEach((key) => {
      if (!normalized[key] || normalized[key] === 'all') {
        delete normalized[key];
      }
    });
    return normalized;
  }

  function sanitizeFilterValue(value) {
    if (Array.isArray(value)) {
      return LodashUtils.compact(value.map((item) => sanitizePrimitiveValue(item)));
    }
    return sanitizePrimitiveValue(value);
  }

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

  function collectFormValues(form) {
    const serializer = global.UI?.serializeForm;
    if (serializer) {
      return serializer(form);
    }
    if (!form) {
      return {};
    }
    const formData = new FormData(form);
    const result = {};
    formData.forEach((value, key) => {
      const normalized = value instanceof File ? value.name : value;
      if (result[key] === undefined) {
        result[key] = normalized;
      } else if (Array.isArray(result[key])) {
        result[key].push(normalized);
      } else {
        result[key] = [result[key], normalized];
      }
    });
    return result;
  }

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

  function openUserEditor(userId) {
    if (!userModals || !userId) {
      return;
    }
    userModals.openEdit(userId);
  }

  function requestDeleteUser(userId, username) {
    if (!userService || !userId || !canManageUsers) {
      return;
    }
    if (Number(userId) === Number(currentUserId)) {
      global.toast?.warning?.('不能删除当前登录用户');
      return;
    }
    const confirmed = global.confirm(`确定要删除用户 "${username || ''}" 吗？此操作不可撤销。`);
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

  function showLoadingState(element, text) {
    const target = from(element);
    if (!target.length) {
      return;
    }
    target.attr('data-original-text', target.html());
    target.html(`<i class="fas fa-spinner fa-spin me-2"></i>${text}`);
    target.attr('disabled', 'disabled');
  }

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
