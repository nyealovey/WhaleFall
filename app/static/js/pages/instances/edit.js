/**
 * 编辑实例页面 JavaScript
 * 使用 Just-Validate 统一表单验证，同时保留标签选择与连接测试等能力。
 */

let editPageTagSelector = null;
let instanceEditValidator = null;

document.addEventListener('DOMContentLoaded', function () {
    if (typeof TagSelector === 'undefined') {
        setTimeout(() => {
            initializeInstanceEditTagSelector();
        }, 500);
    } else {
        try {
            if (typeof initializeInstanceEditTagSelector === 'function') {
                initializeInstanceEditTagSelector();
            }
        } catch (error) {
            console.error('initializeInstanceEditTagSelector 调用失败:', error);
        }
    }

    initializeForm();
});

function initializeForm() {
    initializeFormValidation();

    const dbTypeSelect = document.getElementById('db_type');
    if (dbTypeSelect) {
        dbTypeSelect.addEventListener('change', function () {
            handleDbTypeChange(this);
            if (instanceEditValidator) {
                instanceEditValidator.revalidateField('#db_type');
                instanceEditValidator.revalidateField('#port');
            }
        });

        if (dbTypeSelect.value) {
            handleDbTypeChange(dbTypeSelect);
        }
    }

    const nameInput = document.getElementById('name');
    if (nameInput) {
        nameInput.addEventListener('blur', function () {
            if (instanceEditValidator) {
                instanceEditValidator.revalidateField('#name');
            }
        });
    }

    const hostInput = document.getElementById('host');
    if (hostInput) {
        hostInput.addEventListener('blur', function () {
            if (instanceEditValidator) {
                instanceEditValidator.revalidateField('#host');
            }
        });
    }

    const portInput = document.getElementById('port');
    if (portInput) {
        portInput.addEventListener('input', function () {
            if (instanceEditValidator) {
                instanceEditValidator.revalidateField('#port');
            }
        });
    }

    const credentialSelect = document.getElementById('credential_id');
    if (credentialSelect) {
        credentialSelect.addEventListener('change', function () {
            if (instanceEditValidator) {
                instanceEditValidator.revalidateField('#credential_id');
            }
        });
    }
}

function initializeFormValidation() {
    if (!window.FormValidator || !window.ValidationRules) {
        console.error('表单校验模块未正确加载');
        return;
    }

    instanceEditValidator = window.FormValidator.create('#instanceForm');
    if (!instanceEditValidator) {
        return;
    }

    instanceEditValidator
        .useRules('#name', window.ValidationRules.instance.name)
        .useRules('#db_type', window.ValidationRules.instance.dbType)
        .useRules('#host', window.ValidationRules.instance.host)
        .useRules('#port', window.ValidationRules.instance.port)
        .useRules('#credential_id', window.ValidationRules.instance.credential)
        .onSuccess(function (event) {
            const form = event.target;
            showLoadingState(form, '保存中...');
            form.submit();
        })
        .onFail(function () {
            toast.error('请检查实例表单填写');
        });
}

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

