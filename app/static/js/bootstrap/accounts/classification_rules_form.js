(function (global) {
  "use strict";

  document.addEventListener("DOMContentLoaded", function () {
    if (!global.ClassificationRuleFormPage || typeof global.ClassificationRuleFormPage.mount !== "function") {
      console.error("ClassificationRuleFormPage 未注册，无法初始化规则表单");
      return;
    }
    global.ClassificationRuleFormPage.mount();
  });
})(window);
