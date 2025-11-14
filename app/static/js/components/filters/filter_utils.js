(function (window, document) {
  "use strict";

  const LodashUtils = window.LodashUtils;
  if (!LodashUtils) {
    throw new Error("LodashUtils 未初始化");
  }

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

  const DEFAULT_REGISTER_CONFIG = {
    onSubmit: null,
    onClear: null,
    submitButtonSelector: "[data-filter-submit]",
    clearButtonSelector: "[data-filter-clear]",
    autoSubmitOnChange: true,
    autoSubmitSelectors: null,
    autoSubmitDebounce: 0,
  };

  const DEFAULT_AUTO_SUBMIT_SELECTORS =
    "select:not([data-no-auto-submit]), input[type='radio']:not([data-no-auto-submit]), input[type='checkbox']:not([data-no-auto-submit]), input[data-auto-submit]:not([data-no-auto-submit])";

  function createDebounced(fn, delay) {
    if (!delay) {
      return fn;
    }
    return LodashUtils.debounce(fn, delay);
  }

  function serializeForm(element) {
    if (!(element instanceof HTMLFormElement)) {
      return {};
    }
    const result = {};
    const formData = new FormData(element);
    formData.forEach((value, key) => {
      const normalizedValue = value instanceof File ? value.name : value;
      if (result[key] === undefined) {
        result[key] = normalizedValue;
      } else if (Array.isArray(result[key])) {
        result[key].push(normalizedValue);
      } else {
        result[key] = [result[key], normalizedValue];
      }
    });
    return result;
  }

  function emitFilterEvent(element, action, extra = {}) {
    if (!window.EventBus || !(element instanceof HTMLFormElement)) {
      return;
    }
    const detail = Object.assign(
      {
        action,
        formId: element.id || null,
        formName: element.getAttribute("name") || null,
        source: element.dataset.filterName || element.id || null,
        values: serializeForm(element),
      },
      extra || {},
    );
    window.EventBus.emit(`filters:${action}`, detail);
  }

  function requestFormSubmit(form) {
    if (!form) {
      return;
    }
    if (typeof form.requestSubmit === "function") {
      form.requestSubmit();
    } else {
      form.submit();
    }
  }

  const formRegistry = new Map();
  const caches = {
    tags: null,
  };

  function performSubmit(entry, event) {
    if (!entry) {
      return;
    }
    const { element, config } = entry;
    if (!element) {
      return;
    }
    emitFilterEvent(element, "submit", {
      trigger: event?.type || "manual",
    });
    if (config.onSubmit) {
      config.onSubmit({ form: element, event });
    } else {
      requestFormSubmit(element);
    }
  }

  function detachAutoSubmit(entry) {
    if (!entry || !entry.autoSubmitListeners) {
      return;
    }
    entry.autoSubmitListeners.forEach(({ target, handler, eventName }) => {
      if (target && handler) {
        target.removeEventListener(eventName, handler);
      }
    });
    entry.autoSubmitListeners = [];
  }

  function attachAutoSubmit(entry) {
    if (!entry) {
      return;
    }

    const { element, config } = entry;
    if (!element) {
      return;
    }

    detachAutoSubmit(entry);

    if (config.autoSubmitOnChange === false) {
      return;
    }

    const selectors = config.autoSubmitSelectors || DEFAULT_AUTO_SUBMIT_SELECTORS;
    const controls = selectors ? element.querySelectorAll(selectors) : [];

    entry.autoSubmitListeners = [];

    controls.forEach((control) => {
      if (!control || control.dataset.noAutoSubmit !== undefined) {
        return;
      }

      const eventName = control.dataset.autoSubmitEvent || (control.tagName === "INPUT" && control.type === "text" ? "change" : "change");
      const handler = createDebounced((event) => {
        emitFilterEvent(element, "change", {
          trigger: event?.type || eventName,
          targetName: control.name || control.id || null,
        });
        performSubmit(entry, event);
      }, config.autoSubmitDebounce);

      control.addEventListener(eventName, handler);
      entry.autoSubmitListeners.push({ target: control, handler, eventName });
    });
  }

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

    emitFilterEvent(element, "clear");
  }

  function registerFilterForm(form, config) {
    const element = resolveElement(form);
    if (!element) {
      return null;
    }

    const mergedConfig = Object.assign({}, DEFAULT_REGISTER_CONFIG, config || {});

    let entry = formRegistry.get(element);

    if (!entry) {
      entry = {
        element,
        config: mergedConfig,
        autoSubmitListeners: [],
      };

      const submitHandler = (event) => {
        if (entry.config.onSubmit) {
          event.preventDefault();
          emitFilterEvent(element, "submit", {
            trigger: event?.type || "submit",
          });
          entry.config.onSubmit({ form: element, event });
        }
      };
      element.addEventListener("submit", submitHandler);
      entry.submitHandler = submitHandler;

      const submitButton = element.querySelector(mergedConfig.submitButtonSelector);
      if (submitButton) {
        submitButton.addEventListener("click", (event) => {
          if (entry.config.onSubmit) {
            event.preventDefault();
            entry.config.onSubmit({ form: element, event });
          }
        });
      }

      const clearButton = element.querySelector(mergedConfig.clearButtonSelector);
      if (clearButton) {
        clearButton.addEventListener("click", (event) => {
          event.preventDefault();
          clearForm(element);
          if (entry.config.onClear) {
            entry.config.onClear({ form: element, event });
          } else {
            requestFormSubmit(element);
          }
        });
      }

      formRegistry.set(element, entry);
    }

    entry.config = mergedConfig;
    attachAutoSubmit(entry);
    element.dataset.filterRegistered = "true";
    emitFilterEvent(element, "register", {
      values: serializeForm(element),
    });
    return entry;
  }

  function setTagCache(data) {
    caches.tags = Array.isArray(data) ? data : null;
  }

  function getTagCache() {
    return caches.tags;
  }

  function submitRegisteredForm(form, event) {
    const element = resolveElement(form);
    if (!element) {
      return;
    }
    const entry = formRegistry.get(element);
    if (entry) {
      performSubmit(entry, event || null);
    } else {
      requestFormSubmit(element);
    }
  }

  window.FilterUtils = {
    initTomSelect,
    destroyTomSelect,
    clearForm,
    registerFilterForm,
    submitForm: submitRegisteredForm,
    setTagCache,
    getTagCache,
    formRegistry,
    serializeForm,
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
    document.querySelectorAll("form.filter-form").forEach((form) => {
      if (form.dataset.filterAuto === "false") {
        return;
      }
      registerFilterForm(form);
    });
  });
})(window, document);
