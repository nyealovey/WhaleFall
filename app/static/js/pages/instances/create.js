/**
 * 创建实例页面 JavaScript
 * 统一使用 Just-Validate 进行表单验证，并保持标签选择器等交互。
 */

let createPageTagSelector = null;
let instanceCreateValidator = null;

document.addEventListener('DOMContentLoaded', function () {
    // 同步或延迟初始化标签选择器
    if (typeof TagSelector === 'undefined') {
        setTimeout(() => {
            initializeInstanceCreateTagSelector();
        }, 500);
    } else {
        try {
            if (typeof initializeInstanceCreateTagSelector === 'function') {
                initializeInstanceCreateTagSelector();
            }
        } catch (error) {
            console.error('initializeInstanceCreateTagSelector 调用失败:', error);
        }
    }

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

function openTagSelector() {
    const modalElement = document.getElementById('tagSelectorModal');
    if (!modalElement) {
        console.error('Tag selector modal not found');
        return;
    }

    const modal = new bootstrap.Modal(modalElement);

    modalElement.addEventListener(
        'shown.bs.modal',
        function () {
            if (!getTagSelector()) {
                const selector = initializeTagSelector({
                    onSelectionChange: updateSelectedTagsPreview,
                });
                if (selector && createPageTagSelector) {
                    const selectedTags = createPageTagSelector.getSelectedTags();
                    updateSelectedTagsPreview(selectedTags);
                }
            }
        },
        { once: true }
    );

    modal.show();
}

function closeTagSelector() {
    const modal = bootstrap.Modal.getInstance(document.getElementById('tagSelectorModal'));
    if (modal) {
        modal.hide();
    }
}

function initializeInstanceCreateTagSelector() {
    try {
        const createPageSelector = document.getElementById('create-page-tag-selector');

        if (createPageSelector) {
            const modalElement = createPageSelector.querySelector('#tagSelectorModal');

            if (modalElement) {
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
    } catch (error) {
        console.error('initializeInstanceCreateTagSelector 函数执行出错:', error);
    }
}

function initializeTagSelectorComponent(modalElement, containerElement) {
    if (typeof TagSelector !== 'undefined' && modalElement && containerElement) {
        try {
            createPageTagSelector = new TagSelector('tag-selector-container', {
                allowMultiple: true,
                allowCreate: true,
                allowSearch: true,
                allowCategoryFilter: true,
            });

            setTimeout(() => {
                if (createPageTagSelector && createPageTagSelector.container) {
                    setupTagSelectorEvents();
                }
            }, 100);
        } catch (error) {
            console.error('初始化标签选择器组件时出错:', error);
            toast.error('标签选择器初始化失败: ' + error.message);
        }
    }
}

function setupTagSelectorEvents() {
    if (!createPageTagSelector) {
        return;
    }

    const openBtn = document.getElementById('open-tag-selector-btn');

    if (openBtn) {
        openBtn.removeEventListener('click', openTagSelector);

        openBtn.addEventListener('click', function (e) {
            e.preventDefault();

            try {
                if (typeof openTagSelector === 'function') {
                    openTagSelector();
                } else {
                    const modal = new bootstrap.Modal(document.getElementById('tagSelectorModal'));
                    modal.show();
                }

                setTimeout(() => {
                    if (createPageTagSelector) {
                        createPageTagSelector.rebindModalButtons();
                    }
                }, 100);
            } catch (error) {
                console.error('打开标签选择器时出错:', error);
                toast.error('打开标签选择器失败: ' + error.message);
            }
        });
    }

    if (createPageTagSelector.container) {
        createPageTagSelector.container.addEventListener('tagSelectionConfirmed', function (event) {
            const selectedTags = event.detail.selectedTags;
            updateSelectedTagsPreview(selectedTags);
            closeTagSelector();
        });

        createPageTagSelector.container.addEventListener('tagSelectionCancelled', function () {
            closeTagSelector();
        });
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
            chips.innerHTML = selectedTags
                .map(
                    (tag) => `
                <span class="badge bg-${tag.color} me-1 mb-1">
                    <i class="fas fa-tag me-1"></i>${tag.display_name}
                    <button type="button" class="btn-close btn-close-white ms-1" 
                            onclick="removeTagFromPreview('${tag.name}')" 
                            style="font-size: 0.6em;"></button>
                </span>
            `
                )
                .join('');
        }

        if (hiddenInput) {
            hiddenInput.value = selectedTags.map((tag) => tag.name).join(',');
        }
    } else {
        if (preview) preview.style.display = 'none';
        if (count) count.textContent = '未选择标签';
        if (hiddenInput) hiddenInput.value = '';
    }
}

function removeTagFromPreview(tagName) {
    if (createPageTagSelector) {
        const tag = createPageTagSelector.availableTags.find((t) => t.name === tagName);
        if (tag) {
            createPageTagSelector.toggleTag(tag.id);
            const selectedTags = createPageTagSelector.getSelectedTags();
            updateSelectedTagsPreview(selectedTags);
        }
    }
}

function resetForm() {
    const form = document.getElementById('instanceForm');
    form.reset();

    restoreLoadingState(form);

    const oracleSidRow = document.getElementById('oracle-sid-row');
    if (oracleSidRow) {
        oracleSidRow.style.display = 'none';
    }

    if (createPageTagSelector) {
        createPageTagSelector.clearSelection();
        updateSelectedTagsPreview([]);
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

window.initializeInstanceCreateTagSelector = initializeInstanceCreateTagSelector;
window.previewInstance = previewInstance;
window.resetForm = resetForm;
