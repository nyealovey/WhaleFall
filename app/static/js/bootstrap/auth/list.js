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
