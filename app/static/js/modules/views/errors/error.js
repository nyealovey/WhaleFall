(function (global) {
  "use strict";

  function mountErrorPage(global) {
    const document = global.document;
    if (!document) {
      return;
    }

    const backButton = document.querySelector('[data-action="history-back"]');
    if (!backButton) {
      return;
    }

    backButton.addEventListener("click", (event) => {
      event.preventDefault();
      global.history.back();
    });
  }

  global.ErrorPage = {
    mount: function () {
      mountErrorPage(window);
    },
  };
})(window);
