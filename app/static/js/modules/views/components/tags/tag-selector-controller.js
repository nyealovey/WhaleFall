(function (window, document) {
  "use strict";

  const TagSelectorView = window.TagSelectorView;
  const TagSelectorModalAdapter = window.TagSelectorModalAdapter;
  const TagManagementService = window.TagManagementService;
  const createTagManagementStore = window.createTagManagementStore;
  const LodashUtils = window.LodashUtils;

  if (!TagSelectorView || !TagSelectorModalAdapter || !TagManagementService || !createTagManagementStore) {
    console.error("TagSelectorController 初始化失败: 依赖缺失");
    return;
  }

  const DEFAULT_ENDPOINTS = {
    tags: "/api/v1/tags/options",
    categories: "/api/v1/tags/categories",
  };
  const UNSAFE_KEYS = ["__proto__", "prototype", "constructor"];
  const isSafeKey = (key) => typeof key === "string" && !UNSAFE_KEYS.includes(key);

  function buildSafeEndpoints(custom = {}) {
    const safe = {
      tags: DEFAULT_ENDPOINTS.tags,
      categories: DEFAULT_ENDPOINTS.categories,
    };
    if (custom && typeof custom.tags === "string") {
      safe.tags = custom.tags;
    }
    if (custom && typeof custom.categories === "string") {
      safe.categories = custom.categories;
    }
    return safe;
  }

  function hasLodashMethod(methodName) {
    if (!LodashUtils) {
      return false;
    }
    switch (methodName) {
      case "orderBy":
        return typeof LodashUtils.orderBy === "function";
      case "uniqBy":
        return typeof LodashUtils.uniqBy === "function";
      default:
        return false;
    }
  }

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

  function buildPreviewChip(label, { muted = false } = {}) {
    const classes = ["ledger-chip", muted ? "ledger-chip--muted" : ""].filter(Boolean).join(" ");
    return `<span class="${classes}"><i class="fas fa-tag"></i>${escapeHtml(label)}</span>`;
  }

  function updatePreviewDisplay(previewSelector, chipsSelector, tags = [], limit = 3) {
    const previewEl = toElement(previewSelector);
    const chipsEl = toElement(chipsSelector);
    if (!chipsEl || !previewEl) {
      return;
    }
    if (!tags.length) {
      chipsEl.innerHTML = "";
      previewEl.style.display = "none";
      return;
    }
    const visible = tags.slice(0, limit);
    const html = visible
      .map((tag) => buildPreviewChip(tag.display_name || tag.name || tag.hiddenValue || "", { muted: tag.is_active === false }))
      .join("");
    const overflow = tags.length - visible.length;
    chipsEl.innerHTML = overflow > 0
      ? `${html}<span class="ledger-chip ledger-chip--muted">+${overflow}</span>`
      : html;
    previewEl.style.display = "";
  }

  /**
   * 解析输入为 DOM 元素，兼容字符串/Element/umbrella 对象。
   *
   * @param {string|Element|Object} target - 目标元素
   * @return {Element|null} DOM 元素，未找到则返回 null
   */
  function toElement(target) {
    if (!target) {
      return null;
    }
    if (target instanceof Element) {
      return target;
    }
    if (typeof target === "string") {
      return document.querySelector(target);
    }
    if (target && typeof target.first === "function") {
      return target.first();
    }
    return null;
  }

  /**
   * 排序工具，供 controller 和 view 共享。
   *
   * 按激活状态和显示名称排序标签。
   *
   * @param {Array<Object>} items - 标签数组
   * @return {Array<Object>} 排序后的标签数组
   */
  function orderTags(items) {
    if (!Array.isArray(items)) {
      return [];
    }
    if (hasLodashMethod("orderBy")) {
      return LodashUtils.orderBy(
        items,
        [
          (tag) => (tag.is_active === false ? 1 : 0),
          (tag) => (tag.display_name || tag.name || "").toLowerCase(),
        ],
        ["asc", "asc"],
      );
    }
    return items.slice();
  }

  function pickTagValue(tag, key) {
    if (!tag) {
      return undefined;
    }
    if (isSafeKey(key)) {
      switch (key) {
        case "id":
          return tag.id;
        case "name":
          return tag.name;
        case "display_name":
          return tag.display_name;
        case "hiddenValue":
          return tag.hiddenValue;
        default:
          break;
      }
    }
    if (tag.name !== undefined && tag.name !== null) {
      return tag.name;
    }
    return tag.id;
  }

  /**
   * 视图与 store 的中间层，负责数据同步与外部 API。
   *
   * @class
   */
  class TagSelectorController {
    /**
     * 构造函数。
     *
     * @constructor
     * @param {string|Element} root - 根元素选择器或元素
     * @param {Object} [options] - 配置选项
     * @param {Object} [options.endpoints] - API 端点配置
     * @param {string} [options.hiddenInputSelector] - 隐藏输入框选择器
     * @param {string} [options.hiddenValueKey] - 隐藏值字段名
     * @param {Array} [options.initialValues] - 初始选中值
     * @param {Function} [options.onConfirm] - 确认回调
     * @param {Function} [options.onCancel] - 取消回调
     * @param {Element} [options.modalElement] - 模态框元素
     * @throws {Error} 当 root 未找到时抛出
     */
    constructor(root, options = {}) {
      this.root = toElement(root);
      if (!this.root) {
        throw new Error("TagSelectorController: root 未找到");
      }
      this.id =
        this.root.dataset.tagSelectorId ||
        `tag-selector-${Date.now()}-${Math.floor(Math.random() * 10000)}`;
      this.root.dataset.tagSelectorId = this.id;

      this.options = {
        endpoints: buildSafeEndpoints(options.endpoints),
        hiddenInputSelector: options.hiddenInputSelector || "#selected-tag-names",
        hiddenValueKey: options.hiddenValueKey || "name",
        initialValues: options.initialValues || [],
        onConfirm: options.onConfirm || null,
        onCancel: options.onCancel || null,
        modalElement:
          options.modalElement || this.root.closest("[data-tag-selector-modal]") || null,
      };

      this.state = {
        categories: [],
        tags: [],
        filteredTags: [],
        selection: new Set(),
        stats: { total: 0, selected: 0, active: 0, filtered: 0 },
      };

      this.service = new TagManagementService(window.httpU, this.options.endpoints);
      this.store = createTagManagementStore({
        service: this.service,
        emitter: window.mitt ? window.mitt() : null,
      });

      this.view = new TagSelectorView(this.root, {
        onCategoryChange: (value) => this.handleCategory(value),
        onTagToggle: (id) => this.toggleTag(id),
        onSelectedRemove: (id) => this.removeTag(id),
      });

      this.modal = TagSelectorModalAdapter.createModalAdapter(
        this.options.modalElement,
        {
          onClose: () => this.emitCancel({ reason: "modal-close", hideModal: false }),
          onCancel: () => this.emitCancel({ reason: "modal-cancel" }),
          onConfirm: () => this.confirmSelection(),
        },
      );

      this.readyPromise = this.initialize();
    }

    /**
     * 初始化 store 订阅并同步初始状态。
     *
     * @return {Promise<TagSelectorController>} 返回自身实例
     */
    async initialize() {
      this.bindStoreEvents();
      await this.store.init();
      this.syncFromStore();
      if (this.options.initialValues && this.options.initialValues.length) {
        this.store.actions.selectBy(this.options.initialValues, this.options.hiddenValueKey);
      }
      this.renderAll();
      return this;
    }

    /**
     * 订阅 store 事件，捕获分类/标签/选择的变化。
     *
     * @return {void}
     */
    bindStoreEvents() {
      this.store.subscribe("tagManagement:categoriesUpdated", (payload) => {
        const categories = (payload && payload.categories) || [];
        this.state.categories = categories;
        this.renderCategories();
      });
      this.store.subscribe("tagManagement:tagsUpdated", (payload) => {
        const tags = (payload && payload.tags) || [];
        const filteredTags = (payload && payload.filteredTags) || tags;
        this.state.tags = orderTags(tags);
        this.state.filteredTags = orderTags(filteredTags);
        this.state.stats = (payload && payload.stats) || this.state.stats;
        this.renderTags();
        this.renderStats();
      });
      this.store.subscribe("tagManagement:selectionChanged", (payload) => {
        const selectedIds = (payload && payload.selectedIds) || [];
        this.state.selection = new Set(selectedIds);
        this.renderSelection();
      });
      this.store.subscribe("tagManagement:error", (payload) => {
        const target = payload && payload.target;
        const errorMessage = payload && payload.error ? payload.error.message : undefined;
        if (target === "categories") {
          this.view.renderCategories([], errorMessage || "分类加载失败");
        } else if (target === "tags") {
          this.view.renderTagList([], new Set(), { error: errorMessage });
        }
      });
    }

    /**
     * 将当前 store 状态同步到 controller 内部 state。
     *
     * @return {void}
     */
    syncFromStore() {
      const current = this.store.getState();
      this.state.categories = current.categories || [];
      this.state.tags = orderTags(current.tags || []);
      this.state.filteredTags = orderTags(current.filteredTags || current.tags || []);
      this.state.selection = new Set(current.selection || []);
      this.state.stats = current.stats || this.state.stats;
    }

    /**
     * 初次渲染所有区域。
     *
     * @return {void}
     */
    renderAll() {
      this.renderCategories();
      this.renderTags();
      this.renderSelection();
      this.renderStats();
    }

    /**
     * 分类区域渲染。
     *
     * @return {void}
     */
    renderCategories() {
      this.view.renderCategories(this.state.categories);
    }

    /**
     * 标签列表渲染。
     *
     * @return {void}
     */
    renderTags() {
      this.view.renderTagList(this.state.filteredTags, this.state.selection);
    }

    /**
     * 已选标签区域渲染与隐藏域同步。
     *
     * @return {void}
     */
    renderSelection() {
      const selectedTags = this.getSelectedTags();
      this.view.updateSelectedDisplay(selectedTags);
      this.syncHiddenInput(selectedTags);
    }

    /**
     * 统计信息渲染。
     *
     * @return {void}
     */
    renderStats() {
      this.view.updateStats(this.state.stats);
    }

    /**
     * 分类筛选切换处理。
     *
     * @param {string} value - 分类值
     * @return {void}
     */
    handleCategory(value) {
      this.store.actions.setCategory(value || "all");
    }

    /**
     * 点击标签的切换逻辑。
     *
     * @param {number|string} tagId - 标签 ID
     * @return {void}
     */
    toggleTag(tagId) {
      const numericId = Number(tagId);
      if (!Number.isFinite(numericId)) {
        return;
      }
      if (this.state.selection.has(numericId)) {
        this.store.actions.removeTag(numericId);
      } else {
        this.store.actions.addTag(numericId);
      }
    }

    /**
     * 从已选中移除标签。
     *
     * @param {number} tagId - 标签 ID
     * @return {void}
     */
    removeTag(tagId) {
      this.store.actions.removeTag(tagId);
    }

    /**
     * 点击确认后分发事件并关闭模态。
     *
     * @return {void}
     */
    confirmSelection() {
      const selectedTags = this.getSelectedTags();
      this.syncHiddenInput(selectedTags);
      const detail = { selectedTags };
      this.dispatchCustomEvent("tagSelectionConfirmed", detail);
      if (typeof this.options.onConfirm === "function") {
        this.options.onConfirm(detail);
      }
      if (this.modal && typeof this.modal.close === "function") {
        this.modal.close();
      }
    }

    /**
     * 关闭或取消模态时的统一处理。
     *
     * @param {Object} [options] - 配置选项
     * @param {string} [options.reason] - 取消原因
     * @param {boolean} [options.hideModal] - 是否隐藏模态框
     * @return {void}
     */
    emitCancel(options = {}) {
      const detail = {
        reason: options.reason || "cancel",
        selectedTags: this.getSelectedTags(),
      };
      this.dispatchCustomEvent("tagSelectionCanceled", detail);
      if (typeof this.options.onCancel === "function") {
        this.options.onCancel(detail);
      }
      if (options.hideModal !== false && this.modal && typeof this.modal.close === "function") {
        this.modal.close();
      }
    }

    /**
     * 对外派发自定义事件，供监听方使用。
     *
     * @param {string} name - 事件名称
     * @param {Object} detail - 事件详情
     * @return {void}
     */
    dispatchCustomEvent(name, detail) {
      const event = new CustomEvent(name, { bubbles: true, detail });
      this.root.dispatchEvent(event);
    }

    /**
     * 将已选标签写回隐藏 input，供表单提交使用。
     *
     * @param {Array<Object>} tags - 标签数组
     * @return {void}
     */
    syncHiddenInput(tags) {
      const hiddenInput = toElement(this.options.hiddenInputSelector);
      if (!hiddenInput) {
        return;
      }
      const key = this.options.hiddenValueKey || "name";
      hiddenInput.value = (tags || [])
        .map((tag) => pickTagValue(tag, key))
        .filter((value) => value !== undefined && value !== null && value !== "")
        .join(",");
    }

    /**
     * 根据 selection id 列表返回完整标签对象数组。
     *
     * @return {Array<Object>} 已选标签数组
     */
    getSelectedTags() {
      const ids = Array.from(this.state.selection);
      const tags = ids
        .map((id) => this.state.tags.find((tag) => tag.id === id))
        .filter(Boolean);
      return orderTags(tags);
    }

    /**
     * 对外暴露的打开模态方法。
     *
     * @return {void}
     */
    openModal() {
      if (this.modal && typeof this.modal.open === "function") {
        this.modal.open();
      }
    }

    /**
     * 返回初始化 promise，方便外部等待。
     *
     * @return {Promise<TagSelectorController>} 初始化 Promise
     */
    ready() {
      return this.readyPromise;
    }
  }

  /**
   * 管理 TagSelectorController 的单例容器。
   */
  class TagSelectorManager {
    constructor() {
      this.instances = new Map();
      this.isReady = false;
      this.queue = [];
      document.addEventListener("DOMContentLoaded", () => this.markReady());
    }

    /**
     * DOMContentLoaded 后执行等待队列。
     */
    markReady() {
      this.isReady = true;
      this.queue.splice(0).forEach((cb) => {
        try {
          cb();
        } catch (error) {
          console.error("TagSelectorManager whenReady 执行失败", error);
        }
      });
    }

    /**
     * 提供延迟 ready 的回调。
     */
    whenReady(callback) {
      if (this.isReady) {
        callback();
      } else {
        this.queue.push(callback);
      }
    }

    /**
     * 创建或返回一个标签选择器 controller 实例。
     */
    create(root, options) {
      const element = toElement(root);
      if (!element) {
        console.error("TagSelectorManager: root 未找到");
        return null;
      }
      const controller = new TagSelectorController(element, options);
      if (this.instances.has(controller.id)) {
        return this.instances.get(controller.id);
      }
      this.instances.set(controller.id, controller);
      return controller;
    }

    /**
     * 按 root 查找已有实例。
     */
    get(root) {
      const element = toElement(root);
      if (!element) {
        return null;
      }
      const id = element.dataset.tagSelectorId;
      return (id && this.instances.get(id)) || null;
    }
  }

  const manager = new TagSelectorManager();

  const TagSelectorHelper = {
    setupForForm(options = {}) {
      const {
        modalSelector = "#tagSelectorModal",
        rootSelector = "[data-tag-selector]",
        openButtonSelector = "#open-tag-filter-btn",
        previewSelector = "#selected-tags-preview",
        chipsSelector = "#selected-tags-chips",
        hiddenInputSelector = "#selected-tag-names",
        hiddenValueKey = "name",
        initialValues = [],
        onConfirm = null,
      } = options;

      // DOM 就绪后再创建实例，保证模态节点已经存在
      manager.whenReady(() => {
        const modalElement = toElement(modalSelector);
        const container = modalElement && typeof modalElement.closest === "function"
          ? modalElement.closest("[data-tag-selector-modal]")
          : modalElement;
        const root = container ? container.querySelector(rootSelector) : toElement(rootSelector);
        if (!root) {
          console.error("TagSelectorHelper.setupForForm: 未找到标签选择器容器");
          return;
        }
        const instance = manager.create(root, {
          modalElement: container,
          hiddenInputSelector,
          hiddenValueKey,
          initialValues,
          onConfirm: (detail) => {
            const selectedTags = detail.selectedTags || [];
            updatePreviewDisplay(previewSelector, chipsSelector, selectedTags);
            if (typeof onConfirm === "function") {
              onConfirm(detail);
            }
          },
        });

        const openBtn = toElement(openButtonSelector);
        if (openBtn) {
          openBtn.addEventListener("click", (event) => {
            event.preventDefault();
            if (instance && typeof instance.openModal === "function") {
              instance.openModal();
            }
          });
        }

        if (instance) {
          instance.ready().then(() => {
            instance.renderSelection();
            updatePreviewDisplay(previewSelector, chipsSelector, instance.getSelectedTags());
          });
        }
      });
    },

    setupForFilter(options = {}) {
      const {
        modalSelector = "#tagSelectorModal",
        rootSelector = "[data-tag-selector]",
        openButtonSelector = "#open-tag-filter-btn",
        hiddenInputSelector = "#selected-tag-names",
        valueKey = "name",
        previewSelector = "#selected-tags-preview",
        chipsSelector = "#selected-tags-chips",
        onConfirm = null,
      } = options;

      // 过滤模式同样等待 DOMReady，确保隐藏域已渲染
      manager.whenReady(() => {
        const modalBase = toElement(modalSelector);
        const modal = modalBase && typeof modalBase.closest === "function"
          ? modalBase.closest("[data-tag-selector-modal]")
          : modalBase;
        const root = modal ? modal.querySelector(rootSelector) : toElement(rootSelector);
        if (!root) {
          console.error("TagSelectorHelper.setupForFilter: 未找到标签选择器容器");
          return;
        }
        const instance = manager.create(root, {
          modalElement: modal,
          hiddenInputSelector,
          hiddenValueKey: valueKey,
          onConfirm: (detail) => {
            const hiddenInput = toElement(hiddenInputSelector);
            if (hiddenInput) {
              hiddenInput.value = (detail.selectedTags || [])
                .map((tag) => pickTagValue(tag, valueKey))
                .filter((val) => val !== undefined && val !== null && val !== "")
                .join(",");
            }
            updatePreviewDisplay(previewSelector, chipsSelector, detail.selectedTags || []);
            if (typeof onConfirm === "function") {
              onConfirm(detail);
            }
          },
        });

        const openBtn = toElement(openButtonSelector);
        if (openBtn) {
          openBtn.addEventListener("click", (event) => {
            event.preventDefault();
            if (instance && typeof instance.openModal === "function") {
              instance.openModal();
            }
          });
        }

        if (instance) {
          instance.ready().then(() => {
            const hiddenInput = toElement(hiddenInputSelector);
            if (hiddenInput && hiddenInput.value) {
              const initialValues = hiddenInput.value
                .split(",")
                .map((value) => value.trim())
                .filter(Boolean);
              if (initialValues.length) {
                instance.store.actions.selectBy(initialValues, valueKey);
              }
            }
            updatePreviewDisplay(previewSelector, chipsSelector, instance.getSelectedTags());
          });
        }
      });
    },

    clearSelection(options = {}) {
      const {
        modalSelector = "#tagSelectorModal",
        rootSelector = "[data-tag-selector]",
        hiddenInputSelector = "#selected-tag-names",
        previewSelector = "#selected-tags-preview",
        chipsSelector = "#selected-tags-chips",
        onCleared = null,
      } = options;

      manager.whenReady(() => {
        const modalElement = toElement(modalSelector);
        const container = modalElement && typeof modalElement.closest === "function"
          ? modalElement.closest("[data-tag-selector-modal]")
          : modalElement;
        const root = container ? container.querySelector(rootSelector) : toElement(rootSelector);
        if (!root) {
          console.error("TagSelectorHelper.clearSelection: 未找到标签选择器容器");
          return;
        }
        const instance = manager.get(root);
        if (!instance) {
          console.warn("TagSelectorHelper.clearSelection: 标签选择器尚未初始化");
          return;
        }
        if (instance.store && instance.store.actions && typeof instance.store.actions.clearSelection === "function") {
          instance.store.actions.clearSelection();
        }
        instance.syncHiddenInput([]);
        const hiddenInput = toElement(hiddenInputSelector);
        if (hiddenInput) {
          hiddenInput.value = "";
        }
        updatePreviewDisplay(previewSelector, chipsSelector, []);
        if (typeof onCleared === "function") {
          onCleared();
        }
      });
    },
  };

  window.TagSelectorController = TagSelectorController;
  window.TagSelectorHelper = TagSelectorHelper;
})(window, document);
