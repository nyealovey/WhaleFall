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
