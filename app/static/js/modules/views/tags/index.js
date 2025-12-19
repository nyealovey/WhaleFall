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

  const http = global.httpU;
  const gridHtml = gridjs.html;
  const { ready, selectOne, from } = helpers;
  let statsContainer = null;

  const TAG_FILTER_FORM_ID = "tag-filter-form";
  let tagsGrid = null;
  let filterCard = null;
  let filterUnloadHandler = null;
  let tagModals = null;
  let deleteModal = null;
  let pendingDeleteTagId = null;
  let canManageTags = false;
  let gridActionDelegationBound = false;

  ready(() => {
    statsContainer = document.getElementById('tagStatsContainer');
    initializeTagModals();
    initializeGrid();
    initializeDeleteModal();
    initializeFilterCard();
    bindQuickActions();
  });

  /**
   * 初始化标签表格。
   *
   * 创建 Grid.js 表格实例，配置列定义、服务端分页和筛选。
   * 根据用户权限动态显示操作列。
   *
   * @return {void}
   */
  function initializeGrid() {
    const container = document.getElementById("tags-grid");
    if (!container) {
      console.warn("找不到 #tags-grid 容器");
      return;
    }
    canManageTags = container.dataset.canManage === "true";
    tagsGrid = new GridWrapper(container, {
      search: false,
      sort: false,
      columns: [
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
      ],
      server: {
        url: "/tags/api/list",
        headers: {
          "X-Requested-With": "XMLHttpRequest",
        },
        then: (response) => {
          const payload = response?.data || response || {};
          updateTagStats(payload.stats);
          const items = payload.items || [];
          return items.map((item) => [
            item.display_name || item.name || "-",
            item.category || "-",
            item.color_name || item.color || "-",
            item.is_active,
            item.instance_count || 0,
            item,
          ]);
        },
        total: (response) => {
          const payload = response?.data || response || {};
          return payload.total || 0;
        },
      },
    });

    const initialFilters = normalizeGridFilters(resolveTagFilters(resolveFormElement()));
    tagsGrid.init();
    bindGridActionDelegation(container);
    if (initialFilters && Object.keys(initialFilters).length > 0) {
      tagsGrid.setFilters(initialFilters);
    }
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
      http: global.httpU,
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
      createBtn.on('click', (event) => {
        event.preventDefault();
        tagModals.openCreate();
      });
    }
  }

  /**
   * 初始化删除确认模态。
   *
   * @returns {void} 创建 modal 控制器并注册钩子。
   */
  function initializeDeleteModal() {
    const factory = global.UI?.createModal;
    if (!factory) {
      console.error('UI.createModal 未加载，删除模态无法初始化');
      return;
    }
    deleteModal = factory({
      modalSelector: '#deleteModal',
      confirmSelector: '#confirmDeleteTag',
      onOpen: ({ payload }) => {
        const { tagName } = payload || {};
        selectOne('#deleteTagName').text(tagName || '');
      },
      onConfirm: handleDeleteConfirmation,
      onClose: () => {
        pendingDeleteTagId = null;
      },
    });
  }

  /**
   * 打开删除模态。
   *
   * @param {number|string} tagId 标签 ID。
   * @param {string} tagName 标签名称。
   * @returns {void} 设置待删除标签并打开模态。
   */
  function confirmDeleteTag(tagId, tagName) {
    pendingDeleteTagId = tagId;
    deleteModal?.open({ tagName });
  }

  /**
   * 删除模态确认按钮处理。
   *
   * @param {Event} event 点击事件。
   * @returns {void} 调用删除接口并提示结果。
   */
  function handleDeleteConfirmation(event) {
    event?.preventDefault?.();
    if (!pendingDeleteTagId) {
      return;
    }
    const target = selectOne('#confirmDeleteTag');
    showLoadingState(target, '删除中...');
    http
      .post(`/tags/api/delete/${pendingDeleteTagId}`, {})
      .then((resp) => {
        if (!resp?.success) {
          throw new Error(resp?.message || '删除标签失败');
        }
        global.toast?.success?.(resp?.message || '删除标签成功');
        tagsGrid?.refresh?.();
      })
      .catch((error) => {
        console.error('删除标签失败', error);
        global.toast?.error?.(resolveErrorMessage(error, '删除标签失败'));
      })
      .finally(() => {
        hideLoadingState(target, '确认删除');
        pendingDeleteTagId = null;
        deleteModal?.close?.();
      });
  }

  /**
   * 初始化标签筛选表单。
   *
   * @returns {void} 绑定表单事件并注册卸载钩子。
   */
  function initializeFilterCard() {
    const form = document.getElementById(TAG_FILTER_FORM_ID);
    if (!form) {
      return;
    }
    filterCard = { form };
    form.addEventListener('submit', (event) => {
      event.preventDefault();
      applyTagFilters(form);
    });
    const clearButton = form.querySelector('[data-filter-clear]');
    if (clearButton) {
      clearButton.addEventListener('click', (event) => {
        event.preventDefault();
        resetTagFilters(form);
      });
    }
    const autoInputs = form.querySelectorAll('[data-auto-submit]');
    if (autoInputs.length) {
      const debouncedSubmit = LodashUtils.debounce(() => applyTagFilters(form), 400);
      autoInputs.forEach((input) => {
        input.addEventListener('input', () => debouncedSubmit());
      });
    }
    form.querySelectorAll("select, input[type='checkbox'], input[type='radio']").forEach((element) => {
      element.addEventListener('change', () => applyTagFilters(form));
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
   * 销毁筛选卡片引用。
   *
   * @returns {void} 清空内部引用，避免内存泄露。
   */
  function destroyFilterCard() {
    filterCard = null;
  }

  /**
   * 应用筛选条件。
   *
   * @param {HTMLFormElement|Element|string} form 表单或选择器。
   * @param {Object} [overrideValues] 额外的过滤参数。
   * @returns {void} 更新 Grid。
   */
  function applyTagFilters(form, overrideValues) {
    const targetForm = resolveFormElement(form);
    if (!targetForm) {
      return;
    }
    const filters = normalizeGridFilters(resolveTagFilters(targetForm, overrideValues));
    const searchTerm = filters.search || "";
    if (typeof searchTerm === "string" && searchTerm.trim().length > 0 && searchTerm.trim().length < 2) {
      global.toast?.warning?.("搜索关键词至少需要2个字符");
      return;
    }
    if (!tagsGrid) {
      console.error('tagsGrid 未初始化，无法应用筛选');
      return;
    }
    tagsGrid.updateFilters(filters);
  }

  /**
   * 重置筛选表单。
   *
   * @param {HTMLFormElement|Element|string} form 表单引用。
   * @returns {void} 清空表单并重新应用筛选。
   */
  function resetTagFilters(form) {
    const targetForm = resolveFormElement(form);
    if (targetForm) {
      targetForm.reset();
    }
    applyTagFilters(targetForm, {});
  }

  /**
   * 解析表单字段。
   *
   * @param {HTMLFormElement|Element|string} form 表单。
   * @param {Object} [overrideValues] 外部传入值。
   * @returns {Object} 过滤值。
   */
  const UNSAFE_KEYS = ['__proto__', 'prototype', 'constructor'];
  const ALLOWED_FILTER_KEYS = ['name', 'display_name', 'category', 'status', 'search', 'page', 'page_size', 'sort', 'direction'];
  const isSafeKey = (key) => typeof key === 'string' && !UNSAFE_KEYS.includes(key);
  const isAllowedFilterKey = (key) => isSafeKey(key) && ALLOWED_FILTER_KEYS.includes(key);

  function assignFilterField(target, key, value) {
    switch (key) {
      case 'name':
        target.name = value;
        break;
      case 'display_name':
        target.display_name = value;
        break;
      case 'category':
        target.category = value;
        break;
      case 'status':
        target.status = value;
        break;
      case 'search':
        target.search = value;
        break;
      case 'page':
        target.page = value;
        break;
      case 'page_size':
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
      case 'name':
        return target.name;
      case 'display_name':
        return target.display_name;
      case 'category':
        return target.category;
      case 'status':
        return target.status;
      case 'search':
        return target.search;
      case 'page':
        return target.page;
      case 'page_size':
        return target.page_size;
      case 'sort':
        return target.sort;
      case 'direction':
        return target.direction;
      default:
        return undefined;
    }
  }

  function resolveTagFilters(form, overrideValues) {
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
   * 清理空值，返回有效 filters。
   */
  /**
   * 规范化筛选对象，移除空值。
   *
   * @param {Object} filters 原始过滤条件。
   * @returns {Object} 去除空值后的过滤结果。
   */
  function normalizeGridFilters(filters) {
    const normalized = filters || {};
    const cleaned = {};
    if (normalized.name) cleaned.name = normalized.name;
    if (normalized.display_name) cleaned.display_name = normalized.display_name;
    if (normalized.search) cleaned.search = normalized.search;
    if (normalized.category && normalized.category !== 'all') cleaned.category = normalized.category;
    if (normalized.status && normalized.status !== 'all') cleaned.status = normalized.status;
    return cleaned;
  }

  /**
   * 规范化单个过滤值。
   *
   * @param {any} value 原始值。
   * @returns {any} 处理后的值或 null。
   */
  function sanitizeFilterValue(value) {
    if (Array.isArray(value)) {
      return LodashUtils.compact(value.map((item) => sanitizePrimitiveValue(item)));
    }
    return sanitizePrimitiveValue(value);
  }

  /**
   * 处理基本类型的过滤值。
   *
   * @param {any} value 输入值。
   * @returns {string|number|null} 标准化后的基本类型。
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
   * 将过滤值编码为 URLSearchParams。
   *
   * @param {Object} filters 过滤条件。
   * @returns {URLSearchParams} URL 查询参数。
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
   * 统一处理 selector/DOM 对象。
   *
   * @param {HTMLFormElement|Element|string|Object|null} form 多种形态的表单参数。
   * @returns {HTMLFormElement|null} 解析后的原生表单。
   */
  function resolveFormElement(form) {
    if (!form && filterCard?.form) {
      return filterCard.form;
    }
    if (!form) {
      return selectOne(`#${TAG_FILTER_FORM_ID}`).first();
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
   * 收集表单字段。
   *
   * @param {HTMLFormElement} form 目标表单。
   * @returns {Object} 键值对形式的表单数据。
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
      } else if (Array.isArray(existing)) {
        existing.push(normalized);
        assignFilterField(result, key, existing);
      } else {
        assignFilterField(result, key, [existing, normalized]);
      }
    });
    return result;
  }

  /**
   * 简单 HTML 转义。
   *
   * @param {string} value 待处理字符串。
   * @returns {string} 转义后的字符串。
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

  /**
   * 显示按钮 loading 状态。
   *
   * @param {Element|import('umbrella-storage').default} target 目标元素或包装器。
   * @param {string} text 加载中文案。
   * @returns {void} 更新按钮内容与禁用状态。
   */
  function showLoadingState(target, text) {
    const element = from(target);
    if (!element.length) {
      return;
    }
    element.attr('data-original-text', element.html());
    element.html(`<i class="fas fa-spinner fa-spin me-2"></i>${text}`);
    element.attr('disabled', 'disabled');
  }

  /**
   * 恢复按钮默认状态。
   *
   * @param {Element|import('umbrella-storage').default} target 目标元素。
   * @param {string} fallbackText 默认文本。
   * @returns {void} 恢复按钮内容并解除禁用。
   */
  function hideLoadingState(target, fallbackText) {
    const element = from(target);
    if (!element.length) {
      return;
    }
    const original = element.attr('data-original-text');
    element.html(original || fallbackText || '');
    element.attr('disabled', null);
    element.attr('data-original-text', null);
  }

  function resolveRowMeta(row) {
    if (!row?.cells?.length) {
      return {};
    }
    return row.cells[row.cells.length - 1]?.data || {};
  }

  function renderTagCell(meta) {
    const displayName = escapeHtmlValue(meta.display_name || meta.name || '-');
    const code = meta.name ? `#${escapeHtmlValue(meta.name)}` : '';
    if (!gridHtml) {
      return code ? `${displayName} (${code})` : displayName;
    }
    return gridHtml(`
      <div>
        <div class="fw-semibold">${displayName}</div>
        ${code ? `<div class="tags-name-cell__code">${code}</div>` : ''}
      </div>
    `);
  }

  function renderCategoryChip(meta) {
    const category = meta.category || '-';
    if (!gridHtml) {
      return category;
    }
    return gridHtml(buildChipOutlineHtml(category, 'muted', 'fas fa-bookmark')); 
  }

  function renderColorChip(meta) {
    const colorName = meta.color_name || meta.color || '-';
    if (!gridHtml) {
      return colorName;
    }
    const tone = meta.color ? 'brand' : 'muted';
    return gridHtml(buildChipOutlineHtml(colorName, tone, 'fas fa-fill-drip'));
  }

  function renderBindings(meta) {
    const instanceCount = Number(meta.instance_count) || 0;
    if (!gridHtml) {
      return instanceCount ? `实例 ${instanceCount}` : '无关联';
    }
    const chips = instanceCount
      ? [buildLedgerChipHtml(`<i class="fas fa-database"></i>实例 ${instanceCount}`)]
      : [buildLedgerChipHtml('<i class="fas fa-minus"></i>无关联', true)];
    return gridHtml(`<div class="ledger-chip-stack">${chips.join('')}</div>`);
  }

  function renderActionButtons(meta) {
    if (!canManageTags) {
      return gridHtml ? gridHtml('<span class="text-muted small">只读</span>') : '只读';
    }
    const tagId = meta.id;
    if (!tagId) {
      return '';
    }
    const encodedName = encodeURIComponent(meta.display_name || meta.name || '');
    if (!gridHtml) {
      return '管理';
    }
    return gridHtml(`
      <div class="d-flex justify-content-center gap-2">
        <button type="button" class="btn btn-outline-secondary btn-icon" data-action="edit-tag" data-tag-id="${tagId}" title="编辑">
          <i class="fas fa-edit"></i>
        </button>
        <button type="button" class="btn btn-outline-secondary btn-icon text-danger" data-action="delete-tag" data-tag-id="${tagId}" data-tag-name="${encodedName}" title="删除">
          <i class="fas fa-trash"></i>
        </button>
      </div>
    `);
  }

  function renderStatusPill(isActive) {
    const text = isActive ? '启用' : '停用';
    if (!gridHtml) {
      return text;
    }
    const variant = isActive ? 'success' : 'muted';
    const icon = isActive ? 'fas fa-check-circle' : 'fas fa-ban';
    return gridHtml(buildStatusPillHtml(text, variant, icon));
  }

  function buildChipOutlineHtml(text, tone = 'muted', iconClass) {
    const classes = ['chip-outline'];
    classes.push(tone === 'brand' ? 'chip-outline--brand' : 'chip-outline--muted');
    const iconHtml = iconClass ? `<i class="${iconClass}" aria-hidden="true"></i>` : '';
    return `<span class="${classes.join(' ')}">${iconHtml}${text ? escapeHtmlValue(text) : '-'}</span>`;
  }

  function buildStatusPillHtml(text, variant = 'muted', iconClass) {
    const classes = ['status-pill'];
    if (variant) {
      classes.push(`status-pill--${variant}`);
    }
    const iconHtml = iconClass ? `<i class="${iconClass}" aria-hidden="true"></i>` : '';
    return `<span class="${classes.join(' ')}">${iconHtml}${escapeHtmlValue(text || '-')}</span>`;
  }

  function buildLedgerChipHtml(content, muted = false) {
    const classes = ['ledger-chip'];
    if (muted) {
      classes.push('ledger-chip--muted');
    }
    return `<span class="${classes.join(' ')}">${content}</span>`;
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
      if (typeof value === 'undefined' || value === null) {
        return;
      }
      const card = statsContainer.querySelector(`[data-stat-key="${key}"]`);
      if (!card) {
        return;
      }
      const valueEl = card.querySelector('.tags-stat-card__value');
      if (valueEl) {
        valueEl.textContent = value;
      }
    });
  }

  function resolveErrorMessage(error, fallback) {
    if (!error) {
      return fallback;
    }
    if (error.response?.message) {
      return error.response.message;
    }
    if (error.response?.data?.message) {
      return error.response.data.message;
    }
    if (typeof error.response === 'string') {
      return error.response;
    }
    if (error.message) {
      return error.message;
    }
    return fallback;
  }

  /**
   * 绑定 Grid 内动作按钮，替代字符串 onclick。
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
      const tagId = actionBtn.getAttribute('data-tag-id');
      switch (action) {
        case 'edit-tag':
          event.preventDefault();
          openTagEditor(tagId);
          break;
        case 'delete-tag': {
          event.preventDefault();
          const encodedName = actionBtn.getAttribute('data-tag-name') || '';
          const decodedName = encodedName ? decodeURIComponent(encodedName) : '';
          confirmDeleteTag(tagId, decodedName);
          break;
        }
        default:
          break;
      }
    });
    gridActionDelegationBound = true;
  }

  global.TagsIndexActions = {
    openEditor: openTagEditor,
    confirmDelete: confirmDeleteTag,
  };
}

window.TagsIndexPage = {
  mount: function () {
    mountTagsIndexPage(window);
  },
};
