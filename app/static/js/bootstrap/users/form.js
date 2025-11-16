(function (global) {
  "use strict";

  document.addEventListener("DOMContentLoaded", function () {
    if (!global.UserFormPage || typeof global.UserFormPage.mount !== "function") {
      console.error("UserFormPage 未注册，无法初始化用户表单");
      return;
    }
    global.UserFormPage.mount();
  });
})(window);
