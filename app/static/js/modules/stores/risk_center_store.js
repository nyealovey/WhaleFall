(function (global) {
  "use strict";

  function ensureService(service) {
    if (!service || typeof service.fetchSummary !== "function" || typeof service.fetchCards !== "function") {
      throw new Error("createRiskCenterStore: service 未实现");
    }
    return service;
  }

  function ensureEmitter(emitter) {
    if (emitter) {
      return emitter;
    }
    if (!global.mitt) {
      throw new Error("createRiskCenterStore: mitt 未初始化");
    }
    return global.mitt();
  }

  function cloneState(state) {
    return {
      summary: state.summary,
      cards: state.cards,
      loading: state.loading,
      lastError: state.lastError,
    };
  }

  function createRiskCenterStore(options) {
    const service = ensureService(options?.service);
    const emitter = ensureEmitter(options?.emitter);
    const state = {
      summary: null,
      cards: null,
      loading: false,
      lastError: null,
    };

    function emit(eventName, payload) {
      emitter.emit(eventName, payload || { state: cloneState(state) });
    }

    function setLoading(loading) {
      state.loading = Boolean(loading);
      emit("risk-center:loading", { loading: state.loading, state: cloneState(state) });
    }

    function unwrap(payload) {
      return payload?.data ?? payload ?? {};
    }

    return {
      getState() {
        return cloneState(state);
      },
      subscribe(eventName, handler) {
        emitter.on(eventName, handler);
      },
      actions: {
        refresh(params) {
          setLoading(true);
          return Promise.all([service.fetchSummary(), service.fetchCards(params)])
            .then(([summaryPayload, cardsPayload]) => {
              state.summary = unwrap(summaryPayload);
              state.cards = unwrap(cardsPayload);
              state.lastError = null;
              emit("risk-center:updated", { summary: state.summary, cards: state.cards, state: cloneState(state) });
              return { summary: state.summary, cards: state.cards };
            })
            .catch((error) => {
              state.lastError = error;
              emit("risk-center:error", { error, state: cloneState(state) });
              throw error;
            })
            .finally(() => setLoading(false));
        },
      },
    };
  }

  global.createRiskCenterStore = createRiskCenterStore;
})(window);
