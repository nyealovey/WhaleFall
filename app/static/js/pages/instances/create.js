/**
 * 创建实例页面 JavaScript
 * 统一使用 Just-Validate 进行表单验证，并保持标签选择器等交互。
 */

let instanceCreateValidator = null;

document.addEventListener('DOMContentLoaded', function () {
    initializeTagSelector();
    initializeForm();
});

// 初始化表单及其校验
function initializeForm() {
    initializeFormValidation();

    const dbTypeSelect = document.getElementById('db_type');
    if (dbTypeSelect) {
        dbTypeSelect.addEventListener('change', function () {
            handleDbTypeChange(this);
            if (instanceCreateValidator) {
                instanceCreateValidator.revalidateField('#db_type');
                instanceCreateValidator.revalidateField('#port');
            }
        });

        if (dbTypeSelect.value) {
            handleDbTypeChange(dbTypeSelect);
        }
    }

    const nameInput = document.getElementById('name');
    if (nameInput) {
        nameInput.addEventListener('blur', function () {
            if (instanceCreateValidator) {
                instanceCreateValidator.revalidateField('#name');
            }
        });
    }

    const hostInput = document.getElementById('host');
    if (hostInput) {
        hostInput.addEventListener('blur', function () {
            if (instanceCreateValidator) {
                instanceCreateValidator.revalidateField('#host');
            }
        });
    }

    const portInput = document.getElementById('port');
    if (portInput) {
        portInput.addEventListener('input', function () {
            if (instanceCreateValidator) {
                instanceCreateValidator.revalidateField('#port');
            }
        });
    }

    const credentialSelect = document.getElementById('credential_id');
    if (credentialSelect) {
        credentialSelect.addEventListener('change', function () {
            if (instanceCreateValidator) {
                instanceCreateValidator.revalidateField('#credential_id');
            }
        });
    }
}

function initializeFormValidation() {
    if (!window.FormValidator || !window.ValidationRules) {
        console.error('表单校验模块未正确加载');
        return;
    }

    instanceCreateValidator = window.FormValidator.create('#instanceForm');
    if (!instanceCreateValidator) {
        return;
    }

    instanceCreateValidator
        .useRules('#name', window.ValidationRules.instance.name)
        .useRules('#db_type', window.ValidationRules.instance.dbType)
        .useRules('#host', window.ValidationRules.instance.host)
        .useRules('#port', window.ValidationRules.instance.port)
        .useRules('#credential_id', window.ValidationRules.instance.credential)
        .onSuccess(function (event) {
            const form = event.target;
            showLoadingState(form, '创建中...');
            form.submit();
        })
        .onFail(function () {
            toast.error('请检查实例表单填写');
        });
}

// 处理数据库类型变化
function handleDbTypeChange(selectElement) {
    const select = selectElement || document.getElementById('db_type');
    if (!select) {
        return;
    }

    const portInput = document.getElementById('port');
    const databaseNameInput = document.getElementById('database_name');
    const oracleSidRow = document.getElementById('oracle-sid-row');
    const selectedOption = select.options[select.selectedIndex];
    const dbType = select.value;

    if (selectedOption && selectedOption.dataset.port && portInput) {
        portInput.value = selectedOption.dataset.port;
    }

    if (databaseNameInput && !databaseNameInput.value) {
        const defaultDatabaseNames = {
            mysql: 'mysql',
            postgresql: 'postgres',
            sqlserver: 'master',
            oracle: 'orcl',
        };

        if (defaultDatabaseNames[dbType]) {
            databaseNameInput.value = defaultDatabaseNames[dbType];
        }
    }

    if (oracleSidRow) {
        if (dbType === 'oracle') {
            oracleSidRow.style.display = 'block';
            oracleSidRow.classList.add('fade-in');
        } else {
            oracleSidRow.style.display = 'none';
            oracleSidRow.classList.remove('fade-in');
        }
    }
}

function showLoadingState(form, text) {
    const submitBtn = form.querySelector('button[type="submit"]');
    if (submitBtn) {
        submitBtn.dataset.originalText = submitBtn.dataset.originalText || submitBtn.innerHTML;
        submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>' + text;
        submitBtn.disabled = true;
    }
}

function restoreLoadingState(form) {
    const submitBtn = form.querySelector('button[type="submit"]');
    if (submitBtn && submitBtn.dataset.originalText) {
        submitBtn.innerHTML = submitBtn.dataset.originalText;
        submitBtn.disabled = false;
    }
}

/**
 * 以下为标签选择器及辅助方法实现
 */
function initializeTagSelector() {
    if (!window.TagSelectorHelper) {
        console.warn('TagSelectorHelper 未加载，跳过标签选择器初始化');
        return;
    }

    TagSelectorHelper.setupForForm({
        modalSelector: '#tagSelectorModal',
        rootSelector: '[data-tag-selector]',
        openButtonSelector: '#open-tag-selector-btn',
        previewSelector: '#selected-tags-preview',
        countSelector: '#selected-tags-count',
        chipsSelector: '#selected-tags-chips',
        hiddenInputSelector: '#selected-tag-names',
        hiddenValueKey: 'name',
    });
}

function resetForm() {
    const form = document.getElementById('instanceForm');
    form.reset();

    restoreLoadingState(form);

    const oracleSidRow = document.getElementById('oracle-sid-row');
    if (oracleSidRow) {
        oracleSidRow.style.display = 'none';
    }

    const preview = document.getElementById('selected-tags-preview');
    const count = document.getElementById('selected-tags-count');
    const chips = document.getElementById('selected-tags-chips');
    const hiddenInput = document.getElementById('selected-tag-names');

    if (preview) preview.style.display = 'none';
    if (count) count.textContent = '未选择标签';
    if (chips) chips.innerHTML = '';
    if (hiddenInput) hiddenInput.value = '';

    const selectorInstance = window.tagSelectorManager?.get('[data-tag-selector]');
    if (selectorInstance && typeof selectorInstance.clearSelection === 'function') {
        selectorInstance.clearSelection({ silent: true });
    }

    if (instanceCreateValidator) {
        instanceCreateValidator.revalidate();
    }
}

function previewInstance() {
    const form = document.getElementById('instanceForm');
    const formData = new FormData(form);

    const preview = {
        name: formData.get('name'),
        db_type: formData.get('db_type'),
        host: formData.get('host'),
        port: formData.get('port'),
        database_name: formData.get('database_name'),
        oracle_sid: formData.get('oracle_sid'),
        description: formData.get('description'),
    };

    return preview;
}

window.previewInstance = previewInstance;
window.resetForm = resetForm;
