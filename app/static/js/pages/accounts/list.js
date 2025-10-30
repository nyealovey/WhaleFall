/**
 * 账户列表页面JavaScript
 * 处理账户同步、权限查看、标签选择等功能
 */

// 页面加载完成后初始化
document.addEventListener('DOMContentLoaded', function() {
    initializeTagFilter();
});

// 同步所有账户
function syncAllAccounts() {
    const btn = event.target;
    const originalText = btn.innerHTML;

    btn.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>同步中...';
    btn.disabled = true;

    http.post('/account_sync/api/sync-all')
    .then(data => {
        if (data.success) {
            toast.success( data.message);
            // 同步完成后刷新页面显示最新数据
            setTimeout(() => {
                location.reload();
            }, 2000);
        } else if (data.error) {
            toast.error( data.error);
        }
    })
    .catch(error => {
        console.error('Error:', error);
        toast.error( '同步失败');
    })
    .finally(() => {
        btn.innerHTML = originalText;
        btn.disabled = false;
    });
}

// 保持向后兼容
function syncAllInstances() {
    syncAllAccounts();
}

// 查看账户详情
function viewAccount(accountId) {
    toast.info(`查看账户 ${accountId} 的详情`);
}

// 显示账户统计
function showAccountStatistics() {
    // 直接跳转到账户统计页面
    window.location.href = '/account-static/';
}

function initializeTagFilter() {
    if (!window.TagSelectorHelper) {
        console.warn('TagSelectorHelper 未加载，跳过标签筛选初始化');
        return;
    }

    const hiddenInput = document.getElementById('selected-tag-names');
    const initialValues = hiddenInput?.value
        ? hiddenInput.value.split(',').map((value) => value.trim()).filter(Boolean)
        : [];

    TagSelectorHelper.setupForForm({
        modalSelector: '#tagSelectorModal',
        rootSelector: '[data-tag-selector]',
        openButtonSelector: '#open-tag-filter-btn',
        previewSelector: '#selected-tags-preview',
        countSelector: '#selected-tags-count',
        chipsSelector: '#selected-tags-chips',
        hiddenInputSelector: '#selected-tag-names',
        hiddenValueKey: 'name',
        initialValues,
        onConfirm: () => {
            const form = document.getElementById('account-filter-form');
            if (form) {
                if (typeof form.requestSubmit === 'function') {
                    form.requestSubmit();
                } else {
                    form.submit();
                }
            }
        },
    });
}

// 辅助函数：判断颜色是否为深色
function isColorDark(colorStr) {
    if (!colorStr) return false;

    // 创建一个临时元素来解析颜色
    const tempDiv = document.createElement('div');
    tempDiv.style.color = colorStr;
    document.body.appendChild(tempDiv);

    const rgbColor = window.getComputedStyle(tempDiv).color;
    document.body.removeChild(tempDiv);

    const rgb = rgbColor.match(/\d+/g).map(Number);
    const r = rgb[0];
    const g = rgb[1];
    const b = rgb[2];

    // 使用 HSP（高敏感度池）方程计算亮度
    const hsp = Math.sqrt(
        0.299 * (r * r) +
        0.587 * (g * g) +
        0.114 * (b * b)
    );

    return hsp < 127.5;
}

// CSRF Token处理已统一到csrf-utils.js中的全局getCSRFToken函数

// 权限调试功能
function debugPermissionFunctions() {
}


// 页面卸载时清理
window.addEventListener('beforeunload', function() {
    // 清理资源
});

// 导出函数供全局使用
window.syncAllAccounts = syncAllAccounts;
window.syncAllInstances = syncAllInstances;
window.viewAccount = viewAccount;
window.showAccountStatistics = showAccountStatistics;
window.debugPermissionFunctions = debugPermissionFunctions;
