// 账户列表入口：等待 DOM ready 后委托 AccountsListPage.mount 管理筛选/分页
(function (global) {
  "use strict";

  document.addEventListener("DOMContentLoaded", function () {
    if (!global.AccountsListPage || typeof global.AccountsListPage.mount !== "function") {
      console.error("AccountsListPage 未注册，无法初始化账户列表");
      return;
    }
    global.AccountsListPage.mount();
  });
})(window);
