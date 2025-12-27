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
     *
     * @param {Element|Event|Object} trigger - 按钮引用或事件对象
     * @return {Element|null} 按钮元素，未找到则返回 null
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
     *
     * @param {Element} button - 按钮元素
     * @param {boolean} isLoading - 是否显示加载状态
     * @return {void}
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
     *
     * @param {void} 无参数。直接从 DOM 中获取。
     * @return {string} CSRF token 值
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
     *
     * @param {number|string} accountId - 账户 ID
     * @param {Object} [options] - 配置选项
     * @param {string} [options.apiUrl] - API 地址
     * @param {Function} [options.onSuccess] - 成功回调
     * @param {Function} [options.onError] - 错误回调
     * @param {Function} [options.onFinally] - 完成回调
     * @param {Element|Event} [options.trigger] - 触发元素
     * @return {void}
     */
    function viewAccountPermissions(accountId, options = {}) {
        const {
            apiUrl = `/api/v1/accounts/ledgers/${accountId}/permissions`,
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
     *
     * @param {number|string} accountId - 账户 ID
     * @param {string} [apiUrl] - API 地址
     * @return {Promise<Object>} 权限数据 Promise
     * @throws {Error} 当获取失败时抛出
     */
    function fetchAccountPermissions(accountId, apiUrl = `/api/v1/accounts/ledgers/${accountId}/permissions`) {
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
