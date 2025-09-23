/**
 * 编辑实例页面JavaScript
 * 处理表单验证、数据库类型切换、标签选择、连接测试等功能
 */

// 全局变量
let editPageTagSelector = null;

// 页面加载完成后初始化
document.addEventListener('DOMContentLoaded', function() {
    console.log('DOMContentLoaded 事件触发，开始初始化标签选择器...');
    console.log('TagSelector 类可用性:', typeof TagSelector !== 'undefined');

    // 如果TagSelector类还没有加载，等待一下
    if (typeof TagSelector === 'undefined') {
        console.log('TagSelector类未加载，等待500ms后重试...');
        setTimeout(() => {
            console.log('延迟初始化，TagSelector 类可用性:', typeof TagSelector !== 'undefined');
            console.log('准备调用 initializeInstanceEditTagSelector()...');
            initializeInstanceEditTagSelector();
        }, 500);
    } else {
        console.log('TagSelector类已加载，立即调用 initializeInstanceEditTagSelector()...');
        console.log('准备调用 initializeInstanceEditTagSelector 函数...');
        try {
            console.log('正在调用 initializeInstanceEditTagSelector()...');
            console.log('initializeInstanceEditTagSelector 函数类型:', typeof initializeInstanceEditTagSelector);
            console.log('initializeInstanceEditTagSelector 函数存在:', initializeInstanceEditTagSelector !== undefined);

            if (typeof initializeInstanceEditTagSelector === 'function') {
                console.log('调用 initializeInstanceEditTagSelector 函数...');
                initializeInstanceEditTagSelector();
                console.log('initializeInstanceEditTagSelector() 调用完成');
            } else {
                console.error('initializeInstanceEditTagSelector 不是一个函数:', typeof initializeInstanceEditTagSelector);
            }
        } catch (error) {
            console.error('initializeInstanceEditTagSelector 调用失败:', error);
            console.error('错误堆栈:', error.stack);
        }
    }
    
    initializeForm();
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

/**
 * 打开标签选择器模态框
 * @function openTagSelector
 */
function openTagSelector() {
    const modalElement = document.getElementById('tagSelectorModal');
    if (!modalElement) {
        console.error('Tag selector modal not found');
        return;
    }

    const modal = new bootstrap.Modal(modalElement);

    // 确保在模态框显示后再初始化，避免DOM查找问题
    modalElement.addEventListener('shown.bs.modal', function () {
        if (!getTagSelector()) {
            const selector = initializeTagSelector({
                onSelectionChange: updateSelectedTagsUI
            });
            // 编辑页面需要设置已有的标签
            const currentTags = getCurrentTags();
            if (selector && currentTags.length > 0) {
                selector.setSelectedTags(currentTags);
            }
        }
    }, { once: true });

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
function initializeInstanceEditTagSelector() {
    console.log('=== initializeInstanceEditTagSelector 函数被调用 ===');
    console.log('函数开始执行...');
    console.log('当前时间:', new Date().toISOString());
    console.log('函数作用域检查...');

    try {
        console.log('开始初始化标签选择器...');
        console.log('TagSelector 类可用性:', typeof TagSelector !== 'undefined');

        // 查找容器元素
        const editPageSelector = document.getElementById('edit-page-tag-selector');
        console.log('容器元素:', editPageSelector ? '找到' : '未找到');

        if (editPageSelector) {
            const modalElement = editPageSelector.querySelector('#tagSelectorModal');
            console.log('模态框元素:', modalElement ? '找到' : '未找到');

            if (modalElement) {
                // 在模态框内部查找容器元素
                const containerElement = modalElement.querySelector('#tag-selector-container');
                console.log('容器元素:', containerElement ? '找到' : '未找到');

                if (containerElement) {
                    console.log('立即初始化TagSelector组件...');
                    initializeTagSelectorComponent(modalElement, containerElement);
                } else {
                    // 等待标签选择器组件加载完成
                    console.log('等待标签选择器组件加载...');
                    setTimeout(() => {
                        const delayedContainerElement = modalElement.querySelector('#tag-selector-container');

                        if (delayedContainerElement) {
                            console.log('延迟加载成功，初始化组件');
                            initializeTagSelectorComponent(modalElement, delayedContainerElement);
                        } else {
                            console.error('延迟加载失败，容器元素仍未找到');
                        }
                    }, 1000);
                }
            } else {
                console.error('模态框元素未找到');
            }
        } else {
            console.error('容器元素 edit-page-tag-selector 未找到');
        }

        // 添加额外的调试信息
        console.log('initializeInstanceEditTagSelector 完成，editPageTagSelector:', editPageTagSelector ? '已创建' : '未创建');

        // 如果初始化失败，提供强制初始化的建议
        if (!editPageTagSelector) {
            console.warn('正常初始化失败，可以尝试运行 forceInitializeTagSelector() 进行强制初始化');
        }
    } catch (error) {
        console.error('initializeInstanceEditTagSelector 函数执行出错:', error);
        console.error('错误堆栈:', error.stack);
        console.error('错误类型:', typeof error);
        console.error('错误消息:', error.message);
    }
}

// 初始化标签选择器组件
function initializeTagSelectorComponent(modalElement, containerElement) {
    console.log('开始初始化标签选择器组件...');
    console.log('TagSelector可用:', typeof TagSelector !== 'undefined');
    console.log('模态框元素:', modalElement ? '找到' : '未找到');
    console.log('容器元素:', containerElement ? '找到' : '未找到');

    if (typeof TagSelector !== 'undefined' && modalElement && containerElement) {
        try {
            // 获取当前实例的标签
            const currentTagNames = getCurrentTagNames();
            console.log('当前标签名称:', currentTagNames);
            
            // 初始化标签选择器
            console.log('创建TagSelector实例...');
            editPageTagSelector = new TagSelector('tag-selector-container', {
                allowMultiple: true,
                allowCreate: true,
                allowSearch: true,
                allowCategoryFilter: true
            });
            console.log('TagSelector实例创建成功');

            // 等待TagSelector完全初始化
            setTimeout(() => {
                console.log('检查TagSelector初始化状态...');
                console.log('editPageTagSelector存在:', !!editPageTagSelector);
                console.log('editPageTagSelector.container存在:', !!(editPageTagSelector && editPageTagSelector.container));
                console.log('editPageTagSelector类型:', typeof editPageTagSelector);

                if (editPageTagSelector && editPageTagSelector.container) {
                    console.log('TagSelector完全初始化完成');
                    console.log('TagSelector容器ID:', editPageTagSelector.containerId);
                    console.log('TagSelector选项:', editPageTagSelector.options);
                    setupTagSelectorEvents();
                    
                    // 设置当前选中的标签
                    if (currentTagNames.length > 0) {
                        console.log('设置当前选中的标签:', currentTagNames);
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
                } else {
                    console.error('TagSelector初始化失败');
                    console.error('editPageTagSelector:', editPageTagSelector);
                    if (editPageTagSelector) {
                        console.error('container:', editPageTagSelector.container);
                    }
                }
            }, 100);

            console.log('标签选择器组件初始化完成');
        } catch (error) {
            console.error('初始化标签选择器组件时出错:', error);
            showAlert('danger', '标签选择器初始化失败: ' + error.message);
        }
    } else {
        console.error('初始化失败:');
        console.error('- TagSelector可用:', typeof TagSelector !== 'undefined');
        console.error('- 模态框元素:', modalElement ? '找到' : '未找到');
        console.error('- 容器元素:', containerElement ? '找到' : '未找到');
    }
}

// 设置标签选择器事件
function setupTagSelectorEvents() {
    console.log('设置标签选择器事件...');

    // 检查依赖
    console.log('检查依赖环境:');
    console.log('- jQuery可用:', typeof $ !== 'undefined');
    console.log('- Bootstrap可用:', typeof bootstrap !== 'undefined');
    console.log('- TagSelector可用:', typeof TagSelector !== 'undefined');

    if (!editPageTagSelector) {
        console.error('editPageTagSelector未初始化，无法设置事件');
        return;
    }

    console.log('editPageTagSelector状态:');
    console.log('- 实例存在:', !!editPageTagSelector);
    console.log('- 容器存在:', !!editPageTagSelector.container);
    console.log('- 容器ID:', editPageTagSelector.containerId);
    console.log('- 选项:', editPageTagSelector.options);

    // 绑定打开标签选择器按钮
    const openBtn = document.getElementById('open-tag-selector-btn');
    console.log('打开按钮:', openBtn ? '找到' : '未找到');

    if (openBtn) {
        // 移除之前的事件监听器（如果有）
        openBtn.removeEventListener('click', openTagSelector);

        // 添加新的事件监听器
        openBtn.addEventListener('click', function(e) {
            console.log('打开标签选择器按钮被点击');
            e.preventDefault();

            try {
                if (typeof openTagSelector === 'function') {
                    openTagSelector();
                } else {
                    console.error('openTagSelector函数未定义');
                    // 直接显示模态框作为备用方案
                    const modal = new bootstrap.Modal(document.getElementById('tagSelectorModal'));
                    modal.show();
                }

                // 模态框显示后重新绑定按钮
                setTimeout(() => {
                    if (editPageTagSelector) {
                        console.log('重新绑定模态框按钮');
                        editPageTagSelector.rebindModalButtons();
                    } else {
                        console.warn('editPageTagSelector未初始化，无法重新绑定按钮');
                    }
                }, 100);
            } catch (error) {
                console.error('打开标签选择器时出错:', error);
                showAlert('danger', '打开标签选择器失败: ' + error.message);
            }
        });
        console.log('打开按钮事件绑定成功');
    } else {
        console.error('未找到打开标签选择器按钮 (id: open-tag-selector-btn)');
    }

    // 监听TagSelector的确认事件
    if (editPageTagSelector.container) {
        editPageTagSelector.container.addEventListener('tagSelectionConfirmed', function(event) {
            console.log('收到标签选择确认事件:', event.detail);
            const selectedTags = event.detail.selectedTags;
            updateSelectedTagsPreview(selectedTags);
            closeTagSelector();
        });

        // 监听TagSelector的取消事件
        editPageTagSelector.container.addEventListener('tagSelectionCancelled', function(event) {
            console.log('收到标签选择取消事件');
            closeTagSelector();
        });

        console.log('标签选择器事件监听器设置成功');
    }

    console.log('标签选择器事件设置完成');
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

// 强制初始化标签选择器（调试用）
function forceInitializeTagSelector() {
    console.log('强制初始化标签选择器...');
    
    const editPageSelector = document.getElementById('edit-page-tag-selector');
    const modalElement = editPageSelector?.querySelector('#tagSelectorModal');
    const containerElement = modalElement?.querySelector('#tag-selector-container');
    
    console.log('强制初始化 - 容器元素:', editPageSelector ? '找到' : '未找到');
    console.log('强制初始化 - 模态框元素:', modalElement ? '找到' : '未找到');
    console.log('强制初始化 - 容器元素:', containerElement ? '找到' : '未找到');
    console.log('强制初始化 - TagSelector可用:', typeof TagSelector !== 'undefined');
    
    if (typeof TagSelector !== 'undefined' && modalElement && containerElement) {
        console.log('强制创建TagSelector实例...');
        editPageTagSelector = new TagSelector('tag-selector-container', {
            allowMultiple: true,
            allowCreate: true,
            allowSearch: true,
            allowCategoryFilter: true
        });
        console.log('强制创建成功，editPageTagSelector:', editPageTagSelector ? '已创建' : '未创建');
        
        // 强制绑定打开按钮
        const openBtn = document.getElementById('open-tag-selector-btn');
        if (openBtn) {
            openBtn.addEventListener('click', function() {
                console.log('强制绑定的按钮被点击');
                openTagSelector();
            });
            console.log('强制绑定打开按钮成功');
        }
        
        // 测试确认按钮
        setTimeout(() => {
            const confirmBtn = document.getElementById('confirm-selection-btn');
            console.log('测试确认按钮:', confirmBtn ? '找到' : '未找到');
            if (confirmBtn) {
                console.log('确认按钮状态:', confirmBtn.disabled ? '禁用' : '启用');
                console.log('确认按钮可见性:', confirmBtn.offsetParent !== null ? '可见' : '隐藏');
                console.log('确认按钮点击事件:', confirmBtn.onclick ? '有' : '无');
            }
        }, 1000);
    }
}

// 调试函数
function debugTagSelector() {
    console.log('=== 标签选择器调试信息 ===');
    console.log('TagSelector 类:', typeof TagSelector);
    console.log('editPageTagSelector 实例:', editPageTagSelector ? '已创建' : '未创建');
    console.log('edit-page-tag-selector 容器:', document.getElementById('edit-page-tag-selector') ? '找到' : '未找到');
    console.log('tagSelectorModal 模态框:', document.getElementById('tagSelectorModal') ? '找到' : '未找到');
    console.log('tag-selector-container 容器:', document.getElementById('tag-selector-container') ? '找到' : '未找到');
    console.log('open-tag-selector-btn 按钮:', document.getElementById('open-tag-selector-btn') ? '找到' : '未找到');
    console.log('confirm-selection-btn 按钮:', document.getElementById('confirm-selection-btn') ? '找到' : '未找到');
    console.log('cancel-selection-btn 按钮:', document.getElementById('cancel-selection-btn') ? '找到' : '未找到');
    
    if (editPageTagSelector) {
        console.log('TagSelector 容器:', editPageTagSelector.container ? '找到' : '未找到');
        console.log('TagSelector 选项:', editPageTagSelector.options);
        console.log('TagSelector 已选择标签:', editPageTagSelector.getSelectedTags ? editPageTagSelector.getSelectedTags() : '方法不存在');
    }
    console.log('========================');
}

// 导出到全局作用域
window.initializeInstanceEditTagSelector = initializeInstanceEditTagSelector;
window.forceInitializeTagSelector = forceInitializeTagSelector;
window.debugTagSelector = debugTagSelector;
