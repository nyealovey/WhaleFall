/**
 * 账户列表页面JavaScript
 * 处理账户同步、权限查看、标签选择等功能
 */

// 全局变量
let accountListTagSelector = null;

// 页面加载完成后初始化
document.addEventListener('DOMContentLoaded', function() {
    initializeTagSelector();
});

// 同步所有账户
function syncAllAccounts() {
    const btn = event.target;
    const originalText = btn.innerHTML;

    btn.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>同步中...';
    btn.disabled = true;

    fetch('/account-sync/sync-all', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCSRFToken()
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showAlert('success', data.message);
            // 同步完成后刷新页面显示最新数据
            setTimeout(() => {
                location.reload();
            }, 2000);
        } else if (data.error) {
            showAlert('danger', data.error);
        }
    })
    .catch(error => {
        console.error('Error:', error);
        showAlert('danger', '同步失败');
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
    showAlert('info', `查看账户 ${accountId} 的详情`);
}

// 显示账户统计
function showAccountStatistics() {
    // 直接跳转到账户统计页面
    window.location.href = '/account-static/';
}

// 显示提示信息
function showAlert(type, message) {
    const alertDiv = document.createElement('div');
    alertDiv.className = `alert alert-${type} alert-dismissible fade show`;
    alertDiv.innerHTML = `
        <i class="fas fa-${getAlertIcon(type)} me-2"></i>
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;

    const container = document.querySelector('.container');
    if (container) {
        container.insertBefore(alertDiv, container.firstChild);
    }

    setTimeout(() => {
        alertDiv.remove();
    }, 5000);
}

// 获取提示图标
function getAlertIcon(type) {
    const icons = {
        'success': 'check-circle',
        'info': 'info-circle',
        'warning': 'exclamation-triangle',
        'danger': 'exclamation-triangle'
    };
    return icons[type] || 'info-circle';
}

// 表单验证
function validateForm() {
    const form = document.getElementById('account-search-form');
    if (!form) return true;

    // 可以添加具体的验证逻辑
    return true;
}

// 初始化标签选择器
function initializeTagSelector() {
    // 立即检查元素
    const accountListSelector = document.getElementById('account-list-tag-selector');
    
    if (accountListSelector) {
        const modalElement = accountListSelector.querySelector('#tagSelectorModal');
        
        if (modalElement) {
            // 在模态框内部查找容器元素
            const containerElement = modalElement.querySelector('#tag-selector-container');
            
            if (containerElement) {
                initializeTagSelectorComponent(modalElement, containerElement);
            } else {
                // 等待标签选择器组件加载完成
                setTimeout(() => {
                    const delayedContainerElement = modalElement.querySelector('#tag-selector-container');
                    
                    if (delayedContainerElement) {
                        initializeTagSelectorComponent(modalElement, delayedContainerElement);
                    }
                }, 1000);
            }
        }
    }
}

// 初始化标签选择器组件
function initializeTagSelectorComponent(modalElement, containerElement) {
    if (typeof TagSelector !== 'undefined' && modalElement && containerElement) {
        // 初始化标签选择器
        accountListTagSelector = new TagSelector('tag-selector-container', {
            allowMultiple: true,
            allowCreate: true,
            allowSearch: true,
            allowCategoryFilter: true
        });
        
        // 绑定打开标签选择器按钮
        const openBtn = document.getElementById('open-tag-selector-btn');
        if (openBtn) {
            openBtn.addEventListener('click', function() {
                if (typeof openTagSelector === 'function') {
                    openTagSelector();
                } else {
                    console.error('openTagSelector函数未定义');
                }
                
                // 模态框显示后重新绑定按钮
                setTimeout(() => {
                    if (accountListTagSelector) {
                        accountListTagSelector.rebindModalButtons();
                    }
                }, 100);
            });
        }
        
        // 绑定确认选择按钮
        const confirmBtn = document.getElementById('confirm-selection-btn');
        if (confirmBtn) {
            confirmBtn.addEventListener('click', confirmTagSelection);
        }
    } else {
        console.error('初始化失败:');
        console.error('- TagSelector可用:', typeof TagSelector !== 'undefined');
        console.error('- 模态框元素:', modalElement ? '找到' : '未找到');
        console.error('- 容器元素:', containerElement ? '找到' : '未找到');
    }
}

// 确认标签选择
function confirmTagSelection() {
    if (accountListTagSelector) {
        // 直接调用标签选择器的确认方法
        accountListTagSelector.confirmSelection();
        
        // 获取选中的标签并更新预览
        const selectedTags = accountListTagSelector.getSelectedTags();
        updateSelectedTagsPreview(selectedTags);
        closeTagSelector();
    }
}

// 更新选中标签预览
function updateSelectedTagsPreview(selectedTags) {
    const preview = document.getElementById('selected-tags-preview');
    const count = document.getElementById('selected-tags-count');
    const chips = document.getElementById('selected-tags-chips');
    const hiddenInput = document.getElementById('selected-tag-names');
    
    if (selectedTags.length > 0) {
        if (preview) preview.style.display = 'block';
        if (count) count.textContent = `已选择 ${selectedTags.length} 个标签`;
        
        if (chips) {
            chips.innerHTML = selectedTags.map(tag => `
                <span class="badge bg-${tag.color} me-1 mb-1">
                    <i class="fas fa-tag me-1"></i>${tag.display_name}
                    <button type="button" class="btn-close btn-close-white ms-1" 
                            onclick="removeTagFromPreview('${tag.name}')" 
                            style="font-size: 0.6em;"></button>
                </span>
            `).join('');
        }
        
        if (hiddenInput) {
            hiddenInput.value = selectedTags.map(tag => tag.name).join(',');
        }
    } else {
        if (preview) preview.style.display = 'none';
        if (count) count.textContent = '未选择标签';
        if (hiddenInput) hiddenInput.value = '';
    }
}

// 从预览中移除标签
function removeTagFromPreview(tagName) {
    if (accountListTagSelector) {
        const tag = accountListTagSelector.availableTags.find(t => t.name === tagName);
        if (tag) {
            accountListTagSelector.toggleTag(tag.id);
            const selectedTags = accountListTagSelector.getSelectedTags();
            updateSelectedTagsPreview(selectedTags);
        }
    }
}

// 工具函数
function getCSRFToken() {
    return document.querySelector('meta[name="csrf-token"]')?.getAttribute('content') ||
           document.querySelector('input[name="csrf_token"]')?.value || '';
}

// 权限调试功能
function debugPermissionFunctions() {
    console.log('=== 权限功能调试信息 ===');
    console.log('viewAccountPermissions 函数:', typeof viewAccountPermissions);
    console.log('showPermissionsModal 函数:', typeof showPermissionsModal);
    console.log('PermissionViewer 类:', typeof PermissionViewer);
    console.log('PermissionModal 类:', typeof PermissionModal);
    console.log('========================');
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
window.showAlert = showAlert;
window.validateForm = validateForm;
window.debugPermissionFunctions = debugPermissionFunctions;
