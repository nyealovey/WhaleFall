/**
 * 实例管理页面JavaScript
 * 处理实例的连接测试、批量操作等功能
 */

// 页面加载完成后初始化
document.addEventListener('DOMContentLoaded', function() {
    initializeTagFilter();
    setupEventListeners();
    loadInstanceTotalSizes();
    
    // 初始化批量操作按钮状态
    updateBatchButtons();
});

// 加载实例总大小
async function loadInstanceTotalSizes() {
    try {
        const sizeElements = document.querySelectorAll('.instance-total-size');
        
        for (const element of sizeElements) {
            const instanceId = element.getAttribute('data-instance-id');
            if (!instanceId) continue;
            
            try {
                const data = await http.get(`/database_stats/api/instances/${instanceId}/database-sizes/total`);
                
                if (data.success && data.total_size_mb !== undefined) {
                    // API返回的是MB，需要转换为字节再格式化
                    const totalSizeBytes = data.total_size_mb * 1024 * 1024;
                    element.innerHTML = `<small class="text-success">${formatSize(totalSizeBytes)}</small>`;
                } else {
                    element.innerHTML = '<small class="text-muted">暂无数据</small>';
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
            const form = document.getElementById('instance-filter-form');
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

// 初始化标签选择器
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
            toast.success(data.message || '连接测试成功');
        },
        onError: (error) => {
            toast.error(error.error || '连接测试失败');
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
        toast.warning('请先选择要测试的实例');
        return;
    }
    
    if (selectedInstances.length > 50) {
        toast.warning('批量测试最多支持50个实例');
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
            toast.error(error.error || '批量测试失败');
        }
    });
}

// 获取选中的实例ID列表
function getSelectedInstances() {
    const checkboxes = document.querySelectorAll('input.instance-checkbox:checked');
    return Array.from(checkboxes).map(checkbox => parseInt(checkbox.value));
}

// 同步容量
function syncCapacity(instanceId, instanceName) {
    const btn = event.target.closest('button');
    const originalHtml = btn.innerHTML;

    btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i>';
    btn.disabled = true;

    // 记录操作开始日志
    console.info('开始同步实例容量', {
        operation: 'sync_instance_capacity',
        instance_id: instanceId,
        instance_name: instanceName
    });

    http.post(`/storage_sync/api/instances/${instanceId}/sync-capacity`)
    .then(data => {
        if (data.success) {
            // 记录成功日志
            console.info('同步实例容量成功', {
                operation: 'sync_instance_capacity',
                instance_id: instanceId,
                instance_name: instanceName,
                result: 'success',
                message: data.message,
                data: data.data
            });
            
            toast.success(data.message);
            
            // 刷新页面以更新容量显示
            setTimeout(() => {
                location.reload();
            }, 1500);
        } else {
            // 记录失败日志
            console.error('同步实例容量失败', {
                operation: 'sync_instance_capacity',
                instance_id: instanceId,
                instance_name: instanceName,
                result: 'failed',
                error: data.error
            });
            toast.error(data.error);
        }
    })
    .catch(error => {
        // 记录异常日志
        console.error('同步实例容量异常', error, {
            operation: 'sync_instance_capacity',
            instance_id: instanceId,
            instance_name: instanceName,
            result: 'exception'
        });
        toast.error('同步容量失败');
    })
    .finally(() => {
        btn.innerHTML = originalHtml;
        btn.disabled = false;
    });
}



// 显示提示信息

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
    const batchTestBtn = document.getElementById('batchTestBtn');

    if (batchDeleteBtn) {
        if (selectedCheckboxes.length > 0) {
            batchDeleteBtn.disabled = false;
            batchDeleteBtn.textContent = `批量删除 (${selectedCheckboxes.length})`;
        } else {
            batchDeleteBtn.disabled = true;
            batchDeleteBtn.textContent = '批量删除';
        }
    }
    
    // 更新批量测试连接按钮状态
    if (batchTestBtn) {
        if (selectedCheckboxes.length > 0) {
            batchTestBtn.disabled = false;
            batchTestBtn.textContent = `批量测试连接 (${selectedCheckboxes.length})`;
        } else {
            batchTestBtn.disabled = true;
            batchTestBtn.textContent = '批量测试连接';
        }
    }
}

