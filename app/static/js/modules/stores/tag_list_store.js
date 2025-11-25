(function (window) {
  "use strict";

  /**
   * 统一获取 mitt 实例。
   *
   * @param {Object} [emitter] - 可选的 mitt 实例
   * @return {Object} mitt 事件总线实例
   * @throws {Error} 当 emitter 为空且 window.mitt 不存在时抛出
   */
  function ensureEmitter(emitter) {
    if (emitter) {
      return emitter;
    }
    if (!window.mitt) {
      throw new Error("createTagListStore: 需要 mitt 实例");
    }
    return window.mitt();
  }

  /**
   * 将 id 列表转换成数值数组。
   *
   * @param {Array} ids - ID 数组
   * @return {Array} 规范化后的数字 ID 数组
   */
  function normalizeIds(ids) {
    if (!Array.isArray(ids)) {
      return [];
    }
    return ids
      .map(function (value) {
        const numeric = Number(value);
        return Number.isFinite(numeric) ? numeric : null;
      })
      .filter(function (value) {
        return value !== null;
      });
  }

  /**
   * 拷贝 state，方便事件 payload 传递。
   *
   * @param {Object} state - 状态对象
   * @return {Object} 状态对象的拷贝
   */
  function cloneState(state) {
    return {
      allIds: Array.from(state.allIds),
      selection: Array.from(state.selection),
      lastError: state.lastError,
    };
  }

  /**
   * 创建标签列表状态管理 Store。
   *
   * 提供标签选择管理功能，支持添加、移除、切换、全选等操作。
   * 适用于需要管理标签选择状态的场景。
   *
   * @param {Object} options - 配置选项
   * @param {Object} [options.emitter] - 可选的 mitt 事件总线实例
   * @param {Array} [options.initialTagIds] - 初始可用标签 ID 列表
   * @param {Array} [options.initialSelection] - 初始选中的标签 ID 列表
   * @return {Object} Store API 对象
   *
   * @example
   * const store = createTagListStore({
   *   initialTagIds: [1, 2, 3],
   *   initialSelection: [1]
   * });
   * store.actions.addTag(2);
   * console.log(store.getState());
   */
  function createTagListStore(options) {
    const opts = options || {};
    const emitter = ensureEmitter(opts.emitter);

    const state = {
      allIds: new Set(normalizeIds(opts.initialTagIds || [])),
      selection: new Set(normalizeIds(opts.initialSelection || [])),
      lastError: null,
    };

    function emit(eventName, payload) {
      emitter.emit(
        eventName,
        payload ?? {
          state: cloneState(state),
        },
      );
    }

    function emitSelection(reason) {
      emit("tagList:selectionChanged", {
        reason: reason || "update",
        selection: Array.from(state.selection),
        state: cloneState(state),
      });
    }

    const api = {
      getState: function () {
        return cloneState(state);
      },
      subscribe: function (eventName, handler) {
        emitter.on(eventName, handler);
      },
      unsubscribe: function (eventName, handler) {
        emitter.off(eventName, handler);
      },
      actions: {
        setAvailableTagIds: function (ids) {
          state.allIds = new Set(normalizeIds(ids));
          emit("tagList:updated", cloneState(state));
        },
        addTag: function (tagId) {
          const numericId = Number(tagId);
          if (!Number.isFinite(numericId)) {
            return;
          }
          if (state.selection.has(numericId)) {
            return;
          }
          state.selection.add(numericId);
          emitSelection("add");
        },
        removeTag: function (tagId) {
          const numericId = Number(tagId);
          if (!state.selection.has(numericId)) {
            return;
          }
          state.selection.delete(numericId);
          emitSelection("remove");
        },
        toggleTag: function (tagId) {
          const numericId = Number(tagId);
          if (!Number.isFinite(numericId)) {
            return;
          }
          if (state.selection.has(numericId)) {
            state.selection.delete(numericId);
            emitSelection("toggle");
            return;
          }
          state.selection.add(numericId);
          emitSelection("toggle");
        },
        clearSelection: function () {
          if (!state.selection.size) {
            return;
          }
          state.selection.clear();
          emitSelection("clear");
        },
        selectAll: function () {
          if (!state.allIds.size) {
            return;
          }
          state.selection = new Set(state.allIds);
          emitSelection("selectAll");
        },
        replaceSelection: function (ids) {
          state.selection = new Set(normalizeIds(ids));
          emitSelection("replace");
        },
      },
      destroy: function () {
        if (emitter.all && typeof emitter.all.clear === "function") {
          emitter.all.clear();
        }
        state.selection.clear();
        state.allIds.clear();
      },
    };

    return api;
  }

  window.createTagListStore = createTagListStore;
})(window);
