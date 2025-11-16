(function (window) {
  "use strict";

  const helpers = window.DOMHelpers;
  if (!helpers) {
    console.error("DOMHelpers 未初始化，无法加载 CapacityStatsFilters");
    return;
  }

  const { selectOne, select } = helpers;

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

  function readSelectValue(selector) {
    const element = getElement(selector);
    if (!element) {
      return "";
    }
    return element.value || "";
  }

  function readRadioValue(name, fallback) {
    if (!name) {
      return fallback;
    }
    const checked = select(`input[name="${name}"]:checked`).first();
    return checked ? checked.value : fallback;
  }

  function readInitialFilters(config) {
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

  function syncSelectValue(selector, value) {
    const element = getElement(selector);
    if (!element) {
      return;
    }
    element.value = value ?? "";
    element.dispatchEvent(new Event("change", { bubbles: true }));
  }

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
