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
   * @return {Element|null} DOM 元素或 null
   */
  function getElement(selector) {
    if (!selector) {
      return null;
    }
    if (typeof selector === "string") {
      return selectOne(selector).first();
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
   * @return {string} 下拉框的值
   */
  function readSelectValue(selector) {
    const element = getElement(selector);
    if (!element) {
      return "";
    }
    return element.value || "";
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
   * @return {Object} 筛选条件对象
   */
  function readInitialFilters() {
    const dbType = readSelectValue("#db_type");
    const instanceId = readSelectValue("#instance");
    const databaseSelect = getElement("#database");
    const databaseId = databaseSelect ? databaseSelect.value || "" : "";
    let databaseName = null;
    if (databaseSelect && databaseId) {
      const option = databaseSelect.options[databaseSelect.selectedIndex];
      if (option && option.textContent) {
        databaseName = option.textContent.trim();
      }
    }
    const periodType = readSelectValue("#period_type") || "daily";

    return {
      dbType: dbType || "",
      instanceId,
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
      if (selected && String(selected) === String(value)) {
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
  function syncSelectValue(selector, value) {
    const element = getElement(selector);
    if (!element) {
      return;
    }
    element.value = value ?? "";
    element.dispatchEvent(new Event("change", { bubbles: true }));
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
    element.disabled = Boolean(disabled);
  }

  window.CapacityStatsFilters = {
    readInitialFilters,
    readChartState,
    updateSelectOptions,
    syncSelectValue,
    setDisabled,
  };
})(window);
