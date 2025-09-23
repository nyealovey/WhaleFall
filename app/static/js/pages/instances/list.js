/**
 * 实例管理页面JavaScript
 * 处理实例的连接测试、删除、批量操作等功能
 */

// 全局变量
let deleteInstanceId = null;
let tagSelector = null;

// 页面加载完成后初始化
document.addEventListener('DOMContentLoaded', function() {
    initializeTagSelector();
    setupEventListeners();
});

// 初始化标签选择器
function initializeTagSelector() {
    // 立即检查元素
    const listPageSelector = document.getElementById('list-page-tag-selector');
    
    if (listPageSelector) {
        const modalElement = listPageSelector.querySelector('#tagSelectorModal');
        
        if (modalElement) {
            // 在模态框内部查找容器元素
            const containerElement = modalElement.querySelector('#tag-selector-container');
            
            if (containerElement) {
                initializeTagSelectorComponent(modalElement, containerElement);
            } else {
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
        tagSelector = new TagSelector('tag-selector-container', {
            allowMultiple: true,
            allowCreate: true,
            allowSearch: true,
            allowCategoryFilter: true
        });
        
        // 绑定打开标签选择器按钮
        const openBtn = document.getElementById('open-tag-filter-btn');
        if (openBtn) {
            openBtn.addEventListener('click', function() {
                if (typeof openTagSelector === 'function') {
                    openTagSelector();
                } else {
                    console.error('openTagSelector函数未定义');
                }
            });
        } else {
            console.error('找不到open-tag-filter-btn按钮');
        }
        
        // 绑定确认选择按钮
        const confirmBtn = document.getElementById('confirm-tag-selection');
        if (confirmBtn) {
            confirmBtn.addEventListener('click', confirmTagSelection);
        } else {
            console.error('找不到confirm-tag-selection按钮');
        }
        
        // 预填充已选择的标签
        const selectedTagNames = document.getElementById('selected-tag-names').value;
        if (selectedTagNames) {
            const tagNames = selectedTagNames.split(',').filter(name => name.trim());
            setTimeout(() => {
                const allTags = tagSelector.availableTags;
                const currentTagIds = allTags.filter(tag => tagNames.includes(tag.name)).map(tag => tag.id);
                tagSelector.setSelectedTags(currentTagIds);
                updateSelectedTagsPreview(tagSelector.getSelectedTags());
            }, 500);
        }
    } else {
        console.error('初始化失败:');
        console.error('- TagSelector可用:', typeof TagSelector !== 'undefined');
        console.error('- 模态框元素:', modalElement ? '找到' : '未找到');
        console.error('- 容器元素:', containerElement ? '找到' : '未找到');
    }
}

// 设置事件监听器
function setupEventListeners() {
    // 删除确认按钮
    const confirmDeleteBtn = document.getElementById('confirmDelete');
    if (confirmDeleteBtn) {
        confirmDeleteBtn.addEventListener('click', handleDeleteConfirm);
    }

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

// 测试连接
function testConnection(instanceId) {
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

    fetch(`/instances/api/instances/${instanceId}/test`, {
        method: 'GET',
        headers: headers
    })
    .then(response => response.json())
    .then(data => {
        if (data.message) {
            showAlert('success', data.message);
        } else if (data.error) {
            showAlert('danger', data.error);
        }
    })
    .catch(error => {
        showAlert('danger', '测试连接失败');
    })
    .finally(() => {
        btn.innerHTML = originalHtml;
        btn.disabled = false;
    });
}

// 删除实例
function deleteInstance(instanceId, instanceName) {
    deleteInstanceId = instanceId;
    const nameElement = document.getElementById('deleteInstanceName');
    if (nameElement) {
        nameElement.textContent = instanceName;
    }
    new bootstrap.Modal(document.getElementById('deleteModal')).show();
}

// 处理删除确认
function handleDeleteConfirm() {
    if (deleteInstanceId) {
        const csrfToken = getCSRFToken();

        fetch(`/instances/${deleteInstanceId}/delete`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrfToken
            }
        })
        .then(response => response.json())
        .then(data => {
            if (data.message) {
                showAlert('success', data.message);
                setTimeout(() => location.reload(), 1000);
            } else if (data.error) {
                showAlert('danger', data.error);
            }
        })
        .catch(error => {
            showAlert('danger', '删除失败');
        });
    }
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

    fetch('/instances/batch-delete', {
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

    fetch('/instances/batch-create', {
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

        fetch('/instances/batch-create', {
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
    if (tagSelector) {
        const selectedTags = tagSelector.getSelectedTags();
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
    if (tagSelector) {
        const tag = tagSelector.availableTags.find(t => t.name === tagName);
        if (tag) {
            tagSelector.toggleTag(tag.id);
            const selectedTags = tagSelector.getSelectedTags();
            updateSelectedTagsPreview(selectedTags);
        }
    }
}

// 工具函数
function getCSRFToken() {
    return document.querySelector('meta[name="csrf-token"]')?.getAttribute('content') ||
           document.querySelector('input[name="csrf_token"]')?.value || '';
}
