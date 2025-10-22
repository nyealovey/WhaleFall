/**
 * notify.js
 * 统一的前端提示封装，默认优先使用 toastr，未加载时回退到 Bootstrap Alert。
 */
(function (global) {
    const ALERT_CONTAINER_SELECTOR = ".container, .container-fluid, body";
    const TOASTR_TYPES = new Set(["success", "info", "warning", "error"]);
    const FALLBACK_TYPE_MAP = {
        danger: "error",
        success: "success",
        warning: "warning",
        info: "info",
        error: "error",
    };

    function normalizeType(type) {
        if (!type) return "info";
        const lower = String(type).toLowerCase();
        if (TOASTR_TYPES.has(lower)) {
            return lower;
        }
        return FALLBACK_TYPE_MAP[lower] || "info";
    }

    function resolveContainer(selector) {
        if (selector && typeof selector === "string") {
            const candidate = document.querySelector(selector);
            if (candidate) {
                return candidate;
            }
        }

        const roots = document.querySelectorAll(ALERT_CONTAINER_SELECTOR);
        return roots.length ? roots[0] : document.body;
    }

    function createBootstrapAlert(type, message, options = {}) {
        const container = resolveContainer(options.container);
        if (!container) {
            return;
        }

        const alertDiv = document.createElement("div");
        alertDiv.className = `alert alert-${type} alert-dismissible fade show`;
        alertDiv.role = "alert";
        alertDiv.innerHTML = `
            <span class="me-2">${message}</span>
            <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
        `;

        if (container.firstChild) {
            container.insertBefore(alertDiv, container.firstChild);
        } else {
            container.appendChild(alertDiv);
        }

        const duration = Math.max(2000, options.duration || 5000);
        setTimeout(() => {
            if (alertDiv && alertDiv.parentNode) {
                alertDiv.classList.remove("show");
                alertDiv.classList.add("fade");
                setTimeout(() => alertDiv.remove(), 150);
            }
        }, duration);
    }

    function sendToToastr(type, message, options = {}) {
        if (!global.toastr || typeof global.toastr[type] !== "function") {
            return false;
        }

        const title = options.title || "";
        const toastOptions = Object.assign({}, options.toastOptions || {});
        global.toastr[type](message, title, toastOptions);
        return true;
    }

    function notify(type, message, options) {
        const normalizedType = normalizeType(type);
        const normalizedMessage = message != null ? String(message) : "";
        if (!normalizedMessage) {
            return;
        }

        const config = options || {};
        const usedToastr = sendToToastr(normalizedType, normalizedMessage, config);

        if (!usedToastr) {
            createBootstrapAlert(normalizedType === "error" ? "danger" : normalizedType, normalizedMessage, config);
        }
    }

    function showByArgs(arg1, arg2, options) {
        // 兼容两种调用方式：showAlert('success', 'message') 或 showAlert('message', 'success')
        let type;
        let message;

        if (arg1 != null && arg2 != null) {
            const firstIsType = TOASTR_TYPES.has(String(arg1).toLowerCase()) || arg1 === "danger";
            if (firstIsType) {
                type = arg1;
                message = arg2;
            } else {
                type = arg2;
                message = arg1;
            }
        } else {
            message = arg1 != null ? arg1 : arg2;
            type = "info";
        }

        notify(type, message, options);
    }

    function confirm(options = {}) {
        const {
            message,
            title = "确认",
            okText = "确认",
            cancelText = "取消",
            onConfirm,
            onCancel,
        } = options;

        // 若页面存在 Bootstrap 模态框，可在此扩展；当前使用浏览器 confirm 作为降级方案
        const result = window.confirm(title ? `${title}\n\n${message}` : message);
        if (result) {
            if (typeof onConfirm === "function") {
                onConfirm();
            }
        } else if (typeof onCancel === "function") {
            onCancel();
        }
        return result;
    }

    const api = {
        success(message, options) {
            notify("success", message, options);
        },
        error(message, options) {
            notify("error", message, options);
        },
        warning(message, options) {
            notify("warning", message, options);
        },
        info(message, options) {
            notify("info", message, options);
        },
        alert(type, message, options) {
            notify(type, message, options);
        },
        toast(type, message, options) {
            notify(type, message, options);
        },
        confirm,
    };

    global.notify = api;
    global.showSuccessAlert = api.success;
    global.showErrorAlert = api.error;
    global.showWarningAlert = api.warning;
    global.showInfoAlert = api.info;
    global.showAlert = showByArgs;
    global.showToast = (message, type, options) => {
        showByArgs(type || "info", message, options);
    };
})(window);
