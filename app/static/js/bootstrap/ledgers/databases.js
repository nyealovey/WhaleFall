(function (global) {
  "use strict";

  if (!global.DatabaseLedgerPage || typeof global.DatabaseLedgerPage.mount !== "function") {
    console.error("DatabaseLedgerPage 未注册，无法初始化数据库台账页面");
    return;
  }

  global.addEventListener("DOMContentLoaded", function () {
    global.DatabaseLedgerPage.mount(global);
  });
})(window);
