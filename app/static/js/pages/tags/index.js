/**
 * 标签管理页面JavaScript
 * 处理标签删除、搜索、筛选、状态切换等功能
 */

// 全局变量
window.currentTags = window.currentTags || [];
window.currentFilters = window.currentFilters || {};

// 页面加载完成后初始化
document.addEventListener('DOMContentLoaded', function() {
    initializeTagsPage();
});

// 初始化标签管理页面
function initializeTagsPage() {
    initializeEventHandlers();
    initializeSearchForm();
    initializeTagActions();
    initializeBatchAssignModal();
    console.log('标签管理页面已加载');
}

// 初始化事件处理器
function initializeEventHandlers() {
    // 搜索表单提交
    const searchForm = document.querySelector('form[method="GET"]');
    if (searchForm) {
        searchForm.addEventListener('submit', function(e) {
            handleSearchSubmit(e, this);
        });
    }

    // 清除搜索
    const clearSearchBtn = document.getElementById('clearSearch');
    if (clearSearchBtn) {
        clearSearchBtn.addEventListener('click', function() {
            clearSearch();
        });
    }

    // 批量操作
    const selectAllCheckbox = document.getElementById('selectAll');
    const tagCheckboxes = document.querySelectorAll('input[name="tag_ids"]');
    const batchActions = document.querySelector('.batch-actions');

    if (selectAllCheckbox) {
        selectAllCheckbox.addEventListener('change', function() {
            toggleAllTags(this.checked);
        });
    }

    tagCheckboxes.forEach(checkbox => {
        checkbox.addEventListener('change', function() {
            updateTagSelection(this.value, this.checked);
        });
    });

    // 批量操作按钮
    const batchDeleteBtn = document.getElementById('batchDelete');
    const batchActivateBtn = document.getElementById('batchActivate');
    const batchDeactivateBtn = document.getElementById('batchDeactivate');

    if (batchDeleteBtn) {
        batchDeleteBtn.addEventListener('click', function() {
            performBatchAction('delete');
        });
    }

    if (batchActivateBtn) {
        batchActivateBtn.addEventListener('click', function() {
            performBatchAction('activate');
        });
    }

    if (batchDeactivateBtn) {
        batchDeactivateBtn.addEventListener('click', function() {
            performBatchAction('deactivate');
        });
    }
}

// 初始化搜索表单
function initializeSearchForm() {
    const searchInput = document.querySelector('input[name="search"]');
    const categorySelect = document.querySelector('select[name="category"]');
    const statusSelect = document.querySelector('select[name="status"]');

    // 实时搜索
    if (searchInput) {
        searchInput.addEventListener('input', function() {
            debounceSearch();
        });
    }

    // 分类筛选
    if (categorySelect) {
        categorySelect.addEventListener('change', function() {
            debounceSearch();
        });
    }

    // 状态筛选
    if (statusSelect) {
        statusSelect.addEventListener('change', function() {
            debounceSearch();
        });
    }
}

// 初始化标签操作
function initializeTagActions() {
    // 标签状态切换
    const statusToggles = document.querySelectorAll('.tag-status-toggle');
    statusToggles.forEach(toggle => {
        toggle.addEventListener('click', function() {
            const tagId = this.getAttribute('data-tag-id');
            const currentStatus = this.getAttribute('data-status');
            const newStatus = currentStatus === 'active' ? 'inactive' : 'active';
            
            if (tagId) {
                toggleTagStatus(tagId, newStatus);
            }
        });
    });
}

// 处理搜索提交
function handleSearchSubmit(event, form) {
    const searchInput = form.querySelector('input[name="search"]');
    
    // 基本验证
    if (searchInput && searchInput.value.trim().length > 0 && searchInput.value.trim().length < 2) {
        event.preventDefault();
        showAlert('warning', '搜索关键词至少需要2个字符');
        return false;
    }
    
    // 显示加载状态
    const submitBtn = form.querySelector('button[type="submit"]');
    if (submitBtn) {
        showLoadingState(submitBtn, '搜索中...');
    }
    
    return true;
}

// 防抖搜索
function debounceSearch() {
    clearTimeout(window.searchTimeout);
    window.searchTimeout = setTimeout(function() {
        const form = document.querySelector('form[method="GET"]');
        if (form) {
            form.submit();
        }
    }, 500);
}

// 清除搜索
function clearSearch() {
    const searchInput = document.querySelector('input[name="search"]');
    const categorySelect = document.querySelector('select[name="category"]');
    const statusSelect = document.querySelector('select[name="status"]');
    
    if (searchInput) searchInput.value = '';
    if (categorySelect) categorySelect.value = '';
    if (statusSelect) statusSelect.value = 'all';
    
    // 提交表单
    const form = document.querySelector('form[method="GET"]');
    if (form) {
        form.submit();
    }
}

