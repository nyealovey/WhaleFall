// 账户分类入口：挂载 AccountClassificationPage 以驱动分类管理交互
(function (global) {
  "use strict";

  document.addEventListener("DOMContentLoaded", function () {
    if (!global.AccountClassificationPage || typeof global.AccountClassificationPage.mount !== "function") {
      console.error("AccountClassificationPage 未注册，无法初始化账户分类页面");
      return;
    }
    global.AccountClassificationPage.mount();
  });
})(window);
