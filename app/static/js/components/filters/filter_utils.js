(function (window, document) {
  "use strict";

  const DEFAULT_TOM_SELECT_CONFIG = {
    create: false,
    allowEmptyOption: true,
    persist: false,
    sortField: [
      { field: "order", direction: "asc" },
      { field: "$score" },
      { field: "text", direction: "asc" },
    ],
    maxOptions: 1000,
    render: {
      option: function (data, escape) {
        if (data.color) {
          return `<div class="d-flex align-items-center gap-2">
                    <span class="badge bg-${escape(data.color)}">${escape(data.text)}</span>
                    ${data.category ? `<span class="text-muted small">${escape(data.category)}</span>` : ""}
                  </div>`;
        }
        return `<div>${escape(data.text)}</div>`;
      },
      item: function (data, escape) {
        if (data.color) {
          return `<div class="tag-chip badge bg-${escape(data.color)}">
                    ${escape(data.text)}
                    <button type="button" data-ts-item-remove aria-label="移除 ${escape(data.text)}">&times;</button>
                  </div>`;
        }
        return `<div>${escape(data.text)}</div>`;
      },
    },
  };

  const formRegistry = new Map();
  const caches = {
    tags: null,
  };

  function resolveElement(target) {
    if (typeof target === "string") {
      return document.querySelector(target);
    }
    return target;
  }

  function initTomSelect(target, config) {
    const element = resolveElement(target);
    if (!element) {
      return null;
    }
    if (element.tomselect) {
      return element.tomselect;
    }
    const userConfig = config || {};
    const options = Object.assign({}, DEFAULT_TOM_SELECT_CONFIG, userConfig);

    const defaultRender = DEFAULT_TOM_SELECT_CONFIG.render || {};
    const customRender = userConfig.render || {};
    const renderConfig = Object.assign({}, defaultRender, customRender);
    if (!element.multiple && !customRender.item) {
      renderConfig.item = function (data, escape) {
        return `<div>${escape(data.text)}</div>`;
      };
    }
    options.render = renderConfig;

    const mergedPlugins = Object.assign({}, userConfig.plugins || {});
    if (element.multiple) {
      mergedPlugins.remove_button = mergedPlugins.remove_button || { title: "移除" };
      mergedPlugins.clear_button = mergedPlugins.clear_button || { title: "清除已选" };
    }
    if (Object.keys(mergedPlugins).length > 0) {
      options.plugins = mergedPlugins;
    } else {
      delete options.plugins;
    }

    const instance = new TomSelect(element, options);
    return instance;
  }

  function destroyTomSelect(target) {
    const element = resolveElement(target);
    if (element && element.tomselect) {
      element.tomselect.destroy();
    }
  }

  function clearForm(form) {
    const element = resolveElement(form);
    if (!element) {
      return;
    }

    element.querySelectorAll("input[type='text'], input[type='search'], input[type='number']").forEach((input) => {
      input.value = "";
    });

    element.querySelectorAll("select").forEach((select) => {
      if (select.multiple) {
        Array.from(select.options).forEach((option) => {
          option.selected = false;
        });
      } else {
        select.selectedIndex = 0;
      }
      if (select.tomselect) {
        select.tomselect.clear(true);
        select.tomselect.refreshOptions(false);
      }
    });

    element.querySelectorAll("input[type='hidden']").forEach((hidden) => {
      if (!hidden.dataset.preserve) {
        hidden.value = "";
      }
    });
  }

  function registerFilterForm(form, config) {
    const element = resolveElement(form);
    if (!element) {
      return null;
    }

    const mergedConfig = Object.assign(
      {
        onSubmit: null,
        onClear: null,
        submitButtonSelector: "[data-filter-submit]",
        clearButtonSelector: "[data-filter-clear]",
      },
      config || {}
    );

    const entry = {
      element,
      config: mergedConfig,
    };

    const submitButton = element.querySelector(mergedConfig.submitButtonSelector);
    if (submitButton) {
      submitButton.addEventListener("click", (event) => {
        if (mergedConfig.onSubmit) {
          event.preventDefault();
          mergedConfig.onSubmit({ form: element, event });
        } else {
          element.requestSubmit();
        }
      });
    }

    const clearButton = element.querySelector(mergedConfig.clearButtonSelector);
    if (clearButton) {
      clearButton.addEventListener("click", (event) => {
        event.preventDefault();
        clearForm(element);
        if (mergedConfig.onClear) {
          mergedConfig.onClear({ form: element, event });
        } else {
          element.submit();
        }
      });
    }

    element.addEventListener("submit", (event) => {
      if (mergedConfig.onSubmit) {
        event.preventDefault();
        mergedConfig.onSubmit({ form: element, event });
      }
    });

    formRegistry.set(element, entry);
    return entry;
  }

  function setTagCache(data) {
    caches.tags = Array.isArray(data) ? data : null;
  }

  function getTagCache() {
    return caches.tags;
  }

  window.FilterUtils = {
    initTomSelect,
    destroyTomSelect,
    clearForm,
    registerFilterForm,
    setTagCache,
    getTagCache,
    formRegistry,
  };
  document.addEventListener("DOMContentLoaded", () => {
    document.querySelectorAll("[data-tom-select]").forEach((element) => {
      let config = {};
      if (element.dataset.tomSelectConfig) {
        try {
          config = JSON.parse(element.dataset.tomSelectConfig);
        } catch (error) {
          console.warn("Tom Select 配置解析失败:", error);
        }
      }
      initTomSelect(element, config);
    });
  });
})(window, document);