// 删除标签
function deleteTag(tagId, tagName) {
    // 设置删除确认对话框的内容
    const deleteTagNameElement = document.getElementById('deleteTagName');
    const deleteFormElement = document.getElementById('deleteForm');
    
    if (deleteTagNameElement) {
        deleteTagNameElement.textContent = tagName;
    }
    
    if (deleteFormElement) {
        // 使用正确的URL构建方式，避免字符串替换导致的IP地址错误
        const baseUrl = window.location.origin;
        deleteFormElement.action = `${baseUrl}/tags/delete/${tagId}`;
    }
    
    // 显示删除确认模态框
    const deleteModal = new bootstrap.Modal(document.getElementById('deleteModal'));
    deleteModal.show();
}

// 处理删除按钮点击事件
function handleDeleteClick(event) {
    const button = event.target.closest('button[data-tag-id]');
    if (button) {
        const tagId = button.getAttribute('data-tag-id');
        const tagName = button.getAttribute('data-tag-name');
        deleteTag(tagId, tagName);
    }
}

// 切换所有标签选择
function toggleAllTags(checked) {
    const tagCheckboxes = document.querySelectorAll('input[name="tag_ids"]');
    
    tagCheckboxes.forEach(checkbox => {
        checkbox.checked = checked;
        updateTagSelection(checkbox.value, checked);
    });
}

// 更新标签选择
function updateTagSelection(tagId, selected) {
    if (selected) {
        if (!window.currentTags.includes(tagId)) {
            window.currentTags.push(tagId);
        }
    } else {
        const index = window.currentTags.indexOf(tagId);
        if (index > -1) {
            window.currentTags.splice(index, 1);
        }
    }
    
    updateBatchActions();
}

// 更新批量操作显示
function updateBatchActions() {
    const batchActions = document.querySelector('.batch-actions');
    const selectionCounter = document.querySelector('.selection-counter');
    
    if (window.currentTags.length > 0) {
        if (batchActions) {
            batchActions.classList.add('show');
        }
        if (selectionCounter) {
            selectionCounter.textContent = `已选择 ${window.currentTags.length} 个标签`;
        }
    } else {
        if (batchActions) {
            batchActions.classList.remove('show');
        }
    }
}

// 执行批量操作
function performBatchAction(action) {
    if (window.currentTags.length === 0) {
        showAlert('warning', '请选择要操作的标签');
        return;
    }
    
    const actionNames = {
        'delete': '删除',
        'activate': '激活',
        'deactivate': '停用'
    };
    
    if (confirm(`确定要${actionNames[action]}选中的 ${window.currentTags.length} 个标签吗？`)) {
        const tagIds = window.currentTags.slice();
        
        fetch('/tags/api/batch_action', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCSRFToken()
            },
            body: JSON.stringify({
                action: action,
                tag_ids: tagIds
            })
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                showAlert('success', data.message);
                location.reload();
            } else {
                showAlert('error', data.message);
            }
        })
        .catch(error => {
            console.error('Error:', error);
            showAlert('error', '批量操作失败');
        });
    }
}

// 切换标签状态
function toggleTagStatus(tagId, newStatus) {
    showLoadingState(document.querySelector(`[data-tag-id="${tagId}"]`), '更新中...');
    
    fetch('/tags/api/toggle_status', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCSRFToken()
        },
        body: JSON.stringify({
            tag_id: tagId,
            status: newStatus
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showAlert('success', data.message);
            location.reload();
        } else {
            showAlert('error', data.message);
            // 恢复切换状态
            const toggle = document.querySelector(`[data-tag-id="${tagId}"]`);
            if (toggle) {
                const currentStatus = toggle.getAttribute('data-status');
                toggle.setAttribute('data-status', currentStatus);
            }
        }
    })
    .catch(error => {
        console.error('Error:', error);
        showAlert('error', '状态切换失败');
        // 恢复切换状态
        const toggle = document.querySelector(`[data-tag-id="${tagId}"]`);
        if (toggle) {
            const currentStatus = toggle.getAttribute('data-status');
            toggle.setAttribute('data-status', currentStatus);
        }
    })
    .finally(() => {
        hideLoadingState(document.querySelector(`[data-tag-id="${tagId}"]`), '切换');
    });
}

