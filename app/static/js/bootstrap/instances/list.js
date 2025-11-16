(function (global) {
  "use strict";

  document.addEventListener("DOMContentLoaded", function () {
    if (!global.InstancesListPage || typeof global.InstancesListPage.mount !== "function") {
      console.error("InstancesListPage 未注册，无法初始化实例列表");
      return;
    }
    global.InstancesListPage.mount();
  });
})(window);
