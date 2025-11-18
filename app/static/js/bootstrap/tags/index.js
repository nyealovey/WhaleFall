// 标签管理首页入口：触发 modules/views/tags/index.js 渲染全量交互
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
