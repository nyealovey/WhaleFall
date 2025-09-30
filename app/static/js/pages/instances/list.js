/**
 * 实例管理页面JavaScript
 * 处理实例的连接测试、批量操作等功能
 */

// 全局变量
let listPageTagSelector = null;

// 页面加载完成后初始化
document.addEventListener('DOMContentLoaded', function() {
    // 如果TagSelector类还没有加载，等待一下
    if (typeof TagSelector === 'undefined') {
        setTimeout(() => {
            initializeInstanceListTagSelector();
        }, 500);
    } else {
        try {
            if (typeof initializeInstanceListTagSelector === 'function') {
                initializeInstanceListTagSelector();
            }
        } catch (error) {
            console.error('initializeInstanceListTagSelector 调用失败:', error);
        }
    }
    
    setupEventListeners();
    loadInstanceTotalSizes();
});

// 打开标签选择器
function openTagSelector() {
    const modal = new bootstrap.Modal(document.getElementById('tagSelectorModal'));
    modal.show();
}

// 关闭标签选择器
function closeTagSelector() {
    const modal = bootstrap.Modal.getInstance(document.getElementById('tagSelectorModal'));
    if (modal) {
        modal.hide();
    }
}

// 加载实例总大小
async function loadInstanceTotalSizes() {
    try {
        const sizeElements = document.querySelectorAll('.instance-total-size');
        
        for (const element of sizeElements) {
            const instanceId = element.getAttribute('data-instance-id');
            if (!instanceId) continue;
            
            try {
                const response = await fetch(`/storage-sync/instances/${instanceId}/database-sizes/total`, {
                    method: 'GET',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': getCSRFToken()
                    }
                });
                
                if (response.ok) {
                    const data = await response.json();
                    if (data.success && data.total_size_mb !== undefined) {
                        // API返回的是MB，需要转换为字节再格式化
                        const totalSizeBytes = data.total_size_mb * 1024 * 1024;
                        element.innerHTML = `<small class="text-success">${formatSize(totalSizeBytes)}</small>`;
                    } else {
                        element.innerHTML = '<small class="text-muted">暂无数据</small>';
                    }
                } else {
                    element.innerHTML = '<small class="text-muted">加载失败</small>';
                }
            } catch (error) {
                console.error(`加载实例 ${instanceId} 总大小失败:`, error);
                element.innerHTML = '<small class="text-muted">加载失败</small>';
            }
        }
    } catch (error) {
        console.error('加载实例总大小失败:', error);
    }
}

// 格式化文件大小 - 统一使用GB单位，保留3位小数
function formatSize(bytes) {
    if (bytes === 0) return '0.000 GB';
    
    // 将字节转换为GB
    const gb = bytes / (1024 * 1024 * 1024);
    
    return gb.toFixed(3) + ' GB';
}

// 初始化标签选择器
function initializeInstanceListTagSelector() {
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
        console.error('initializeInstanceListTagSelector 函数执行出错:', error);
    }
}

// 初始化标签选择器组件
function initializeTagSelectorComponent(modalElement, containerElement) {
    if (typeof TagSelector !== 'undefined' && modalElement && containerElement) {
        try {
            // 初始化标签选择器
            listPageTagSelector = new TagSelector('tag-selector-container', {
                allowMultiple: true,
                allowCreate: true,
                allowSearch: true,
                allowCategoryFilter: true
            });

            // 等待TagSelector完全初始化
            setTimeout(() => {
                if (listPageTagSelector && listPageTagSelector.container) {
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
    if (!listPageTagSelector) {
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
                    if (listPageTagSelector) {
                        listPageTagSelector.rebindModalButtons();
                    }
                }, 100);
            } catch (error) {
                console.error('打开标签选择器时出错:', error);
                showAlert('danger', '打开标签选择器失败: ' + error.message);
            }
        });
    }

    // 监听TagSelector的确认事件
    if (listPageTagSelector.container) {
        listPageTagSelector.container.addEventListener('tagSelectionConfirmed', function(event) {
            const selectedTags = event.detail.selectedTags;
            updateSelectedTagsPreview(selectedTags);
            closeTagSelector();
        });

        // 监听TagSelector的取消事件
        listPageTagSelector.container.addEventListener('tagSelectionCancelled', function(event) {
            closeTagSelector();
        });
    }

    // 预填充已选择的标签
    const selectedTagNames = document.getElementById('selected-tag-names');
    if (selectedTagNames && selectedTagNames.value) {
        setTimeout(() => {
            if (listPageTagSelector) {
                const tagNames = selectedTagNames.value.split(',').filter(name => name.trim());
                // 这里需要根据标签名称找到对应的ID，暂时跳过
            }
        }, 500);
    }
}