function batchDelete() {
    const selectedCheckboxes = document.querySelectorAll('.instance-checkbox:checked');
    const instanceIds = Array.from(selectedCheckboxes).map(cb => parseInt(cb.value));

    if (instanceIds.length === 0) {
        toast.warning('请选择要删除的实例');
        return;
    }

    if (!confirm(`确定要删除选中的 ${instanceIds.length} 个实例吗？此操作不可撤销！`)) {
        return;
    }

    // 记录操作开始日志
    console.info('开始批量删除实例', {
        operation: 'batch_delete_instances',
        instance_count: instanceIds.length,
        instance_ids: instanceIds
    });

    const btn = document.getElementById('batchDeleteBtn');
    const originalText = btn.textContent;

    btn.textContent = '删除中...';
    btn.disabled = true;

    http.post('/instances/api/batch-delete', { instance_ids: instanceIds })
    .then(data => {
        if (data.success) {
            // 记录成功日志
            console.info('批量删除实例成功', {
                operation: 'batch_delete_instances',
                instance_count: instanceIds.length,
                instance_ids: instanceIds,
                result: 'success',
                message: data.message
            });
            toast.success(data.message);
            setTimeout(() => location.reload(), 1000);
        } else {
            // 记录失败日志
            console.error('批量删除实例失败', {
                operation: 'batch_delete_instances',
                instance_count: instanceIds.length,
                instance_ids: instanceIds,
                result: 'failed',
                error: data.error
            });
            toast.error(data.error);
        }
    })
    .catch(error => {
        // 记录异常日志
        console.error('批量删除实例异常', error, {
            operation: 'batch_delete_instances',
            instance_count: instanceIds.length,
            instance_ids: instanceIds,
            result: 'exception'
        });
        toast.error('批量删除失败');
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
    if (csvFileInput) {
        csvFileInput.value = '';
        const info = csvFileInput.parentNode.querySelector('.file-info');
        if (info) info.remove();
    }

    new bootstrap.Modal(document.getElementById('batchCreateModal')).show();
}

function handleFileSelect(event) {
    const file = event.target.files[0];
    if (file) {
        // 验证文件类型
        if (!file.name.toLowerCase().endsWith('.csv')) {
            toast.warning('请选择CSV格式文件');
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
    submitFileUpload();
}

function submitFileUpload() {
    const fileInput = document.getElementById('csvFile');
    const file = fileInput.files[0];

    if (!file) {
        toast.warning('请选择CSV文件');
        return;
    }

    const formData = new FormData();
    formData.append('file', file);

    const btn = document.querySelector('#batchCreateModal .btn-primary');
    const originalText = btn.textContent;

    btn.textContent = '创建中...';
    btn.disabled = true;

    http.post('/instances/api/batch-create', formData, {
        headers: {
            'Content-Type': 'multipart/form-data'
        }
    })
    .then(data => {
        if (data.success) {
            toast.success(data.message);
            if (data.errors && data.errors.length > 0) {
                toast.warning(`部分实例创建失败：\n${data.errors.join('\n')}`);
            }
            // 关闭模态框
            const modal = bootstrap.Modal.getInstance(document.getElementById('batchCreateModal'));
            if (modal) modal.hide();
            setTimeout(() => location.reload(), 1000);
        } else {
            toast.error(data.error);
        }
    })
    .catch(error => {
        toast.error('批量创建失败');
    })
    .finally(() => {
        btn.textContent = originalText;
        btn.disabled = false;
    });
}

// 标签选择器相关功能
// 导出到全局作用域

// CSRF Token处理已统一到csrf-utils.js中的全局getCSRFToken函数