function testConnection(evt) {
    const eventObj = evt || window.event || null;
    const testBtn =
        (eventObj && eventObj.currentTarget) ||
        (eventObj && eventObj.target) ||
        document.querySelector('button[onclick*="testConnection"]');
    if (!testBtn) {
        return;
    }

    const originalText = testBtn.innerHTML;
    testBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>测试中...';
    testBtn.disabled = true;

    const instanceId = getInstanceId();

    connectionManager
        .testInstanceConnection(instanceId, {
            onSuccess: (data) => {
                const resultDiv = document.getElementById('testResult');
                connectionManager.showTestResult(data, 'testResultContent');
                resultDiv.style.display = 'block';
            },
            onError: (error) => {
                const resultDiv = document.getElementById('testResult');
                connectionManager.showTestResult(error, 'testResultContent');
                resultDiv.style.display = 'block';
            },
        })
        .finally(() => {
            testBtn.innerHTML = originalText;
            testBtn.disabled = false;
        });
}

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
                const currentTags = getCurrentTagNames();
                if (selector && currentTags.length > 0) {
                    selector.setSelectedTags(currentTags);
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

function initializeInstanceEditTagSelector() {
    try {
        const editPageSelector = document.getElementById('edit-page-tag-selector');

        if (editPageSelector) {
            const modalElement = editPageSelector.querySelector('#tagSelectorModal');

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
        console.error('initializeInstanceEditTagSelector 函数执行出错:', error);
    }
}

function initializeTagSelectorComponent(modalElement, containerElement) {
    if (typeof TagSelector !== 'undefined' && modalElement && containerElement) {
        try {
            const currentTagNames = getCurrentTagNames();

            editPageTagSelector = new TagSelector('tag-selector-container', {
                allowMultiple: true,
                allowCreate: true,
                allowSearch: true,
                allowCategoryFilter: true,
            });

            setTimeout(() => {
                if (editPageTagSelector && editPageTagSelector.container) {
                    setupTagSelectorEvents();

                    if (currentTagNames.length > 0) {
                        setTimeout(() => {
                            const allTags = editPageTagSelector.allTags || [];
                            const currentTagIds = allTags
                                .filter((tag) => currentTagNames.includes(tag.name))
                                .map((tag) => tag.id);
                            editPageTagSelector.setSelectedTags(currentTagIds);
                            updateSelectedTagsPreview(editPageTagSelector.getSelectedTags());
                        }, 200);
                    }
                }
            }, 100);
        } catch (error) {
            console.error('初始化标签选择器组件时出错:', error);
            toast.error('标签选择器初始化失败: ' + error.message);
        }
    }
}

function setupTagSelectorEvents() {
    if (!editPageTagSelector) {
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
                    if (editPageTagSelector) {
                        editPageTagSelector.rebindModalButtons();
                    }
                }, 100);
            } catch (error) {
                console.error('打开标签选择器时出错:', error);
                toast.error('打开标签选择器失败: ' + error.message);
            }
        });
    }

    if (editPageTagSelector.container) {
        editPageTagSelector.container.addEventListener('tagSelectionConfirmed', function (event) {
            const selectedTags = event.detail.selectedTags;
            updateSelectedTagsPreview(selectedTags);
            closeTagSelector();
        });

        editPageTagSelector.container.addEventListener('tagSelectionCancelled', function () {
            closeTagSelector();
        });
    }
}

function getCurrentTagNames() {
    const tagNamesElement = document.querySelector('[data-current-tags]');
    if (tagNamesElement) {
        try {
            const value = tagNamesElement.dataset.currentTags;
            if (!value) {
                return [];
            }
            const parsed = JSON.parse(value);
            if (Array.isArray(parsed)) {
                return parsed;
            }
            return [];
        } catch (error) {
            console.error('解析当前标签失败:', error);
            return [];
        }
    }

    if (Array.isArray(window.currentTagNames)) {
        return window.currentTagNames;
    }

    return [];
}

function confirmTagSelection() {
    if (editPageTagSelector) {
        editPageTagSelector.confirmSelection();
        const selectedTags = editPageTagSelector.getSelectedTags();
        updateSelectedTagsPreview(selectedTags);
        closeTagSelector();
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
    if (editPageTagSelector) {
        const tag = editPageTagSelector.availableTags.find((t) => t.name === tagName);
        if (tag) {
            editPageTagSelector.toggleTag(tag.id);
            const selectedTags = editPageTagSelector.getSelectedTags();
            updateSelectedTagsPreview(selectedTags);
        }
    }
}

function getInstanceId() {
    const urlParts = window.location.pathname.split('/');
    let instanceId = urlParts[urlParts.length - 1];

    if (instanceId === 'edit') {
        instanceId = urlParts[urlParts.length - 2];
    }

    return instanceId;
}

window.initializeInstanceEditTagSelector = initializeInstanceEditTagSelector;
window.confirmTagSelection = confirmTagSelection;
window.removeTagFromPreview = removeTagFromPreview;
window.testConnection = testConnection;
