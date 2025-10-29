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

    const POSITION_CLASS_MAP = {
        'top-right': ['top-0', 'end-0'],
        'top-left': ['top-0', 'start-0'],
        'bottom-right': ['bottom-0', 'end-0'],
        'bottom-left': ['bottom-0', 'start-0']
    };

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

    function normalizeType(type) {
        const normalized = String(type || 'info').toLowerCase();
        return TYPE_CLASS_MAP[normalized] ? normalized : 'info';
    }

    function resolvePosition(position) {
        const normalized = String(position || DEFAULT_OPTIONS.position).toLowerCase();
        return POSITION_CLASS_MAP[normalized] ? normalized : 'top-right';
    }

    function getContainer(position) {
        const normalized = resolvePosition(position);
        if (containers.has(normalized)) {
            return containers.get(normalized);
        }

        const container = document.createElement('div');
        container.className = 'toast-container position-fixed p-3';
        container.setAttribute('data-position', normalized);

        POSITION_CLASS_MAP[normalized].forEach((cls) => container.classList.add(cls));
        container.style.zIndex = '1080';

        document.body.appendChild(container);
        containers.set(normalized, container);
        return container;
    }

    function createCloseButton(typeConfig) {
        const button = document.createElement('button');
        button.type = 'button';
        button.className = 'btn-close';
        button.setAttribute('data-bs-dismiss', 'toast');
        button.setAttribute('aria-label', '关闭');
        typeConfig.close.forEach((cls) => button.classList.add(cls));
        return button;
    }

    function createIconElement(icon) {
        if (!icon) {
            return null;
        }
        const span = document.createElement('span');
        span.className = typeof icon === 'string' ? icon : '';
        span.setAttribute('aria-hidden', 'true');
        return span;
    }

    function buildToastElement(type, message, options) {
        const typeKey = normalizeType(type);
        const typeConfig = TYPE_CLASS_MAP[typeKey];
        const toastElement = document.createElement('div');
        toastElement.className = 'toast border-0 shadow-sm';
        toastElement.setAttribute('role', 'status');
        toastElement.setAttribute('aria-atomic', 'true');

        typeConfig.toast.forEach((cls) => toastElement.classList.add(cls));

        const ariaLive = options.ariaLive || typeConfig.ariaLive || 'polite';
        toastElement.setAttribute('aria-live', ariaLive);

        if (options.title) {
            const header = document.createElement('div');
            header.className = 'toast-header border-0';

            const iconElement = createIconElement(options.icon);
            if (iconElement) {
                iconElement.classList.add('me-2');
                header.appendChild(iconElement);
            }

            const strong = document.createElement('strong');
            strong.className = 'me-auto';
            strong.textContent = options.title;
            header.appendChild(strong);

            if (options.closable) {
                header.appendChild(createCloseButton(typeConfig));
            }

            toastElement.appendChild(header);

            const body = document.createElement('div');
            body.className = 'toast-body';
            body.textContent = message;
            toastElement.appendChild(body);
        } else {
            const wrapper = document.createElement('div');
            wrapper.className = 'd-flex';

            const body = document.createElement('div');
            body.className = 'toast-body';
            body.textContent = message;
            typeConfig.body.forEach((cls) => body.classList.add(cls));
            wrapper.appendChild(body);

            if (options.closable) {
                const closeButton = createCloseButton(typeConfig);
                closeButton.classList.add('me-2', 'm-auto');
                wrapper.appendChild(closeButton);
            }

            toastElement.appendChild(wrapper);
        }

        return toastElement;
    }

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

    function mountToastElement(container, toastElement) {
        const position = container.getAttribute('data-position') || 'top-right';
        if (position.includes('top')) {
            container.prepend(toastElement);
        } else {
            container.appendChild(toastElement);
        }
    }

    function showToast(type, message, options = {}) {
        const normalizedMessage = message != null ? String(message) : '';
        if (!normalizedMessage) {
            return;
        }

        const config = Object.assign({}, DEFAULT_OPTIONS, options);
        const position = resolvePosition(config.position);
        const container = getContainer(position);
        const toastElement = buildToastElement(type, normalizedMessage, config);

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
