/**
 * 实例管理页面脚本
 * 处理标签筛选、批量操作等功能
 */

const LodashUtils = window.LodashUtils;
if (!LodashUtils) {
    throw new Error('LodashUtils 未初始化');
}

const DOMHelpers = window.DOMHelpers;
if (!DOMHelpers) {
    throw new Error('DOMHelpers 未初始化');
}

const { ready, selectOne, select, from } = DOMHelpers;

const InstanceManagementService = window.InstanceManagementService;
let instanceService = null;
try {
    if (InstanceManagementService) {
        instanceService = new InstanceManagementService(window.httpU);
    } else {
        throw new Error('InstanceManagementService 未加载');
    }
} catch (error) {
    console.error('初始化 InstanceManagementService 失败:', error);
}

function ensureInstanceService() {
    if (!instanceService) {
        if (window.toast?.error) {
            window.toast.error('实例管理服务未初始化');
        } else {
            console.error('实例管理服务未初始化');
        }
        return false;
    }
    return true;
}

const INSTANCE_FILTER_FORM_ID = 'instance-filter-form';
const AUTO_APPLY_FILTER_CHANGE = true;
let instanceFilterEventHandler = null;

function getInstanceFilterForm() {
    return selectOne(`#${INSTANCE_FILTER_FORM_ID}`).first();
}

ready(() => {
    initializeTagFilter();
    registerInstanceFilterForm();
    subscribeInstanceFilters();
    setupEventListeners();
    loadInstanceTotalSizes();
    
    // 初始化批量操作按钮状态
    updateBatchButtons();
});

function sanitizePrimitiveValue(value) {
    if (value instanceof File) {
        return value.name;
    }
    if (typeof value === 'string') {
        const trimmed = value.trim();
        return trimmed === '' ? null : trimmed;
    }
    if (value === undefined || value === null) {
        return null;
    }
    return value;
}

function sanitizeFilterValue(value) {
    if (Array.isArray(value)) {
        return LodashUtils.compact(value.map((item) => sanitizePrimitiveValue(item)));
    }
    return sanitizePrimitiveValue(value);
}

function resolveInstanceFilterValues(form, overrideValues) {
    const baseForm = form || selectOne(`#${INSTANCE_FILTER_FORM_ID}`).first();
    const rawValues = overrideValues && Object.keys(overrideValues || {}).length
        ? overrideValues
        : collectFormValues(baseForm);
    return Object.entries(rawValues || {}).reduce((result, [key, value]) => {
        if (key === 'csrf_token') {
            return result;
        }
        const normalized = sanitizeFilterValue(value);
        if (normalized === null || normalized === undefined) {
            return result;
        }
        if (Array.isArray(normalized) && normalized.length === 0) {
            return result;
        }
        result[key] = normalized;
        return result;
    }, {});
}

function buildInstanceQueryParams(filters) {
    const params = new URLSearchParams();
    Object.entries(filters || {}).forEach(([key, value]) => {
        if (Array.isArray(value)) {
            value.forEach((item) => params.append(key, item));
        } else {
            params.append(key, value);
        }
    });
    return params;
}

// 加载实例总大小
async function loadInstanceTotalSizes() {
    if (!ensureInstanceService()) {
        return;
    }
    try {
        const elements = select('.instance-total-size').nodes || [];
        for (const element of elements) {
            const instanceId = element.getAttribute('data-instance-id');
            if (!instanceId) continue;

            try {
                const data = await instanceService.fetchDatabaseTotalSize(instanceId);
                
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
    return window.NumberFormat.formatBytes(bytes, {
        unit: 'GB',
        precision: 3,
        trimZero: false,
        fallback: '0 GB',
    });
}

function initializeTagFilter() {
    if (!window.TagSelectorHelper) {
        console.warn('TagSelectorHelper 未加载，跳过标签筛选初始化');
        return;
    }

    const hiddenInput = selectOne('#selected-tag-names').first();
    const initialValues = parseInitialTagValues(hiddenInput?.value);

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
            const form = selectOne(`#${INSTANCE_FILTER_FORM_ID}`).first();
            if (!form) {
                return;
            }
            if (window.EventBus) {
                EventBus.emit('filters:change', {
                    formId: form.id,
                    source: 'instance-tag-selector',
                    values: collectFormValues(form),
                });
            } else if (typeof form.requestSubmit === 'function') {
                form.requestSubmit();
            } else {
                form.submit();
            }
        },
    });
}

