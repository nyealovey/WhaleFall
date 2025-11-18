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

    const PermissionService = window.PermissionService;
    if (!PermissionService) {
        console.error('PermissionService 未初始化，无法加载 PermissionViewer');
        return;
    }
    let permissionService = null;
    try {
        permissionService = new PermissionService(window.httpU);
    } catch (error) {
        console.error('初始化 PermissionService 失败:', error);
        return;
    }

    /**
     * 从事件或传入引用解析出按钮。
     */
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

    /**
     * 控制按钮 loading 状态，防重复点击。
     */
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

    /**
     * 向后兼容的 CSRF 读取（httpU 已处理）。
     */
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

    /**
     * 入口：查看账户权限并展示模态。
     */
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

        permissionService
            .fetchByUrl(finalApiUrl)
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

    /**
     * 直接拉取账户权限数据（返回 Promise）。
     */
    function fetchAccountPermissions(accountId, apiUrl = `/account/api/${accountId}/permissions`) {
        resolveCsrfToken();
        const finalApiUrl = apiUrl.replace('${accountId}', accountId);

        return permissionService.fetchByUrl(finalApiUrl).then((data) => {
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
