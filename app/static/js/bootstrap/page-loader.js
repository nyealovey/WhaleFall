(function (global) {
  "use strict";

  document.addEventListener("DOMContentLoaded", function () {
    const pageId = global.document?.body?.dataset?.page;
    if (!pageId) {
      return;
    }
    const mountMethod = global.document.body.dataset.pageMount || "mount";
    const target = global[pageId];
    if (!target) {
      console.error(`[page-loader] 找不到页面入口 ${pageId}`);
      return;
    }
    const mountFn = typeof target === "function" ? target : target[mountMethod];
    if (typeof mountFn !== "function") {
      console.error(`[page-loader] ${pageId} 缺少可调用的 ${mountMethod}`);
      return;
    }
    try {
      mountFn.call(target, global);
    } catch (error) {
      console.error(`[page-loader] 初始化 ${pageId} 失败`, error);
    }
  });
})(window);
