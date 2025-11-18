// 修改密码入口：监听 DOM ready 后启动 ChangePasswordPage（modules/views/auth/change_password.js）
(function (global) {
  "use strict";

  document.addEventListener("DOMContentLoaded", function () {
    if (!global.ChangePasswordPage || typeof global.ChangePasswordPage.mount !== "function") {
      console.error("ChangePasswordPage 未注册，无法初始化修改密码页面");
      return;
    }
    global.ChangePasswordPage.mount();
  });
})(window);
