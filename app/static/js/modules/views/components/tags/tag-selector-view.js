(function (window, document) {
  "use strict";

  const LodashUtils = window.LodashUtils;
  const NumberFormat = window.NumberFormat;

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

  /**
   * 将标签颜色转成 badge 的 class/style。
   *
   * @param {Object} tag - 标签对象
   * @param {string} [tag.color] - 标签颜色
   * @return {Object} 包含 className 和 style 的对象
   */
  function resolveBadge(tag) {
    const color = tag?.color || "";
    if (color.startsWith("bg-")) {
      return { className: `badge rounded-pill ${color}`, style: "" };
    }
    if (color.startsWith("#")) {
      return {
        className: "badge rounded-pill",
        style: `background-color: ${color}; color: var(--surface-elevated);`,
      };
    }
    return { className: "badge rounded-pill bg-secondary", style: "" };
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
        categoryGroup.addEventListener("change", (event) => {
          const radio = event.target.closest('input[type="radio"]');
          if (radio) {
            this.handlers.onCategoryChange(radio.value);
          }
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
        group.innerHTML = `<div class="alert alert-warning w-100 mb-0">${error}</div>`;
        return;
      }
      const ordered = orderCategories(
        categories.map((item) => ({
          value: item.value ?? item.name ?? item[0],
          label: item.label ?? item.display_name ?? item[1],
        })),
      );
      const radios = [`
        <label class="btn btn-outline-secondary btn-sm">
          <input type="radio" name="tag-category" value="all" autocomplete="off" checked>
          全部
        </label>
      `].concat(
        ordered.map(
          (item) => `
          <label class="btn btn-outline-secondary btn-sm">
            <input type="radio" name="tag-category" value="${item.value}" autocomplete="off">
            ${item.label || item.value}
          </label>
        `,
        ),
      );
      group.innerHTML = radios.join("");
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
      if (!tags.length) {
        list.innerHTML = this.renderEmptyState();
        return;
      }
      const html = tags
        .map((tag) => {
          const badge = resolveBadge(tag);
          const isSelected = selection.has(tag.id);
          const classes = [
            "list-group-item",
            "d-flex",
            "justify-content-between",
            "align-items-center",
            "tag-selector__item",
            isSelected ? "active" : "",
            tag.is_active === false ? "disabled" : "",
          ]
            .filter(Boolean)
            .join(" ");
          return `
            <button type="button" class="${classes}" data-tag-id="${tag.id}">
              <div class="text-start">
                <div class="fw-semibold">${tag.display_name || tag.name}
                  ${tag.is_active === false ? '<span class="badge bg-danger ms-2">禁用</span>' : ""}
                </div>
                <div class="small text-muted">${tag.description || "未提供描述"}</div>
              </div>
              <span class="badge bg-light text-dark rounded-pill">${badge.label || "标签"}</span>
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
        <div class="text-center text-muted py-5">
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
        <div class="text-center text-muted py-5">
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
        .map((tag) => {
          const badge = resolveBadge(tag);
          return `
            <span class="tag-chip ${badge.className}" ${badge.style ? `style="${badge.style}"` : ""} data-role="selected-chip" data-tag-id="${tag.id}">
              <span><i class="fas fa-tag me-1"></i>${tag.display_name || tag.name}</span>
              <button type="button" class="btn-close btn-close-white" aria-label="移除标签" data-role="chip-remove" data-tag-id="${tag.id}"></button>
            </span>`;
        })
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
      this.elements.statsWrapper.hidden = false;
    }
  }

  window.TagSelectorView = TagSelectorView;
})(window, document);
