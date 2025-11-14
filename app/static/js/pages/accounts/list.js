/**
 * 账户列表页面JavaScript
 * 处理账户同步、权限查看、标签选择等功能
 */

// 页面加载完成后初始化
document.addEventListener('DOMContentLoaded', function() {
    initializeTagFilter();
});

// 同步所有账户
function syncAllAccounts() {
    const btn = event.target;
    const originalText = btn.innerHTML;

    btn.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>同步中...';
    btn.disabled = true;

    http.post('/account_sync/api/sync-all')
    .then(data => {
        if (data.success) {
            toast.success(data.message || '批量同步任务已启动');
            if (data.data?.manual_job_id) {
                toast.info(`任务线程: ${data.data.manual_job_id}`);
            }
        } else if (data.error) {
            toast.error(data.error);
        }
    })
    .catch(error => {
        console.error('Error:', error);
        toast.error('同步失败');
    })
    .finally(() => {
        btn.innerHTML = originalText;
        btn.disabled = false;
    });
}

// 保持向后兼容
function syncAllInstances() {
    syncAllAccounts();
}

// 查看账户详情
function viewAccount(accountId) {
    toast.info(`查看账户 ${accountId} 的详情`);
}

// 显示账户统计
function showAccountStatistics() {
    // 直接跳转到账户统计页面
    window.location.href = '/account-static/';
}

function initializeTagFilter() {
    if (!window.TagSelectorHelper) {
        console.warn('TagSelectorHelper 未加载，跳过标签筛选初始化');
        return;
    }

const ACCOUNT_FILTER_FORM_ID = 'account-filter-form';
const AUTO_APPLY_FILTER_CHANGE = true;
let accountFilterEventHandler = null;

document.addEventListener("DOMContentLoaded", () => {
  initializeAccountsListPage();
});

function initializeAccountsListPage() {
  initializeTagFilter();
  registerAccountFilterForm();
  subscribeAccountFilters();
}

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
            const form = document.getElementById(ACCOUNT_FILTER_FORM_ID);
            if (!form) {
                return;
            }
            if (window.EventBus) {
                EventBus.emit('filters:change', {
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

// 辅助函数：判断颜色是否为深色
function isColorDark(colorStr) {
    if (!colorStr) return false;

    // 创建一个临时元素来解析颜色
    const tempDiv = document.createElement('div');
    tempDiv.style.color = colorStr;
    document.body.appendChild(tempDiv);

    const rgbColor = window.getComputedStyle(tempDiv).color;
    document.body.removeChild(tempDiv);

    const rgb = rgbColor.match(/\d+/g).map(Number);
    const r = rgb[0];
    const g = rgb[1];
    const b = rgb[2];

    // 使用 HSP（高敏感度池）方程计算亮度
    const hsp = Math.sqrt(
        0.299 * (r * r) +
        0.587 * (g * g) +
        0.114 * (b * b)
    );

    return hsp < 127.5;
}

// CSRF Token处理已统一到csrf-utils.js中的全局getCSRFToken函数

// 权限调试功能
function debugPermissionFunctions() {
}


// 页面卸载时清理
window.addEventListener('beforeunload', function() {
    // 清理资源
});

// 导出函数供全局使用
window.syncAllAccounts = syncAllAccounts;
window.syncAllInstances = syncAllInstances;
window.viewAccount = viewAccount;
window.showAccountStatistics = showAccountStatistics;
window.debugPermissionFunctions = debugPermissionFunctions;

function registerAccountFilterForm() {
    if (!window.FilterUtils) {
        console.warn('FilterUtils 未加载，跳过账户筛选初始化');
        return;
    }
    const selector = `#${ACCOUNT_FILTER_FORM_ID}`;
    const form = document.querySelector(selector);
    if (!form) {
        return;
    }
    window.FilterUtils.registerFilterForm(selector, {
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
    if (!window.EventBus) {
        return;
    }
    const form = document.getElementById(ACCOUNT_FILTER_FORM_ID);
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
        EventBus.on(`filters:${action}`, handler);
    });
    accountFilterEventHandler = handler;
    window.addEventListener('beforeunload', cleanupAccountFilters, { once: true });
}

function cleanupAccountFilters() {
    if (!window.EventBus || !accountFilterEventHandler) {
        return;
    }
    ['change', 'submit', 'clear'].forEach((action) => {
        EventBus.off(`filters:${action}`, accountFilterEventHandler);
    });
    accountFilterEventHandler = null;
}

function applyAccountFilters(form, values) {
    const targetForm = form || document.getElementById(ACCOUNT_FILTER_FORM_ID);
    if (!targetForm) {
        return;
    }
    const data = values && Object.keys(values || {}).length ? values : collectFormValues(targetForm);
    const params = new URLSearchParams();
    Object.entries(data || {}).forEach(([key, value]) => {
        if (key === 'csrf_token') {
            return;
        }
        if (value === undefined || value === null) {
            return;
        }
        if (Array.isArray(value)) {
            value
                .filter((item) => item !== '' && item !== null)
                .forEach((item) => params.append(key, item));
        } else if (String(value).trim() !== '') {
            params.append(key, value);
        }
    });
    const action = targetForm.getAttribute('action') || window.location.pathname;
    const query = params.toString();
    window.location.href = query ? `${action}?${query}` : action;
}

function resetAccountFilters(form) {
    const targetForm = form || document.getElementById(ACCOUNT_FILTER_FORM_ID);
    if (targetForm) {
        targetForm.reset();
    }
    applyAccountFilters(targetForm, {});
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
