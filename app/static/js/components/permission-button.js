(function (window) {
    /**
     * 权限按钮组件
     * 提供统一的权限查看按钮创建功能
     */
    'use strict';

    const helpers = window.DOMHelpers;
    if (!helpers) {
        console.error('DOMHelpers 未初始化，无法加载权限按钮组件');
        return;
    }
    const { selectOne, from } = helpers;

    function bindPermissionClick(button, accountId, apiUrl) {
        from(button).on('click', (event) => {
            event.preventDefault();
            window.viewAccountPermissions(accountId, { apiUrl, trigger: button });
        });
    }

    function createPermissionButton(accountId, options = {}) {
        const {
            buttonClass = 'btn btn-outline-primary btn-sm',
            icon = 'fas fa-eye',
            text = '权限',
            title = '查看权限',
            apiUrl = `/account/api/${accountId}/permissions`,
            attributes = {},
        } = options;

        const button = document.createElement('a');
        button.href = 'javascript:void(0)';
        button.className = buttonClass;
        button.title = title;
        button.setAttribute('data-account-id', accountId);

        Object.entries(attributes || {}).forEach(([key, value]) => {
            button.setAttribute(key, value);
        });

        button.innerHTML = `<i class="${icon} me-1"></i>${text}`;
        bindPermissionClick(button, accountId, apiUrl);
        return button;
    }

    function resolveContainer(container) {
        if (!container) {
            return null;
        }
        if (typeof container === 'string') {
            return selectOne(container).first();
        }
        if (container instanceof Element) {
            return container;
        }
        if (container.first) {
            return container.first();
        }
        return null;
    }

    function createPermissionButtonInContainer(container, accountId, options = {}) {
        const containerElement = resolveContainer(container);
        if (!containerElement) {
            console.error('容器元素未找到:', container);
            return null;
        }
        const button = createPermissionButton(accountId, options);
        containerElement.appendChild(button);
        return button;
    }

    function createPermissionButtons(accounts, options = {}) {
        const {
            containerSelector,
            buttonClass = 'btn btn-outline-primary btn-sm',
            icon = 'fas fa-eye',
            text = '权限',
            title = '查看权限',
        } = options;

        const buttons = [];
        const containerElement = containerSelector ? selectOne(containerSelector).first() : null;

        (accounts || []).forEach((account) => {
            const buttonOptions = {
                ...options,
                buttonClass,
                icon,
                text,
                title: title.replace('{username}', account.username || account.id),
            };

            const button = createPermissionButton(account.id, buttonOptions);
            buttons.push(button);

            if (containerElement) {
                containerElement.appendChild(button);
            }
        });

        return buttons;
    }

    function updatePermissionButtonApiUrl(button, apiUrl) {
        if (!button || !button.hasAttribute('data-account-id')) {
            return;
        }
        const accountId = button.getAttribute('data-account-id');
        const cloned = button.cloneNode(true);
        const parent = button.parentNode;
        if (!parent) {
            return;
        }
        parent.replaceChild(cloned, button);
        bindPermissionClick(cloned, accountId, apiUrl);
    }

    window.createPermissionButton = createPermissionButton;
    window.createPermissionButtonInContainer = createPermissionButtonInContainer;
    window.createPermissionButtons = createPermissionButtons;
    window.updatePermissionButtonApiUrl = updatePermissionButtonApiUrl;
})(window);