function parseInitialTagValues(rawValue) {
    if (!rawValue) {
        return [];
    }
    return rawValue
        .split(',')
        .map((value) => value.trim())
        .filter(Boolean);
}

function collectFormValues(form) {
    if (!form) {
        return {};
    }
    if (window.FilterUtils && typeof window.FilterUtils.serializeForm === 'function') {
        return window.FilterUtils.serializeForm(form);
    }
    const formData = new FormData(form);
    const result = {};
    formData.forEach((value, key) => {
        const normalized = value instanceof File ? value.name : value;
        if (result[key] === undefined) {
            result[key] = normalized;
        } else if (Array.isArray(result[key])) {
            result[key].push(normalized);
        } else {
            result[key] = [result[key], normalized];
        }
    });
    return result;
}

function registerInstanceFilterForm() {
    if (!window.FilterUtils) {
        console.warn('FilterUtils 未加载，跳过实例筛选初始化');
        return;
    }
    const selector = `#${INSTANCE_FILTER_FORM_ID}`;
    const form = selectOne(selector).first();
    if (!form) {
        return;
    }
    window.FilterUtils.registerFilterForm(selector, {
        onSubmit: ({ form, event }) => {
            event?.preventDefault?.();
            applyInstanceFilters(form);
        },
        onClear: ({ form, event }) => {
            event?.preventDefault?.();
            resetInstanceFilters(form);
        },
        autoSubmitOnChange: true,
    });
}

