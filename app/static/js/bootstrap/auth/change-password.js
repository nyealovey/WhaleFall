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
