// 操作日志入口：初始化 modules/views/history/logs/logs.js 提供的 LogsPage
(function (global) {
  "use strict";

  document.addEventListener("DOMContentLoaded", function () {
    if (!global.LogsPage || typeof global.LogsPage.mount !== "function") {
      console.error("LogsPage 未注册，无法初始化日志页面");
      return;
    }
    global.LogsPage.mount();
  });
})(window);
