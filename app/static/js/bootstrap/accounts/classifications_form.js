(function (global) {
  "use strict";

  document.addEventListener("DOMContentLoaded", function () {
    if (!global.AccountClassificationFormPage || typeof global.AccountClassificationFormPage.mount !== "function") {
      console.error("AccountClassificationFormPage 未注册，无法初始化分类表单");
      return;
    }
    global.AccountClassificationFormPage.mount();
  });
})(window);
