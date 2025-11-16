(function (global) {
  "use strict";

  document.addEventListener("DOMContentLoaded", function () {
    if (!global.InstanceDetailPage || typeof global.InstanceDetailPage.mount !== "function") {
      console.error("InstanceDetailPage 未注册，无法初始化实例详情");
      return;
    }
    global.InstanceDetailPage.mount();
  });
})(window);
