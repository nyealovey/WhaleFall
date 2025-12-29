(function (global) {
  "use strict";

  function createPlugin(options = {}) {
    const selector = options.selector || "[data-action='export']";
    const navigate = options.navigate || "location";

    function resolveEndpoint(ctx) {
      if (typeof options.endpoint === "function") {
        return options.endpoint(ctx);
      }
      if (typeof options.endpoint === "string") {
        return options.endpoint;
      }
      return "";
    }

    function openUrl(url) {
      if (!url) {
        return;
      }
      if (navigate === "open") {
        global.open(url, "_blank", "noreferrer");
      } else {
        global.location.href = url;
      }
    }

    return {
      name: "exportButton",
      init: (ctx) => {
        const button = ctx.queryOne(selector);
        if (!button) {
          return null;
        }
        const handler = (event) => {
          event.preventDefault();
          const endpoint = resolveEndpoint(ctx);
          if (!endpoint) {
            return;
          }
          const filters = ctx.getFilters();
          const query = ctx.buildSearchParams(filters).toString();
          const url = query ? `${endpoint}?${query}` : endpoint;
          openUrl(url);
        };
        button.addEventListener("click", handler);
        return {
          destroy: () => button.removeEventListener("click", handler),
        };
      },
    };
  }

  global.Views = global.Views || {};
  global.Views.GridPlugins = global.Views.GridPlugins || {};
  global.Views.GridPlugins.exportButton = createPlugin;
})(window);

