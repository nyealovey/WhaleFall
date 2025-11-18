// 标签批量分配入口：挂载 modules/views/tags/batch_assign.js 暴露的页面对象
(function (global) {
  "use strict";

  document.addEventListener("DOMContentLoaded", function () {
    if (!global.TagsBatchAssignPage || typeof global.TagsBatchAssignPage.mount !== "function") {
      console.error("TagsBatchAssignPage 未注册，无法初始化批量分配入口");
      return;
    }
    global.TagsBatchAssignPage.mount();
  });
})(window);
