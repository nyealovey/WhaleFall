/**
 * 账户列表页面JavaScript
 * 处理账户同步、权限查看、标签选择等功能
 */

// 全局变量
let accountListTagSelector = null;

// 页面加载完成后初始化
document.addEventListener('DOMContentLoaded', function() {
    console.log('DOMContentLoaded 事件触发，开始初始化标签选择器...');
    console.log('TagSelector 类可用性:', typeof TagSelector !== 'undefined');
    
    // 如果TagSelector类还没有加载，等待一下
    if (typeof TagSelector === 'undefined') {
        console.log('TagSelector类未加载，等待500ms后重试...');
        setTimeout(() => {
            console.log('延迟初始化，TagSelector 类可用性:', typeof TagSelector !== 'undefined');
            console.log('准备调用 initializeTagSelector()...');
            initializeTagSelector();
        }, 500);
    } else {
        console.log('TagSelector类已加载，立即调用 initializeTagSelector()...');
        try {
            initializeTagSelector();
        } catch (error) {
            console.error('initializeTagSelector 调用失败:', error);
        }
    }
});

// 备用初始化方法 - 在脚本加载时立即尝试
console.log('list.js 脚本加载完成，TagSelector 类可用性:', typeof TagSelector !== 'undefined');

// 如果DOM已经加载完成，立即初始化
if (document.readyState === 'loading') {
    console.log('DOM 仍在加载中，等待 DOMContentLoaded 事件...');
} else {
    console.log('DOM 已加载完成，立即初始化标签选择器...');
    if (typeof TagSelector === 'undefined') {
        console.log('TagSelector类未加载，等待1000ms后重试...');
        setTimeout(() => {
            console.log('延迟初始化，TagSelector 类可用性:', typeof TagSelector !== 'undefined');
            initializeTagSelector();
        }, 1000);
    } else {
        initializeTagSelector();
    }
}

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
function initializeTagSelector() {
    try {
        console.log('开始初始化标签选择器...');
        console.log('TagSelector 类可用性:', typeof TagSelector !== 'undefined');
        
        // 查找容器元素
        const listPageSelector = document.getElementById('list-page-tag-selector');
        console.log('容器元素:', listPageSelector ? '找到' : '未找到');
    
    if (listPageSelector) {
        const modalElement = listPageSelector.querySelector('#tagSelectorModal');
        console.log('模态框元素:', modalElement ? '找到' : '未找到');
        
        if (modalElement) {
            // 在模态框内部查找容器元素
            const containerElement = modalElement.querySelector('#tag-selector-container');
            console.log('容器元素:', containerElement ? '找到' : '未找到');
            
            if (containerElement) {
                console.log('立即初始化TagSelector组件...');
                initializeTagSelectorComponent(modalElement, containerElement);
            } else {
                // 等待标签选择器组件加载完成
                console.log('等待标签选择器组件加载...');
                setTimeout(() => {
                    const delayedContainerElement = modalElement.querySelector('#tag-selector-container');
                    
                    if (delayedContainerElement) {
                        console.log('延迟加载成功，初始化组件');
                        initializeTagSelectorComponent(modalElement, delayedContainerElement);
                    } else {
                        console.error('延迟加载失败，容器元素仍未找到');
                    }
                }, 1000);
            }
        } else {
            console.error('模态框元素未找到');
        }
    } else {
        console.error('容器元素 list-page-tag-selector 未找到');
    }
    
        // 添加额外的调试信息
        console.log('initializeTagSelector 完成，accountListTagSelector:', accountListTagSelector ? '已创建' : '未创建');
        
        // 如果初始化失败，提供强制初始化的建议
        if (!accountListTagSelector) {
            console.warn('正常初始化失败，可以尝试运行 forceInitializeTagSelector() 进行强制初始化');
        }
    } catch (error) {
        console.error('initializeTagSelector 函数执行出错:', error);
        console.error('错误堆栈:', error.stack);
    }
}

