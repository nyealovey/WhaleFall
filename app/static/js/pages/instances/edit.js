/**
 * 编辑实例页面JavaScript
 * 处理表单验证、数据库类型切换、标签选择、连接测试等功能
 */

// 全局变量
let editPageTagSelector = null;

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
    
    // 设置默认数据库名称（仅在字段为空时设置）
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
    submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>保存中...';
    submitBtn.disabled = true;
    
    // 如果保存失败，恢复按钮状态
    setTimeout(() => {
        submitBtn.innerHTML = originalText;
        submitBtn.disabled = false;
    }, 5000);
}

// 测试连接功能
function testConnection() {
    const testBtn = event.target;
    const originalText = testBtn.innerHTML;
    
    testBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>测试中...';
    testBtn.disabled = true;
    
    // 获取CSRF token
    const csrfToken = getCSRFToken();
    const instanceId = getInstanceId();
    
    console.log('测试连接 - 实例ID:', instanceId);
    console.log('测试连接 - CSRF Token:', csrfToken);
    console.log('测试连接 - API URL:', `/instances/api/instances/${instanceId}/test`);
    
    fetch(`/instances/api/instances/${instanceId}/test`, {
        method: 'GET',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': csrfToken
        }
    })
    .then(response => response.json())
    .then(data => {
        const resultDiv = document.getElementById('testResult');
        const contentDiv = document.getElementById('testResultContent');
        
        if (data.success) {
            contentDiv.innerHTML = `
                <div class="alert alert-success">
                    <i class="fas fa-check-circle me-2"></i>
                    <strong>连接成功！</strong><br>
                    ${data.message || '数据库连接正常'}
                </div>
            `;
        } else {
            // 构建详细的错误信息
            let errorHtml = `
                <div class="alert alert-danger">
                    <i class="fas fa-exclamation-triangle me-2"></i>
                    <strong>连接失败！</strong><br>
                    <strong>错误类型：</strong>${data.error || '未知错误'}<br>
            `;
            
            // 添加详细信息
            if (data.details) {
                errorHtml += `<strong>详细信息：</strong>${data.details}<br>`;
            }
            
            // 添加解决方案
            if (data.solution) {
                errorHtml += `<strong>解决方案：</strong>${data.solution}<br>`;
            }
            
            // 添加错误类型
            if (data.error_type) {
                errorHtml += `<small class="text-muted">错误类型: ${data.error_type}</small>`;
            }
            
            errorHtml += `</div>`;
            
            contentDiv.innerHTML = errorHtml;
        }
        
        resultDiv.style.display = 'block';
    })
    .catch(error => {
        const resultDiv = document.getElementById('testResult');
        const contentDiv = document.getElementById('testResultContent');
        
        contentDiv.innerHTML = `
            <div class="alert alert-danger">
                <i class="fas fa-exclamation-triangle me-2"></i>
                <strong>测试失败！</strong><br>
                网络错误或服务器无响应
            </div>
        `;
        resultDiv.style.display = 'block';
    })
    .finally(() => {
        testBtn.innerHTML = originalText;
        testBtn.disabled = false;
    });
}

// 打开标签选择器
function openTagSelector() {
    const modal = new bootstrap.Modal(document.getElementById('tagSelectorModal'));
    modal.show();
}

// 关闭标签选择器
function closeTagSelector() {
    const modal = bootstrap.Modal.getInstance(document.getElementById('tagSelectorModal'));
    if (modal) {
        modal.hide();
    }
}

// 初始化标签选择器
function initializeTagSelector() {
    // 等待标签选择器组件加载完成
    setTimeout(() => {
        if (typeof TagSelector !== 'undefined' && document.getElementById('tag-selector-container')) {
            // 获取当前实例的标签
            const currentTagNames = getCurrentTagNames();
            
            // 初始化标签选择器
            editPageTagSelector = new TagSelector('tag-selector-container', {
                allowMultiple: true,
                allowCreate: true,
                allowSearch: true,
                allowCategoryFilter: true
            });
            
            // 绑定打开标签选择器按钮
            const openBtn = document.getElementById('open-tag-selector-btn');
            if (openBtn) {
                openBtn.addEventListener('click', function() {
                    openTagSelector();
                    
                    // 模态框显示后重新绑定按钮
                    setTimeout(() => {
                        if (editPageTagSelector) {
                            editPageTagSelector.rebindModalButtons();
                        }
                    }, 100);
                });
            }
            
            // 绑定确认选择按钮
            const confirmBtn = document.getElementById('confirm-selection-btn');
            if (confirmBtn) {
                confirmBtn.addEventListener('click', confirmTagSelection);
            }
            
            // 设置当前选中的标签
            if (currentTagNames.length > 0) {
                // 等待标签加载完成后再设置选中状态
                setTimeout(() => {
                    const allTags = editPageTagSelector.availableTags;
                    const currentTagIds = allTags
                        .filter(tag => currentTagNames.includes(tag.name))
                        .map(tag => tag.id);
                    editPageTagSelector.setSelectedTags(currentTagIds);
                    // 更新预览显示
                    updateSelectedTagsPreview(editPageTagSelector.getSelectedTags());
                }, 200);
            }
        }
    }, 100);
}

// 获取当前标签名称
function getCurrentTagNames() {
    // 从页面中获取当前标签名称
    const tagNamesElement = document.querySelector('[data-current-tags]');
    if (tagNamesElement) {
        try {
            return JSON.parse(tagNamesElement.dataset.currentTags);
        } catch (error) {
            console.error('解析当前标签失败:', error);
            return [];
        }
    }
    
    // 如果没有data属性，尝试从全局变量获取
    if (typeof window.currentTagNames !== 'undefined') {
        return window.currentTagNames;
    }
    
    return [];
}

// 确认标签选择
function confirmTagSelection() {
    if (editPageTagSelector) {
        // 直接调用标签选择器的确认方法
        editPageTagSelector.confirmSelection();
        
        // 获取选中的标签并更新预览
        const selectedTags = editPageTagSelector.getSelectedTags();
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
    if (editPageTagSelector) {
        const tag = editPageTagSelector.availableTags.find(t => t.name === tagName);
        if (tag) {
            editPageTagSelector.toggleTag(tag.id);
            const selectedTags = editPageTagSelector.getSelectedTags();
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

// 工具函数
function getInstanceId() {
    // 从页面URL中获取实例ID
    const urlParts = window.location.pathname.split('/');
    let instanceId = urlParts[urlParts.length - 1];
    
    // 如果最后一部分是'edit'，则取倒数第二部分
    if (instanceId === 'edit') {
        instanceId = urlParts[urlParts.length - 2];
    }
    
    console.log('当前URL:', window.location.pathname);
    console.log('解析的实例ID:', instanceId);
    return instanceId;
}

function getCSRFToken() {
    return document.querySelector('input[name="csrf_token"]')?.value || '';
}
