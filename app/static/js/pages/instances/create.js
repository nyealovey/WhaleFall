/**
 * 创建实例页面JavaScript
 * 处理表单验证、数据库类型切换、标签选择等功能
 */

// 全局变量
let createPageTagSelector = null;

// 页面加载完成后初始化
document.addEventListener('DOMContentLoaded', function() {
    initializeForm();
    initializeTagSelector();
});

// 初始化表单
function initializeForm() {
    const dbTypeSelect = document.getElementById('db_type');
    if (dbTypeSelect) {
        dbTypeSelect.addEventListener('change', handleDbTypeChange);
    }

    const instanceForm = document.getElementById('instanceForm');
    if (instanceForm) {
        instanceForm.addEventListener('submit', handleFormSubmit);
    }
}

// 处理数据库类型变化
function handleDbTypeChange() {
    const portInput = document.getElementById('port');
    const databaseNameInput = document.getElementById('database_name');
    const oracleSidRow = document.getElementById('oracle-sid-row');
    const selectedOption = this.options[this.selectedIndex];
    const dbType = this.value;
    
    // 使用动态的默认端口
    if (selectedOption && selectedOption.dataset.port) {
        portInput.value = selectedOption.dataset.port;
    }
    
    // 设置默认数据库名称
    if (!databaseNameInput.value) {
        const defaultDatabaseNames = {
            'mysql': 'mysql',
            'postgresql': 'postgres',
            'sqlserver': 'master',
            'oracle': 'orcl'
        };
        
        if (defaultDatabaseNames[dbType]) {
            databaseNameInput.value = defaultDatabaseNames[dbType];
        }
    }
    
    // 控制Oracle SID字段的显示
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

// 处理表单提交
function handleFormSubmit(e) {
    const submitBtn = this.querySelector('button[type="submit"]');
    const originalText = submitBtn.innerHTML;
    
    // 显示加载状态
    submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>创建中...';
    submitBtn.disabled = true;
    
    // 如果创建失败，恢复按钮状态
    setTimeout(() => {
        submitBtn.innerHTML = originalText;
        submitBtn.disabled = false;
    }, 5000);
}

// 初始化标签选择器
function initializeTagSelector() {
    // 立即检查元素
    const createPageSelector = document.getElementById('create-page-tag-selector');
    
    if (createPageSelector) {
        const modalElement = createPageSelector.querySelector('#tagSelectorModal');
        
        if (modalElement) {
            // 在模态框内部查找容器元素
            const containerElement = modalElement.querySelector('#tag-selector-container');
            
            if (containerElement) {
                initializeTagSelectorComponent(modalElement, containerElement);
            } else {
                // 等待标签选择器组件加载完成
                setTimeout(() => {
                    const delayedContainerElement = modalElement.querySelector('#tag-selector-container');
                    
                    if (delayedContainerElement) {
                        initializeTagSelectorComponent(modalElement, delayedContainerElement);
                    }
                }, 1000);
            }
        }
    }
}

// 初始化标签选择器组件
function initializeTagSelectorComponent(modalElement, containerElement) {
    if (typeof TagSelector !== 'undefined' && modalElement && containerElement) {
        // 初始化标签选择器
        createPageTagSelector = new TagSelector('tag-selector-container', {
            allowMultiple: true,
            allowCreate: true,
            allowSearch: true,
            allowCategoryFilter: true
        });
        
        // 绑定打开标签选择器按钮
        const openBtn = document.getElementById('open-tag-selector-btn');
        if (openBtn) {
            openBtn.addEventListener('click', function() {
                if (typeof openTagSelector === 'function') {
                    openTagSelector();
                } else {
                    console.error('openTagSelector函数未定义');
                }
            });
        } else {
            console.error('找不到open-tag-selector-btn按钮');
        }
        
        // 绑定确认选择按钮
        const confirmBtn = document.getElementById('confirm-tag-selection');
        if (confirmBtn) {
            confirmBtn.addEventListener('click', confirmTagSelection);
        } else {
            console.error('找不到confirm-tag-selection按钮');
        }
    } else {
        console.error('初始化失败:');
        console.error('- TagSelector可用:', typeof TagSelector !== 'undefined');
        console.error('- 模态框元素:', modalElement ? '找到' : '未找到');
        console.error('- 容器元素:', containerElement ? '找到' : '未找到');
    }
}

// 确认标签选择
function confirmTagSelection() {
    if (createPageTagSelector) {
        const selectedTags = createPageTagSelector.getSelectedTags();
        updateSelectedTagsPreview(selectedTags);
        closeTagSelector();
    }
}

// 更新选中标签预览
function updateSelectedTagsPreview(selectedTags) {
    const preview = document.getElementById('selected-tags-preview');
    const count = document.getElementById('selected-tags-count');
    const chips = document.getElementById('selected-tags-chips');
    const hiddenInput = document.getElementById('selected-tag-names');
    
    if (selectedTags.length > 0) {
        if (preview) preview.style.display = 'block';
        if (count) count.textContent = `已选择 ${selectedTags.length} 个标签`;
        
        if (chips) {
            chips.innerHTML = selectedTags.map(tag => `
                <span class="badge bg-${tag.color} me-1 mb-1">
                    <i class="fas fa-tag me-1"></i>${tag.display_name}
                    <button type="button" class="btn-close btn-close-white ms-1" 
                            onclick="removeTagFromPreview('${tag.name}')" 
                            style="font-size: 0.6em;"></button>
                </span>
            `).join('');
        }
        
        if (hiddenInput) {
            hiddenInput.value = selectedTags.map(tag => tag.name).join(',');
        }
    } else {
        if (preview) preview.style.display = 'none';
        if (count) count.textContent = '未选择标签';
        if (hiddenInput) hiddenInput.value = '';
    }
}

// 从预览中移除标签
function removeTagFromPreview(tagName) {
    if (createPageTagSelector) {
        const tag = createPageTagSelector.availableTags.find(t => t.name === tagName);
        if (tag) {
            createPageTagSelector.toggleTag(tag.id);
            const selectedTags = createPageTagSelector.getSelectedTags();
            updateSelectedTagsPreview(selectedTags);
        }
    }
}

// 显示提示信息
function showAlert(type, message) {
    const alertDiv = document.createElement('div');
    alertDiv.className = `alert alert-${type} alert-dismissible fade show`;
    alertDiv.innerHTML = `
        <i class="fas fa-${type === 'success' ? 'check-circle' : 'exclamation-triangle'} me-2"></i>
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    
    const container = document.querySelector('.container');
    if (container) {
        container.insertBefore(alertDiv, container.firstChild);
    }
    
    setTimeout(() => {
        alertDiv.remove();
    }, 5000);
}

// 表单验证
function validateForm() {
    const form = document.getElementById('instanceForm');
    const requiredFields = form.querySelectorAll('[required]');
    let isValid = true;
    
    requiredFields.forEach(field => {
        if (!field.value.trim()) {
            field.classList.add('is-invalid');
            isValid = false;
        } else {
            field.classList.remove('is-invalid');
            field.classList.add('is-valid');
        }
    });
    
    return isValid;
}

// 重置表单
function resetForm() {
    const form = document.getElementById('instanceForm');
    form.reset();
    
    // 清除验证状态
    const fields = form.querySelectorAll('.is-valid, .is-invalid');
    fields.forEach(field => {
        field.classList.remove('is-valid', 'is-invalid');
    });
    
    // 隐藏Oracle SID字段
    const oracleSidRow = document.getElementById('oracle-sid-row');
    if (oracleSidRow) {
        oracleSidRow.style.display = 'none';
    }
    
    // 清空标签选择
    if (createPageTagSelector) {
        createPageTagSelector.clearSelection();
        updateSelectedTagsPreview([]);
    }
}

// 预览实例信息
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
        description: formData.get('description')
    };
    
    // 显示预览信息
    console.log('实例预览:', preview);
    
    return preview;
}
