(function (window, document) {
  "use strict";

  const LodashUtils = window.LodashUtils;
  const NumberFormat = window.NumberFormat;
  const DEFAULT_CATEGORY = "all";

  /**
   * 将多种输入转换为 DOM 元素，方便外部引用选择器。
   *
   * @param {string|Element} target - 目标元素或选择器
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
    return null;
  }

  /**
   * 对分类列表进行去重和排序，保持 UI 稳定。
   *
   * @param {Array<Object>} items - 分类数组
   * @return {Array<Object>} 去重并排序后的分类数组
   */
  function orderCategories(items) {
    const collection = Array.isArray(items) ? items.filter(Boolean) : [];
    const deduped = LodashUtils?.uniqBy ? LodashUtils.uniqBy(collection, "value") : collection;
    return LodashUtils?.orderBy
      ? LodashUtils.orderBy(deduped, ["label"], ["asc"])
      : deduped;
  }

  /**
   * 按激活状态与名称排序标签，用于列表与已选区。
   *
   * @param {Array<Object>} items - 标签数组
   * @return {Array<Object>} 排序后的标签数组
   */
  function orderTags(items) {
    if (!Array.isArray(items)) {
      return [];
    }
    if (!LodashUtils?.orderBy) {
      return items.slice();
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

  function buildChipOutline(text, tone = "muted", iconClass) {
    const classes = ["chip-outline", tone === "brand" ? "chip-outline--brand" : "chip-outline--muted"];
    const icon = iconClass ? `<i class="${iconClass}" aria-hidden="true"></i>` : "";
    return `<span class="${classes.join(" ")}">${icon}${escapeHtml(text)}</span>`;
  }

  function buildStatusPill(isActive) {
    const variant = isActive ? "status-pill--info" : "status-pill--muted";
    const label = isActive ? "启用" : "停用";
    const icon = isActive ? "fas fa-check" : "fas fa-ban";
    return `<span class="status-pill ${variant}"><i class="${icon}"></i>${label}</span>`;
  }

  function buildLedgerChip(text, { muted = false } = {}) {
    const classes = ["ledger-chip", muted ? "ledger-chip--muted" : ""].filter(Boolean).join(" ");
    return `<span class="${classes}"><i class="fas fa-tag"></i>${escapeHtml(text)}</span>`;
  }

  /**
   * 使用统一的数字格式化工具展示统计数。
   *
   * @param {number} value - 数值
   * @return {string} 格式化后的字符串
   */
  function formatNumber(value) {
    return NumberFormat?.formatInteger
      ? NumberFormat.formatInteger(value, { fallback: "0" })
      : value;
  }

  /**
   * 负责标签选择器的 DOM 渲染与用户交互绑定。
   *
   * @class
   */
  class TagSelectorView {
    /**
     * 构造函数。
     *
     * @constructor
     * @param {string|Element} root - 根元素或选择器
     * @param {Object} [handlers] - 事件处理器
     * @param {Function} [handlers.onCategoryChange] - 分类切换回调
     * @param {Function} [handlers.onTagToggle] - 标签切换回调
     * @param {Function} [handlers.onSelectedRemove] - 移除已选标签回调
     * @throws {Error} 当 root 未找到时抛出
     */
    constructor(root, handlers = {}) {
      this.root = toElement(root);
      if (!this.root) {
        throw new Error("TagSelectorView: root 未找到");
      }
      this.handlers = {
        onCategoryChange: handlers.onCategoryChange || (() => {}),
        onTagToggle: handlers.onTagToggle || (() => {}),
        onSelectedRemove: handlers.onSelectedRemove || (() => {}),
      };
      this.elements = this.cacheElements();
      this.activeCategory = DEFAULT_CATEGORY;
      this.bindEvents();
    }

    /**
     * 缓存组件用到的核心节点，避免重复查询。
     *
     * @return {Object} 包含所有缓存元素的对象
     */
    cacheElements() {
      return {
        categoryGroup: this.root.querySelector('[data-role="category-group"]'),
        categoryLoading: this.root.querySelector('[data-role="category-loading"]'),
        statsWrapper: this.root.querySelector('[data-role="stats"]'),
        statTotal: this.root.querySelector('[data-role="stat-total"]'),
        statSelected: this.root.querySelector('[data-role="stat-selected"]'),
        statActive: this.root.querySelector('[data-role="stat-active"]'),
        statFiltered: this.root.querySelector('[data-role="stat-filtered"]'),
        tagList: this.root.querySelector('[data-role="tag-list"]'),
        selectedList: this.root.querySelector('[data-role="selected-list"]'),
        selectedEmpty: this.root.querySelector('[data-role="selected-empty"]'),
      };
    }

    /**
     * 绑定分类切换、标签点击与已选标签删除等交互。
     *
     * @return {void}
     */
    bindEvents() {
      const { categoryGroup, tagList, selectedList } = this.elements;
      if (categoryGroup) {
        categoryGroup.addEventListener("click", (event) => {
          const chip = event.target.closest("[data-category-value]");
          if (!chip) {
            return;
          }
          const value = chip.dataset.categoryValue;
          this.setActiveCategory(value);
          this.handlers.onCategoryChange(value);
        });
      }
      if (tagList) {
        tagList.addEventListener("click", (event) => {
          const target = event.target.closest('[data-tag-id]');
          if (!target || target.classList.contains("disabled")) {
            return;
          }
          const tagId = Number(target.dataset.tagId);
          if (Number.isFinite(tagId)) {
            this.handlers.onTagToggle(tagId);
          }
        });
      }
      if (selectedList) {
        selectedList.addEventListener("click", (event) => {
          const removeBtn = event.target.closest('[data-role="chip-remove"]');
          if (!removeBtn) {
            return;
          }
          const tagId = Number(removeBtn.dataset.tagId);
          if (Number.isFinite(tagId)) {
            this.handlers.onSelectedRemove(tagId);
          }
        });
      }
    }

    /**
     * 渲染分类按钮，出现错误时输出告警文案。
     *
     * @param {Array<Object>} [categories] - 分类数组
     * @param {string} [error] - 错误消息
     * @return {void}
     */
    renderCategories(categories = [], error) {
      const group = this.elements.categoryGroup;
      if (!group) {
        return;
      }
      const loading = this.elements.categoryLoading;
      if (loading) {
        loading.remove();
      }
      group.innerHTML = "";
      if (error) {
        group.innerHTML = `<div class="tag-selector__placeholder text-muted">${escapeHtml(error)}</div>`;
        return;
      }
      const ordered = orderCategories(
        categories.map((item) => ({
          value: item.value ?? item.name ?? item[0],
          label: item.label ?? item.display_name ?? item[1],
        })),
      );
      const chips = [
        { value: DEFAULT_CATEGORY, label: "全部" },
        ...ordered.map((item) => ({ value: item.value, label: item.label || item.value })),
      ];
      group.innerHTML = chips
        .map(
          (item) =>
            `<button type="button" class="chip-outline chip-outline--muted" data-category-value="${item.value}" aria-pressed="false">
              ${escapeHtml(item.label)}
            </button>`,
        )
        .join("");
      this.setActiveCategory(this.activeCategory);
    }

    /**
     * 渲染标签列表，结合当前选择状态展示。
     *
     * @param {Array<Object>} [tags] - 标签数组
     * @param {Set<number>} [selection] - 已选标签 ID 集合
     * @param {Object} [options] - 渲染选项
     * @return {void}
     */
    renderTagList(tags = [], selection = new Set(), options = {}) {
      const list = this.elements.tagList;
      if (!list) {
        return;
      }
      if (options?.error) {
        list.innerHTML = this.renderErrorState(options.error);
        return;
      }
      if (!tags.length) {
        list.innerHTML = this.renderEmptyState();
        return;
      }
      const html = tags
        .map((tag) => {
          const isSelected = selection.has(tag.id);
          const classes = [
            "tag-selector__item",
            isSelected ? "tag-selector__item--selected" : "",
            tag.is_active === false ? "tag-selector__item--disabled disabled" : "",
          ]
            .filter(Boolean)
            .join(" ");
          const disabledAttr = tag.is_active === false ? 'aria-disabled="true"' : '';
          return `
            <button type="button" class="${classes}" data-tag-id="${tag.id}" aria-pressed="${isSelected}" ${disabledAttr}>
              <div class="tag-selector__item-main">
                <div class="tag-selector__item-title">${escapeHtml(tag.display_name || tag.name || "-")}</div>
                <div class="tag-selector__item-description">${escapeHtml(tag.description || "未提供描述")}</div>
                <div class="tag-selector__item-meta">
                  ${buildChipOutline(tag.category || "未分类", "muted", "fas fa-folder")}
                  ${buildStatusPill(tag.is_active !== false)}
                </div>
              </div>
              <span class="tag-selector__item-action"><i class="${isSelected ? "fas fa-check" : "fas fa-plus"}"></i></span>
            </button>
          `;
        })
        .join("");
      list.innerHTML = html;
    }

    /**
     * 返回用于标签列表的加载占位 DOM 片段。
     *
     * @return {string} 加载状态 HTML
     */
    renderLoadingState() {
      return `
        <div class="tag-selector__placeholder text-muted">
          <div class="spinner-border text-primary mb-3" role="status">
            <span class="visually-hidden">加载中...</span>
          </div>
          <div>正在加载标签...</div>
        </div>`;
    }

    /**
     * 返回“暂无标签”占位 DOM 片段。
     */
    renderEmptyState() {
      return `
        <div class="tag-selector__placeholder text-muted">
          <i class="fas fa-tags fa-2x mb-2"></i>
          <p class="mb-0">暂无标签数据</p>
        </div>`;
    }

    /**
     * 返回错误态占位 DOM 片段。
     *
     * @param {string} message - 错误消息
     * @return {string} 错误状态 HTML
     */
    renderErrorState(message) {
      return `
        <div class="alert alert-warning mb-0">
          <i class="fas fa-exclamation-triangle me-2"></i>${message || "加载失败"}
        </div>`;
    }

    /**
     * 根据已选标签渲染 chips 区域。
     *
     * @param {Array<Object>} [tags] - 已选标签数组
     * @return {void}
     */
    updateSelectedDisplay(tags = []) {
      const selectedList = this.elements.selectedList;
      const selectedEmpty = this.elements.selectedEmpty;
      if (!selectedList || !selectedEmpty) {
        return;
      }
      if (!tags.length) {
        selectedList.innerHTML = "";
        selectedEmpty.hidden = false;
        return;
      }
      selectedEmpty.hidden = true;
      const chips = tags
        .map((tag) => `
          <span class="ledger-chip" data-role="selected-chip" data-tag-id="${tag.id}">
            <i class="fas fa-tag"></i>${escapeHtml(tag.display_name || tag.name || "")}
            <button type="button" class="btn-icon btn-icon--sm" aria-label="移除标签" data-role="chip-remove" data-tag-id="${tag.id}">
              <i class="fas fa-times"></i>
            </button>
          </span>`)
        .join("");
      selectedList.innerHTML = chips;
    }

    /**
     * 更新统计条展示。
     *
     * @param {Object} [stats] - 统计数据
     * @param {number} [stats.total] - 总标签数
     * @param {number} [stats.selected] - 已选标签数
     * @param {number} [stats.active] - 激活标签数
     * @param {number} [stats.filtered] - 筛选后标签数
     * @return {void}
     */
    updateStats(stats = {}) {
      if (!this.elements.statsWrapper) {
        return;
      }
      const resolved = {
        total: stats.total || 0,
        selected: stats.selected || 0,
        active: stats.active || 0,
        filtered: stats.filtered || 0,
      };
      this.elements.statTotal.textContent = formatNumber(resolved.total);
      this.elements.statSelected.textContent = formatNumber(resolved.selected);
      this.elements.statActive.textContent = formatNumber(resolved.active);
      this.elements.statFiltered.textContent = formatNumber(resolved.filtered);
      const shouldHide = !resolved.total && !resolved.selected && !resolved.active && !resolved.filtered;
      this.elements.statsWrapper.hidden = shouldHide;
    }
  }

  window.TagSelectorView = TagSelectorView;
})(window, document);
    setActiveCategory(value) {
      this.activeCategory = value || DEFAULT_CATEGORY;
      const group = this.elements.categoryGroup;
      if (!group) {
        return;
      }
      group.querySelectorAll("[data-category-value]").forEach((chip) => {
        const isActive = chip.dataset.categoryValue === this.activeCategory;
        chip.classList.toggle("chip-outline--brand", isActive);
        chip.classList.toggle("chip-outline--muted", !isActive);
        chip.setAttribute("aria-pressed", isActive ? "true" : "false");
      });
    }