// 初始化标签选择器组件
function initializeTagSelectorComponent(modalElement, containerElement) {
    console.log('开始初始化标签选择器组件...');
    console.log('TagSelector可用:', typeof TagSelector !== 'undefined');
    console.log('模态框元素:', modalElement ? '找到' : '未找到');
    console.log('容器元素:', containerElement ? '找到' : '未找到');
    
    if (typeof TagSelector !== 'undefined' && modalElement && containerElement) {
        try {
            // 初始化标签选择器
            console.log('创建TagSelector实例...');
            accountListTagSelector = new TagSelector('tag-selector-container', {
                allowMultiple: true,
                allowCreate: true,
                allowSearch: true,
                allowCategoryFilter: true
            });
            console.log('TagSelector实例创建成功');
            
            // 绑定打开标签选择器按钮
            const openBtn = document.getElementById('open-tag-filter-btn');
            console.log('打开按钮:', openBtn ? '找到' : '未找到');
            
            if (openBtn) {
                // 移除之前的事件监听器（如果有）
                openBtn.removeEventListener('click', openTagSelector);
                
                // 添加新的事件监听器
                openBtn.addEventListener('click', function(e) {
                    console.log('打开标签选择器按钮被点击');
                    e.preventDefault();
                    
                    try {
                        if (typeof openTagSelector === 'function') {
                            openTagSelector();
                        } else {
                            console.error('openTagSelector函数未定义');
                            // 直接显示模态框作为备用方案
                            const modal = new bootstrap.Modal(document.getElementById('tagSelectorModal'));
                            modal.show();
                        }
                        
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
                });
                console.log('打开按钮事件绑定成功');
            } else {
                console.error('未找到打开标签选择器按钮 (id: open-tag-filter-btn)');
            }
            
            // 绑定确认选择按钮 - 使用TagSelector的事件系统
            const confirmBtn = document.getElementById('confirm-selection-btn');
            console.log('确认按钮:', confirmBtn ? '找到' : '未找到');
            
            if (confirmBtn) {
                // 监听TagSelector的确认事件
                accountListTagSelector.container.addEventListener('tagSelectionConfirmed', function(event) {
                    console.log('收到标签选择确认事件:', event.detail);
                    const selectedTags = event.detail.selectedTags;
                    updateSelectedTagsPreview(selectedTags);
                    closeTagSelector();
                });
                
                // 监听TagSelector的取消事件
                accountListTagSelector.container.addEventListener('tagSelectionCancelled', function(event) {
                    console.log('收到标签选择取消事件');
                    closeTagSelector();
                });
                
                console.log('确认按钮事件监听器设置成功');
            } else {
                console.error('未找到确认选择按钮 (id: confirm-selection-btn)');
            }
            
            // 预填充已选择的标签
            const selectedTagNames = document.getElementById('selected-tag-names');
            if (selectedTagNames && selectedTagNames.value) {
                console.log('预填充已选择的标签:', selectedTagNames.value);
                setTimeout(() => {
                    if (accountListTagSelector) {
                        const tagNames = selectedTagNames.value.split(',').filter(name => name.trim());
                        // 这里需要根据标签名称找到对应的ID，暂时跳过
                        console.log('预填充标签名称:', tagNames);
                    }
                }, 500);
            }
            
            console.log('标签选择器组件初始化完成');
        } catch (error) {
            console.error('初始化标签选择器组件时出错:', error);
            showAlert('danger', '标签选择器初始化失败: ' + error.message);
        }
    } else {
        console.error('初始化失败:');
        console.error('- TagSelector可用:', typeof TagSelector !== 'undefined');
        console.error('- 模态框元素:', modalElement ? '找到' : '未找到');
        console.error('- 容器元素:', containerElement ? '找到' : '未找到');
    }
}

// 确认标签选择 - 已改为使用事件系统，此函数保留用于向后兼容
function confirmTagSelection() {
    console.log('confirmTagSelection被调用，但已改为使用事件系统');
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

// 标签选择器调试功能
function debugTagSelector() {
    console.log('=== 标签选择器调试信息 ===');
    console.log('TagSelector 类:', typeof TagSelector);
    console.log('accountListTagSelector 实例:', accountListTagSelector ? '已创建' : '未创建');
    console.log('list-page-tag-selector 容器:', document.getElementById('list-page-tag-selector') ? '找到' : '未找到');
    console.log('tagSelectorModal 模态框:', document.getElementById('tagSelectorModal') ? '找到' : '未找到');
    console.log('tag-selector-container 容器:', document.getElementById('tag-selector-container') ? '找到' : '未找到');
    console.log('open-tag-filter-btn 按钮:', document.getElementById('open-tag-filter-btn') ? '找到' : '未找到');
    console.log('confirm-selection-btn 按钮:', document.getElementById('confirm-selection-btn') ? '找到' : '未找到');
    console.log('cancel-selection-btn 按钮:', document.getElementById('cancel-selection-btn') ? '找到' : '未找到');
    
    if (accountListTagSelector) {
        console.log('TagSelector 容器:', accountListTagSelector.container ? '找到' : '未找到');
        console.log('TagSelector 选项:', accountListTagSelector.options);
        console.log('TagSelector 已选择标签:', accountListTagSelector.getSelectedTags ? accountListTagSelector.getSelectedTags() : '方法不存在');
    }
    console.log('========================');
}

// 强制初始化标签选择器（用于调试）
function forceInitializeTagSelector() {
    console.log('强制初始化标签选择器...');
    
    const listPageSelector = document.getElementById('list-page-tag-selector');
    const modalElement = listPageSelector ? listPageSelector.querySelector('#tagSelectorModal') : null;
    const containerElement = modalElement ? modalElement.querySelector('#tag-selector-container') : null;
    
    console.log('强制初始化 - 容器元素:', listPageSelector ? '找到' : '未找到');
    console.log('强制初始化 - 模态框元素:', modalElement ? '找到' : '未找到');
    console.log('强制初始化 - 容器元素:', containerElement ? '找到' : '未找到');
    console.log('强制初始化 - TagSelector可用:', typeof TagSelector !== 'undefined');
    
    if (typeof TagSelector !== 'undefined' && modalElement && containerElement) {
        try {
            console.log('强制创建TagSelector实例...');
            accountListTagSelector = new TagSelector('tag-selector-container', {
                allowMultiple: true,
                allowCreate: true,
                allowSearch: true,
                allowCategoryFilter: true
            });
            console.log('强制创建成功，accountListTagSelector:', accountListTagSelector ? '已创建' : '未创建');
            
            // 绑定按钮事件
            const openBtn = document.getElementById('open-tag-filter-btn');
            if (openBtn) {
                openBtn.addEventListener('click', function(e) {
                    console.log('强制绑定的按钮被点击');
                    e.preventDefault();
                    openTagSelector();
                });
                console.log('强制绑定打开按钮成功');
            }
            
            return true;
        } catch (error) {
            console.error('强制创建失败:', error);
            return false;
        }
    } else {
        console.error('强制初始化失败：缺少必需元素');
        return false;
    }
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
window.debugTagSelector = debugTagSelector;
window.forceInitializeTagSelector = forceInitializeTagSelector;
window.openTagSelector = openTagSelector;
window.closeTagSelector = closeTagSelector;
window.confirmTagSelection = confirmTagSelection;
