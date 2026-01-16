(function (global) {
  "use strict";

  function mountAboutPage() {
    // noop: About 页面暂不需要 page-level JS，但仍保留稳定入口以满足 page-loader 契约。
  }

  global.AboutPage = {
    mount: function () {
      mountAboutPage(window);
    },
  };
})(window);
