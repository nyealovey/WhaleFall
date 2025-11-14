(function (global) {
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

    let accountFilterEventHandler = null;
    let unloadCleanupHandler = null;

    ready(initializeAccountsListPage);

    function initializeAccountsListPage() {
        initializeTagFilter();
        registerAccountFilterForm();
        subscribeAccountFilters();
    }

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

        return instanceService
            .syncAllAccounts()
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

    function syncAllInstances(trigger) {
        return syncAllAccounts(trigger);
    }

    function viewAccount(accountId) {
        global.toast.info(`查看账户 ${accountId} 的详情`);
    }

    function showAccountStatistics() {
        global.location.href = '/account-static/';
    }

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
                if (global.EventBus) {
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

    function registerAccountFilterForm() {
        if (!global.FilterUtils) {
            console.warn('FilterUtils 未加载，跳过账户筛选初始化');
            return;
        }

        const selector = `#${ACCOUNT_FILTER_FORM_ID}`;
        const form = selectOne(selector);
        if (!form.length) {
            return;
        }

        global.FilterUtils.registerFilterForm(selector, {
            onSubmit: ({ form, event }) => {
                event?.preventDefault?.();
                applyAccountFilters(form);
            },
            onClear: ({ form, event }) => {
                event?.preventDefault?.();
                resetAccountFilters(form);
            },
            autoSubmitOnChange: true,
        });
    }

    function subscribeAccountFilters() {
        if (!global.EventBus) {
            return;
        }
        const form = selectOne(`#${ACCOUNT_FILTER_FORM_ID}`).first();
        if (!form) {
            return;
        }
        const handler = (detail) => {
            if (!detail) {
                return;
            }
            const incoming = (detail.formId || '').replace(/^#/, '');
            if (incoming !== ACCOUNT_FILTER_FORM_ID) {
                return;
            }
            switch (detail.action) {
                case 'clear':
                    resetAccountFilters(form);
                    break;
                case 'change':
                    if (AUTO_APPLY_FILTER_CHANGE) {
                        applyAccountFilters(form, detail.values);
                    }
                    break;
                case 'submit':
                    applyAccountFilters(form, detail.values);
                    break;
                default:
                    break;
            }
        };

        ['change', 'submit', 'clear'].forEach((action) => {
            global.EventBus.on(`filters:${action}`, handler);
        });
        accountFilterEventHandler = handler;

        unloadCleanupHandler = () => {
            cleanupAccountFilters();
            from(global).off('beforeunload', unloadCleanupHandler);
        };
        from(global).on('beforeunload', unloadCleanupHandler);
    }

    function cleanupAccountFilters() {
        if (!global.EventBus || !accountFilterEventHandler) {
            return;
        }
        ['change', 'submit', 'clear'].forEach((action) => {
            global.EventBus.off(`filters:${action}`, accountFilterEventHandler);
        });
        accountFilterEventHandler = null;
    }

    function applyAccountFilters(form, values) {
        const targetForm = form || selectOne(`#${ACCOUNT_FILTER_FORM_ID}`).first();
        if (!targetForm) {
            return;
        }
        const filters = resolveAccountFilterValues(targetForm, values);
        const params = buildAccountSearchParams(filters);
        const action = targetForm.getAttribute('action') || global.location.pathname;
        const query = params.toString();
        global.location.href = query ? `${action}?${query}` : action;
    }

    function resetAccountFilters(form) {
        const targetForm = form || selectOne(`#${ACCOUNT_FILTER_FORM_ID}`).first();
        if (targetForm) {
            targetForm.reset();
        }
        applyAccountFilters(targetForm, {});
    }

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
})(window);
