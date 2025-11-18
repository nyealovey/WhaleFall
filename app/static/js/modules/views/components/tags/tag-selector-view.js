(function (window, document) {
  "use strict";

  const LodashUtils = window.LodashUtils;
  const NumberFormat = window.NumberFormat;

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

  function orderCategories(items) {
    const collection = Array.isArray(items) ? items.filter(Boolean) : [];
    const deduped = LodashUtils?.uniqBy ? LodashUtils.uniqBy(collection, "value") : collection;
    return LodashUtils?.orderBy
      ? LodashUtils.orderBy(deduped, ["label"], ["asc"])
      : deduped;
  }

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

  function resolveBadge(tag) {
    const color = tag?.color || "";
    if (color.startsWith("bg-")) {
      return { className: `badge rounded-pill ${color}`, style: "" };
    }
    if (color.startsWith("#")) {
      return {
        className: "badge rounded-pill",
        style: `background-color: ${color}; color: #fff;`,
      };
    }
    return { className: "badge rounded-pill bg-secondary", style: "" };
  }

  function formatNumber(value) {
    return NumberFormat?.formatInteger
      ? NumberFormat.formatInteger(value, { fallback: "0" })
      : value;
  }

  class TagSelectorView {
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

    renderLoadingState() {
      return `
        <div class="text-center text-muted py-5">
          <div class="spinner-border text-primary mb-3" role="status">
            <span class="visually-hidden">加载中...</span>
          </div>
          <div>正在加载标签...</div>
        </div>`;
    }

    renderEmptyState() {
      return `
        <div class="text-center text-muted py-5">
          <i class="fas fa-tags fa-2x mb-2"></i>
          <p class="mb-0">暂无标签数据</p>
        </div>`;
    }

    renderErrorState(message) {
      return `
        <div class="alert alert-warning mb-0">
          <i class="fas fa-exclamation-triangle me-2"></i>${message || "加载失败"}
        </div>`;
    }

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
