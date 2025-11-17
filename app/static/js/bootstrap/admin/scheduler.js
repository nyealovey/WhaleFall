(function (global) {
  "use strict";

  document.addEventListener("DOMContentLoaded", function () {
    if (!global.SchedulerPage || typeof global.SchedulerPage.mount !== "function") {
      console.error("SchedulerPage 未注册，无法初始化调度页面");
      return;
    }
    global.SchedulerPage.mount();
  });
})(window);
