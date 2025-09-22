/**
 * 鲸落 - 统一Alert工具函数
 * 提供统一的用户提示功能，替代原生alert
 * 与后端structlog系统集成，记录用户交互日志
 */

/**
 * 发送日志到后端
 * @param {string} level - 日志级别
 * @param {string} message - 日志消息
 * @param {object} context - 上下文信息
 */
function sendLogToBackend(level, message, context = {}) {
    // 暂时禁用前端日志发送，避免404错误
    // 前端日志只在控制台显示
    // 生产环境不输出调试日志
    if (level !== 'debug') {
        console.log(`[${level}] ${message}`, context);
    }
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
 * 显示成功提示
 * @param {string} message - 提示消息
 * @param {string} title - 标题（可选）
 * @param {object} context - 上下文信息（可选）
 */
function showSuccessAlert(message, title = '成功', context = {}) {
    // 记录到后端日志
    sendLogToBackend('info', `用户提示: ${message}`, {
        alert_type: 'success',
        title: title,
        ...context
    });

    showAlert(message, 'success', title);
}

/**
 * 显示错误提示
 * @param {string} message - 提示消息
 * @param {string} title - 标题（可选）
 * @param {object} context - 上下文信息（可选）
 */
function showErrorAlert(message, title = '错误', context = {}) {
    // 记录到后端日志
    sendLogToBackend('error', `用户提示: ${message}`, {
        alert_type: 'error',
        title: title,
        ...context
    });

    showAlert(message, 'error', title);
}

/**
 * 显示警告提示
 * @param {string} message - 提示消息
 * @param {string} title - 标题（可选）
 * @param {object} context - 上下文信息（可选）
 */
function showWarningAlert(message, title = '警告', context = {}) {
    // 记录到后端日志
    sendLogToBackend('warning', `用户提示: ${message}`, {
        alert_type: 'warning',
        title: title,
        ...context
    });

    showAlert(message, 'warning', title);
}

/**
 * 显示信息提示
 * @param {string} message - 提示消息
 * @param {string} title - 标题（可选）
 * @param {object} context - 上下文信息（可选）
 */
function showInfoAlert(message, title = '信息', context = {}) {
    // 记录到后端日志
    sendLogToBackend('info', `用户提示: ${message}`, {
        alert_type: 'info',
        title: title,
        ...context
    });

    showAlert(message, 'info', title);
}

/**
 * 显示确认对话框
 * @param {string} message - 提示消息
 * @param {string} title - 标题（可选）
 * @param {function} onConfirm - 确认回调函数
 * @param {function} onCancel - 取消回调函数（可选）
 * @param {object} context - 上下文信息（可选）
 */
function showConfirmAlert(message, title = '确认', onConfirm = null, onCancel = null, context = {}) {
    // 记录到后端日志
    sendLogToBackend('info', `用户确认对话框: ${message}`, {
        alert_type: 'confirm',
        title: title,
        ...context
    });

    if (confirm(`${title}: ${message}`)) {
        // 记录确认操作
        sendLogToBackend('info', `用户确认操作: ${message}`, {
            alert_type: 'confirm',
            action: 'confirmed',
            title: title,
            ...context
        });

        if (onConfirm && typeof onConfirm === 'function') {
            onConfirm();
        }
    } else {
        // 记录取消操作
        sendLogToBackend('info', `用户取消操作: ${message}`, {
            alert_type: 'confirm',
            action: 'cancelled',
            title: title,
            ...context
        });

        if (onCancel && typeof onCancel === 'function') {
            onCancel();
        }
    }
}

/**
 * 统一的Alert显示函数
 * @param {string} message - 提示消息
 * @param {string} type - 类型：success, error, warning, info
 * @param {string} title - 标题
 */
function showAlert(message, type = 'info', title = '提示') {
    // 创建Bootstrap模态框
    const modalId = 'alertModal_' + Date.now();
    const modalHtml = `
        <div class="modal fade" id="${modalId}" tabindex="-1" aria-labelledby="${modalId}Label" aria-hidden="true">
            <div class="modal-dialog modal-dialog-centered">
                <div class="modal-content">
                    <div class="modal-header">
                        <h5 class="modal-title" id="${modalId}Label">
                            <i class="fas fa-${getIconClass(type)} me-2"></i>
                            ${title}
                        </h5>
                        <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                    </div>
                    <div class="modal-body">
                        <p class="mb-0">${message}</p>
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-${getButtonClass(type)}" data-bs-dismiss="modal">确定</button>
                    </div>
                </div>
            </div>
        </div>
    `;

    // 添加到页面
    document.body.insertAdjacentHTML('beforeend', modalHtml);

    // 显示模态框
    const modal = new bootstrap.Modal(document.getElementById(modalId));
    modal.show();

    // 模态框关闭后移除DOM元素
    document.getElementById(modalId).addEventListener('hidden.bs.modal', function() {
        this.remove();
    });
}

/**
 * 根据类型获取图标类名
 * @param {string} type - 类型
 * @returns {string} 图标类名
 */
function getIconClass(type) {
    const iconMap = {
        'success': 'check-circle',
        'error': 'exclamation-triangle',
        'warning': 'exclamation-circle',
        'info': 'info-circle'
    };
    return iconMap[type] || 'info-circle';
}

/**
 * 根据类型获取按钮类名
 * @param {string} type - 类型
 * @returns {string} 按钮类名
 */
function getButtonClass(type) {
    const buttonMap = {
        'success': 'success',
        'error': 'danger',
        'warning': 'warning',
        'info': 'primary'
    };
    return buttonMap[type] || 'primary';
}

/**
 * 显示Toast提示（更轻量的提示方式）
 * @param {string} message - 提示消息
 * @param {string} type - 类型：success, error, warning, info
 */
function showToast(message, type = 'info') {
    const toastId = 'toast_' + Date.now();
    const toastHtml = `
        <div class="toast" id="${toastId}" role="alert" aria-live="assertive" aria-atomic="true">
            <div class="toast-header">
                <i class="fas fa-${getIconClass(type)} me-2"></i>
                <strong class="me-auto">${getTitle(type)}</strong>
                <button type="button" class="btn-close" data-bs-dismiss="toast" aria-label="Close"></button>
            </div>
            <div class="toast-body">
                ${message}
            </div>
        </div>
    `;

    // 添加到页面
    document.body.insertAdjacentHTML('beforeend', toastHtml);

    // 显示Toast
    const toast = new bootstrap.Toast(document.getElementById(toastId));
    toast.show();

    // Toast关闭后移除DOM元素
    document.getElementById(toastId).addEventListener('hidden.bs.toast', function() {
        this.remove();
    });
}

/**
 * 根据类型获取标题
 * @param {string} type - 类型
 * @returns {string} 标题
 */
function getTitle(type) {
    const titleMap = {
        'success': '成功',
        'error': '错误',
        'warning': '警告',
        'info': '信息'
    };
    return titleMap[type] || '提示';
}

// 导出函数到全局作用域
window.showSuccessAlert = showSuccessAlert;
window.showErrorAlert = showErrorAlert;
window.showWarningAlert = showWarningAlert;
window.showInfoAlert = showInfoAlert;
window.showConfirmAlert = showConfirmAlert;
window.showAlert = showAlert;
window.showToast = showToast;
