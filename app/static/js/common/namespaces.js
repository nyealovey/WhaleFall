(function (global) {
  "use strict";

  // Centralize namespace initialization so feature modules don't need
  // to silently create globals via `global.X = global.X || {}`.
  if (!global.UI || typeof global.UI !== "object") {
    global.UI = {};
  }
  if (!global.Views || typeof global.Views !== "object") {
    global.Views = {};
  }
  if (!global.Views.GridPlugins || typeof global.Views.GridPlugins !== "object") {
    global.Views.GridPlugins = {};
  }
  if (!global.Views.GridPage || typeof global.Views.GridPage !== "object") {
    global.Views.GridPage = {};
  }
})(window);

