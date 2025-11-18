/**
 * 标签管理页面视图
 */
(function (global) {
    'use strict';

    function mount() {
        const TagManagementService = global.TagManagementService;
        if (!TagManagementService) {
            console.error('TagManagementService 未初始化，无法加载标签管理页面');
            return;
        }

        const tagService = new TagManagementService(global.httpU);
        const createTagManagementStore = global.createTagManagementStore;
        const createTagListStore = global.createTagListStore;
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

        let tagManagementStore = null;
        let tagListStore = null;
    let tagFilterCard = null;
    let tagDeleteModal = null;
    let unloadFilterCleanupHandler = null;

        global.currentTags = global.currentTags || [];
        global.currentFilters = global.currentFilters || {};

        ready(() => {
            if (global.tagsPageInitialized) {
                console.warn('标签管理页面已经初始化，跳过重复初始化');
                return;
            }
            initializeTagStore();
            initializeTagManagementStore();
            initializeTagsPage();
            global.tagsPageInitialized = true;
        });

    /**
     * 页面入口：初始化 modal、事件与筛选卡片。
     */
    function initializeTagsPage() {
        initializeDeleteModal();
        initializeTagModals();
        initializeEventHandlers();
        initializeTagActions();
        initializeTagFilterCard();
    }

    /**
     * 初始化 tagListStore，用于批量选择。
     */
    function initializeTagStore() {
        if (!createTagListStore) {
            console.error('createTagListStore 未加载，无法管理列表选择');
            return;
        }
        const ids = getAllTagIds();
        tagListStore = createTagListStore({
            initialTagIds: ids,
        });
        bindTagListStoreEvents();
        syncSelectionView(tagListStore.getState().selection || []);
        updateBatchActions();
    }

    /**
     * 初始化 TagManagementStore，拉取标签数据。
     */
    function initializeTagManagementStore() {
        if (!createTagManagementStore) {
            console.error('createTagManagementStore 未加载');
            return;
        }
        try {
            tagManagementStore = createTagManagementStore({
                service: tagService,
                emitter: global.mitt ? global.mitt() : null,
            });
            tagManagementStore.init({ silent: true }).catch((error) => {
                console.error('TagManagementStore 初始化失败:', error);
            });
        } catch (error) {
            console.error('创建 TagManagementStore 失败:', error);
            tagManagementStore = null;
        }
    }

    /**
     * 绑定列表勾选、批量操作等事件。
     */
    function initializeEventHandlers() {
        const selectAllCheckbox = selectOne('#selectAll');
        if (selectAllCheckbox.length) {
            selectAllCheckbox.on('change', (event) => {
                toggleAllTags(event.target.checked);
            });
        }

        select('input[name="tag_ids"]').on('change', (event) => {
            const checkbox = event.target;
            const tagId = Number(checkbox.value);
            if (!Number.isFinite(tagId) || !tagListStore) {
                return;
            }
            if (checkbox.checked) {
                tagListStore.actions.addTag(tagId);
            } else {
                tagListStore.actions.removeTag(tagId);
            }
        });

        const batchDeleteBtn = selectOne('#batchDelete');
        if (batchDeleteBtn.length) {
            batchDeleteBtn.on('click', handleBatchDelete);
        }

        const batchExportBtn = selectOne('#batchExport');
        if (batchExportBtn.length) {
            batchExportBtn.on('click', handleBatchExport);
        }

        bindDeleteButtons();
        bindModalTriggers();
    }

    function initializeTagActions() {
        // 预留扩展
    }

    /**
     * 删除确认模态的初始化。
     */
    function initializeDeleteModal() {
        const factory = global.UI?.createModal;
        if (!factory) {
            console.error('UI.createModal 未加载，无法初始化标签删除模态框');
            return;
        }
        tagDeleteModal = factory({
            modalSelector: '#deleteModal',
            onOpen: ({ payload }) => {
                const { tagId, tagName } = payload || {};
                selectOne('#deleteTagName').text(tagName || '');
                const deleteForm = selectOne('#deleteForm').first();
                if (deleteForm && tagId) {
                    deleteForm.action = `/tags/api/delete/${tagId}`;
                }
            },
            onClose: () => {
                const deleteForm = selectOne('#deleteForm').first();
                if (deleteForm) {
                    deleteForm.action = '/tags/api/delete/0';
                }
            },
        });
    }

    function bindDeleteButtons() {
        const deleteButtons = select('button[data-tag-id][data-tag-name]');
        if (!deleteButtons.length) {
            return;
        }
        deleteButtons.on('click', (event) => {
            event?.preventDefault?.();
            const target =
                event?.currentTarget ||
                event?.delegateTarget ||
                event?.target?.closest?.('button[data-tag-id][data-tag-name]') ||
                event?.target;
            const button =
                target && typeof target.closest === 'function'
                    ? target.closest('button[data-tag-id][data-tag-name]')
                    : target;
            if (!button || !tagDeleteModal) {
                return;
            }
            const tagId = button.getAttribute('data-tag-id');
            const tagName = button.getAttribute('data-tag-name');
            tagDeleteModal.open({ tagId, tagName });
        });
    }

    function initializeTagModals() {
        if (!global.TagModals?.createController) {
            console.warn('TagModals 未加载，创建/编辑模态不可用');
            return;
        }
        global.tagModals = global.TagModals.createController({
            http: global.httpU,
            FormValidator: global.FormValidator,
            ValidationRules: global.ValidationRules,
            toast: global.toast,
            DOMHelpers: global.DOMHelpers,
        });
        global.tagModals.init?.();
    }

    function bindModalTriggers() {
        if (!global.tagModals) {
            return;
        }
        const createBtn = selectOne('[data-action="create-tag"]');
        if (createBtn.length) {
            createBtn.on('click', (event) => {
                event.preventDefault();
                global.tagModals.openCreate();
            });
        }
        select('[data-action="edit-tag"]').each((button) => {
            const wrapper = from(button);
            wrapper.on('click', (event) => {
                event.preventDefault();
                const tagId = wrapper.attr('data-tag-id');
                if (tagId) {
                    global.tagModals.openEdit(tagId);
                }
            });
        });
    }

    function toggleAllTags(checked) {
        if (!tagListStore) {
            return;
        }
        if (checked) {
            tagListStore.actions.selectAll();
        } else {
            tagListStore.actions.clearSelection();
        }
    }

    function updateBatchActions() {
        const selectedIds = getSelectedTagIds();
        const batchActions = selectOne('.batch-actions');
        if (!batchActions.length) {
            return;
        }
        batchActions.first().style.display = selectedIds.length ? 'block' : 'none';
    }

    function handleBatchDelete(event) {
        event?.preventDefault?.();
        const tagIds = getSelectedTagIds();
        if (!tagIds.length) {
            global.toast.warning('请选择要删除的标签');
            return;
        }
        const confirmText = `确定要删除选中的 ${tagIds.length} 个标签吗？此操作不可撤销！`;
        if (global.confirm(confirmText)) {
            performBatchDelete(tagIds);
        }
    }

    async function performBatchDelete(tagIds) {
        if (!tagManagementStore) {
            throw new Error('TagManagementStore 未初始化');
        }
        try {
            showLoadingState('#batchDelete', '删除中...');
            const data = await tagManagementStore.actions.deleteTags(tagIds);
            global.toast.success(data?.message || '批量删除成功');
            global.setTimeout(() => global.location.reload(), 1000);
        } catch (error) {
            console.error('批量删除失败:', error);
            global.toast.error(error?.message || '批量删除失败，请检查网络或服务器日志。');
        } finally {
            hideLoadingState('#batchDelete', '批量删除');
        }
    }

    /**
     * 构建标签筛选卡片，自动提交筛选。
     */
    function initializeTagFilterCard() {
        const factory = global.UI?.createFilterCard;
        if (!factory) {
            console.error('UI.createFilterCard 未加载，标签筛选无法初始化');
            return;
        }
        tagFilterCard = factory({
            formSelector: `#${TAG_FILTER_FORM_ID}`,
            autoSubmitOnChange: AUTO_APPLY_FILTER_CHANGE,
            onSubmit: ({ values }) => applyTagFilters(null, values),
            onClear: () => applyTagFilters(null, {}),
            onChange: ({ values }) => {
                if (AUTO_APPLY_FILTER_CHANGE) {
                    applyTagFilters(null, values);
                }
            },
        });

        unloadFilterCleanupHandler = () => {
            destroyTagFilterCard();
            from(global).off('beforeunload', unloadFilterCleanupHandler);
            unloadFilterCleanupHandler = null;
        };
        from(global).on('beforeunload', unloadFilterCleanupHandler);
    }

    function destroyTagFilterCard() {
        if (tagFilterCard?.destroy) {
            tagFilterCard.destroy();
        }
        tagFilterCard = null;
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
        const tagIds = getSelectedTagIds();
        if (!tagIds.length) {
            global.toast.warning('请选择要导出的标签');
            return;
        }
        exportTags(tagIds);
    }

    function exportTags(tagIds = null) {
        const params = buildTagQueryParams(resolveTagFilterValues(getTagFilterForm()));
        const ids = Array.isArray(tagIds) && tagIds.length > 0 ? tagIds : getSelectedTagIds();
        if (ids.length > 0) {
            params.append('tag_ids', ids.join(','));
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
        if (tagFilterCard?.form) {
            return tagFilterCard.form;
        }
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
        if (tagFilterCard?.serialize) {
            return tagFilterCard.serialize();
        }
        const serializer = global.UI?.serializeForm;
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

    function bindTagListStoreEvents() {
        if (!tagListStore) {
            return;
        }
        tagListStore.subscribe('tagList:selectionChanged', ({ selection }) => {
            syncSelectionView(selection || []);
            updateBatchActions();
        });
        tagListStore.subscribe('tagList:updated', () => {
            updateBatchActions();
        });
    }

    function syncSelectionView(selection) {
        const selectedSet = new Set(Array.isArray(selection) ? selection : []);
        select('input[name="tag_ids"]').each((checkbox) => {
            const value = Number(checkbox.value);
            checkbox.checked = selectedSet.has(value);
        });
        const selectAllElement = selectOne('#selectAll').first();
        if (selectAllElement) {
            const total = getAllTagIds().length;
            const count = selectedSet.size;
            selectAllElement.checked = total > 0 && count === total;
            selectAllElement.indeterminate = count > 0 && count < total;
        }
    }

    function getAllTagIds() {
        return select('input[name="tag_ids"]').nodes
            .map((checkbox) => Number(checkbox.value))
            .filter((value) => Number.isFinite(value));
    }

    function getSelectedTagIds() {
        if (!tagListStore) {
            return [];
        }
        const state = tagListStore.getState();
        return state.selection || [];
    }

        global.exportTags = exportTags;
    }

    global.TagsIndexPage = {
        mount,
    };
})(window);
