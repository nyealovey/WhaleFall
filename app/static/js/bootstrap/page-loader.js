(function (global) {
  "use strict";

  document.addEventListener("DOMContentLoaded", function () {
    const unsafeKeys = new Set(["__proto__", "prototype", "constructor"]);
    const isSafeKey = (key) => typeof key === "string" && key && !unsafeKeys.has(key);
    const hasOwn = (obj, key) => Object.prototype.hasOwnProperty.call(obj, key);

    const pageId = global.document?.body?.dataset?.page;
    if (!pageId) {
      return;
    }
    if (!isSafeKey(pageId)) {
      console.error("[page-loader] pageId 非法，已拒绝加载");
      return;
    }

    const rawMountMethod = global.document.body.dataset.pageMount || "mount";
    const mountMethod = isSafeKey(rawMountMethod) ? rawMountMethod : "mount";

    const target = hasOwn(global, pageId) ? Reflect.get(global, pageId) : null;
    if (!target) {
      console.error(`[page-loader] 找不到页面入口 ${pageId}`);
      return;
    }
    const mountFn = typeof target === "function"
      ? target
      : (hasOwn(target, mountMethod) ? Reflect.get(target, mountMethod) : null);
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
