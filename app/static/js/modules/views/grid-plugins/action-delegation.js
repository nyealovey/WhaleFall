(function (global) {
  "use strict";

  const UNSAFE_KEYS = ["__proto__", "prototype", "constructor"];
  const isSafeKey = (key) => typeof key === "string" && !UNSAFE_KEYS.includes(key);

  function createPlugin(options = {}) {
    const actions = options.actions && typeof options.actions === "object" ? options.actions : {};
    const containerSelector = options.containerSelector || null;

    return {
      name: "actionDelegation",
      init: (ctx) => {
        const container = containerSelector ? ctx.queryOne(containerSelector) : ctx.gridEl;
        if (!container) {
          console.warn("GridPlugins.actionDelegation: container 未找到");
          return null;
        }
        const handler = (event) => {
          const actionEl = event.target?.closest?.("[data-action]");
          if (!actionEl || !container.contains(actionEl)) {
            return;
          }
          const action = actionEl.getAttribute("data-action");
          if (!isSafeKey(action)) {
            return;
          }
          if (!Object.prototype.hasOwnProperty.call(actions, action)) {
            return;
          }
          // eslint-disable-next-line security/detect-object-injection
          const fn = actions[action];
          if (typeof fn !== "function") {
            return;
          }
          fn({ ctx, event, el: actionEl });
        };
        container.addEventListener("click", handler);
        return {
          destroy: () => container.removeEventListener("click", handler),
        };
      },
    };
  }

  global.Views.GridPlugins.actionDelegation = createPlugin;
})(window);
