// 登录页面入口脚本：挂载 modules/views/auth/login.js 暴露的 LoginPage
(function (global) {
  "use strict";

  document.addEventListener("DOMContentLoaded", function () {
    if (!global.LoginPage || typeof global.LoginPage.mount !== "function") {
      console.error("LoginPage 未注册，无法初始化登录页面");
      return;
    }
    global.LoginPage.mount();
  });
})(window);
