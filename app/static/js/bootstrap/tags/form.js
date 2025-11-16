(function (global) {
  "use strict";

  document.addEventListener("DOMContentLoaded", function () {
    if (!global.TagFormPage || typeof global.TagFormPage.mount !== "function") {
      console.error("TagFormPage 未注册，无法初始化标签表单");
      return;
    }
    global.TagFormPage.mount();
  });
})(window);