// 显示加载状态
function showLoadingState(element, text) {
    if (typeof element === 'string') {
        element = document.getElementById(element);
    }
    
    if (element) {
        element.innerHTML = `<i class="fas fa-spinner fa-spin me-2"></i>${text}`;
        element.disabled = true;
    }
}

// 隐藏加载状态
function hideLoadingState(element, originalText) {
    if (typeof element === 'string') {
        element = document.getElementById(element);
    }
    
    if (element) {
        element.innerHTML = originalText;
        element.disabled = false;
    }
}

// 获取CSRF令牌
function getCSRFToken() {
    const csrfInput = document.querySelector('input[name="csrf_token"]');
    return csrfInput ? csrfInput.value : '';
}

// 显示提示信息
function showAlert(type, message) {
    const alertDiv = document.createElement('div');
    alertDiv.className = `alert alert-${type === 'error' ? 'danger' : type} alert-dismissible fade show`;
    alertDiv.innerHTML = `
        <i class="fas fa-${getAlertIcon(type)} me-2"></i>
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    
    const container = document.querySelector('.container-fluid');
    if (container) {
        container.insertBefore(alertDiv, container.firstChild);
    }
    
    setTimeout(() => {
        alertDiv.remove();
    }, 5000);
}

// 获取提示图标
function getAlertIcon(type) {
    switch (type) {
        case 'success': return 'check-circle';
        case 'danger': return 'exclamation-triangle';
        case 'warning': return 'exclamation-triangle';
        case 'info': return 'info-circle';
        default: return 'info-circle';
    }
}

// 显示成功提示
function showSuccessAlert(message) {
    showAlert('success', message);
}

// 显示警告提示
function showWarningAlert(message) {
    showAlert('warning', message);
}

// 显示错误提示
function showErrorAlert(message) {
    showAlert('error', message);
}

// 键盘快捷键
function initializeKeyboardShortcuts() {
    document.addEventListener('keydown', function(e) {
        // Ctrl+F 聚焦搜索框
        if (e.ctrlKey && e.key === 'f') {
            e.preventDefault();
            const searchInput = document.querySelector('input[name="search"]');
            if (searchInput) {
                searchInput.focus();
            }
        }
        
        // Escape 清除搜索
        if (e.key === 'Escape') {
            const searchInput = document.querySelector('input[name="search"]');
            if (searchInput && searchInput.value) {
                clearSearch();
            }
        }
        
        // Ctrl+A 全选
        if (e.ctrlKey && e.key === 'a' && e.target.tagName !== 'INPUT' && e.target.tagName !== 'TEXTAREA') {
            e.preventDefault();
            toggleAllTags(true);
        }
    });
}

// 初始化键盘快捷键
initializeKeyboardShortcuts();

// 导出标签数据
function exportTags(format = 'csv') {
    const searchParams = new URLSearchParams(window.location.search);
    searchParams.append('export', format);
    
    const url = `${window.location.pathname}?${searchParams.toString()}`;
    window.open(url, '_blank');
}

// 页面加载完成后绑定事件监听器
document.addEventListener('DOMContentLoaded', function() {
    // 绑定删除按钮点击事件
    document.addEventListener('click', handleDeleteClick);
});

// 导出函数供全局使用
window.deleteTag = deleteTag;
window.toggleTagStatus = toggleTagStatus;
window.performBatchAction = performBatchAction;
window.clearSearch = clearSearch;
window.exportTags = exportTags;
window.showAlert = showAlert;
window.showSuccessAlert = showSuccessAlert;
window.showWarningAlert = showWarningAlert;
window.showErrorAlert = showErrorAlert;

// 批量分配模态框初始化
function initializeBatchAssignModal() {
    const batchAssignModal = document.getElementById('batchAssignModal');
    if (batchAssignModal) {
        batchAssignModal.addEventListener('show.bs.modal', function () {
            loadInstancesForBatchAssign();
            loadTagsForBatchAssign();
        });

        const batchAssignSaveBtn = document.getElementById('batchAssignSave');
        if (batchAssignSaveBtn) {
            batchAssignSaveBtn.addEventListener('click', handleBatchAssignSave);
        }
    }
}

// 加载实例列表到批量分配模态框
async function loadInstancesForBatchAssign() {
    const instanceListContainer = document.querySelector('#batchAssignModal .instance-list-container');
    if (!instanceListContainer) return;

    instanceListContainer.innerHTML = '<p class="text-center"><i class="fas fa-spinner fa-spin"></i> 加载实例中...</p>';

    try {
        const response = await fetch('/tags/api/instances');
        const data = await response.json();
        console.log('Instances data:', data); // 调试信息

        if (data.success) {
            if (data.instances.length > 0) {
                // 按数据库类型分组实例
                const groupedInstances = groupInstancesByDbType(data.instances);
                let html = '<div class="instance-groups">';
                
                // 生成分组HTML
                Object.keys(groupedInstances).forEach(dbType => {
                    const dbTypeName = getDbTypeDisplayName(dbType);
                    const instances = groupedInstances[dbType];
                    const groupId = `instance-group-${dbType}`;
                    
                    html += `
                        <div class="instance-group mb-3">
                            <div class="instance-group-header" onclick="toggleInstanceGroup('${groupId}')" style="cursor: pointer;">
                                <h6 class="mb-0 d-flex align-items-center">
                                    <i class="fas fa-chevron-right me-2 instance-group-icon" id="${groupId}-icon"></i>
                                    <span class="badge bg-secondary me-2">${dbTypeName}</span>
                                    <small class="text-muted">(${instances.length} 个实例)</small>
                                </h6>
                            </div>
                            <div class="instance-group-content collapse" id="${groupId}">
                                <div class="list-group mt-2">
                    `;
                    
                    instances.forEach(instance => {
                        html += `
                            <label class="list-group-item">
                                <input class="form-check-input me-1" type="checkbox" value="${instance.id}" data-instance-name="${instance.name}">
                                ${instance.name} (${instance.host}:${instance.port})
                            </label>
                        `;
                    });
                    
                    html += `
                                </div>
                            </div>
                        </div>
                    `;
                });
                
                html += '</div>';
                instanceListContainer.innerHTML = html;
            } else {
                instanceListContainer.innerHTML = '<p class="text-muted text-center">没有可用的实例。</p>';
            }
        } else {
            instanceListContainer.innerHTML = `<p class="text-danger">加载实例失败: ${data.error}</p>`;
            showErrorAlert(`加载实例失败: ${data.error}`);
        }
    } catch (error) {
        console.error('Error loading instances:', error);
        instanceListContainer.innerHTML = '<p class="text-danger">加载实例失败，请检查网络或服务器日志。</p>';
        showErrorAlert('加载实例失败，请检查网络或服务器日志。');
    }
}

// 按数据库类型分组实例
function groupInstancesByDbType(instances) {
    const grouped = {};
    instances.forEach(instance => {
        if (!grouped[instance.db_type]) {
            grouped[instance.db_type] = [];
        }
        grouped[instance.db_type].push(instance);
    });
    
    // 对每个数据库类型的实例按名称排序
    Object.keys(grouped).forEach(dbType => {
        grouped[dbType].sort((a, b) => a.name.localeCompare(b.name));
    });
    
    return grouped;
}

// 获取数据库类型显示名称
function getDbTypeDisplayName(dbType) {
    const dbTypeNames = {
        'mysql': 'MySQL',
        'postgresql': 'PostgreSQL',
        'sqlserver': 'SQL Server',
        'oracle': 'Oracle'
    };
    return dbTypeNames[dbType] || dbType.toUpperCase();
}

// 切换实例分组展开/合拢
function toggleInstanceGroup(groupId) {
    const content = document.getElementById(groupId);
    const icon = document.getElementById(`${groupId}-icon`);
    
    if (content.classList.contains('show')) {
        content.classList.remove('show');
        icon.classList.remove('fa-chevron-down');
        icon.classList.add('fa-chevron-right');
    } else {
        content.classList.add('show');
        icon.classList.remove('fa-chevron-right');
        icon.classList.add('fa-chevron-down');
    }
}

// 加载标签列表到批量分配模态框
async function loadTagsForBatchAssign() {
    const tagListContainer = document.querySelector('#batchAssignModal .tag-list-container');
    if (!tagListContainer) return;

    tagListContainer.innerHTML = '<p class="text-center"><i class="fas fa-spinner fa-spin"></i> 加载标签中...</p>';

    try {
        const response = await fetch('/tags/api/all_tags'); // 获取所有标签，包括非活跃的
        const data = await response.json();
        console.log('Tags data:', data); // 调试信息

        if (data.success) {
            if (data.tags.length > 0) {
                // 按分类分组标签
                const groupedTags = groupTagsByCategory(data.tags);
                let html = '<div class="tag-groups">';
                
                // 生成分组HTML
                Object.keys(groupedTags).forEach(category => {
                    const categoryName = getCategoryDisplayName(category);
                    const tags = groupedTags[category];
                    const groupId = `tag-group-${category}`;
                    
                    html += `
                        <div class="tag-group mb-3">
                            <div class="tag-group-header" onclick="toggleTagGroup('${groupId}')" style="cursor: pointer;">
                                <h6 class="mb-0 d-flex align-items-center">
                                    <i class="fas fa-chevron-right me-2 tag-group-icon" id="${groupId}-icon"></i>
                                    <span class="badge bg-secondary me-2">${categoryName}</span>
                                    <small class="text-muted">(${tags.length} 个标签)</small>
                                </h6>
                            </div>
                            <div class="tag-group-content collapse" id="${groupId}">
                                <div class="list-group mt-2">
                    `;
                    
                    tags.forEach(tag => {
                        html += `
                            <label class="list-group-item">
                                <input class="form-check-input me-1" type="checkbox" value="${tag.id}" data-tag-name="${tag.display_name}">
                                <span class="badge bg-${tag.color} me-2">${tag.display_name}</span>
                                <small class="text-muted">(${tag.name})</small>
                            </label>
                        `;
                    });
                    
                    html += `
                                </div>
                            </div>
                        </div>
                    `;
                });
                
                html += '</div>';
                tagListContainer.innerHTML = html;
            } else {
                tagListContainer.innerHTML = '<p class="text-muted text-center">没有可用的标签。</p>';
            }
        } else {
            tagListContainer.innerHTML = `<p class="text-danger">加载标签失败: ${data.error}</p>`;
            showErrorAlert(`加载标签失败: ${data.error}`);
        }
    } catch (error) {
        console.error('Error loading tags:', error);
        tagListContainer.innerHTML = '<p class="text-danger">加载标签失败，请检查网络或服务器日志。</p>';
        showErrorAlert('加载标签失败，请检查网络或服务器日志。');
    }
}

// 按分类分组标签
function groupTagsByCategory(tags) {
    const grouped = {};
    tags.forEach(tag => {
        if (!grouped[tag.category]) {
            grouped[tag.category] = [];
        }
        grouped[tag.category].push(tag);
    });
    
    // 对每个分类内的标签按sort_order和name排序
    Object.keys(grouped).forEach(category => {
        grouped[category].sort((a, b) => {
            if (a.sort_order !== b.sort_order) {
                return a.sort_order - b.sort_order;
            }
            return a.name.localeCompare(b.name);
        });
    });
    
    return grouped;
}

// 获取分类显示名称
function getCategoryDisplayName(category) {
    const categoryNames = {
        'location': '地区标签',
        'company_type': '公司类型',
        'environment': '环境标签',
        'architecture': '架构类型',
        'custom': '自定义标签'
    };
    return categoryNames[category] || category;
}

// 切换标签分组展开/合拢
function toggleTagGroup(groupId) {
    const content = document.getElementById(groupId);
    const icon = document.getElementById(`${groupId}-icon`);
    
    if (content.classList.contains('show')) {
        content.classList.remove('show');
        icon.classList.remove('fa-chevron-down');
        icon.classList.add('fa-chevron-right');
    } else {
        content.classList.add('show');
        icon.classList.remove('fa-chevron-right');
        icon.classList.add('fa-chevron-down');
    }
}

// 处理批量分配保存按钮点击事件
async function handleBatchAssignSave() {
    const selectedInstanceIds = Array.from(document.querySelectorAll('#batchAssignModal .instance-groups input[type="checkbox"]:checked'))
        .map(checkbox => checkbox.value);
    const selectedTagIds = Array.from(document.querySelectorAll('#batchAssignModal .tag-groups input[type="checkbox"]:checked'))
        .map(checkbox => checkbox.value);

    if (selectedInstanceIds.length === 0) {
        showWarningAlert('请至少选择一个实例进行分配。');
        return;
    }
    if (selectedTagIds.length === 0) {
        showWarningAlert('请至少选择一个标签进行分配。');
        return;
    }

    showLoadingState('batchAssignSave', '分配中...');

    try {
        const response = await fetch('/tags/api/batch_assign_tags', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCSRFToken()
            },
            body: JSON.stringify({
                instance_ids: selectedInstanceIds,
                tag_ids: selectedTagIds
            })
        });
        const data = await response.json();

        if (data.success) {
            showSuccessAlert(data.message);
            const batchAssignModal = bootstrap.Modal.getInstance(document.getElementById('batchAssignModal'));
            if (batchAssignModal) batchAssignModal.hide();
            location.reload(); // 重新加载页面以显示更新后的标签分配
        } else {
            showErrorAlert(`批量分配失败: ${data.error}`);
        }
    } catch (error) {
        console.error('Error during batch assignment:', error);
        showErrorAlert('批量分配失败，请检查网络或服务器日志。');
    } finally {
        hideLoadingState('batchAssignSave', '保存');
    }
}
