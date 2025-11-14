/**
 * 用户管理列表页脚本（Umbrella 版本）
 */
(function (global) {
    'use strict';

    const helpers = global.DOMHelpers;
    if (!helpers) {
        console.error('DOMHelpers 未初始化，无法加载用户列表脚本');
        return;
    }

    const { ready, select, selectOne, from } = helpers;
    const UserService = global.UserService;
    if (!UserService) {
        console.error('UserService 未初始化，无法加载用户列表脚本');
        return;
    }
    const userService = new UserService(global.httpU);

    ready(() => {
        initDeleteUserHandlers();
    });

    function initDeleteUserHandlers() {
        select('[data-action="delete-user"]').each((button) => {
            const wrapper = from(button);
            wrapper.on('click', (event) => {
                event.preventDefault();
                if (button.disabled) {
                    return;
                }
                const userId = wrapper.attr('data-user-id');
                const username = wrapper.attr('data-username') || '';
                if (!userId) {
                    return;
                }
                confirmDeleteUser(userId, username);
            });
        });
    }

    function confirmDeleteUser(userId, username) {
        const displayName = username || '';
        if (global.confirm(`确定要删除用户 "${displayName}" 吗？此操作不可撤销。`)) {
            performDeleteUser(userId);
        }
    }

    function performDeleteUser(userId) {
        const trigger = selectOne(`[data-action="delete-user"][data-user-id="${userId}"]`);
        showLoadingState(trigger, '删除中...');

        userService
            .deleteUser(userId)
            .then((data) => {
                if (data.success) {
                    global.toast.success(data.message || '用户删除成功');
                    global.location.reload();
                } else {
                    global.toast.error(data.message || '删除用户失败');
                }
            })
            .catch((error) => {
                console.error('删除用户失败', error);
                global.toast.error('删除用户失败');
            })
            .finally(() => {
                hideLoadingState(trigger, '删除');
            });
    }

    function showLoadingState(element, text) {
        const target = from(element);
        if (!target.length) {
            return;
        }
        const node = target.first();
        node.dataset.originalText = target.html();
        target.html(`<i class="fas fa-spinner fa-spin me-2"></i>${text}`);
        target.attr('disabled', 'disabled');
    }

    function hideLoadingState(element, fallbackText) {
        const target = from(element);
        if (!target.length) {
            return;
        }
        const node = target.first();
        const original = node.dataset.originalText;
        target.html(original || fallbackText || '删除');
        target.attr('disabled', null);
        delete node.dataset.originalText;
    }
})(window);
