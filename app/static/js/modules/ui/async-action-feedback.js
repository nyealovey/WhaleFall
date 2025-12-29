(function (global) {
  "use strict";

  const DEFAULT_RESULT_URL = "/history/sessions";
  const DEFAULT_RESULT_TEXT = "前往会话中心查看结果";
  const DEFAULT_STARTED_MESSAGE = "任务已启动";
  const DEFAULT_FAILED_MESSAGE = "操作失败";
  const DEFAULT_UNKNOWN_MESSAGE = "操作未完成，请稍后在会话中心确认";

  const unknownReported = new Set();

  function isNonEmptyString(value) {
    return typeof value === "string" && value.trim().length > 0;
  }

  function normalizeSuggestions(value) {
    if (!Array.isArray(value)) {
      return [];
    }
    return value
      .map((item) => (isNonEmptyString(item) ? item.trim() : ""))
      .filter((item) => item.length > 0);
  }

  function reportUnknownOutcome(action, response) {
    const key = isNonEmptyString(action) ? action.trim() : "unknown";
    if (unknownReported.has(key)) {
      return;
    }
    unknownReported.add(key);

    global.EventBus?.emit?.("async-action:unknown-response", {
      action: key,
      response,
      timestamp: Date.now(),
    });
    console.warn("[async-action-feedback] Unknown response schema", { action: key, response });
  }

  function isEnvelopeLike(response) {
    if (!response || typeof response !== "object") {
      return false;
    }
    return typeof response.success === "boolean" || typeof response.error === "boolean" || isNonEmptyString(response.message);
  }

  /**
   * 规范化 sync/batch 异步动作的返回值，避免各调用点自行写兜底链。
   *
   * @param {*} response 请求返回值（通常为 JSON）。
   * @param {Object} [options={}] 配置。
   * @param {string} [options.action] 动作标识（用于 unknown 观测）。
   * @param {string} [options.startedMessage] started 兜底文案。
   * @param {string} [options.failedMessage] failed 兜底文案。
   * @param {string} [options.unknownMessage] unknown 兜底文案。
   * @param {string} [options.resultUrl] 结果入口链接。
   * @param {string} [options.resultText] 结果入口文案。
   * @returns {{status: string, tone: string, message: string, resultUrl: string, resultText: string, meta: Object, recoverable: (boolean|null), suggestions: Array<string>}}
   */
  function resolveAsyncActionOutcome(response, options = {}) {
    const resultUrl = isNonEmptyString(options?.resultUrl) ? options.resultUrl.trim() : DEFAULT_RESULT_URL;
    const resultText = isNonEmptyString(options?.resultText) ? options.resultText.trim() : DEFAULT_RESULT_TEXT;
    const startedMessage = isNonEmptyString(options?.startedMessage) ? options.startedMessage.trim() : DEFAULT_STARTED_MESSAGE;
    const failedMessage = isNonEmptyString(options?.failedMessage) ? options.failedMessage.trim() : DEFAULT_FAILED_MESSAGE;
    const unknownMessage = isNonEmptyString(options?.unknownMessage) ? options.unknownMessage.trim() : DEFAULT_UNKNOWN_MESSAGE;

    const meta = {
      session_id: response?.data?.session_id ?? null,
    };

    const suggestions = normalizeSuggestions(response?.suggestions);
    const recoverable = typeof response?.recoverable === "boolean" ? response.recoverable : null;

    if (!isEnvelopeLike(response)) {
      reportUnknownOutcome(options?.action, response);
      return {
        status: "unknown",
        tone: "warning",
        message: unknownMessage,
        resultUrl,
        resultText,
        meta,
        recoverable,
        suggestions,
      };
    }

    const hasErrorFlag = response?.error === true;
    const hasSuccessFlag = response?.success === true;
    const hasFailureFlag = response?.success === false;

    if (hasErrorFlag || hasFailureFlag) {
      return {
        status: "failed",
        tone: "error",
        message: isNonEmptyString(response?.message) ? response.message.trim() : failedMessage,
        resultUrl,
        resultText,
        meta,
        recoverable,
        suggestions,
      };
    }

    if (hasSuccessFlag) {
      return {
        status: "started",
        tone: "success",
        message: isNonEmptyString(response?.message) ? response.message.trim() : startedMessage,
        resultUrl,
        resultText,
        meta,
        recoverable,
        suggestions,
      };
    }

    reportUnknownOutcome(options?.action, response);
    return {
      status: "unknown",
      tone: "warning",
      message: unknownMessage,
      resultUrl,
      resultText,
      meta,
      recoverable,
      suggestions,
    };
  }

  global.UI = global.UI || {};
  global.UI.resolveAsyncActionOutcome = resolveAsyncActionOutcome;
})(window);

