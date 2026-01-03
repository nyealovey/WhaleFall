(function (global) {
  "use strict";

  function createPlugin(options = {}) {
    return {
      name: "filterCard",
      init: (ctx) => {
        const factory = ctx.UI?.createFilterCard;
        if (typeof factory !== "function") {
          console.error("GridPlugins.filterCard: UI.createFilterCard 未加载");
          return null;
        }
        if (!ctx.filterFormEl) {
          console.warn("GridPlugins.filterCard: filterForm 未配置，跳过");
          return null;
        }

        const filterCard = factory({
          formSelector: ctx.filterFormEl,
          autoSubmitOnChange: options.autoSubmitOnChange !== false,
          autoSubmitSelectors: options.autoSubmitSelectors,
          autoSubmitDebounce: options.autoSubmitDebounce,
          onSubmit: ({ values }) => ctx.applyFiltersFromValues(values, { source: "filter-submit" }),
          onChange: ({ values }) => ctx.applyFiltersFromValues(values, { source: "filter-change" }),
          onClear: (payload) => {
            if (typeof options.onClear === "function") {
              options.onClear(ctx, payload);
              return;
            }
            ctx.applyFiltersFromValues(payload?.values || {}, { source: "filter-clear" });
          },
        });

        ctx.filterCard = filterCard;
        return {
          destroy: () => {
            filterCard?.destroy?.();
            if (ctx.filterCard === filterCard) {
              ctx.filterCard = null;
            }
          },
        };
      },
    };
  }

  global.Views = global.Views || {};
  global.Views.GridPlugins = global.Views.GridPlugins || {};
  global.Views.GridPlugins.filterCard = createPlugin;
})(window);
