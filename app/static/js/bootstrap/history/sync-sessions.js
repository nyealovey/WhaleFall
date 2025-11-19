// 同步会话历史入口：挂载 modules/views/history/sessions/sync-sessions.js 输出的页面对象
(function (global) {
  "use strict";

  document.addEventListener("DOMContentLoaded", function () {
    if (!global.SyncSessionsPage || typeof global.SyncSessionsPage.mount !== "function") {
      console.error("SyncSessionsPage 未注册，无法初始化会话页面");
      return;
    }
    global.SyncSessionsPage.mount();
  });
})(window);
