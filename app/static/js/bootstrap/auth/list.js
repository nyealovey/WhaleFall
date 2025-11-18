// 登录态用户列表入口：等待 DOM ready 后挂载 AuthListPage（modules/views/auth/list.js）
(function (global) {
  "use strict";

  document.addEventListener("DOMContentLoaded", function () {
    if (!global.AuthListPage || typeof global.AuthListPage.mount !== "function") {
      console.error("AuthListPage 未注册，无法初始化用户列表");
      return;
    }
    global.AuthListPage.mount();
  });
})(window);
