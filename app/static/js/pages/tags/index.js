/**
 * 标签管理页面脚本：统一通过 Umbrella/DOMHelpers 操作 DOM 与事件。
 */
(function (global) {
    'use strict';

    const TagManagementService = global.TagManagementService;
    if (!TagManagementService) {
        console.error('TagManagementService 未初始化，无法加载标签管理页面');
        return;
    }

    const tagService = new TagManagementService(global.httpU);
    const helpers = global.DOMHelpers;
    if (!helpers) {
        console.error('DOMHelpers 未初始化，无法加载标签管理页面');
        return;
    }

    const LodashUtils = global.LodashUtils;
    if (!LodashUtils) {
        throw new Error('LodashUtils 未初始化');
    }

    const { ready, select, selectOne, from } = helpers;

    const TAG_FILTER_FORM_ID = 'tag-filter-form';
    const AUTO_APPLY_FILTER_CHANGE = true;

    let tagFilterEventHandler = null;
    let unloadFilterCleanupHandler = null;

    global.currentTags = global.currentTags || [];
    global.currentFilters = global.currentFilters || {};

    ready(() => {
        if (global.tagsPageInitialized) {
            console.warn('标签管理页面已经初始化，跳过重复初始化');
            return;
        }
        initializeTagsPage();
        global.tagsPageInitialized = true;
    });

    function initializeTagsPage() {
        initializeEventHandlers();
        initializeTagActions();
        registerTagFilterForm();
        subscribeFilterEvents();
    }

    function initializeEventHandlers() {
        const selectAllCheckbox = selectOne('#selectAll');
        if (selectAllCheckbox.length) {
            selectAllCheckbox.on('change', (event) => {
                toggleAllTags(event.target.checked);
            });
        }

        select('input[name="tag_ids"]').on('change', () => {
            updateBatchActions();
        });

        const batchDeleteBtn = selectOne('#batchDelete');
        if (batchDeleteBtn.length) {
            batchDeleteBtn.on('click', handleBatchDelete);
        }

        const batchExportBtn = selectOne('#batchExport');
        if (batchExportBtn.length) {
            batchExportBtn.on('click', handleBatchExport);
        }

        const deleteModalElement = selectOne('#deleteModal').first();
        if (deleteModalElement) {
            deleteModalElement.addEventListener('show.bs.modal', (event) => {
                const button = event.relatedTarget;
                if (!button) {
                    return;
                }
                const tagId = button.getAttribute('data-tag-id');
                const tagName = button.getAttribute('data-tag-name');

                selectOne('#deleteTagName').text(tagName || '');
                const deleteForm = selectOne('#deleteForm').first();
                if (deleteForm) {
                    deleteForm.action = `/tags/api/delete/${tagId}`;
                }
            });
        }
    }

    function initializeTagActions() {
        // 预留扩展
    }

    function toggleAllTags(checked) {
        select('input[name="tag_ids"]').each((checkbox) => {
            checkbox.checked = checked;
        });
        updateBatchActions();
    }

    function updateBatchActions() {
        const selectedCheckboxes = select('input[name="tag_ids"]:checked');
        const batchActions = selectOne('.batch-actions');
        if (!batchActions.length) {
            return;
        }
        batchActions.first().style.display = selectedCheckboxes.length ? 'block' : 'none';
    }

    function handleBatchDelete(event) {
        event?.preventDefault?.();
        const selectedCheckboxes = select('input[name="tag_ids"]:checked').nodes;
        if (!selectedCheckboxes.length) {
            global.toast.warning('请选择要删除的标签');
            return;
        }
        const tagIds = selectedCheckboxes.map((cb) => cb.value);
        const confirmText = `确定要删除选中的 ${tagIds.length} 个标签吗？此操作不可撤销！`;
        if (global.confirm(confirmText)) {
            performBatchDelete(tagIds);
        }
    }

    async function performBatchDelete(tagIds) {
        try {
            showLoadingState('#batchDelete', '删除中...');
            const data = await tagService.batchDelete({ tag_ids: tagIds });
            if (data.success) {
                global.toast.success(data.message);
                global.setTimeout(() => global.location.reload(), 1000);
            } else {
                global.toast.error(`批量删除失败: ${data.error}`);
            }
        } catch (error) {
            console.error('批量删除失败:', error);
            global.toast.error('批量删除失败，请检查网络或服务器日志。');
        } finally {
            hideLoadingState('#batchDelete', '批量删除');
        }
    }

    function registerTagFilterForm() {
        if (!global.FilterUtils) {
            console.warn('FilterUtils 未加载，跳过标签筛选初始化');
            return;
        }
        const selector = `#${TAG_FILTER_FORM_ID}`;
        const form = selectOne(selector);
        if (!form.length) {
            return;
        }
        global.FilterUtils.registerFilterForm(selector, {
            onSubmit: ({ form, event }) => {
                event?.preventDefault?.();
                applyTagFilters(form);
            },
            onClear: ({ form, event }) => {
                event?.preventDefault?.();
                resetTagFilters(form);
            },
            autoSubmitOnChange: false,
        });
    }

    function subscribeFilterEvents() {
        if (!global.EventBus) {
            return;
        }
        const formElement = getTagFilterForm();
        if (!formElement) {
            return;
        }
        const handler = (detail) => {
            if (!detail) {
                return;
            }
            const incoming = (detail.formId || '').replace(/^#/, '');
            if (incoming !== TAG_FILTER_FORM_ID) {
                return;
            }
            switch (detail.action) {
                case 'clear':
                    resetTagFilters(formElement);
                    break;
                case 'change':
                    if (AUTO_APPLY_FILTER_CHANGE) {
                        applyTagFilters(formElement, detail.values);
                    }
                    break;
                case 'submit':
                    applyTagFilters(formElement, detail.values);
                    break;
                default:
                    break;
            }
        };

        ['change', 'submit', 'clear'].forEach((action) => {
            global.EventBus.on(`filters:${action}`, handler);
        });
        tagFilterEventHandler = handler;

        unloadFilterCleanupHandler = () => {
            cleanupFilterEvents();
            from(global).off('beforeunload', unloadFilterCleanupHandler);
        };
        from(global).on('beforeunload', unloadFilterCleanupHandler);
    }

    function cleanupFilterEvents() {
        if (!global.EventBus || !tagFilterEventHandler) {
            return;
        }
        ['change', 'submit', 'clear'].forEach((action) => {
            global.EventBus.off(`filters:${action}`, tagFilterEventHandler);
        });
        tagFilterEventHandler = null;
    }

    function applyTagFilters(form, values) {
        const targetForm = resolveForm(form) || getTagFilterForm();
        if (!targetForm) {
            return;
        }
        const filters = resolveTagFilterValues(targetForm, values);
        const params = buildTagQueryParams(filters);
        const action = targetForm.getAttribute('action') || global.location.pathname;
        const query = params.toString();
        global.location.href = query ? `${action}?${query}` : action;
    }

    function resetTagFilters(form) {
        const targetForm = resolveForm(form) || getTagFilterForm();
        if (targetForm) {
            targetForm.reset();
        }
        applyTagFilters(targetForm, {});
    }

    function handleBatchExport(event) {
        event?.preventDefault?.();
        const selectedCheckboxes = select('input[name="tag_ids"]:checked').nodes;
        if (!selectedCheckboxes.length) {
            global.toast.warning('请选择要导出的标签');
            return;
        }
        const tagIds = selectedCheckboxes.map((cb) => cb.value);
        exportTags(tagIds);
    }

    function exportTags(tagIds = null) {
        const params = buildTagQueryParams(resolveTagFilterValues(getTagFilterForm()));
        if (Array.isArray(tagIds) && tagIds.length > 0) {
            params.append('tag_ids', tagIds.join(','));
        }
        const exportUrl = `/tags/export?${params.toString()}`;
        global.open(exportUrl, '_blank', 'noopener');
    }

    function showLoadingState(target, text) {
        const button = typeof target === 'string' ? selectOne(target) : from(target);
        if (!button.length) {
            return;
        }
        button.attr('data-original-text', button.html());
        button.html(`<i class="fas fa-spinner fa-spin me-1"></i>${text}`);
        button.attr('disabled', 'disabled');
    }

    function hideLoadingState(target, originalText) {
        const button = typeof target === 'string' ? selectOne(target) : from(target);
        if (!button.length) {
            return;
        }
        const fallback = button.attr('data-original-text');
        button.html(fallback || originalText || '');
        button.attr('disabled', null);
        button.attr('data-original-text', null);
    }

    function getTagFilterForm() {
        return selectOne(`#${TAG_FILTER_FORM_ID}`).first();
    }

    function resolveForm(form) {
        if (!form) {
            return null;
        }
        if (form instanceof Element) {
            return form;
        }
        if (form && typeof form.first === 'function') {
            return form.first();
        }
        return form;
    }

    function resolveTagFilterValues(form, overrideValues) {
        const rawValues =
            overrideValues && Object.keys(overrideValues || {}).length
                ? overrideValues
                : collectFormValues(form);
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

    function sanitizeFilterValue(value) {
        if (Array.isArray(value)) {
            return LodashUtils.compact(value.map((item) => sanitizePrimitiveValue(item)));
        }
        return sanitizePrimitiveValue(value);
    }

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

    function buildTagQueryParams(filters) {
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

    function collectFormValues(form) {
        if (!form) {
            return {};
        }
        if (global.FilterUtils && typeof global.FilterUtils.serializeForm === 'function') {
            return global.FilterUtils.serializeForm(form);
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

    global.exportTags = exportTags;
})(window);
