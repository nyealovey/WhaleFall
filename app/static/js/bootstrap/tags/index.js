(function (global) {
  "use strict";

  document.addEventListener("DOMContentLoaded", function () {
    if (!global.TagsIndexPage || typeof global.TagsIndexPage.mount !== "function") {
      console.error("TagsIndexPage 未注册，无法初始化标签管理入口");
      return;
    }
    global.TagsIndexPage.mount();
  });
})(window);
