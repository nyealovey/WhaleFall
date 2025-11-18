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
    tags: "/tags/api/tags",
    categories: "/tags/api/categories",
  };

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

  function orderTags(items) {
    if (!Array.isArray(items)) {
      return [];
    }
    if (LodashUtils?.orderBy) {
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

  class TagSelectorController {
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
        endpoints: { ...DEFAULT_ENDPOINTS, ...(options.endpoints || {}) },
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

    bindStoreEvents() {
      this.store.subscribe("tagManagement:categoriesUpdated", (payload) => {
        this.state.categories = payload?.categories || [];
        this.renderCategories();
      });
      this.store.subscribe("tagManagement:tagsUpdated", (payload) => {
        this.state.tags = orderTags(payload?.tags || []);
        this.state.filteredTags = orderTags(payload?.filteredTags || payload?.tags || []);
        this.state.stats = payload?.stats || this.state.stats;
        this.renderTags();
        this.renderStats();
      });
      this.store.subscribe("tagManagement:selectionChanged", (payload) => {
        this.state.selection = new Set(payload?.selectedIds || []);
        this.renderSelection();
      });
      this.store.subscribe("tagManagement:error", (payload) => {
        if (payload?.target === "categories") {
          this.view.renderCategories([], payload.error?.message || "分类加载失败");
        } else if (payload?.target === "tags") {
          this.view.renderTagList([], new Set(), { error: payload.error?.message });
        }
      });
    }

    syncFromStore() {
      const current = this.store.getState();
      this.state.categories = current.categories || [];
      this.state.tags = orderTags(current.tags || []);
      this.state.filteredTags = orderTags(current.filteredTags || current.tags || []);
      this.state.selection = new Set(current.selection || []);
      this.state.stats = current.stats || this.state.stats;
    }

    renderAll() {
      this.renderCategories();
      this.renderTags();
      this.renderSelection();
      this.renderStats();
    }

    renderCategories() {
      this.view.renderCategories(this.state.categories);
    }

    renderTags() {
      this.view.renderTagList(this.state.filteredTags, this.state.selection);
    }

    renderSelection() {
      const selectedTags = this.getSelectedTags();
      this.view.updateSelectedDisplay(selectedTags);
      this.syncHiddenInput(selectedTags);
    }

    renderStats() {
      this.view.updateStats(this.state.stats);
    }

    handleCategory(value) {
      this.store.actions.setCategory(value || "all");
    }

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

    removeTag(tagId) {
      this.store.actions.removeTag(tagId);
    }

    confirmSelection() {
      const selectedTags = this.getSelectedTags();
      this.syncHiddenInput(selectedTags);
      const detail = { selectedTags };
      this.dispatchCustomEvent("tagSelectionConfirmed", detail);
      if (typeof this.options.onConfirm === "function") {
        this.options.onConfirm(detail);
      }
      this.modal?.close?.();
    }

    emitCancel(options = {}) {
      const detail = {
        reason: options.reason || "cancel",
        selectedTags: this.getSelectedTags(),
      };
      this.dispatchCustomEvent("tagSelectionCanceled", detail);
      if (typeof this.options.onCancel === "function") {
        this.options.onCancel(detail);
      }
      if (options.hideModal !== false) {
        this.modal?.close?.();
      }
    }

    dispatchCustomEvent(name, detail) {
      const event = new CustomEvent(name, { bubbles: true, detail });
      this.root.dispatchEvent(event);
    }

    syncHiddenInput(tags) {
      const hiddenInput = toElement(this.options.hiddenInputSelector);
      if (!hiddenInput) {
        return;
      }
      const key = this.options.hiddenValueKey || "name";
      hiddenInput.value = (tags || [])
        .map((tag) => tag?.[key] ?? tag?.name ?? tag?.id)
        .filter(Boolean)
        .join(",");
    }

    getSelectedTags() {
      const ids = Array.from(this.state.selection);
      const tags = ids
        .map((id) => this.state.tags.find((tag) => tag.id === id))
        .filter(Boolean);
      return orderTags(tags);
    }

    openModal() {
      this.modal?.open?.();
    }

    ready() {
      return this.readyPromise;
    }
  }

  class TagSelectorManager {
    constructor() {
      this.instances = new Map();
      this.isReady = false;
      this.queue = [];
      document.addEventListener("DOMContentLoaded", () => this.markReady());
    }

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

    whenReady(callback) {
      if (this.isReady) {
        callback();
      } else {
        this.queue.push(callback);
      }
    }

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
        countSelector = "#selected-tags-count",
        chipsSelector = "#selected-tags-chips",
        hiddenInputSelector = "#selected-tag-names",
        hiddenValueKey = "name",
        initialValues = [],
        onConfirm = null,
      } = options;

      manager.whenReady(() => {
        const container = toElement(modalSelector)?.closest("[data-tag-selector-modal]") || toElement(modalSelector);
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
          onConfirm,
        });

        const openBtn = toElement(openButtonSelector);
        if (openBtn) {
          openBtn.addEventListener("click", (event) => {
            event.preventDefault();
            instance?.openModal();
          });
        }

        if (instance) {
          instance.ready().then(() => {
            instance.renderSelection();
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
        onConfirm = null,
      } = options;

      manager.whenReady(() => {
        const modal = toElement(modalSelector)?.closest("[data-tag-selector-modal]") || toElement(modalSelector);
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
                .map((tag) => tag?.[valueKey] ?? tag?.name ?? tag?.id)
                .join(",");
            }
            if (typeof onConfirm === "function") {
              onConfirm(detail);
            }
          },
        });

        const openBtn = toElement(openButtonSelector);
        if (openBtn) {
          openBtn.addEventListener("click", (event) => {
            event.preventDefault();
            instance?.openModal();
          });
        }

        if (instance) {
          instance.ready().then(() => {
            const hiddenInput = toElement(hiddenInputSelector);
            if (hiddenInput?.value) {
              const initialValues = hiddenInput.value
                .split(",")
                .map((value) => value.trim())
                .filter(Boolean);
              if (initialValues.length) {
                instance.store.actions.selectBy(initialValues, valueKey);
              }
            }
          });
        }
      });
    },
  };

  window.TagSelectorController = TagSelectorController;
  window.TagSelectorHelper = TagSelectorHelper;
})(window, document);
