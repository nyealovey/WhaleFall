(function (window) {
  "use strict";

  const helpers = window.DOMHelpers;
  if (!helpers) {
    console.error("DOMHelpers 未初始化，无法加载 CapacityStatsFilters");
    return;
  }

  const { selectOne, select } = helpers;

  /**
   * 工具：支持 selector 或 Element。
   *
   * @param {string|Element} selector - CSS 选择器或 DOM 元素
   * @param {Element|null} [context=null] - 限定查找上下文（用于多实例组件隔离）
   * @return {Element|null} DOM 元素或 null
   */
  function getElement(selector, context = null) {
    if (!selector) {
      return null;
    }
    if (typeof selector === "string") {
      return selectOne(selector, context).first();
    }
    if (selector instanceof Element) {
      return selector;
    }
    return null;
  }

  /**
   * 读取下拉框值，找不到则返回空字符串。
   *
   * @param {string|Element} selector - CSS 选择器或 DOM 元素
   * @param {Element|null} [context=null] - 限定查找上下文
   * @return {string} 下拉框的值
   */
  function readSelectValue(selector, context = null) {
    const element = getElement(selector, context);
    if (!element) {
      return "";
    }
    return element.value || "";
  }

  function readCheckboxValues(selector, context = null) {
    const element = getElement(selector, context);
    if (!element) {
      return [];
    }
    return Array.from(element.querySelectorAll('input[type="checkbox"]:checked'))
      .map((input) => input?.value || "")
      .filter(Boolean);
  }

  /**
   * 获取 radio 组当前选中值，无则返回 fallback。
   *
   * @param {string} name - radio 组的 name 属性
   * @param {string} fallback - 默认值
   * @return {string} 选中的值或默认值
   */
  function readRadioValue(name, fallback) {
    if (!name) {
      return fallback;
    }
    const checked = select(`input[name="${name}"]:checked`).first();
    return checked ? checked.value : fallback;
  }

  /**
   * 初始化筛选（实例/数据库/周期等）。
   *
   * @param {Object} [config] 由 CapacityStats.Manager 传入的配置。
   * @return {Object} 筛选条件对象
   */
  function readInitialFilters(config = {}) {
    const filterForm = getElement(config?.filterFormId || null);

    const dbTypes = readCheckboxValues("#db_type", filterForm);
    const instanceIds = readCheckboxValues('[data-role="instance-filter"]', filterForm);
    const databaseSelect = getElement('[data-role="database-filter"]', filterForm);
    const databaseId = databaseSelect ? databaseSelect.value || "" : "";
    let databaseName = null;
    if (databaseSelect && databaseId) {
      const option = databaseSelect.options[databaseSelect.selectedIndex];
      if (option && option.textContent) {
        databaseName = option.textContent.trim();
      }
    }
    const periodType = readSelectValue("#period_type", filterForm) || "daily";

    return {
      dbTypes,
      instanceIds,
      databaseId,
      databaseName,
      periodType: periodType || "daily",
    };
  }

  /**
   * 读取图表类型/Top/周期的初始状态。
   *
   * @param {void} 无参数。直接解析已渲染表单。
   * @returns {Object} trend/change/percent 的配置对象。
   */
  function readChartState() {
    const trendType = readRadioValue("chartType", "line");
    const trendTop = Number(readRadioValue("topSelector", "5")) || 5;
    const trendPeriods = Number(readRadioValue("statisticsPeriod", "7")) || 7;

    const changeType = readRadioValue("changeChartType", "line");
    const changeTop = Number(readRadioValue("changeTopSelector", "5")) || 5;
    const changePeriods = Number(readRadioValue("changeStatisticsPeriod", "7")) || 7;

    const percentType = readRadioValue("changePercentChartType", "line");
    const percentTop = Number(readRadioValue("changePercentTopSelector", "5")) || 5;
    const percentPeriods = Number(readRadioValue("changePercentStatisticsPeriod", "7")) || 7;

    return {
      trend: {
        type: trendType,
        top: trendTop,
        periods: trendPeriods,
      },
      change: {
        type: changeType,
        top: changeTop,
        periods: changePeriods,
      },
      percent: {
        type: percentType,
        top: percentTop,
        periods: percentPeriods,
      },
    };
  }

  /**
   * 更新下拉框选项，支持占位、默认值等配置。
   *
   * @param {string|Element} element 目标 select 或其选择器。
   * @param {Object} options 选项配置，包含 placeholder/items 等。
   * @returns {void}
   */
  function updateSelectOptions(element, options) {
    const target = getElement(element);
    if (!target) {
      return;
    }
    const {
      placeholder = "",
      allowEmpty = true,
      items = [],
      selected = "",
      getOptionValue,
      getOptionLabel,
    } = options || {};

    target.innerHTML = "";

    if (allowEmpty) {
      const emptyOption = document.createElement("option");
      emptyOption.value = "";
      emptyOption.textContent = placeholder || "全部";
      target.appendChild(emptyOption);
    }

    items.forEach((item) => {
      const option = document.createElement("option");
      const value =
        (typeof getOptionValue === "function"
          ? getOptionValue(item)
          : item?.value) ?? "";
      const label =
        (typeof getOptionLabel === "function"
          ? getOptionLabel(item)
          : item?.label) ?? value ?? "";
      option.value = String(value);
      option.textContent = label;
      if (target.multiple) {
        const selectedValues = Array.isArray(selected)
          ? selected.map((item) => String(item))
          : selected
            ? [String(selected)]
            : [];
        if (selectedValues.includes(String(value))) {
          option.selected = true;
        }
      } else if (selected && String(selected) === String(value)) {
        option.selected = true;
      }
      target.appendChild(option);
    });
  }

  /**
   * 设置 select 的值并触发 change。
   *
   * @param {string|Element} selector 目标选择器或元素。
   * @param {string|number} value 需要设置的值。
   * @returns {void}
   */
  function updateCheckboxSummary(element) {
    const target = getElement(element);
    if (!target) {
      return;
    }
    const summary = target.querySelector('[data-role="multiselect-summary"]');
    if (!summary) {
      return;
    }
    const placeholder = target.dataset.placeholder || "请选择";
    const summaryMode = target.dataset.summaryMode || "count";
    const selectedInputs = Array.from(target.querySelectorAll('input[type="checkbox"]:checked'));
    summary.replaceChildren();

    if (!selectedInputs.length) {
      summary.textContent = placeholder;
      return;
    }

    if (summaryMode !== "instance-assets") {
      summary.textContent = `已选 ${selectedInputs.length} 项`;
      return;
    }

    const summaryShell = document.createElement("span");
    summaryShell.className = "filter-multiselect__summary-inline";
    if (selectedInputs.length === 1) {
      const first = selectedInputs[0];
      const assetUrl = first?.dataset?.assetUrl || "";
      const labelText = first?.dataset?.summaryLabel || first?.value || "";
      if (assetUrl) {
        const asset = document.createElement("img");
        asset.className = "filter-multiselect__asset";
        asset.src = assetUrl;
        asset.alt = "";
        asset.setAttribute("aria-hidden", "true");
        summaryShell.appendChild(asset);
      }
      const text = document.createElement("span");
      text.className = "filter-multiselect__summary-text";
      text.textContent = labelText;
      summaryShell.appendChild(text);
      summary.appendChild(summaryShell);
      return;
    }

    const icons = document.createElement("span");
    icons.className = "filter-multiselect__summary-icons";
    selectedInputs.slice(0, 2).forEach((input) => {
      const assetUrl = input?.dataset?.assetUrl || "";
      if (!assetUrl) {
        return;
      }
      const asset = document.createElement("img");
      asset.className = "filter-multiselect__asset";
      asset.src = assetUrl;
      asset.alt = "";
      asset.setAttribute("aria-hidden", "true");
      icons.appendChild(asset);
    });
    summaryShell.appendChild(icons);

    const text = document.createElement("span");
    text.className = "filter-multiselect__summary-text";
    text.textContent = `已选 ${selectedInputs.length} 个实例`;
    summaryShell.appendChild(text);
    summary.appendChild(summaryShell);
  }

  function updateCheckboxOptions(element, options) {
    const target = getElement(element);
    if (!target) {
      return;
    }
    const host = target.querySelector('[data-role="checkbox-group"]') || target;
    const {
      items = [],
      selected = [],
      disabled = false,
      emptyText = "暂无可选项",
      name = target.dataset.fieldName || "",
      summaryMode = target.dataset.summaryMode || "count",
      showOptionAssets = false,
      getOptionValue,
      getOptionLabel,
      getOptionMeta,
    } = options || {};

    const selectedValues = Array.isArray(selected)
      ? selected.map((item) => String(item))
      : selected
        ? [String(selected)]
        : [];

    host.innerHTML = "";
    target.classList.toggle("filter-multiselect--disabled", Boolean(disabled));
    target.dataset.summaryMode = summaryMode;

    if (!items.length) {
      const empty = document.createElement("div");
      empty.className = "filter-multiselect__empty";
      empty.textContent = emptyText;
      host.appendChild(empty);
      updateCheckboxSummary(target);
      return;
    }

    items.forEach((item, index) => {
      const value = String(
        (typeof getOptionValue === "function" ? getOptionValue(item) : item?.value) ?? "",
      );
      const labelText = String(
        (typeof getOptionLabel === "function" ? getOptionLabel(item) : item?.label) ?? value,
      );
      const meta = typeof getOptionMeta === "function" ? getOptionMeta(item) : {};
      const assetUrl = String(meta?.assetUrl || item?.asset_url || "");
      const option = document.createElement("label");
      option.className = "filter-multiselect__option";
      if (showOptionAssets && assetUrl) {
        option.classList.add("filter-multiselect__option--with-asset");
      }

      const input = document.createElement("input");
      input.className = "form-check-input filter-multiselect__input";
      input.type = "checkbox";
      input.name = name;
      input.value = value;
      input.id = `${target.id || name || "checkbox-filter"}-${index + 1}`;
      input.checked = selectedValues.includes(value);
      input.disabled = Boolean(disabled);
      input.dataset.summaryLabel = labelText;
      input.dataset.assetUrl = assetUrl;

      if (showOptionAssets && assetUrl) {
        const asset = document.createElement("img");
        asset.className = "filter-multiselect__asset";
        asset.src = assetUrl;
        asset.alt = "";
        asset.setAttribute("aria-hidden", "true");
        option.appendChild(asset);
      }

      const label = document.createElement("span");
      label.className = "filter-multiselect__label";
      if (showOptionAssets) {
        label.className = "filter-multiselect__label filter-multiselect__label--single-line";
      }
      label.textContent = labelText;

      option.htmlFor = input.id;
      option.appendChild(input);
      option.appendChild(label);
      host.appendChild(option);
    });

    updateCheckboxSummary(target);
  }

  function syncSelectValue(selector, value) {
    const element = getElement(selector);
    if (!element) {
      return;
    }
    const selectedValues = Array.isArray(value)
      ? value.map((item) => String(item))
      : value
        ? [String(value)]
        : [];

    if (element.tagName === "SELECT") {
      if (element.multiple) {
        Array.from(element.options).forEach((option) => {
          option.selected = selectedValues.includes(String(option.value));
        });
        return;
      }
      element.value = value ?? "";
      return;
    }

    element.querySelectorAll('input[type="checkbox"]').forEach((input) => {
      input.checked = selectedValues.includes(String(input.value));
    });
    updateCheckboxSummary(element);
  }

  /**
   * 启用/禁用控件。
   *
   * @param {string|Element} selector 目标元素或选择器。
   * @param {boolean} disabled 是否禁用。
   * @returns {void}
   */
  function setDisabled(selector, disabled) {
    const element = getElement(selector);
    if (!element) {
      return;
    }
    const resolvedDisabled = Boolean(disabled);
    if (element.tagName === "SELECT" || element.tagName === "INPUT") {
      element.disabled = resolvedDisabled;
      return;
    }
    element.classList.toggle("filter-multiselect--disabled", resolvedDisabled);
    const trigger = element.querySelector('[data-role="multiselect-trigger"]');
    if (trigger) {
      trigger.disabled = resolvedDisabled;
    }
    element.querySelectorAll('input[type="checkbox"]').forEach((input) => {
      input.disabled = resolvedDisabled;
    });
  }

  window.CapacityStatsFilters = {
    readInitialFilters,
    readChartState,
    updateSelectOptions,
    updateCheckboxOptions,
    updateCheckboxSummary,
    syncSelectValue,
    setDisabled,
  };
})(window);