// 设置事件监听器
function setupEventListeners() {
    // 批量操作相关
    const selectAllCheckbox = document.getElementById('selectAll');
    if (selectAllCheckbox) {
        selectAllCheckbox.addEventListener('change', toggleSelectAll);
    }

    const instanceCheckboxes = document.querySelectorAll('.instance-checkbox');
    instanceCheckboxes.forEach(checkbox => {
        checkbox.addEventListener('change', updateBatchButtons);
    });

    // 上传方式切换
    const fileUploadRadio = document.getElementById('fileUpload');
    const jsonInputRadio = document.getElementById('jsonInput');
    const fileUploadArea = document.getElementById('fileUploadArea');
    const jsonInputArea = document.getElementById('jsonInputArea');

    if (fileUploadRadio && fileUploadArea) {
        fileUploadRadio.addEventListener('change', function() {
            if (this.checked) {
                fileUploadArea.style.display = 'block';
                if (jsonInputArea) jsonInputArea.style.display = 'none';
            }
        });
    }

    if (jsonInputRadio && jsonInputArea) {
        jsonInputRadio.addEventListener('change', function() {
            if (this.checked) {
                if (fileUploadArea) fileUploadArea.style.display = 'none';
                jsonInputArea.style.display = 'block';
            }
        });
    }
}

// 测试连接 - 使用新的连接管理API
function testConnection(instanceId) {
    const btn = event.target.closest('button');
    const originalHtml = btn.innerHTML;

    btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i>';
    btn.disabled = true;

    // 使用新的连接管理API
    connectionManager.testInstanceConnection(instanceId, {
        onSuccess: (data) => {
            showAlert('success', data.message || '连接测试成功');
        },
        onError: (error) => {
            showAlert('danger', error.error || '连接测试失败');
        }
    }).finally(() => {
        btn.innerHTML = originalHtml;
        btn.disabled = false;
    });
}

// 批量测试连接
function batchTestConnections() {
    const selectedInstances = getSelectedInstances();
    
    if (selectedInstances.length === 0) {
        showAlert('warning', '请先选择要测试的实例');
        return;
    }
    
    if (selectedInstances.length > 50) {
        showAlert('warning', '批量测试最多支持50个实例');
        return;
    }
    
    // 显示批量测试进度容器
    const progressContainer = document.getElementById('batch-test-progress');
    if (progressContainer) {
        progressContainer.style.display = 'block';
    }
    
    // 使用连接管理API进行批量测试
    connectionManager.batchTestConnections(selectedInstances, {
        onProgress: (result) => {
            if (progressContainer) {
                connectionManager.showBatchTestProgress(result, 'batch-test-progress');
            }
        },
        onError: (error) => {
            showAlert('danger', error.error || '批量测试失败');
        }
    });
}

// 获取选中的实例ID列表
function getSelectedInstances() {
    const checkboxes = document.querySelectorAll('input[name="instance_ids"]:checked');
    return Array.from(checkboxes).map(checkbox => parseInt(checkbox.value));
}

// 同步容量
function syncCapacity(instanceId, instanceName) {
    const btn = event.target.closest('button');
    const originalHtml = btn.innerHTML;

    btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i>';
    btn.disabled = true;

    // 获取CSRF token
    const csrfToken = getCSRFToken();

    const headers = {
        'Content-Type': 'application/json',
    };

    if (csrfToken) {
        headers['X-CSRFToken'] = csrfToken;
    }

    // 记录操作开始日志
    logUserAction('开始同步实例容量', {
        operation: 'sync_instance_capacity',
        instance_id: instanceId,
        instance_name: instanceName
    });

    fetch(`/storage-sync/instances/${instanceId}/sync-capacity`, {
        method: 'POST',
        headers: headers
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            // 记录成功日志
            logUserAction('同步实例容量成功', {
                operation: 'sync_instance_capacity',
                instance_id: instanceId,
                instance_name: instanceName,
                result: 'success',
                message: data.message,
                data: data.data
            });
            
            showAlert('success', data.message);
            
            // 刷新页面以更新容量显示
            setTimeout(() => {
                location.reload();
            }, 1500);
        } else {
            // 记录失败日志
            logError('同步实例容量失败', {
                operation: 'sync_instance_capacity',
                instance_id: instanceId,
                instance_name: instanceName,
                result: 'failed',
                error: data.error
            });
            showAlert('danger', data.error);
        }
    })
    .catch(error => {
        // 记录异常日志
        logErrorWithContext(error, '同步实例容量异常', {
            operation: 'sync_instance_capacity',
            instance_id: instanceId,
            instance_name: instanceName,
            result: 'exception'
        });
        showAlert('danger', '同步容量失败');
    })
    .finally(() => {
        btn.innerHTML = originalHtml;
        btn.disabled = false;
    });
}



