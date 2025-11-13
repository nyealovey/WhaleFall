/**
 * 用户管理列表页脚本
 */

(function () {
    'use strict';

    document.addEventListener('DOMContentLoaded', function () {
        initDeleteUserHandlers();
    });

    function initDeleteUserHandlers() {
        const buttons = document.querySelectorAll('[data-action="delete-user"]');
        buttons.forEach(function (button) {
            button.addEventListener('click', function (event) {
                event.preventDefault();
                if (button.disabled) {
                    return;
                }
                const userId = button.getAttribute('data-user-id');
                const username = button.getAttribute('data-username') || '';
                if (!userId) {
                    return;
                }
                confirmDeleteUser(userId, username);
            });
        });
    }

    function confirmDeleteUser(userId, username) {
        const displayName = username || '';
        if (window.confirm(`确定要删除用户 "${displayName}" 吗？此操作不可撤销。`)) {
            performDeleteUser(userId);
        }
    }

    function performDeleteUser(userId) {
        const trigger = document.querySelector(`[data-action="delete-user"][data-user-id="${userId}"]`);
        showLoadingState(trigger, '删除中...');

        http.delete(`/users/api/users/${userId}`)
            .then((data) => {
                if (data.success) {
                    window.toast.success(data.message || '用户删除成功');
                    window.location.reload();
                } else {
                    window.toast.error(data.message || '删除用户失败');
                }
            })
            .catch((error) => {
                console.error('删除用户失败', error);
                window.toast.error('删除用户失败');
            })
            .finally(() => {
                hideLoadingState(trigger, '删除');
            });
    }

    function showLoadingState(element, text) {
        if (!element) {
            return;
        }
        element.dataset.originalText = element.innerHTML;
        element.innerHTML = `<i class="fas fa-spinner fa-spin me-2"></i>${text}`;
        element.disabled = true;
    }

    function hideLoadingState(element, fallbackText) {
        if (!element) {
            return;
        }
        const original = element.dataset.originalText;
        element.innerHTML = original || fallbackText || '删除';
        element.disabled = false;
        delete element.dataset.originalText;
    }
})();
