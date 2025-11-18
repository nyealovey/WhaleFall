// 凭据列表入口：挂载 CredentialsListPage，驱动凭据增删改查交互
(function (global) {
  "use strict";

  document.addEventListener("DOMContentLoaded", function () {
    if (!global.CredentialsListPage || typeof global.CredentialsListPage.mount !== "function") {
      console.error("CredentialsListPage 未注册，无法初始化凭据列表");
      return;
    }
    global.CredentialsListPage.mount();
  });
})(window);
