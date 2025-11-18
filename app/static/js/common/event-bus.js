(function (window) {
  "use strict";

  if (!window.mitt) {
    throw new Error("Mitt 未加载，无法初始化 EventBus");
  }

  // 轻量事件总线（mitt）
  const emitter = window.mitt();

  window.EventBus = {
    on: emitter.on,
    off: emitter.off,
    emit: emitter.emit,
  };
})(window);
