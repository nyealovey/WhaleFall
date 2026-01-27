(function (global) {
  "use strict";

  function createPlugin(options = {}) {
    const resolveBasePath = () => {
      if (typeof options.basePath === "function") {
        return options.basePath();
      }
      if (typeof options.basePath === "string" && options.basePath.trim()) {
        return options.basePath.trim();
      }
      return global.location?.pathname || "/";
    };

    return {
      name: "urlSync",
      onFiltersChanged: (ctx, { filters }) => {
        if (!global.history?.replaceState) {
          return;
        }
        const params = ctx.buildSearchParams(filters || {});
        const query = params.toString();
        const basePath = resolveBasePath();
        const nextUrl = query ? `${basePath}?${query}` : basePath;
        global.history.replaceState(null, "", nextUrl);
      },
    };
  }

  global.Views.GridPlugins.urlSync = createPlugin;
})(window);
