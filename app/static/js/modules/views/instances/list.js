/**
 * 实例管理页面脚本
 * 处理标签筛选、批量操作等功能
 */

const instanceListExports = {};

function mountInstanceListPage() {

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

let instanceStore = null;
const instanceStoreSubscriptions = [];
let batchCreateModal = null;
let instanceModals = null;

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
const BATCH_CREATE_LOADING_TEXT = '创建中...';
let instanceFilterCard = null;
let unloadCleanupHandler = null;

function getInstanceFilterForm() {
    return instanceFilterCard?.form || selectOne(`#${INSTANCE_FILTER_FORM_ID}`).first();
}

function initializeInstanceModals() {
    if (!window.InstanceModals?.createController) {
        console.warn('InstanceModals 未加载，创建/编辑模态不可用');
        return;
    }
    instanceModals = window.InstanceModals.createController({
        http: window.httpU,
        FormValidator: window.FormValidator,
        ValidationRules: window.ValidationRules,
        toast: window.toast,
        DOMHelpers: window.DOMHelpers,
    });
    instanceModals.init?.();
    bindModalTriggers();
}

    ready(() => {
        initializeInstanceStore();
        initializeInstanceModals();
        initializeTagFilter();
        initializeInstanceFilterCard();
        initializeBatchCreateModal();
        setupEventListeners();
        loadInstanceTotalSizes();
        registerUnloadCleanup();
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

// 将筛选对象转成 URLSearchParams
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

// 初始化实例 store，从 DOM 收集初始选择/筛选
function initializeInstanceStore() {
    if (!window.createInstanceStore) {
        console.warn('createInstanceStore 未加载，跳过实例 Store 初始化');
        return;
    }
    if (!ensureInstanceService()) {
        return;
    }
    try {
        instanceStore = window.createInstanceStore({
            service: instanceService,
            emitter: window.mitt ? window.mitt() : null,
        });
    } catch (error) {
        console.error('初始化 InstanceStore 失败:', error);
        return;
    }
    bindInstanceStoreEvents();
    const metadata = collectInstanceMetadata();
    const filterForm = getInstanceFilterForm();
    const rawFilterValues = filterForm ? collectFormValues(filterForm) : {};
    const initialFilters = resolveInstanceFilterValues(filterForm, rawFilterValues);
    instanceStore
        .init({
            instances: metadata,
            filters: initialFilters,
        })
        .then(() => {
            instanceStore.actions.setSelection(collectSelectedInstanceIds(), { reason: 'initial' });
            instanceStore.actions.loadStats({ silent: true }).catch(() => {});
        });
    window.addEventListener('beforeunload', teardownInstanceStore, { once: true });
}

// 批量创建实例模态初始化
function initializeBatchCreateModal() {
    const factory = window.UI?.createModal;
    if (!factory) {
        throw new Error('UI.createModal 未加载，实例列表批量创建模态无法初始化');
    }
    batchCreateModal = factory({
        modalSelector: '#batchCreateModal',
        loadingText: BATCH_CREATE_LOADING_TEXT,
        onOpen: resetBatchCreateModalState,
        onClose: resetBatchCreateModalState,
        onConfirm: () => submitBatchCreate(),
    });
}

// 获取批量创建模态实例
function ensureBatchCreateModal() {
    if (!batchCreateModal) {
        throw new Error('批量创建模态未初始化');
    }
    return batchCreateModal;
}

// 从列表复选框收集实例 ID/名称，用于 store 初始化
function collectInstanceMetadata() {
    const rows = [];
    const checkboxes = select('.instance-checkbox').nodes || [];
    checkboxes.forEach((checkbox) => {
        const numericId = Number(checkbox.value);
        if (!Number.isFinite(numericId)) {
            return;
        }
        const row = checkbox.closest('tr');
        let name = '';
        if (row) {
            const nameCell = row.querySelector('td:nth-child(2) small');
            if (nameCell) {
                name = nameCell.textContent.trim();
            }
        }
        rows.push({ id: numericId, name });
    });
    return rows;
}

// 当前 DOM 选中的实例 ID
function collectSelectedInstanceIds() {
    const checkboxes = select('input.instance-checkbox:checked').nodes || [];
    return checkboxes
        .map((checkbox) => parseInt(checkbox.value, 10))
        .filter((id) => Number.isFinite(id));
}

// 绑定实例 store 事件，监听选择变化
function bindInstanceStoreEvents() {
    if (!instanceStore) {
        return;
    }
    subscribeToInstanceStore('instances:selectionChanged', handleInstanceSelectionChanged);
}

// 订阅 store 并记录以便 teardown
function subscribeToInstanceStore(eventName, handler) {
    if (!instanceStore) {
        return;
    }
    instanceStore.subscribe(eventName, handler);
    instanceStoreSubscriptions.push({ eventName, handler });
}

// store selection 变化时同步 DOM
function handleInstanceSelectionChanged(payload) {
    const selectedIds = new Set((payload?.selectedIds || []).map((id) => Number(id)));
    const availableIds = payload?.availableInstanceIds || [];
    const checkboxes = select('.instance-checkbox').nodes || [];
    checkboxes.forEach((checkbox) => {
        const value = Number(checkbox.value);
        checkbox.checked = selectedIds.has(value);
    });
    const selectAllCheckbox = selectOne('#selectAll');
    if (selectAllCheckbox.length) {
        const element = selectAllCheckbox.first();
        element.checked = availableIds.length > 0 && selectedIds.size === availableIds.length;
        element.indeterminate = selectedIds.size > 0 && selectedIds.size < availableIds.length;
    }
    renderBatchControls(selectedIds.size);
}

// 根据已选择数量更新批量操作按钮
function renderBatchControls(selectedCount) {
    const batchDeleteBtn = selectOne('#batchDeleteBtn');
    if (batchDeleteBtn.length) {
        batchDeleteBtn.attr('disabled', selectedCount === 0 ? 'disabled' : null);
        batchDeleteBtn.text(selectedCount > 0 ? `批量删除 (${selectedCount})` : '批量删除');
    }
    const batchTestBtn = selectOne('#batchTestBtn');
    if (batchTestBtn.length) {
        batchTestBtn.attr('disabled', selectedCount === 0 ? 'disabled' : null);
        batchTestBtn.text(selectedCount > 0 ? `批量测试连接 (${selectedCount})` : '批量测试连接');
    }
}

// 将 DOM 中勾选的实例同步回 store
function syncSelectionFromDom() {
    if (!instanceStore) {
        renderBatchControls(collectSelectedInstanceIds().length);
        return;
    }
    instanceStore.actions.setSelection(collectSelectedInstanceIds(), { reason: 'domChange' });
}

// 卸载事件并销毁 store
function teardownInstanceStore() {
    if (!instanceStore) {
        return;
    }
    instanceStoreSubscriptions.forEach(({ eventName, handler }) => {
        instanceStore.unsubscribe(eventName, handler);
    });
    instanceStoreSubscriptions.length = 0;
    instanceStore.destroy?.();
    instanceStore = null;
}

// 加载实例总大小并渲染
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

// 初始化标签筛选器，确认后触发表单 submit
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
            if (instanceFilterCard?.emit) {
                instanceFilterCard.emit('change', {
                    source: 'instance-tag-selector',
                });
            } else if (window.EventBus) {
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

// 构建 filter-card 控件，自动提交筛选
function initializeInstanceFilterCard() {
    const factory = window.UI?.createFilterCard;
    if (!factory) {
        console.error('UI.createFilterCard 未加载，实例筛选无法初始化');
        return;
    }
    instanceFilterCard = factory({
        formSelector: `#${INSTANCE_FILTER_FORM_ID}`,
        autoSubmitOnChange: AUTO_APPLY_FILTER_CHANGE,
        onSubmit: ({ values }) => applyInstanceFilters(null, values),
        onClear: () => applyInstanceFilters(null, {}),
        onChange: ({ values }) => {
            if (AUTO_APPLY_FILTER_CHANGE) {
                applyInstanceFilters(null, values);
            }
        },
    });
}

// 销毁 filter-card，避免内存泄露
function destroyInstanceFilterCard() {
    if (instanceFilterCard && typeof instanceFilterCard.destroy === 'function') {
        instanceFilterCard.destroy();
    }
    instanceFilterCard = null;
}

// 注册 beforeunload 钩子清理资源
function registerUnloadCleanup() {
    if (unloadCleanupHandler) {
        window.removeEventListener('beforeunload', unloadCleanupHandler);
    }
    unloadCleanupHandler = () => {
        destroyInstanceFilterCard();
        teardownInstanceStore();
        window.removeEventListener('beforeunload', unloadCleanupHandler);
        unloadCleanupHandler = null;
    };
    window.addEventListener('beforeunload', unloadCleanupHandler);
}

// 将初始隐藏域值转换为数组
function parseInitialTagValues(rawValue) {
    if (!rawValue) {
        return [];
    }
    return rawValue
        .split(',')
        .map((value) => value.trim())
        .filter(Boolean);
}

// 序列化表单为键值对
function collectFormValues(form) {
    if (instanceFilterCard?.serialize) {
        return instanceFilterCard.serialize();
    }
    const serializer = window.UI?.serializeForm;
    if (serializer) {
        return serializer(form);
    }
    if (!form) {
        return {};
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

// 应用筛选值并刷新页面
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

// 重置筛选表单
function resetInstanceFilters(form) {
    const targetForm = form || getInstanceFilterForm();
    if (targetForm) {
        targetForm.reset();
    }
    applyInstanceFilters(targetForm, {});
}

// 绑定新建/编辑模态按钮
function bindModalTriggers() {
    if (!instanceModals) {
        return;
    }
    const createBtn = selectOne('[data-action="create-instance"]');
    if (createBtn.length) {
        createBtn.on('click', (event) => {
            event.preventDefault();
            instanceModals.openCreate();
        });
    }
    select('[data-action="edit-instance"]').each((button) => {
        const wrapper = from(button);
        wrapper.on('click', (event) => {
            event.preventDefault();
            const row = button.closest('tr');
            const id = wrapper.attr('data-instance-id') || row?.getAttribute('data-instance-id');
            if (id) {
                instanceModals.openEdit(id);
            }
        });
    });
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

    bindModalTriggers();
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
                if (payload?.summary) {
                    console.info('批量测试进度', payload.summary);
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
    if (instanceStore) {
        return instanceStore.getState().selection;
    }
    const checkboxes = select('input.instance-checkbox:checked').nodes || [];
    return checkboxes.map((checkbox) => parseInt(checkbox.value, 10)).filter((id) => !Number.isNaN(id));
}

// 显示提示信息

// 批量操作功能
function toggleSelectAll() {
    const selectAllCheckbox = selectOne('#selectAll');
    if (!selectAllCheckbox.length) {
        return;
    }
    const checked = selectAllCheckbox.first().checked;
    if (instanceStore) {
        if (checked) {
            instanceStore.actions.selectAll();
        } else {
            instanceStore.actions.clearSelection();
        }
        return;
    }
    const instanceCheckboxes = select('.instance-checkbox');
    if (!instanceCheckboxes.length) {
        return;
    }
    instanceCheckboxes.each((checkbox) => {
        checkbox.checked = checked;
    });
    renderBatchControls(checked ? instanceCheckboxes.length : 0);
}

function updateBatchButtons() {
    syncSelectionFromDom();
}

function batchDelete() {
    if (!ensureInstanceService()) {
        return;
    }
    const selectedIds = instanceStore ? instanceStore.getState().selection : collectSelectedInstanceIds();
    if (!selectedIds.length) {
        toast.warning('请选择要删除的实例');
        return;
    }
    if (!confirm(`确定要删除选中的 ${selectedIds.length} 个实例吗？此操作不可撤销！`)) {
        return;
    }
    const btn = document.getElementById('batchDeleteBtn');
    const originalText = btn?.textContent;
    if (btn) {
        btn.textContent = '删除中...';
        btn.disabled = true;
    }
    const executeDelete = instanceStore
        ? instanceStore.actions.batchDeleteSelected()
        : instanceService.batchDeleteInstances(selectedIds);
    executeDelete
        .then((data) => {
            const result = data?.data || data;
            if (instanceStore || data?.success !== false) {
                console.info('批量删除实例成功', {
                    operation: 'batch_delete_instances',
                    instance_count: selectedIds.length,
                    instance_ids: selectedIds,
                    result: 'success',
                    message: data?.message || result?.message,
                });
                toast.success(data?.message || result?.message || '批量删除成功');
                setTimeout(() => location.reload(), 1000);
                return;
            }
            console.error('批量删除实例失败', {
                operation: 'batch_delete_instances',
                instance_count: selectedIds.length,
                instance_ids: selectedIds,
                result: 'failed',
                error: data.error,
            });
            toast.error(data.error || '批量删除失败');
        })
        .catch((error) => {
            console.error('批量删除实例异常', error, {
                operation: 'batch_delete_instances',
                instance_count: selectedIds.length,
                instance_ids: selectedIds,
                result: 'exception',
            });
            toast.error(error?.message || '批量删除失败');
        })
        .finally(() => {
            if (btn) {
                btn.textContent = originalText || '批量删除';
                btn.disabled = true;
            }
        });
}

function resetBatchCreateModalState() {
    const csvFileInput = document.getElementById('csvFile');
    if (csvFileInput) {
        csvFileInput.value = '';
        const info = csvFileInput.parentNode.querySelector('.file-info');
        if (info) {
            info.remove();
        }
    }
}

// 批量创建相关功能
function showBatchCreateModal() {
    const modal = ensureBatchCreateModal();
    resetBatchCreateModalState();
    modal.open();
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
    const modalInstance = ensureBatchCreateModal();
    const fileInput = document.getElementById('csvFile');
    const file = fileInput.files[0];

    if (!file) {
        toast.warning('请选择CSV文件');
        return;
    }

    const formData = new FormData();
    formData.append('file', file);

    modalInstance.setLoading(true, BATCH_CREATE_LOADING_TEXT);

    const submitAction = instanceStore
        ? instanceStore.actions.batchCreateInstances(formData)
        : instanceService.batchCreateInstances(formData);

    submitAction
        .then((data) => {
            if (instanceStore || data.success) {
                const result = data?.response || data;
                const message = result?.message || data?.message || '批量创建成功';
                toast.success(message);
                const errors = result?.errors || data?.errors;
                if (errors && errors.length > 0) {
                    toast.warning(`部分实例创建失败：\n${errors.join('\n')}`);
                }
                modalInstance.close();
                setTimeout(() => location.reload(), 1000);
                return;
            }
            toast.error(data.error || '批量创建失败');
        })
        .catch((error) => {
            toast.error(error?.message || '批量创建失败');
        })
        .finally(() => {
            modalInstance.setLoading(false);
        });
}

// 标签选择器相关功能
// CSRF Token处理已统一到csrf-utils.js中的全局getCSRFToken函数

Object.assign(instanceListExports, {
    testConnection,
    batchTestConnections,
    batchDelete,
    showBatchCreateModal,
    submitBatchCreate,
    handleFileSelect,
    toggleSelectAll,
    updateBatchButtons,
    syncAccounts,
});
}

window.InstancesListPage = {
    mount: mountInstanceListPage,
};

function createDeferredExportInvoker(methodName) {
    return function (...args) {
        const handler = instanceListExports[methodName];
        if (typeof handler === 'function') {
            return handler(...args);
        }
        console.error(`InstancesListPage: ${methodName} 尚未初始化`);
        return undefined;
    };
}

window.testConnection = createDeferredExportInvoker('testConnection');
window.batchTestConnections = createDeferredExportInvoker('batchTestConnections');
window.batchDelete = createDeferredExportInvoker('batchDelete');
window.showBatchCreateModal = createDeferredExportInvoker('showBatchCreateModal');
window.submitBatchCreate = createDeferredExportInvoker('submitBatchCreate');
window.handleFileSelect = createDeferredExportInvoker('handleFileSelect');
window.toggleSelectAll = createDeferredExportInvoker('toggleSelectAll');
window.updateBatchButtons = createDeferredExportInvoker('updateBatchButtons');
window.syncAccounts = createDeferredExportInvoker('syncAccounts');
