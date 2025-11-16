(function (global) {
  "use strict";

  document.addEventListener("DOMContentLoaded", function () {
    if (!global.InstanceFormPage || typeof global.InstanceFormPage.mount !== "function") {
      console.error("InstanceFormPage 未注册，无法初始化实例表单");
      return;
    }
    global.InstanceFormPage.mount();
  });
})(window);
