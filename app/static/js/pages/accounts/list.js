/**
 * 账户列表页面JavaScript
 * 处理账户同步、权限查看、标签选择等功能
 */

// 全局变量
let accountListTagSelector = null;

// 页面加载完成后初始化
document.addEventListener('DOMContentLoaded', function() {
    // 如果TagSelector类还没有加载，等待一下
    if (typeof TagSelector === 'undefined') {
        setTimeout(() => {
            initializeAccountListTagSelector();
        }, 500);
    } else {
        try {
            if (typeof initializeAccountListTagSelector === 'function') {
                initializeAccountListTagSelector();
            }
        } catch (error) {
            console.error('initializeAccountListTagSelector 调用失败:', error);
        }
    }
});

// 如果DOM已经加载完成，立即初始化
if (document.readyState !== 'loading') {
    if (typeof TagSelector === 'undefined') {
        setTimeout(() => {
            initializeAccountListTagSelector();
        }, 1000);
    } else {
        initializeAccountListTagSelector();
    }
}

// 同步所有账户
function syncAllAccounts() {
    const btn = event.target;
    const originalText = btn.innerHTML;

    btn.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>同步中...';
    btn.disabled = true;

    fetch('/account_sync/api/sync-all', {
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

// 打开标签选择器
function openTagSelector() {
    try {
        console.log('打开标签选择器...');
        const modalElement = document.getElementById('tagSelectorModal');
        
        if (!modalElement) {
            console.error('模态框元素未找到');
            showAlert('danger', '标签选择器模态框未找到，请刷新页面重试');
            return;
        }
        
        const modal = new bootstrap.Modal(modalElement);
        modal.show();
        console.log('模态框已显示');
        
        // 模态框显示后重新绑定按钮
        setTimeout(() => {
            if (accountListTagSelector) {
                console.log('重新绑定模态框按钮');
                accountListTagSelector.rebindModalButtons();
            } else {
                console.warn('accountListTagSelector未初始化，无法重新绑定按钮');
            }
        }, 100);
        
    } catch (error) {
        console.error('打开标签选择器时出错:', error);
        showAlert('danger', '打开标签选择器失败: ' + error.message);
    }
}

// 关闭标签选择器
function closeTagSelector() {
    const modal = bootstrap.Modal.getInstance(document.getElementById('tagSelectorModal'));
    if (modal) {
        modal.hide();
    }
}

// 初始化标签选择器
function initializeAccountListTagSelector() {
    try {
        // 查找容器元素
        const listPageSelector = document.getElementById('list-page-tag-selector');

        if (listPageSelector) {
            const modalElement = listPageSelector.querySelector('#tagSelectorModal');

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
    } catch (error) {
        console.error('initializeAccountListTagSelector 函数执行出错:', error);
    }
}

// 初始化标签选择器组件
function initializeTagSelectorComponent(modalElement, containerElement) {
    if (typeof TagSelector !== 'undefined' && modalElement && containerElement) {
        try {
            // 初始化标签选择器
            accountListTagSelector = new TagSelector('tag-selector-container', {
                allowMultiple: true,
                allowCreate: true,
                allowSearch: true,
                allowCategoryFilter: true
            });

            // 等待TagSelector完全初始化
            setTimeout(() => {
                if (accountListTagSelector && accountListTagSelector.container) {
                    setupTagSelectorEvents();
                }
            }, 100);
        } catch (error) {
            console.error('初始化标签选择器组件时出错:', error);
            showAlert('danger', '标签选择器初始化失败: ' + error.message);
        }
    }
}

// 设置标签选择器事件
function setupTagSelectorEvents() {
    if (!accountListTagSelector) {
        return;
    }

    // 绑定打开标签选择器按钮
    const openBtn = document.getElementById('open-tag-filter-btn');

    if (openBtn) {
        // 移除之前的事件监听器（如果有）
        openBtn.removeEventListener('click', openTagSelector);

        // 添加新的事件监听器
        openBtn.addEventListener('click', function(e) {
            e.preventDefault();

            try {
                if (typeof openTagSelector === 'function') {
                    openTagSelector();
                } else {
                    // 直接显示模态框作为备用方案
                    const modal = new bootstrap.Modal(document.getElementById('tagSelectorModal'));
                    modal.show();
                }

                // 模态框显示后重新绑定按钮
                setTimeout(() => {
                    if (accountListTagSelector) {
                        accountListTagSelector.rebindModalButtons();
                    }
                }, 100);
            } catch (error) {
                console.error('打开标签选择器时出错:', error);
                showAlert('danger', '打开标签选择器失败: ' + error.message);
            }
        });
    }

    // 监听TagSelector的确认事件
    if (accountListTagSelector.container) {
        accountListTagSelector.container.addEventListener('tagSelectionConfirmed', function(event) {
            const selectedTags = event.detail.selectedTags;
            updateSelectedTagsPreview(selectedTags);
            closeTagSelector();
        });

        // 监听TagSelector的取消事件
        accountListTagSelector.container.addEventListener('tagSelectionCancelled', function(event) {
            closeTagSelector();
        });
    }

    // 预填充已选择的标签
    const selectedTagNames = document.getElementById('selected-tag-names');
    if (selectedTagNames && selectedTagNames.value) {
        setTimeout(() => {
            if (accountListTagSelector) {
                const tagNames = selectedTagNames.value.split(',').filter(name => name.trim());
                // 这里需要根据标签名称找到对应的ID，暂时跳过
            }
        }, 500);
    }
}

// 确认标签选择 - 已改为使用事件系统，此函数保留用于向后兼容
function confirmTagSelection() {
    // 这个函数现在由TagSelector的事件系统处理
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
window.openTagSelector = openTagSelector;
window.closeTagSelector = closeTagSelector;
window.confirmTagSelection = confirmTagSelection;
