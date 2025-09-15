/**
 * 泰摸鱼吧 - 统一Console日志工具函数
 * 提供统一的控制台日志功能，与后端structlog系统集成
 */

/**
 * 发送日志到后端（已禁用，避免404错误）
 * @param {string} level - 日志级别
 * @param {string} message - 日志消息
 * @param {object} context - 上下文信息
 */
function sendLogToBackend(level, message, context = {}) {
    // 暂时禁用前端日志发送，避免404错误
    // 前端日志只在控制台显示
    console.log(`[${level}] ${message}`, context);
}

/**
 * 获取CSRF令牌
 * @returns {string} CSRF令牌
 */
function getCSRFToken() {
    const token = document.querySelector('meta[name="csrf-token"]');
    return token ? token.getAttribute('content') : '';
}

/**
 * 统一的Console日志函数
 * @param {string} level - 日志级别
 * @param {string} message - 日志消息
 * @param {object} context - 上下文信息
 * @param {boolean} sendToBackend - 是否发送到后端
 */
function logToConsole(level, message, context = {}, sendToBackend = true) {
    // 控制台输出
    const timestamp = new Date().toISOString();
    const contextStr = Object.keys(context).length > 0 ? ` | Context: ${JSON.stringify(context)}` : '';
    const logMessage = `[${timestamp}] [${level.toUpperCase()}] ${message}${contextStr}`;

    switch (level) {
        case 'error':
            console.error(logMessage);
            break;
        case 'warn':
        case 'warning':
            console.warn(logMessage);
            break;
        case 'info':
            console.info(logMessage);
            break;
        case 'debug':
            console.debug(logMessage);
            break;
        default:
            console.log(logMessage);
    }

    // 发送到后端
    if (sendToBackend) {
        sendLogToBackend(level, message, context);
    }
}

/**
 * 错误日志
 * @param {string} message - 日志消息
 * @param {object} context - 上下文信息
 * @param {boolean} sendToBackend - 是否发送到后端
 */
function logError(message, context = {}, sendToBackend = true) {
    logToConsole('error', message, context, sendToBackend);
}

/**
 * 警告日志
 * @param {string} message - 日志消息
 * @param {object} context - 上下文信息
 * @param {boolean} sendToBackend - 是否发送到后端
 */
function logWarn(message, context = {}, sendToBackend = true) {
    logToConsole('warn', message, context, sendToBackend);
}

/**
 * 信息日志
 * @param {string} message - 日志消息
 * @param {object} context - 上下文信息
 * @param {boolean} sendToBackend - 是否发送到后端
 */
function logInfo(message, context = {}, sendToBackend = true) {
    logToConsole('info', message, context, sendToBackend);
}

/**
 * 调试日志
 * @param {string} message - 日志消息
 * @param {object} context - 上下文信息
 * @param {boolean} sendToBackend - 是否发送到后端
 */
function logDebug(message, context = {}, sendToBackend = true) {
    logToConsole('debug', message, context, sendToBackend);
}

/**
 * 通用日志
 * @param {string} message - 日志消息
 * @param {object} context - 上下文信息
 * @param {boolean} sendToBackend - 是否发送到后端
 */
function log(message, context = {}, sendToBackend = true) {
    logToConsole('info', message, context, sendToBackend);
}

/**
 * 性能日志
 * @param {string} operation - 操作名称
 * @param {number} startTime - 开始时间
 * @param {object} context - 上下文信息
 */
function logPerformance(operation, startTime, context = {}) {
    const duration = Date.now() - startTime;
    logInfo(`性能监控: ${operation}`, {
        ...context,
        operation: operation,
        duration_ms: duration,
        performance: true
    });
}

/**
 * 用户操作日志
 * @param {string} action - 操作名称
 * @param {object} context - 上下文信息
 */
function logUserAction(action, context = {}) {
    logInfo(`用户操作: ${action}`, {
        ...context,
        action: action,
        user_action: true
    });
}

/**
 * API调用日志
 * @param {string} method - HTTP方法
 * @param {string} url - 请求URL
 * @param {object} context - 上下文信息
 */
function logApiCall(method, url, context = {}) {
    logInfo(`API调用: ${method} ${url}`, {
        ...context,
        method: method,
        url: url,
        api_call: true
    });
}

/**
 * 错误处理日志
 * @param {Error} error - 错误对象
 * @param {string} context - 上下文描述
 * @param {object} additionalContext - 额外上下文
 */
function logErrorWithContext(error, context = '', additionalContext = {}) {
    logError(`错误处理: ${context}`, {
        ...additionalContext,
        error_message: error.message,
        error_stack: error.stack,
        error_name: error.name,
        context: context
    });
}

// 导出函数到全局作用域
window.logError = logError;
window.logWarn = logWarn;
window.logInfo = logInfo;
window.logDebug = logDebug;
window.log = log;
window.logPerformance = logPerformance;
window.logUserAction = logUserAction;
window.logApiCall = logApiCall;
window.logErrorWithContext = logErrorWithContext;
