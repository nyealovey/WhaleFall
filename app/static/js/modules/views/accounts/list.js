function mountAccountsListPage() {
    const global = window;
    /**
     * 账户列表页面 JavaScript
     * 处理账户同步、权限查看、标签选择等功能
     */
    'use strict';

    const helpers = global.DOMHelpers;
    if (!helpers) {
        console.error('DOMHelpers 未初始化，无法加载账户列表页面脚本');
        return;
    }

    const LodashUtils = global.LodashUtils;
    if (!LodashUtils) {
        throw new Error('LodashUtils 未初始化');
    }

const { ready, selectOne, select, from } = helpers;

const InstanceManagementService = global.InstanceManagementService;
let instanceService = null;
try {
    if (InstanceManagementService) {
        instanceService = new InstanceManagementService(global.httpU);
    } else {
        throw new Error('InstanceManagementService 未加载');
    }
} catch (error) {
    console.error('初始化 InstanceManagementService 失败:', error);
}

let instanceStore = null;

function ensureInstanceService() {
    if (!instanceService) {
        if (global.toast?.error) {
            global.toast.error('实例管理服务未初始化');
        } else {
            console.error('实例管理服务未初始化');
        }
        return false;
    }
    return true;
}

const ACCOUNT_FILTER_FORM_ID = 'account-filter-form';
    const AUTO_APPLY_FILTER_CHANGE = true;

    let accountFilterCard = null;
    let unloadCleanupHandler = null;

    ready(initializeAccountsListPage);

    /**
     * 入口：初始化实例 store、标签筛选与筛选卡片。
     */
    /**
     * 页面入口：初始化 store、标签筛选、筛选卡片。
     */
    function initializeAccountsListPage() {
        initializeInstanceStore();
        initializeTagFilter();
        initializeAccountFilterCard();
        registerUnloadCleanup();
    }

    /**
     * 创建实例 store（若存在），用于同步操作。
     */
    /**
     * 仅在可用时创建实例 store，用于批量同步等操作。
     */
    function initializeInstanceStore() {
        if (!global.createInstanceStore) {
            console.warn('createInstanceStore 未加载，跳过实例 Store 初始化');
            return;
        }
        if (!ensureInstanceService()) {
            return;
        }
        try {
            instanceStore = global.createInstanceStore({
                service: instanceService,
                emitter: global.mitt ? global.mitt() : null,
            });
        } catch (error) {
            console.error('初始化 InstanceStore 失败:', error);
            instanceStore = null;
            return;
        }
        instanceStore.init({}).catch((error) => {
            console.warn('InstanceStore 初始化失败', error);
        });
    }

    /**
     * 页面卸载时释放 store。
     */
    /**
     * 页面卸载时销毁实例 store。
     */
    function teardownInstanceStore() {
        if (!instanceStore) {
            return;
        }
        instanceStore.destroy?.();
        instanceStore = null;
    }

    /**
     * 从事件或传入引用解析出触发按钮。
     */
    /**
     * 通用工具：从事件/引用解析出实际按钮 DOM。
     */
    function resolveButton(reference) {
        if (!reference && global.event && global.event.target) {
            return global.event.target;
        }
        if (!reference) {
            return null;
        }
        if (reference instanceof Element) {
            return reference;
        }
        if (reference.currentTarget) {
            return reference.currentTarget;
        }
        if (reference.target) {
            return reference.target;
        }
        return null;
    }

    /**
     * 触发全部账户同步。
     */
    /**
     * 触发所有账户同步，并在按钮上展示 loading。
     */
    function syncAllAccounts(trigger) {
        if (!ensureInstanceService()) {
            return;
        }
        const button = resolveButton(trigger);
        const buttonWrapper = button ? from(button) : null;
        const originalText = buttonWrapper ? buttonWrapper.html() : null;

        if (buttonWrapper) {
            buttonWrapper.html('<i class="fas fa-spinner fa-spin me-2"></i>同步中...');
            buttonWrapper.attr('disabled', 'disabled');
        }

        const request = instanceStore
            ? instanceStore.actions.syncAllAccounts()
            : instanceService.syncAllAccounts();
        return request
            .then((data) => {
                if (data.success) {
                    global.toast.success(data.message || '批量同步任务已启动');
                    if (data.data?.manual_job_id) {
                        global.toast.info(`任务线程: ${data.data.manual_job_id}`);
                    }
                } else if (data.error) {
                    global.toast.error(data.error);
                }
            })
            .catch((error) => {
                console.error('账户同步失败:', error);
                global.toast.error('同步失败');
            })
            .finally(() => {
                if (buttonWrapper) {
                    buttonWrapper.html(originalText || '同步');
                    buttonWrapper.attr('disabled', null);
                }
            });
    }

    /**
     * 别名：保持与历史调用兼容。
     */
    /**
     * 历史兼容别名。
     */
    function syncAllInstances(trigger) {
        return syncAllAccounts(trigger);
    }

    /**
     * 查看账户详情（占位逻辑，可扩展为跳转）。
     */
    /**
     * 查看账户详情（占位，可进一步实现）。
     */
    function viewAccount(accountId) {
        global.toast.info(`查看账户 ${accountId} 的详情`);
    }

    /**
     * 跳转到账户统计页。
     */
    /**
     * 跳转到账户统计页面。
     */
    function showAccountStatistics() {
        global.location.href = '/account-static/';
    }

    /**
     * 初始化标签筛选器并处理确认事件。
     */
    /**
     * 初始化标签选择器，确认后触发表单提交/事件总线。
     */
    function initializeTagFilter() {
        if (!global.TagSelectorHelper) {
            console.warn('TagSelectorHelper 未加载，跳过标签筛选初始化');
            return;
        }

        const hiddenInput = selectOne('#selected-tag-names');
        const initialValues = parseInitialTagValues(hiddenInput.length ? hiddenInput.attr('value') : null);

        global.TagSelectorHelper.setupForForm({
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
                const form = selectOne(`#${ACCOUNT_FILTER_FORM_ID}`).first();
                if (!form) {
                    return;
                }
                if (accountFilterCard?.emit) {
                    accountFilterCard.emit('change', {
                        source: 'account-tag-selector',
                    });
                } else if (global.EventBus) {
                    global.EventBus.emit('filters:change', {
                        formId: form.id,
                        source: 'account-tag-selector',
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

    /**
     * 绑定 filter-card，自动/手动触发筛选。
     */
    function initializeAccountFilterCard() {
        const selector = `#${ACCOUNT_FILTER_FORM_ID}`;
        const formWrapper = selectOne(selector);
        if (!formWrapper.length) {
            return;
        }
        const factory = global.UI?.createFilterCard;
        if (!factory) {
            console.error('UI.createFilterCard 未加载，账户筛选无法初始化');
            return;
        }
        accountFilterCard = factory({
            formSelector: selector,
            autoSubmitOnChange: AUTO_APPLY_FILTER_CHANGE,
            onSubmit: ({ values }) => applyAccountFilters(null, values),
            onClear: () => applyAccountFilters(null, {}),
            onChange: ({ values }) => {
                if (AUTO_APPLY_FILTER_CHANGE) {
                    applyAccountFilters(null, values);
                }
            },
        });
    }

    /**
     * 销毁筛选卡片实例。
     */
    function destroyAccountFilterCard() {
        if (accountFilterCard && typeof accountFilterCard.destroy === 'function') {
            accountFilterCard.destroy();
        }
        accountFilterCard = null;
    }

    /**
     * 注册 beforeunload 钩子做清理。
     */
    function registerUnloadCleanup() {
        if (unloadCleanupHandler) {
            from(global).off('beforeunload', unloadCleanupHandler);
        }
        unloadCleanupHandler = () => {
            destroyAccountFilterCard();
            teardownInstanceStore();
            from(global).off('beforeunload', unloadCleanupHandler);
            unloadCleanupHandler = null;
        };
        from(global).on('beforeunload', unloadCleanupHandler);
    }

    /**
     * 应用筛选表单值并刷新页面。
     */
    function applyAccountFilters(form, values) {
        const targetForm = form || accountFilterCard?.form || selectOne(`#${ACCOUNT_FILTER_FORM_ID}`).first();
        if (!targetForm) {
            return;
        }
        const filters = resolveAccountFilterValues(targetForm, values);
        const params = buildAccountSearchParams(filters);
        const action = targetForm.getAttribute('action') || global.location.pathname;
        const query = params.toString();
        global.location.href = query ? `${action}?${query}` : action;
    }

    /**
     * 重置表单并重新应用筛选。
     */
    function resetAccountFilters(form) {
        const targetForm = form || accountFilterCard?.form || selectOne(`#${ACCOUNT_FILTER_FORM_ID}`).first();
        if (targetForm) {
            targetForm.reset();
        }
        applyAccountFilters(targetForm, {});
    }

    /**
     * 序列化账户筛选参数为 URLSearchParams。
     */
    function buildAccountSearchParams(filters) {
        const params = new URLSearchParams();
        Object.entries(filters || {}).forEach(([key, value]) => {
            if (value === undefined || value === null) {
                return;
            }
            if (Array.isArray(value)) {
                value.forEach((item) => {
                    if (item !== null && item !== undefined) {
                        params.append(key, item);
                    }
                });
            } else {
                params.append(key, value);
            }
        });
        return params;
    }

    /**
     * 组合 form 与覆盖值，过滤空值。
     */
    function resolveAccountFilterValues(form, overrideValues) {
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

    /**
     * 递归清洗筛选值。
     */
    function sanitizeFilterValue(value) {
        if (Array.isArray(value)) {
            return LodashUtils.compact(value.map((item) => sanitizePrimitiveValue(item)));
        }
        return sanitizePrimitiveValue(value);
    }

    /**
     * 基础值清洗，剔除空字符串和 File。
     */
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

    /**
     * 将标签隐藏域拆分成数组。
     */
    function parseInitialTagValues(rawValue) {
        if (!rawValue) {
            return [];
        }
        return rawValue
            .split(',')
            .map((value) => value.trim())
            .filter(Boolean);
    }

    /**
     * 通用表单序列化，fallback 到 FormData。
     */
    function collectFormValues(form) {
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

    /**
     * 简单判断颜色深浅，供 UI 显示使用。
     */
    function isColorDark(colorStr) {
        if (!colorStr) {
            return false;
        }
        const tempDiv = document.createElement('div');
        tempDiv.style.color = colorStr;
        document.body.appendChild(tempDiv);

        const rgbColor = global.getComputedStyle(tempDiv).color;
        document.body.removeChild(tempDiv);

        const rgb = rgbColor.match(/\d+/g).map(Number);
        const [r, g, b] = rgb;
        const hsp = Math.sqrt(0.299 * (r * r) + 0.587 * (g * g) + 0.114 * (b * b));
        return hsp < 127.5;
    }

    function debugPermissionFunctions() {}

    global.syncAllAccounts = syncAllAccounts;
    global.syncAllInstances = syncAllInstances;
    global.viewAccount = viewAccount;
    global.showAccountStatistics = showAccountStatistics;
    global.debugPermissionFunctions = debugPermissionFunctions;
}

window.AccountsListPage = {
    mount: mountAccountsListPage,
};
