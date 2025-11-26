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
  const { ready, selectOne, select, from } = helpers;

  const TAG_FILTER_FORM_ID = "tag-filter-form";
  let tagsGrid = null;
  let filterCard = null;
  let filterUnloadHandler = null;
  let tagModals = null;
  let deleteModal = null;
  let pendingDeleteTagId = null;
  let canManageTags = false;

  ready(() => {
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
        { name: "排序", id: "sort_order" },
        {
          name: "标签代码",
          id: "name",
          formatter: (cell) => (gridHtml ? gridHtml(`<code>${escapeHtmlValue(cell)}</code>`) : cell || "-"),
        },
        {
          name: "显示名称",
          id: "display_name",
          formatter: (cell, row) => {
            const meta = row?.cells?.[row.cells.length - 1]?.data || {};
            const color = meta.color || "primary";
            const name = escapeHtmlValue(cell || "-");
            return gridHtml
              ? gridHtml(`<span class="badge bg-${escapeHtmlValue(color)}">${name}</span>`)
              : name;
          },
        },
        { name: "分类", id: "category" },
        {
          name: "描述",
          id: "description",
          formatter: (cell) => (cell ? gridHtml ? gridHtml(`<small class="text-muted">${escapeHtmlValue(cell)}</small>`) : cell : gridHtml ? gridHtml('<span class="text-muted">无</span>') : "无"),
        },
        {
          name: "状态",
          id: "is_active",
          formatter: (cell) => {
            const isActive = Boolean(cell);
            if (!gridHtml) {
              return isActive ? "激活" : "禁用";
            }
            const color = isActive ? "success" : "secondary";
            const text = isActive ? "激活" : "禁用";
            return gridHtml(`<span class="badge bg-${color}">${text}</span>`);
          },
        },
        {
          name: "实例数量",
          id: "instance_count",
          formatter: (cell) => {
            const count = Number(cell) || 0;
            if (!gridHtml) {
              return `${count}`;
            }
            return gridHtml(
              `<span class="badge bg-info"><i class="fas fa-database me-1"></i>${count}</span>`
            );
          },
        },
        {
          name: "操作",
          sort: false,
          formatter: (cell, row) => {
            const meta = row?.cells?.[row.cells.length - 1]?.data || {};
            if (!canManageTags) {
              return gridHtml ? gridHtml('<span class="text-muted small">只读</span>') : "";
            }
            const tagId = meta.id;
            const tagNameLiteral = JSON.stringify(meta.display_name || meta.name || "");
            return gridHtml
              ? gridHtml(`
                <div class="btn-group btn-group-sm" role="group">
                  <button type="button" class="btn btn-outline-warning" onclick="TagsIndexActions.openEditor(${tagId})" title="编辑">
                    <i class="fas fa-edit"></i>
                  </button>
                  <button type="button" class="btn btn-outline-danger" onclick="TagsIndexActions.confirmDelete(${tagId}, ${tagNameLiteral})" title="删除">
                    <i class="fas fa-trash"></i>
                  </button>
                </div>
              `)
              : "";
          },
        },
      ],
      server: {
        url: "/tags/api/list?sort=sort_order&order=asc",
        headers: {
          "X-Requested-With": "XMLHttpRequest",
        },
        then: (response) => {
          const payload = response?.data || response || {};
          const items = payload.items || [];
          return items.map((item) => [
            item.sort_order ?? "-",
            item.name || "-",
            item.display_name || "-",
            item.category || "-",
            item.description || "",
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
        global.toast?.error?.(error?.message || '删除标签失败');
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
   * @returns {void} 更新 Grid 或回退到 GET 请求。
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
    if (tagsGrid) {
      tagsGrid.updateFilters(filters);
      return;
    }
    const params = buildQueryParams(filters);
    const action = targetForm.getAttribute('action') || global.location.pathname;
    const query = params.toString();
    global.location.href = query ? `${action}?${query}` : action;
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
  function resolveTagFilters(form, overrideValues) {
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
    const normalized = { ...(filters || {}) };
    ['category', 'status'].forEach((key) => {
      if (normalized[key] === 'all' || normalized[key] === '') {
        delete normalized[key];
      }
    });
    return normalized;
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