// 显示提示信息
function showAlert(type, message) {
    const alertDiv = document.createElement('div');
    alertDiv.className = `alert alert-${type} alert-dismissible fade show`;
    alertDiv.innerHTML = `
        <i class="fas fa-${type === 'success' ? 'check-circle' : 'exclamation-triangle'} me-2"></i>
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

// 批量操作功能
function toggleSelectAll() {
    const selectAllCheckbox = document.getElementById('selectAll');
    const instanceCheckboxes = document.querySelectorAll('.instance-checkbox');

    instanceCheckboxes.forEach(checkbox => {
        checkbox.checked = selectAllCheckbox.checked;
    });

    updateBatchButtons();
}

function updateBatchButtons() {
    const selectedCheckboxes = document.querySelectorAll('.instance-checkbox:checked');
    const batchDeleteBtn = document.getElementById('batchDeleteBtn');

    if (batchDeleteBtn) {
        if (selectedCheckboxes.length > 0) {
            batchDeleteBtn.disabled = false;
            batchDeleteBtn.textContent = `批量删除 (${selectedCheckboxes.length})`;
        } else {
            batchDeleteBtn.disabled = true;
            batchDeleteBtn.textContent = '批量删除';
        }
    }
}

function batchDelete() {
    const selectedCheckboxes = document.querySelectorAll('.instance-checkbox:checked');
    const instanceIds = Array.from(selectedCheckboxes).map(cb => parseInt(cb.value));

    if (instanceIds.length === 0) {
        showAlert('warning', '请选择要删除的实例');
        return;
    }

    if (!confirm(`确定要删除选中的 ${instanceIds.length} 个实例吗？此操作不可撤销！`)) {
        return;
    }

    // 记录操作开始日志
    logUserAction('开始批量删除实例', {
        operation: 'batch_delete_instances',
        instance_count: instanceIds.length,
        instance_ids: instanceIds
    });

    const btn = document.getElementById('batchDeleteBtn');
    const originalText = btn.textContent;

    btn.textContent = '删除中...';
    btn.disabled = true;

    const csrfToken = getCSRFToken();

    fetch('/instances/api/batch-delete', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': csrfToken
        },
        body: JSON.stringify({ instance_ids: instanceIds })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            // 记录成功日志
            logUserAction('批量删除实例成功', {
                operation: 'batch_delete_instances',
                instance_count: instanceIds.length,
                instance_ids: instanceIds,
                result: 'success',
                message: data.message
            });
            showAlert('success', data.message);
            setTimeout(() => location.reload(), 1000);
        } else {
            // 记录失败日志
            logError('批量删除实例失败', {
                operation: 'batch_delete_instances',
                instance_count: instanceIds.length,
                instance_ids: instanceIds,
                result: 'failed',
                error: data.error
            });
            showAlert('danger', data.error);
        }
    })
    .catch(error => {
        // 记录异常日志
        logErrorWithContext(error, '批量删除实例异常', {
            operation: 'batch_delete_instances',
            instance_count: instanceIds.length,
            instance_ids: instanceIds,
            result: 'exception'
        });
        showAlert('danger', '批量删除失败');
    })
    .finally(() => {
        btn.textContent = originalText;
        btn.disabled = true;
    });
}

// 批量创建相关功能
function showBatchCreateModal() {
    // 重置表单
    const csvFileInput = document.getElementById('csvFile');
    const batchInstancesDataInput = document.getElementById('batchInstancesData');
    const fileUploadRadio = document.getElementById('fileUpload');
    const fileUploadArea = document.getElementById('fileUploadArea');
    const jsonInputArea = document.getElementById('jsonInputArea');

    if (csvFileInput) csvFileInput.value = '';
    if (batchInstancesDataInput) batchInstancesDataInput.value = '';
    if (fileUploadRadio) fileUploadRadio.checked = true;
    if (fileUploadArea) fileUploadArea.style.display = 'block';
    if (jsonInputArea) jsonInputArea.style.display = 'none';

    new bootstrap.Modal(document.getElementById('batchCreateModal')).show();
}

function handleFileSelect(event) {
    const file = event.target.files[0];
    if (file) {
        // 验证文件类型
        if (!file.name.toLowerCase().endsWith('.csv')) {
            showAlert('warning', '请选择CSV格式文件');
            event.target.value = '';
            return;
        }

        // 显示文件信息
        const fileInfo = document.createElement('div');
        fileInfo.className = 'mt-2 text-muted file-info';
        fileInfo.innerHTML = `<i class="fas fa-file-csv me-1"></i>已选择文件: ${file.name} (${(file.size / 1024).toFixed(1)} KB)`;

        // 移除之前的文件信息
        const existingInfo = event.target.parentNode.querySelector('.file-info');
        if (existingInfo) {
            existingInfo.remove();
        }

        event.target.parentNode.appendChild(fileInfo);
    }
}

function submitBatchCreate() {
    const uploadMethod = document.querySelector('input[name="uploadMethod"]:checked');
    
    if (uploadMethod && uploadMethod.value === 'file') {
        submitFileUpload();
    } else {
        submitJsonInput();
    }
}

function submitFileUpload() {
    const fileInput = document.getElementById('csvFile');
    const file = fileInput.files[0];

    if (!file) {
        showAlert('warning', '请选择CSV文件');
        return;
    }

    const formData = new FormData();
    formData.append('file', file);

    const btn = document.querySelector('#batchCreateModal .btn-primary');
    const originalText = btn.textContent;

    btn.textContent = '创建中...';
    btn.disabled = true;

    const csrfToken = getCSRFToken();

    fetch('/instances/api/batch-create', {
        method: 'POST',
        headers: {
            'X-CSRFToken': csrfToken
        },
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showAlert('success', data.message);
            if (data.errors && data.errors.length > 0) {
                showAlert('warning', `部分实例创建失败：\n${data.errors.join('\n')}`);
            }
            // 关闭模态框
            const modal = bootstrap.Modal.getInstance(document.getElementById('batchCreateModal'));
            if (modal) modal.hide();
            setTimeout(() => location.reload(), 1000);
        } else {
            showAlert('danger', data.error);
        }
    })
    .catch(error => {
        showAlert('danger', '批量创建失败');
    })
    .finally(() => {
        btn.textContent = originalText;
        btn.disabled = false;
    });
}

function submitJsonInput() {
    const dataText = document.getElementById('batchInstancesData').value.trim();

    if (!dataText) {
        showAlert('warning', '请输入实例数据');
        return;
    }

    try {
        const instances = JSON.parse(dataText);

        if (!Array.isArray(instances)) {
            showAlert('warning', '实例数据必须是数组格式');
            return;
        }

        if (instances.length === 0) {
            showAlert('warning', '至少需要提供一个实例');
            return;
        }

        const btn = document.querySelector('#batchCreateModal .btn-primary');
        const originalText = btn.textContent;

        btn.textContent = '创建中...';
        btn.disabled = true;

        const csrfToken = getCSRFToken();

        fetch('/instances/api/batch-create', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrfToken
            },
            body: JSON.stringify({ instances: instances })
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                showAlert('success', data.message);
                if (data.errors && data.errors.length > 0) {
                    showAlert('warning', `部分实例创建失败：\n${data.errors.join('\n')}`);
                }
                // 关闭模态框
                const modal = bootstrap.Modal.getInstance(document.getElementById('batchCreateModal'));
                if (modal) modal.hide();
                setTimeout(() => location.reload(), 1000);
            } else {
                showAlert('danger', data.error);
            }
        })
        .catch(error => {
            showAlert('danger', '批量创建失败');
        })
        .finally(() => {
            btn.textContent = originalText;
            btn.disabled = false;
        });

    } catch (error) {
        showAlert('danger', 'JSON格式错误，请检查输入数据');
    }
}

// 标签选择器相关功能
function confirmTagSelection() {
    if (listPageTagSelector) {
        // 直接调用标签选择器的确认方法
        listPageTagSelector.confirmSelection();
        
        // 获取选中的标签并更新预览
        const selectedTags = listPageTagSelector.getSelectedTags();
        updateSelectedTagsPreview(selectedTags);
        closeTagSelector();
    }
}

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

function removeTagFromPreview(tagName) {
    if (listPageTagSelector) {
        const tag = listPageTagSelector.availableTags.find(t => t.name === tagName);
        if (tag) {
            listPageTagSelector.toggleTag(tag.id);
            const selectedTags = listPageTagSelector.getSelectedTags();
            updateSelectedTagsPreview(selectedTags);
        }
    }
}

// 导出到全局作用域
window.initializeInstanceListTagSelector = initializeInstanceListTagSelector;

// 工具函数
function getCSRFToken() {
    return document.querySelector('meta[name="csrf-token"]')?.getAttribute('content') ||
           document.querySelector('input[name="csrf_token"]')?.value || '';
}
