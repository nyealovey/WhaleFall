/**
 * 基于 Bootstrap 5 的全局 Toast 通知模块。
 * 提供统一的 toast.success / error / warning / info 接口。
 */
(function (global) {
    'use strict';

    const bootstrapLib = global.bootstrap;
    if (!bootstrapLib || !bootstrapLib.Toast) {
        console.error('Bootstrap Toast 未加载，无法初始化通知模块');
        return;
    }

    const helpers = global.DOMHelpers;
    if (!helpers || typeof helpers.selectOne !== 'function') {
        console.error('DOMHelpers 未初始化，无法挂载 toast 容器');
        return;
    }

    const { selectOne, from } = helpers;

    const POSITION_CLASS_MAP = {
        'top-right': ['top-0', 'end-0'],
        'top-left': ['top-0', 'start-0'],
        'bottom-right': ['bottom-0', 'end-0'],
        'bottom-left': ['bottom-0', 'start-0']
    };
    const ALLOWED_POSITIONS = new Set(Object.keys(POSITION_CLASS_MAP));

    const TYPE_CLASS_MAP = {
        success: {
            toast: ['text-bg-success'],
            body: [],
            close: ['btn-close-white'],
            ariaLive: 'polite'
        },
        error: {
            toast: ['text-bg-danger'],
            body: [],
            close: ['btn-close-white'],
            ariaLive: 'assertive'
        },
        warning: {
            toast: ['text-bg-warning', 'text-dark'],
            body: [],
            close: [],
            ariaLive: 'assertive'
        },
        info: {
            toast: ['text-bg-info', 'text-dark'],
            body: [],
            close: [],
            ariaLive: 'polite'
        }
    };
    const ALLOWED_TYPES = new Set(Object.keys(TYPE_CLASS_MAP));

    const DEFAULT_OPTIONS = {
        title: '',
        duration: 4000,
        closable: true,
        position: 'top-right',
        stackLimit: 5,
        icon: null,
        ariaLive: null
    };

    const containers = new Map();

    /**
     * 确保类型在支持范围内，默认 info。
     *
     * @param {string} type 用户传入的类型。
     * @returns {string} 规范化后的类型。
     */
  function normalizeType(type) {
    const normalized = String(type || 'info').toLowerCase();
    return Object.prototype.hasOwnProperty.call(TYPE_CLASS_MAP, normalized) ? normalized : 'info';
  }

    /**
     * 解析位置字符串，回退到默认。
     *
     * @param {string} position 位置标识。
     * @returns {string} 合法位置。
     */
  function resolvePosition(position) {
    const normalized = String(position || DEFAULT_OPTIONS.position).toLowerCase();
    return Object.prototype.hasOwnProperty.call(POSITION_CLASS_MAP, normalized) ? normalized : 'top-right';
  }

    /**
     * 获取/创建指定位置的 toast 容器。
     *
     * @param {string} position 位置标识。
     * @returns {HTMLElement} 容器元素。
     */
    function getContainer(position) {
        const normalizedCandidate = resolvePosition(position);
        const normalized = ALLOWED_POSITIONS.has(normalizedCandidate) ? normalizedCandidate : 'top-right';
        if (containers.has(normalized)) {
            return containers.get(normalized);
        }

        const body = selectOne('body');
        const element = document.createElement('div');
        element.className = 'toast-container position-fixed p-3';
        element.setAttribute('data-position', normalized);
        element.style.zIndex = '1080';
        const container = from(element);
        if (Object.prototype.hasOwnProperty.call(POSITION_CLASS_MAP, normalized)) {
            const classes = POSITION_CLASS_MAP[normalized]; // eslint-disable-line security/detect-object-injection
            if (Array.isArray(classes)) {
                classes.forEach((cls) => container.addClass(cls));
            }
        }
        body.append(element);
        containers.set(normalized, element); // normalized 已经过白名单验证
        return element;
    }

    /**
     * 生成关闭按钮，按类型配置附加类名。
     *
     * @param {Object} typeConfig 类型配置。
     * @returns {HTMLElement} 关闭按钮元素。
     */
    function createCloseButton(typeConfig) {
        const button = selectOne('<button type="button" class="btn-close" data-bs-dismiss="toast" aria-label="关闭"></button>');
        typeConfig.close.forEach((cls) => button.addClass(cls));
        return button;
    }

    /**
     * 创建可选图标元素。
     *
     * @param {string|null} icon 图标类名。
     * @returns {HTMLElement|null} 图标元素。
     */
    function createIconElement(icon) {
        if (!icon) {
            return null;
        }
        const span = selectOne('<span aria-hidden="true"></span>');
        span.attr('class', typeof icon === 'string' ? icon : '');
        return span;
    }

    /**
     * 构造 toast DOM（含标题或纯文本布局）。
     *
     * @param {string} type 消息类型。
     * @param {string} message 文本内容。
     * @param {Object} options 配置项。
     * @returns {Object} DOMHelpers 包装的元素。
     */
    function buildToastElement(type, message, options) {
        const typeKey = normalizeType(type);
        const safeTypeKey = ALLOWED_TYPES.has(typeKey) ? typeKey : 'info';
        const typeConfig = TYPE_CLASS_MAP[safeTypeKey]; // eslint-disable-line security/detect-object-injection
        const toastElement = selectOne('<div class="toast border-0 shadow-sm" role="status" aria-atomic="true"></div>');

        typeConfig.toast.forEach((cls) => toastElement.addClass(cls));

        const ariaLive = options.ariaLive || typeConfig.ariaLive || 'polite';
        toastElement.attr('aria-live', ariaLive);

        if (options.title) {
            const header = selectOne('<div class="toast-header border-0"></div>');

            const iconElement = createIconElement(options.icon);
            if (iconElement) {
                iconElement.addClass('me-2');
                header.append(iconElement);
            }

            const strong = selectOne('<strong class="me-auto"></strong>');
            strong.text(options.title);
            header.append(strong);

            if (options.closable) {
                header.append(createCloseButton(typeConfig));
            }

            toastElement.append(header);

            const body = selectOne('<div class="toast-body"></div>');
            body.text(message);
            toastElement.append(body);
        } else {
            const wrapper = selectOne('<div class="d-flex"></div>');

            const body = selectOne('<div class="toast-body"></div>');
            body.text(message);
        typeConfig.body.forEach((cls) => body.addClass(cls));
            wrapper.append(body);

            if (options.closable) {
                const closeButton = createCloseButton(typeConfig);
                closeButton.addClass('me-2', 'm-auto');
                wrapper.append(closeButton);
            }

            toastElement.append(wrapper);
        }

        return toastElement;
    }

    /**
     * 限制同一位置的 toast 堆栈数量。
     *
     * @param {HTMLElement} container 容器。
     * @param {number} stackLimit 最大数量。
     * @param {string} position 位置标识。
     * @returns {void}
     */
    function trimStack(container, stackLimit, position) {
        if (stackLimit <= 0) {
            return;
        }
        while (container.children.length > stackLimit) {
            const target =
                position.includes('top') ? container.lastElementChild : container.firstElementChild;
            if (target) {
                target.remove();
            } else {
                break;
            }
        }
    }

    /**
     * 根据位置将 toast 插入容器头部或尾部。
     *
     * @param {HTMLElement} container 容器。
     * @param {HTMLElement} toastElement Toast DOM。
     * @returns {void}
     */
    function mountToastElement(container, toastElement) {
        const position = container.getAttribute('data-position') || 'top-right';
        if (position.includes('top')) {
            container.prepend(toastElement);
        } else {
            container.appendChild(toastElement);
        }
    }

    /**
     * 公共入口，渲染并展示 toast。
     *
     * @param {string} type 类型。
     * @param {string} message 内容。
     * @param {Object} [options={}] 配置。
     * @returns {void}
     */
    function showToast(type, message, options = {}) {
        const normalizedMessage = message != null ? String(message) : '';
        if (!normalizedMessage) {
            return;
        }

        const config = Object.assign({}, DEFAULT_OPTIONS, options);
        const position = resolvePosition(config.position);
        const container = getContainer(position);
        const toastElementWrapper = buildToastElement(type, normalizedMessage, config);
        const toastElement = toastElementWrapper.first();

        mountToastElement(container, toastElement);
        trimStack(
            container,
            Number(config.stackLimit) || DEFAULT_OPTIONS.stackLimit,
            position
        );

        const bootstrapToast = new bootstrapLib.Toast(toastElement, {
            autohide: config.duration > 0,
            delay: Math.max(0, Number(config.duration) || DEFAULT_OPTIONS.duration)
        });

        toastElement.addEventListener('hidden.bs.toast', function () {
            bootstrapToast.dispose();
            toastElement.remove();
        });

        bootstrapToast.show();
    }

    const api = {
        show(type, message, options) {
            showToast(type, message, options);
        },
        success(message, options) {
            showToast('success', message, options);
        },
        error(message, options) {
            showToast('error', message, options);
        },
        warning(message, options) {
            showToast('warning', message, options);
        },
        info(message, options) {
            showToast('info', message, options);
        }
    };

    global.toast = api;
})(window);
