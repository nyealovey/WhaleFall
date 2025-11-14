(function (window) {
    /**
     * 权限查看核心逻辑
     * 提供统一的权限查看功能，支持所有数据库类型
     */
    'use strict';

    const helpers = window.DOMHelpers;
    if (!helpers) {
        console.error('DOMHelpers 未初始化，无法加载 PermissionViewer');
        return;
    }
    const { selectOne, from } = helpers;

    function resolveButton(trigger) {
        if (trigger) {
            return trigger;
        }
        if (window.event && window.event.currentTarget) {
            return window.event.currentTarget;
        }
        if (window.event && window.event.target) {
            return window.event.target;
        }
        return null;
    }

    function toggleButtonLoading(button, isLoading) {
        if (!button) {
            return;
        }
        const element = from(button);
        if (!element.length) {
            return;
        }
        if (isLoading) {
            element.attr('data-original-html', element.html());
            element.html('<i class="fas fa-spinner fa-spin me-1"></i>加载中...');
            element.attr('disabled', 'disabled');
        } else {
            const original = element.attr('data-original-html');
            if (original) {
                element.html(original);
                element.attr('data-original-html', null);
            }
            element.attr('disabled', null);
        }
    }

    function resolveCsrfToken() {
        if (!selectOne || !helpers) {
            const meta = document.querySelector('meta[name="csrf-token"]');
            if (meta) {
                return meta.getAttribute('content');
            }
            const input = document.querySelector('input[name="csrf_token"]');
            return input ? input.value : '';
        }
        const meta = selectOne('meta[name="csrf-token"]');
        if (meta.length) {
            return meta.attr('content');
        }
        const input = selectOne('input[name="csrf_token"]');
        return input.length ? input.first().value : '';
    }

    function viewAccountPermissions(accountId, options = {}) {
        const {
            apiUrl = `/account/api/${accountId}/permissions`,
            onSuccess,
            onError,
            onFinally,
            trigger,
        } = options;

        const finalApiUrl = apiUrl.replace('${accountId}', accountId);
        resolveCsrfToken(); // 保持兼容，尽管 httpU 已处理 CSRF

        const triggerButton = resolveButton(trigger);
        toggleButtonLoading(triggerButton, true);

        window.httpU
            .get(finalApiUrl)
            .then((data) => {
                const responsePayload =
                    data && typeof data === 'object' && data.data && typeof data.data === 'object'
                        ? data.data
                        : data;

                if (data && data.success) {
                    if (window.showPermissionsModal) {
                        window.showPermissionsModal(responsePayload?.permissions, responsePayload?.account);
                    } else {
                        console.error('showPermissionsModal 函数未定义');
                    }
                    onSuccess?.(responsePayload);
                } else {
                    const errorMsg = data?.error || data?.message || '获取权限信息失败';
                    window.toast.error(errorMsg);
                    onError?.(data);
                }
            })
            .catch((error) => {
                window.toast.error('获取权限信息失败');
                onError?.(error);
            })
            .finally(() => {
                toggleButtonLoading(triggerButton, false);
                onFinally?.();
            });
    }

    function fetchAccountPermissions(accountId, apiUrl = `/account/api/${accountId}/permissions`) {
        resolveCsrfToken();
        const finalApiUrl = apiUrl.replace('${accountId}', accountId);

        return window.httpU.get(finalApiUrl).then((data) => {
            if (data && data.success) {
                const responsePayload = data.data && typeof data.data === 'object' ? data.data : data;
                return responsePayload;
            }
            throw new Error(data?.error || data?.message || '获取权限信息失败');
        });
    }

    window.viewAccountPermissions = viewAccountPermissions;
    window.fetchAccountPermissions = fetchAccountPermissions;
})(window);
