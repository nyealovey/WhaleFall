(function (global) {
  "use strict";

  document.addEventListener("DOMContentLoaded", function () {
    if (!global.CredentialFormPage || typeof global.CredentialFormPage.mount !== "function") {
      console.error("CredentialFormPage 未注册，无法初始化凭据表单");
      return;
    }
    global.CredentialFormPage.mount();
  });
})(window);
