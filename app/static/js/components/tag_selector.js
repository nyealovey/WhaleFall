(function (window, document) {
  "use strict";

  const LodashUtils = window.LodashUtils;
  if (!LodashUtils) {
    throw new Error("LodashUtils 未初始化");
  }

  const httpClient = window.httpU;
  if (!httpClient) {
    throw new Error("httpU 未初始化，无法加载标签数据");
  }

  const DEFAULT_ENDPOINTS = {
    tags: "/tags/api/tags",
    categories: "/tags/api/categories",
  };

  const EVENT_NAMES = {
    change: "tagSelectionChange",
    confirm: "tagSelectionConfirmed",
    cancel: "tagSelectionCanceled",
  };

  let instanceCounter = 0;

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
    return null;
  }

  function ensureHttp() {
    if (!httpClient || typeof httpClient.get !== "function") {
      throw new Error("httpU 未初始化，无法加载标签数据");
    }
  }

  function orderCategories(items) {
    const collection = Array.isArray(items) ? items.filter(Boolean) : [];
    const deduplicated = LodashUtils.uniqBy(collection, "value");
    return LodashUtils.orderBy(deduplicated, ["label"], ["asc"]);
  }

  function orderTags(items) {
    if (!Array.isArray(items)) {
      return [];
    }
    return LodashUtils.orderBy(
      items,
      [
        (tag) => (tag.is_active === false ? 1 : 0),
        (tag) => (tag.display_name || tag.name || "").toLowerCase(),
      ],
      ["asc", "asc"],
    );
  }

  function formatNumber(value) {
    return window.NumberFormat.formatInteger(value, { fallback: "0" });
  }

  function resolveBadge(tag) {
    const color = tag?.color || "";
    if (color.startsWith("bg-")) {
      return { className: `badge rounded-pill ${color}`, style: "" };
    }
    if (color.startsWith("#")) {
      return {
        className: "badge rounded-pill",
        style: `background-color: ${color}; color: #fff;`,
        variant: "custom",
      };
    }
    return {
      className: "badge rounded-pill bg-secondary",
      style: "",
    };
  }

  class TagSelector {
    constructor(root, options = {}) {
      this.root = toElement(root);
      if (!this.root) {
        console.error("TagSelector: 容器未找到");
        return;
      }

      this.options = {
        allowMultiple: true,
        maxSelections: null,
        endpoints: { ...DEFAULT_ENDPOINTS, ...(options.endpoints || {}) },
        onSelectionChange: null,
        onConfirm: null,
        onCancel: null,
        hiddenValueKey: "name",
        ...options,
      };

      this.id =
        this.root.dataset.tagSelectorId ||
        `tag-selector-${++instanceCounter}`;
      this.root.dataset.tagSelectorId = this.id;

      this.modal =
        toElement(options.modalElement) ||
        this.root.closest("[data-tag-selector-modal]") ||
        null;

      this.elements = this.cacheElements();

      this.state = {
        allTags: [],
        filteredTags: [],
        selectedIds: new Set(),
        category: "all",
        search: "",
        stats: {
          total: 0,
          selected: 0,
          active: 0,
          filtered: 0,
        },
      };

      this.pendingSelection = null;
      this.ignoreNextCancel = false;
      this.readyPromise = this.initialize();
    }

    cacheElements() {
      return {
        categoryGroup: this.root.querySelector('[data-role="category-group"]'),
        categoryLoading: this.root.querySelector(
          '[data-role="category-loading"]',
        ),
        statsWrapper: this.root.querySelector('[data-role="stats"]'),
        statTotal: this.root.querySelector('[data-role="stat-total"]'),
        statSelected: this.root.querySelector('[data-role="stat-selected"]'),
        statActive: this.root.querySelector('[data-role="stat-active"]'),
        statFiltered: this.root.querySelector('[data-role="stat-filtered"]'),
        tagList: this.root.querySelector('[data-role="tag-list"]'),
        selectedContainer: this.root.querySelector(
          '[data-role="selected-container"]',
        ),
        selectedList: this.root.querySelector('[data-role="selected-list"]'),
        selectedEmpty: this.root.querySelector('[data-role="selected-empty"]'),
      };
    }

    async initialize() {
      this.bindEvents();
      this.bindModalLifecycle();

      await Promise.all([this.loadCategories(), this.loadTags()]);

      if (this.pendingSelection) {
        this.selectBy(this.pendingSelection.values, this.pendingSelection.key);
        this.pendingSelection = null;
      } else {
        this.updateSelectedDisplay();
        this.updateStats();
      }

      return this;
    }

    bindEvents() {
      const { categoryGroup, tagList, selectedList } =
        this.elements;

      if (categoryGroup) {
        categoryGroup.addEventListener("change", (event) => {
          const radio = event.target.closest('input[type="radio"]');
          if (radio) {
            this.handleCategory(radio.value);
          }
        });
      }

      if (tagList) {
        tagList.addEventListener("click", (event) => {
          const item = event.target.closest("[data-tag-id]");
          if (!item || item.classList.contains("disabled")) {
            return;
          }
          const tagId = Number(item.dataset.tagId);
          if (Number.isFinite(tagId)) {
            this.toggleTag(tagId);
          }
        });
      }

      if (selectedList) {
        selectedList.addEventListener("click", (event) => {
          const removeBtn = event.target.closest(
            "[data-role=\"chip-remove\"]",
          );
          if (!removeBtn) {
            return;
          }
          const tagId = Number(removeBtn.dataset.tagId);
          if (Number.isFinite(tagId)) {
            this.removeTag(tagId);
          }
        });
      }
    }

    bindModalLifecycle() {
      if (!this.modal) {
        return;
      }
      this.modal.addEventListener("hidden.bs.modal", () => {
        if (this.ignoreNextCancel) {
          this.ignoreNextCancel = false;
          return;
        }
        this.emitCancel({
          reason: "modal-hidden",
          hideModal: false,
        });
      });
    }

    async loadCategories() {
      const { categoryGroup, categoryLoading } = this.elements;
      if (!categoryGroup) {
        return;
      }

      try {
        ensureHttp();
        const response = await httpClient.get(
          this.options.endpoints.categories,
        );
        const categories =
          response?.categories ??
          response?.data?.categories ??
          response?.data ??
          [];
        this.renderCategories(Array.isArray(categories) ? categories : []);
      } catch (error) {
        console.error("TagSelector: 加载分类失败", error);
        this.renderCategories([], error);
      } finally {
        if (categoryLoading) {
          categoryLoading.remove();
        }
      }
    }

    renderCategories(categories, error) {
      const group = this.elements.categoryGroup;
      if (!group) {
        return;
      }

      group.innerHTML = "";

      const list = Array.isArray(categories) ? categories : [];
      const mapped = list
        .map((item) => ({
          value: Array.isArray(item) ? item[0] : item?.value ?? item?.name,
          label:
            Array.isArray(item)
              ? item[1]
              : item?.label ??
                item?.display_name ??
                item?.value ??
                "未命名",
        }))
        .filter((item) => item.value);

      const orderedCategories = orderCategories(mapped);

      const finalItems = [{ value: "all", label: "全部" }, ...orderedCategories];

      const fragment = document.createDocumentFragment();
      finalItems.forEach(({ value, label }, index) => {
        const normalizedValue =
          (value ?? "all").toString().toLowerCase() || "all";
        const input = document.createElement("input");
        input.type = "radio";
        input.name = `${this.id}-category`;
        input.className = "btn-check";
        input.id = `${this.id}-category-${normalizedValue}`;
        input.value = normalizedValue;
        if (index === 0) {
          input.checked = true;
        }

        const button = document.createElement("label");
        button.className = "btn btn-outline-secondary";
        button.setAttribute("for", input.id);
        button.textContent = label;

        fragment.appendChild(input);
        fragment.appendChild(button);
      });

      group.appendChild(fragment);

      if (error) {
        const alert = document.createElement("div");
        alert.className = "alert alert-warning w-100 mt-2 d-flex align-items-center gap-2";
        alert.innerHTML = `<i class="fas fa-exclamation-triangle"></i><span>分类加载失败：${error.message || "未知错误"}</span>`;
        group.appendChild(alert);
      }
    }

    async loadTags() {
      const { tagList } = this.elements;
      if (tagList) {
        tagList.innerHTML = this.renderLoadingState();
      }

      try {
        ensureHttp();
        const response = await httpClient.get(this.options.endpoints.tags);
        const tags =
          response?.data?.tags ??
          response?.tags ??
          response?.data ??
          [];
        const normalized = Array.isArray(tags) ? tags : [];
        this.state.allTags = orderTags(normalized);
        this.state.filteredTags = [...this.state.allTags];
        this.updateStats();
        this.renderTagList();
        this.updateSelectedDisplay();
      } catch (error) {
        console.error("TagSelector: 加载标签失败", error);
        if (tagList) {
          tagList.innerHTML = this.renderErrorState(
            error.message || "标签数据加载失败",
          );
        }
      }
    }

    renderTagList() {
      const { tagList } = this.elements;
      if (!tagList) {
        return;
      }

      if (!this.state.filteredTags.length) {
        tagList.innerHTML = this.renderEmptyState();
        return;
      }

      const html = this.state.filteredTags
        .map((tag) => this.renderTagItem(tag))
        .join("");
      tagList.innerHTML = html;
    }

    renderTagItem(tag) {
      const isSelected = this.state.selectedIds.has(tag.id);
      const isDisabled = tag.is_active === false;
      const badge = resolveBadge(tag);

      const categoryName = tag.category
        ? this.getCategoryDisplayName(tag.category)
        : "未分类";
      const iconClass = isDisabled
        ? "fas fa-ban text-muted"
        : isSelected
        ? "fas fa-check-circle text-primary"
        : "fas fa-plus-circle text-muted";

      const description = tag.description || "未填写描述";

      return `
        <button type="button"
                class="list-group-item list-group-item-action d-flex align-items-start justify-content-between gap-3 ${isSelected ? "active" : ""} ${isDisabled ? "disabled" : ""}"
                data-tag-id="${tag.id}">
          <div class="flex-grow-1 text-start">
            <div class="d-flex flex-wrap align-items-center gap-2 mb-1">
              <span class="${badge.className}" ${badge.style ? `style="${badge.style}"` : ""}>
                <i class="fas fa-tag me-1"></i>${this.highlightSearch(tag.display_name || tag.name || `标签#${tag.id}`)}
              </span>
              <span class="badge bg-light text-muted text-uppercase fw-normal">${categoryName}</span>
              ${isDisabled ? '<span class="badge bg-secondary">已停用</span>' : ""}
            </div>
            <div class="tag-meta">
              ${this.highlightSearch(description)}
            </div>
          </div>
          <div class="tag-actions d-flex align-items-center">
            <i class="${iconClass}"></i>
          </div>
        </button>
      `;
    }

    renderLoadingState() {
      return `
        <div class="text-center text-muted py-5">
          <div class="spinner-border text-primary mb-3" role="status">
            <span class="visually-hidden">加载中...</span>
          </div>
          <div>正在加载标签...</div>
        </div>
      `;
    }

    renderErrorState(message) {
      return `
        <div class="no-data text-center text-muted py-5">
          <i class="fas fa-exclamation-circle fa-2x mb-2 text-warning"></i>
          <div class="fw-semibold mb-1">加载失败</div>
          <p class="mb-3">${message}</p>
          <button type="button" class="btn btn-outline-primary btn-sm" data-role="retry-load">
            <i class="fas fa-redo me-1"></i>重新加载
          </button>
        </div>
      `;
    }

    renderEmptyState() {
      return `
        <div class="no-data text-center text-muted py-5">
          <i class="fas fa-tags fa-2x mb-2"></i>
          <div class="fw-semibold mb-1">暂无可显示的标签</div>
          <p class="mb-0">尝试切换不同的标签分类</p>
        </div>
      `;
    }

    handleCategory(value) {
      this.state.category = (value || "all").toLowerCase();
      this.filterTags();
    }

    filterTags() {
      const category = this.state.category;
      const query = this.state.search;

      this.state.filteredTags = this.state.allTags.filter((tag) => {
        const tagCategory = (tag.category || "").toLowerCase();
        const matchesCategory =
          category === "all" || tagCategory === category;

        if (!matchesCategory) {
          return false;
        }

        if (!query) {
          return true;
        }

        const name = (tag.name || "").toLowerCase();
        const displayName = (tag.display_name || "").toLowerCase();
        const description = (tag.description || "").toLowerCase();

        return (
          name.includes(query) ||
          displayName.includes(query) ||
          description.includes(query) ||
          tagCategory.includes(query)
        );
      });

      this.state.filteredTags = orderTags(this.state.filteredTags);
      this.renderTagList();
      this.updateStats();
    }

    toggleTag(tagId) {
      if (this.state.selectedIds.has(tagId)) {
        this.removeTag(tagId);
      } else {
        this.addTag(tagId);
      }
    }

    addTag(tagId) {
      if (!this.options.allowMultiple && this.state.selectedIds.size) {
        this.state.selectedIds.clear();
      }

      if (
        this.options.maxSelections &&
        this.state.selectedIds.size >= this.options.maxSelections
      ) {
        toast?.warning?.(
          `最多只能选择 ${this.options.maxSelections} 个标签`,
        );
        return;
      }

      const tag = this.state.allTags.find((item) => item.id === tagId);
      if (!tag) {
        return;
      }

      this.state.selectedIds.add(tagId);
      this.updateSelectedDisplay();
      this.renderTagList();
      this.updateStats();
      this.notifySelectionChange(tag, "add");
    }

    removeTag(tagId) {
      if (!this.state.selectedIds.has(tagId)) {
        return;
      }

      const tag = this.state.allTags.find((item) => item.id === tagId);

      this.state.selectedIds.delete(tagId);
      this.updateSelectedDisplay();
      this.renderTagList();
      this.updateStats();
      this.notifySelectionChange(tag, "remove");
    }

    clearSelection({ silent = false } = {}) {
      if (!this.state.selectedIds.size) {
        return;
      }
      this.state.selectedIds.clear();
      this.updateSelectedDisplay();
      this.renderTagList();
      this.updateStats();
      if (!silent) {
        this.notifySelectionChange(null, "clear");
      }
    }

    updateSelectedDisplay() {
      const { selectedList, selectedEmpty } = this.elements;
      if (!selectedList || !selectedEmpty) {
        return;
      }

      const selectedTags = orderTags(
        Array.from(this.state.selectedIds)
          .map((id) => this.state.allTags.find((item) => item.id === id))
          .filter(Boolean),
      );

      if (!selectedTags.length) {
        selectedList.innerHTML = "";
        selectedEmpty.hidden = false;
        return;
      }

      selectedEmpty.hidden = true;
      const chips = selectedTags
        .map((tag) => {
          const badge = resolveBadge(tag);
          return `
            <span class="tag-chip ${badge.className}" ${badge.style ? `style="${badge.style}"` : ""} data-role="selected-chip" data-tag-id="${tag.id}" ${badge.variant ? `data-variant="${badge.variant}"` : ""}>
              <span><i class="fas fa-tag me-1"></i>${tag.display_name || tag.name}</span>
              <button type="button" class="btn-close btn-close-white" aria-label="移除标签" data-role="chip-remove" data-tag-id="${tag.id}"></button>
            </span>
          `;
        })
        .join("");

      selectedList.innerHTML = chips;
    }

    updateStats() {
      if (!this.elements.statsWrapper) {
        return;
      }

      const total = this.state.allTags.length;
      const selected = this.state.selectedIds.size;
      const active = this.state.allTags.filter((tag) => tag.is_active !== false)
        .length;
      const filtered = this.state.filteredTags.length;

      this.state.stats = { total, selected, active, filtered };

      this.elements.statTotal.textContent = formatNumber(total);
      this.elements.statSelected.textContent = formatNumber(selected);
      this.elements.statActive.textContent = formatNumber(active);
      this.elements.statFiltered.textContent = formatNumber(filtered);

      this.elements.statsWrapper.hidden = false;
    }

    notifySelectionChange(tag, type) {
      const detail = {
        type: type || "update",
        tag,
        selectedIds: Array.from(this.state.selectedIds),
        selectedTags: this.getSelectedTags(),
      };

      this.dispatch(EVENT_NAMES.change, detail);

      if (typeof this.options.onSelectionChange === "function") {
        this.options.onSelectionChange(detail.selectedTags, detail);
      }
    }

    dispatch(eventName, detail) {
      const event = new CustomEvent(eventName, {
        bubbles: true,
        detail,
      });
      this.root.dispatchEvent(event);
    }

    confirmSelection() {
      const detail = {
        selectedIds: Array.from(this.state.selectedIds),
        selectedTags: this.getSelectedTags(),
      };

      this.dispatch(EVENT_NAMES.confirm, detail);

      if (typeof this.options.onConfirm === "function") {
        this.options.onConfirm(detail);
      }

      const modalInstance = this.getModalInstance();
      if (modalInstance) {
        this.ignoreNextCancel = true;
        modalInstance.hide();
      }
    }

    cancelSelection(options = {}) {
      this.emitCancel({ reason: "cancel-button", ...options });
    }

    emitCancel({ reason = "cancel", hideModal = true } = {}) {
      const detail = {
        reason,
        selectedIds: Array.from(this.state.selectedIds),
        selectedTags: this.getSelectedTags(),
      };

      this.dispatch(EVENT_NAMES.cancel, detail);

      if (typeof this.options.onCancel === "function") {
        this.options.onCancel(detail);
      }

      if (hideModal) {
        const modalInstance = this.getModalInstance();
        if (modalInstance) {
          this.ignoreNextCancel = true;
          modalInstance.hide();
        }
      }
    }

    getModalInstance() {
      if (!this.modal || typeof bootstrap?.Modal !== "function") {
        return null;
      }
      return (
        bootstrap.Modal.getInstance(this.modal) ||
        new bootstrap.Modal(this.modal)
      );
    }

    getSelectedTags() {
      const selected = Array.from(this.state.selectedIds);
      const tags = selected
        .map((id) => this.state.allTags.find((tag) => tag.id === id))
        .filter(Boolean);
      return orderTags(tags);
    }

    ready() {
      return this.readyPromise;
    }

    selectBy(values, key = "id") {
      const normalized = Array.isArray(values)
        ? values
        : typeof values === "string"
        ? values
            .split(",")
            .map((item) => item.trim())
            .filter(Boolean)
        : [];

      if (!this.state.allTags.length) {
        this.pendingSelection = { values: normalized, key };
        return;
      }

      const compareKey = (tag) => {
        if (key === "id") {
          return String(tag.id);
        }
        return String(tag?.[key] ?? tag?.name ?? "");
      };

      const valueSet = new Set(normalized.map((value) => String(value)));

      this.state.selectedIds.clear();
      this.state.allTags.forEach((tag) => {
        if (valueSet.has(compareKey(tag))) {
          this.state.selectedIds.add(tag.id);
        }
      });

      this.updateSelectedDisplay();
      this.renderTagList();
      this.updateStats();
      this.notifySelectionChange(null, "sync");
    }

    getCategoryDisplayName(category) {
      const mapping = {
        architecture: "架构",
        company_type: "公司",
        department: "部门",
        deployment: "部署",
        environment: "环境",
        region: "地区",
        project: "项目",
        virtualization: "虚拟化",
        other: "其他",
      };
      return mapping[category] || category || "未分类";
    }

    highlightSearch(text) {
      const value = text || "";
      if (!this.state.search) {
        return value;
      }
      const safe = value.replace(
        new RegExp(`(${this.escapeRegExp(this.state.search)})`, "gi"),
        '<span class="search-highlight">$1</span>',
      );
      return safe;
    }

    escapeRegExp(input) {
      return input.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
    }
  }

  class TagSelectorManager {
    constructor() {
      this.instances = new Map();
      this.isReady = false;
      this.queue = [];

      document.addEventListener("DOMContentLoaded", () => {
        this.markReady();
      });
    }

    markReady() {
      this.isReady = true;
      this.queue.splice(0).forEach((callback) => {
        try {
          callback();
        } catch (error) {
          console.error("TagSelectorManager: whenReady 回调执行失败", error);
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

    create(target, options = {}) {
      const element = toElement(target);
      if (!element) {
        console.error("TagSelectorManager.create: 未找到容器", target);
        return null;
      }

      const existing = this.get(element);
      if (existing) {
        return existing;
      }

      const instance = new TagSelector(element, options);
      if (!instance || !instance.id) {
        return null;
      }
      this.instances.set(instance.id, instance);
      return instance;
    }

    get(target) {
      if (!target) {
        return null;
      }

      if (typeof target === "string" && this.instances.has(target)) {
        return this.instances.get(target);
      }

      const element = toElement(target);
      if (!element) {
        return null;
      }

      const id = element.dataset.tagSelectorId;
      if (id && this.instances.has(id)) {
        return this.instances.get(id);
      }

      return null;
    }
  }

  const manager = new TagSelectorManager();

  const TagSelectorHelper = {
    setupForForm(options = {}) {
      const {
        modalSelector = "#tagSelectorModal",
        rootSelector = "[data-tag-selector]",
        openButtonSelector = "#open-tag-selector-btn",
        previewSelector = "#selected-tags-preview",
        countSelector = "#selected-tags-count",
        chipsSelector = "#selected-tags-chips",
        hiddenInputSelector = "#selected-tag-names",
        initialValues = [],
        valueKey = "name",
        hiddenValueKey = "name",
        onConfirm = null,
      } = options;

      manager.whenReady(() => {
        const modal = toElement(modalSelector);
        const root = modal
          ? modal.querySelector(rootSelector)
          : toElement(rootSelector);

        if (!root) {
          console.error("TagSelectorHelper.setupForForm: 未找到标签选择器容器");
          return;
        }

        const ensureInstance = () => {
          let instance = manager.get(root);
          if (!instance) {
            instance = manager.create(root, {
              hiddenValueKey,
              onSelectionChange: (tags) => {
                this.updatePreview(tags, {
                  previewSelector,
                  countSelector,
                  chipsSelector,
                  hiddenInputSelector,
                  hiddenValueKey,
                }, instance);
              },
              onConfirm: (detail) => {
                this.updatePreview(detail.selectedTags, {
                  previewSelector,
                  countSelector,
                  chipsSelector,
                  hiddenInputSelector,
                  hiddenValueKey,
                }, instance);
                if (typeof onConfirm === "function") {
                  onConfirm(detail);
                }
              },
            });
          }
          return instance;
        };

        const openButton = toElement(openButtonSelector);
        if (openButton && modal?.id) {
          openButton.setAttribute("data-bs-toggle", "modal");
          openButton.setAttribute("data-bs-target", `#${modal.id}`);
          openButton.addEventListener("click", () => {
            ensureInstance();
          });
        }

        if (modal) {
          modal.addEventListener("show.bs.modal", () => {
            ensureInstance();
          });
        }

        const instance = ensureInstance();
        if (instance) {
          instance.ready().then(() => {
            if (initialValues && initialValues.length) {
              instance.selectBy(initialValues, valueKey);
            }
            this.updatePreview(instance.getSelectedTags(), {
              previewSelector,
              countSelector,
              chipsSelector,
              hiddenInputSelector,
              hiddenValueKey,
            }, instance, { silent: true });
          });
        }
      });
    },

    setupForFilter(options = {}) {
      const {
        modalSelector = "#tagSelectorModal",
        rootSelector = "[data-tag-selector]",
        openButtonSelector = "#open-tag-filter-btn",
        formSelector = null,
        hiddenInputSelector = "#selected-tag-names",
        valueKey = "name",
        onConfirm = null,
      } = options;

      manager.whenReady(() => {
        const modal = toElement(modalSelector);
        const root = modal
          ? modal.querySelector(rootSelector)
          : toElement(rootSelector);

        if (!root) {
          console.error("TagSelectorHelper.setupForFilter: 未找到标签选择器容器");
          return;
        }

        const ensureInstance = () => {
          let instance = manager.get(root);
          if (!instance) {
            instance = manager.create(root, {
              onConfirm: (detail) => {
                const hiddenInput = toElement(hiddenInputSelector);
                if (hiddenInput) {
                  hiddenInput.value = detail.selectedTags
                    .map((tag) => tag[valueKey] ?? tag.name)
                    .join(",");
                }
                if (typeof onConfirm === "function") {
                  onConfirm(detail);
                }
                if (formSelector) {
                  const form = toElement(formSelector);
                  form?.submit();
                }
              },
            });
          }
          return instance;
        };

        const openButton = toElement(openButtonSelector);
        if (openButton && modal?.id) {
          openButton.setAttribute("data-bs-toggle", "modal");
          openButton.setAttribute("data-bs-target", `#${modal.id}`);
          openButton.addEventListener("click", () => {
            ensureInstance();
          });
        }

        if (modal) {
          modal.addEventListener("show.bs.modal", () => {
            ensureInstance();
          });
        }

        const instance = ensureInstance();
        if (instance) {
          const hiddenInput = toElement(hiddenInputSelector);
          const initialValues = hiddenInput?.value
            ? hiddenInput.value.split(",").map((value) => value.trim())
            : [];
          instance.ready().then(() => {
            if (initialValues.length) {
              instance.selectBy(initialValues, valueKey);
            }
          });
        }
      });
    },

    updatePreview(tags, selectors, instance, options = {}) {
      const {
        previewSelector,
        countSelector,
        chipsSelector,
        hiddenInputSelector,
        hiddenValueKey = "name",
      } = selectors || {};

      const preview = toElement(previewSelector);
      const count = toElement(countSelector);
      const chips = toElement(chipsSelector);
      const hiddenInput = toElement(hiddenInputSelector);

      if (!tags || !Array.isArray(tags)) {
        return;
      }

      if (preview) {
        preview.style.display = tags.length ? "block" : "none";
      }

      if (count) {
        count.textContent = tags.length
          ? `已选择 ${tags.length} 个标签`
          : "未选择标签";
      }

      if (hiddenInput) {
        hiddenInput.value = tags
          .map((tag) => tag[hiddenValueKey] ?? tag.name ?? tag.id)
          .join(",");
      }

      if (chips) {
        if (!tags.length) {
          chips.innerHTML = "";
        } else {
          chips.innerHTML = tags
            .map((tag) => {
              const badge = resolveBadge(tag);
              return `
                <span class="badge rounded-pill d-inline-flex align-items-center gap-2 ${badge.className}" ${badge.style ? `style="${badge.style}"` : ""} data-role="external-chip" data-tag-id="${tag.id}">
                  <span><i class="fas fa-tag me-1"></i>${tag.display_name || tag.name}</span>
                  ${
                    instance
                      ? `<button type="button" class="btn-close btn-close-white" aria-label="移除标签" data-role="external-chip-remove" data-tag-id="${tag.id}"></button>`
                      : ""
                  }
                </span>
              `;
            })
            .join("");

          if (instance) {
            chips.querySelectorAll("[data-role=\"external-chip-remove\"]").forEach((button) => {
              button.addEventListener("click", (event) => {
                event.preventDefault();
                const tagId = Number(button.dataset.tagId);
                if (Number.isFinite(tagId)) {
                  instance.removeTag(tagId);
                  this.updatePreview(
                    instance.getSelectedTags(),
                    selectors,
                    instance,
                    { silent: true },
                  );
                }
              });
            });
          }
        }
      }

      // 更新预览不触发二次变更
    },
  };

  document.addEventListener("click", (event) => {
    const action = event.target.closest("[data-tag-selector-action]");
    if (!action) {
      return;
    }
    const modal = action.closest("[data-tag-selector-modal]");
    if (!modal) {
      return;
    }
    const root = modal.querySelector("[data-tag-selector]");
    if (!root) {
      return;
    }
    const instance = manager.get(root);
    if (!instance) {
      return;
    }

    const mode = action.getAttribute("data-tag-selector-action");
    if (mode === "confirm") {
      event.preventDefault();
      instance.confirmSelection();
    } else if (mode === "cancel") {
      event.preventDefault();
      instance.cancelSelection();
    }
  });

  window.tagSelectorManager = manager;
  window.TagSelectorHelper = TagSelectorHelper;
})(window, document);
