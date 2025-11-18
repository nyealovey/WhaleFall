(function (global) {
  "use strict";

  const helpers = global.DOMHelpers;
  if (!helpers) {
    console.error("DOMHelpers 未初始化，无法注册 FilterCard 组件");
    return;
  }

  const { selectOne } = helpers;
  const DEFAULT_AUTO_SUBMIT_SELECTORS =
    "select:not([data-no-auto-submit]), input[type='radio']:not([data-no-auto-submit]), input[type='checkbox']:not([data-no-auto-submit]), input[data-auto-submit]:not([data-no-auto-submit])";
  const LodashUtils = global.LodashUtils;

  /**
   * 使用 lodash 的 debounce，若不可用则退回简单实现。
   */
  function createDebounced(fn, wait) {
    if (!wait) {
      return fn;
    }
    if (LodashUtils?.debounce) {
      return LodashUtils.debounce(fn, wait);
    }
    let timeout = null;
    return function debounced(...args) {
      clearTimeout(timeout);
      timeout = setTimeout(() => fn.apply(this, args), wait);
    };
  }

  /**
   * 将 form 数据序列化为对象。
   */
  function serializeForm(element) {
    if (!element) {
      return {};
    }
    const result = {};
    const formData = new FormData(element);
    formData.forEach((value, key) => {
      const normalized = value instanceof File ? value.name : value;
      if (result[key] === undefined) {
        result[key] = normalized;
      } else if (Array.isArray(result[key])) {
        result[key].push(normalized);
      } else {
        result[key] = [result[key], normalized];
      }
    });
    return result;
  }

  /**
   * 触发表单提交，兼容 requestSubmit。
   */
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

  /**
   * 统一处理事件绑定并记录，用于销毁。
   */
  function addListener(target, eventName, handler, registry) {
    if (!target || typeof target.addEventListener !== "function" || !handler) {
      return;
    }
    target.addEventListener(eventName, handler);
    registry.push({ target, eventName, handler });
  }

  /**
   * 解析 formSelector（字符串或 umbrella 对象）。
   */
  function normalizeForm(formSelector) {
    if (typeof formSelector === "string") {
      return selectOne(formSelector).first();
    }
    if (formSelector && typeof formSelector.first === "function") {
      return formSelector.first();
    }
    return formSelector;
  }

  function createFilterCard({
    formSelector,
    onSubmit,
    onClear,
    onChange,
    autoSubmitOnChange = true,
    autoSubmitSelectors = DEFAULT_AUTO_SUBMIT_SELECTORS,
    autoSubmitDebounce = 0,
    eventBus = global.EventBus,
  } = {}) {
    const form = normalizeForm(formSelector);
    if (!form) {
      console.warn("[FilterCard] 表单不存在:", formSelector);
      return null;
    }

    const normalizedFormId = (form.id || `${formSelector || ""}`).replace(/^#/, "");
    const listeners = [];
    const busHandlers = [];

    function emitEvent(action, payload = {}, { internal = false } = {}) {
      if (!eventBus || typeof eventBus.emit !== "function") {
        return;
      }
      const detail = Object.assign(
        {
          action,
          formId: normalizedFormId || null,
          formName: form.getAttribute("name") || null,
          source: form.dataset.filterName || normalizedFormId || null,
          values: serializeForm(form),
          origin: internal ? "filter-card" : payload.origin,
        },
        payload,
      );
      eventBus.emit(`filters:${action}`, detail);
    }

    function handleSubmit(event) {
      event?.preventDefault?.();
      const values = serializeForm(form);
      if (typeof onSubmit === "function") {
        onSubmit({ form, values, event });
      } else {
        requestFormSubmit(form);
      }
      emitEvent("submit", { trigger: event?.type || "submit", values }, { internal: true });
    }

    function handleClear(event) {
      event?.preventDefault?.();
      form.reset();
      const values = serializeForm(form);
      if (typeof onClear === "function") {
        onClear({ form, values, event });
      } else {
        requestFormSubmit(form);
      }
      emitEvent("clear", { trigger: event?.type || "clear", values }, { internal: true });
    }

    function handleChange(event, control) {
      const values = serializeForm(form);
      if (typeof onChange === "function") {
        onChange({
          form,
          values,
          event,
          target: control || event?.target || null,
        });
      }
      emitEvent(
        "change",
        {
          trigger: event?.type || "change",
          targetName: control?.name || control?.id || null,
          values,
        },
        { internal: true },
      );
    }

    addListener(form, "submit", handleSubmit, listeners);

    const submitButton = form.querySelector("[data-filter-submit]");
    addListener(
      submitButton,
      "click",
      (event) => handleSubmit(event),
      listeners,
    );

    const clearButton = form.querySelector("[data-filter-clear]");
    addListener(
      clearButton,
      "click",
      (event) => handleClear(event),
      listeners,
    );

    if (autoSubmitOnChange) {
      const controls = autoSubmitSelectors
        ? Array.from(form.querySelectorAll(autoSubmitSelectors))
        : [];
      controls.forEach((control) => {
        if (
          !control ||
          control.dataset.noAutoSubmit !== undefined ||
          typeof control.addEventListener !== "function"
        ) {
          return;
        }
        const eventName =
          control.dataset.autoSubmitEvent ||
          (control.tagName === "INPUT" && control.type === "text"
            ? "input"
            : "change");
        const handler = createDebounced(
          (event) => handleChange(event, control),
          autoSubmitDebounce,
        );
        addListener(control, eventName, handler, listeners);
      });
    }

    if (eventBus && typeof eventBus.on === "function") {
      ["change", "submit", "clear"].forEach((action) => {
        const handler = (detail) => {
          if (!detail) {
            return;
          }
          const incoming = (detail.formId || "").replace(/^#/, "");
          if (incoming && incoming !== normalizedFormId) {
            return;
          }
          if (detail.origin === "filter-card") {
            // 避免自身重复消费
            return;
          }
          const payload = {
            form,
            values: detail.values || serializeForm(form),
            detail,
          };
          switch (action) {
            case "change":
              onChange?.(payload);
              break;
            case "clear":
              onClear?.(payload);
              break;
            case "submit":
              onSubmit?.(payload);
              break;
            default:
              break;
          }
        };
        eventBus.on(`filters:${action}`, handler);
        busHandlers.push({ action, handler });
      });
    }

    emitEvent("register", { origin: "filter-card" }, { internal: true });

    return {
      form,
      formId: normalizedFormId,
      serialize: () => serializeForm(form),
      emit: (action, payload = {}) => emitEvent(action, payload, { internal: false }),
      destroy: () => {
        listeners.forEach(({ target, eventName, handler }) => {
          target.removeEventListener(eventName, handler);
        });
        listeners.length = 0;
        if (eventBus && typeof eventBus.off === "function") {
          busHandlers.forEach(({ action, handler }) => {
            eventBus.off(`filters:${action}`, handler);
          });
        }
      },
    };
  }

  global.UI = global.UI || {};
  global.UI.createFilterCard = createFilterCard;
  global.UI.serializeForm = serializeForm;
})(window);