function subscribeInstanceFilters() {
    if (!window.EventBus) {
        return;
    }
    const form = getInstanceFilterForm();
    if (!form) {
        return;
    }
    const handler = (detail) => {
        if (!detail) {
            return;
        }
        const incoming = (detail.formId || '').replace(/^#/, '');
        if (incoming !== INSTANCE_FILTER_FORM_ID) {
            return;
        }
        switch (detail.action) {
            case 'clear':
                resetInstanceFilters(form);
                break;
            case 'change':
                if (AUTO_APPLY_FILTER_CHANGE) {
                    applyInstanceFilters(form, detail.values);
                }
                break;
            case 'submit':
                applyInstanceFilters(form, detail.values);
                break;
            default:
                break;
        }
    };
    ['change', 'submit', 'clear'].forEach((action) => {
        EventBus.on(`filters:${action}`, handler);
    });
    instanceFilterEventHandler = handler;
    window.addEventListener('beforeunload', () => cleanupInstanceFilters(), { once: true });
}

function cleanupInstanceFilters() {
    if (!window.EventBus || !instanceFilterEventHandler) {
        return;
    }
    ['change', 'submit', 'clear'].forEach((action) => {
        EventBus.off(`filters:${action}`, instanceFilterEventHandler);
    });
    instanceFilterEventHandler = null;
}

function applyInstanceFilters(form, values) {
    const targetForm = form || getInstanceFilterForm();
    if (!targetForm) {
        return;
    }
    const filters = resolveInstanceFilterValues(targetForm, values);
    const params = buildInstanceQueryParams(filters);
    const action = targetForm.getAttribute('action') || window.location.pathname;
    const query = params.toString();
    window.location.href = query ? `${action}?${query}` : action;
}

function resetInstanceFilters(form) {
    const targetForm = form || getInstanceFilterForm();
    if (targetForm) {
        targetForm.reset();
    }
    applyInstanceFilters(targetForm, {});
}

// 初始化标签选择器
// 设置事件监听器
function setupEventListeners() {
    // 批量操作相关
    const selectAllCheckbox = selectOne('#selectAll');
    if (selectAllCheckbox.length) {
        selectAllCheckbox.on('change', toggleSelectAll);
    }

    const instanceCheckboxes = select('.instance-checkbox');
    if (instanceCheckboxes.length) {
        instanceCheckboxes.on('change', updateBatchButtons);
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
    // 使用连接管理API进行批量测试
    connectionManager
        .batchTestConnections(selectedInstances, {
            onProgress: (result) => {
                const payload = result?.data || result;
                if (progressContainer) {
                    connectionManager.showBatchTestProgress(payload, 'batch-test-progress');
                }
            },
            onError: (error) => {
                toast.error(error.error || '批量测试失败');
            },
        })
        .then((result) => {
            if (!result) {
                toast.error('批量测试失败');
                return;
            }

            if (result.success === false && !result.data) {
                toast.error(result.error || '批量测试失败');
                return;
            }

            const payload = result.data || result;
            if (!payload) {
                toast.info(result.message || '批量测试完成');
                return;
            }

            const summary = payload.summary || {};
            const total = summary.total ?? selectedInstances.length;
            const successCount = summary.success ?? 0;
            const failedCount = summary.failed ?? Math.max(total - successCount, 0);
            const toastMessage = `批量连接测试完成：成功 ${successCount} / ${total}${failedCount > 0 ? `，失败 ${failedCount}` : ''}`;

            if (failedCount > 0) {
                toast.warning(toastMessage);
            } else {
                toast.success(toastMessage);
            }
        })
        .catch((error) => {
            toast.error(error?.message || '批量测试失败');
        });
}

// 获取选中的实例ID列表
function getSelectedInstances() {
    const checkboxes = select('input.instance-checkbox:checked').nodes || [];
    return checkboxes.map((checkbox) => parseInt(checkbox.value, 10)).filter((id) => !Number.isNaN(id));
}

// 同步容量
function syncCapacity(instanceId, instanceName) {
    if (!ensureInstanceService()) {
        return;
    }
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

    instanceService.syncInstanceCapacity(instanceId)
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
    const selectAllCheckbox = selectOne('#selectAll');
    const instanceCheckboxes = select('.instance-checkbox');
    if (!selectAllCheckbox.length || !instanceCheckboxes.length) {
        return;
    }
    const checked = selectAllCheckbox.first().checked;
    instanceCheckboxes.each((checkbox) => {
        checkbox.checked = checked;
    });

    updateBatchButtons();
}

function updateBatchButtons() {
    const selectedCount = (select('.instance-checkbox:checked').length) || 0;
    const batchDeleteBtn = selectOne('#batchDeleteBtn');
    const batchTestBtn = selectOne('#batchTestBtn');

    if (batchDeleteBtn.length) {
        batchDeleteBtn.attr('disabled', selectedCount === 0 ? 'disabled' : null);
        batchDeleteBtn.text(selectedCount > 0 ? `批量删除 (${selectedCount})` : '批量删除');
    }
    
    if (batchTestBtn.length) {
        batchTestBtn.attr('disabled', selectedCount === 0 ? 'disabled' : null);
        batchTestBtn.text(selectedCount > 0 ? `批量测试连接 (${selectedCount})` : '批量测试连接');
    }
}

function batchDelete() {
    if (!ensureInstanceService()) {
        return;
    }
    const selectedCheckboxes = select('.instance-checkbox:checked').nodes || [];
    const instanceIds = selectedCheckboxes
        .map((cb) => parseInt(cb.value, 10))
        .filter((id) => !Number.isNaN(id));

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

    instanceService.batchDeleteInstances(instanceIds)
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
        const sizeLabel = window.NumberFormat.formatBytes(file.size, {
                unit: 'KB',
                precision: 1,
                trimZero: true,
                fallback: '0 KB',
              });
        fileInfo.innerHTML = `<i class="fas fa-file-csv me-1"></i>已选择文件: ${file.name} (${sizeLabel})`;

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
    if (!ensureInstanceService()) {
        return;
    }
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

    instanceService.batchCreateInstances(formData)
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
