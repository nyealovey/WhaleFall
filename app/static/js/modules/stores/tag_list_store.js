(function (window) {
  "use strict";

  function ensureEmitter(emitter) {
    if (emitter) {
      return emitter;
    }
    if (!window.mitt) {
      throw new Error("createTagListStore: 需要 mitt 实例");
    }
    return window.mitt();
  }

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

  function cloneState(state) {
    return {
      allIds: Array.from(state.allIds),
      selection: Array.from(state.selection),
      lastError: state.lastError,
    };
  }

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
