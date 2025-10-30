/* 账户分类管理页面JavaScript */

// 引入console工具函数
if (typeof logErrorWithContext === 'undefined') {
    // console-utils.js not loaded, using fallback logging
    window.logErrorWithContext = function (error, context, additionalContext) {
        console.error(`错误处理: ${context}`, error, additionalContext);
    };
}

// CSRF Token处理已统一到csrf-utils.js中的全局getCSRFToken函数

// 全局变量
let currentClassificationId = null;
let currentDbType = null;
let createClassificationValidator = null;
let editClassificationValidator = null;
let createRuleValidator = null;

// 获取分类图标
function getClassificationIcon(iconName, color) {
    const iconMap = {
        'fa-crown': 'fas fa-crown',
        'fa-shield-alt': 'fas fa-shield-alt',
        'fa-exclamation-triangle': 'fas fa-exclamation-triangle',
        'fa-user': 'fas fa-user',
        'fa-eye': 'fas fa-eye',
        'fa-tag': 'fas fa-tag'
    };

    const iconClass = iconMap[iconName] || 'fas fa-tag';
    return `<i class="${iconClass}" style="color: ${color || '#6c757d'};"></i>`;
}

// 页面加载时初始化
document.addEventListener('DOMContentLoaded', function () {
    loadClassifications();
    loadRules();
    loadClassificationsForRules(); // 为规则创建加载分类列表
    initializeClassificationFormValidators();
});

// ==================== 分类管理相关函数 ====================

// 加载分类列表
function loadClassifications() {
    http.get('/account_classification/api/classifications')
        .then(data => {
            if (data.success) {
                const classifications = data?.data?.classifications ?? data.classifications ?? [];
                displayClassifications(Array.isArray(classifications) ? classifications : []);
            } else {
                toast.error('加载分类失败: ' + (data.error || '未知错误'));
            }
        })
        .catch(error => {
            logErrorWithContext(error, '加载分类失败', { action: 'load_classifications' });
            toast.error('加载分类失败');
        });
}

// 显示分类列表
function displayClassifications(classifications) {
    const list = Array.isArray(classifications) ? classifications : [];
    const container = document.getElementById('classificationsList');

    if (list.length === 0) {
        container.innerHTML = '<div class="text-center text-muted py-3"><i class="fas fa-info-circle me-2"></i>暂无分类</div>';
        return;
    }

    let html = '';
    list.forEach(classification => {
        const riskLevelClass = {
            'low': 'success',
            'medium': 'warning',
            'high': 'danger',
            'critical': 'dark'
        }[classification.risk_level] || 'secondary';

        html += `
            <div class="card mb-2 classification-item" data-id="${classification.id}">
                <div class="card-body py-2">
                    <div class="d-flex justify-content-between align-items-center">
                        <div class="d-flex align-items-center">
                            <div class="me-2">
                                ${getClassificationIcon(classification.icon_name, classification.color)}
                            </div>
                            <span class="position-relative d-inline-block me-2">
                                <span class="badge bg-${riskLevelClass}" style="background-color: ${classification.color || '#6c757d'} !important;">
                                    ${classification.name}
                                </span>
                                ${classification.rules_count > 0 ? `
                                    <span class="position-absolute top-0 start-100 translate-middle badge rounded-pill bg-danger shadow-sm">
                                        ${classification.rules_count}
                                        <span class="visually-hidden">匹配规则数量</span>
                                    </span>
                                ` : ''}
                            </span>
                            ${classification.rules_count > 0 ? '' : '<small class="text-muted">无匹配</small>'}
                        </div>
                        <div class="btn-group btn-group-sm">
                            ${window.currentUserRole === 'admin' ? `
                                <button class="btn btn-outline-primary" onclick="editClassification(${classification.id})" title="编辑">
                                    <i class="fas fa-edit"></i>
                                </button>
                                ${!classification.is_system ? `
                                    <button class="btn btn-outline-danger" onclick="deleteClassification(${classification.id})" title="删除">
                                        <i class="fas fa-trash"></i>
                                    </button>
                                ` : ''}
                            ` : `
                                <span class="btn btn-outline-secondary disabled" title="只读模式">
                                    <i class="fas fa-lock"></i>
                                </span>
                            `}
                        </div>
                    </div>
                    ${classification.description ? `<small class="text-muted d-block mt-1">${classification.description}</small>` : ''}
                </div>
            </div>
        `;
    });

    container.innerHTML = html;
}

// 创建分类
function createClassification() {
    const form = document.getElementById('createClassificationForm');
    const formData = new FormData(form);

    const data = {
        name: document.getElementById('classificationName').value,
        description: document.getElementById('classificationDescription').value,
        risk_level: document.getElementById('riskLevel').value,
        color: document.getElementById('classificationColor').value,
        priority: parseInt(document.getElementById('priority').value),
        icon_name: document.querySelector('input[name="classificationIcon"]:checked').value
    };

    http.post('/account_classification/api/classifications', data)
        .then(data => {
            if (data.success) {
                toast.success(data.message || '分类创建成功');
                bootstrap.Modal.getInstance(document.getElementById('createClassificationModal')).hide();
                form.reset();
                loadClassifications();
            } else {
                toast.error(data.error || '创建分类失败');
            }
        })
        .catch(error => {
            console.error('Error:', error);
            toast.error('创建分类失败');
        });
}

// 编辑分类
function editClassification(id) {
    // 获取分类信息
    http.get(`/account_classification/api/classifications/${id}`)
        .then(data => {
            if (data.success) {
                const classification = data?.data?.classification ?? data.classification;

                // 填充编辑表单
                document.getElementById('editClassificationId').value = classification.id;
                document.getElementById('editClassificationName').value = classification.name;
                document.getElementById('editClassificationDescription').value = classification.description || '';
                document.getElementById('editClassificationRiskLevel').value = classification.risk_level;
                document.getElementById('editClassificationColor').value = classification.color_key || 'info';
                document.getElementById('editClassificationPriority').value = classification.priority || 0;

                // 显示编辑模态框
                const editModal = new bootstrap.Modal(document.getElementById('editClassificationModal'));

                // 在模态框显示后设置图标选择
                const modalElement = document.getElementById('editClassificationModal');
                const setIconSelection = () => {
                    const iconName = classification.icon_name || 'fa-tag';

                    // 先清除所有图标选择的选中状态
                    const allIconRadios = document.querySelectorAll('input[name="editClassificationIcon"]');
                    allIconRadios.forEach(radio => {
                        radio.checked = false;
                    });

                    // 然后选中对应的图标
                    const iconRadio = document.querySelector(`input[name="editClassificationIcon"][value="${iconName}"]`);
                    if (iconRadio) {
                        iconRadio.checked = true;
                    } else {
                        // 如果找不到对应的图标，默认选中标签图标
                        const defaultRadio = document.querySelector('input[name="editClassificationIcon"][value="fa-tag"]');
                        if (defaultRadio) {
                            defaultRadio.checked = true;
                        }
                    }
                };

                // 监听模态框显示事件
                modalElement.addEventListener('shown.bs.modal', setIconSelection, { once: true });

                // 延迟设置作为备用方案
                setTimeout(setIconSelection, 100);

                editModal.show();
            } else {
                toast.error('获取分类信息失败: ' + (data.error || '未知错误'));
            }
        })
        .catch(error => {
            console.error('Error:', error);
            toast.error('获取分类信息失败');
        });
}

// 更新分类
function updateClassification() {
    const id = document.getElementById('editClassificationId').value;
    const name = document.getElementById('editClassificationName').value;
    const description = document.getElementById('editClassificationDescription').value;
    const riskLevel = document.getElementById('editClassificationRiskLevel').value;
    const color = document.getElementById('editClassificationColor').value;
    const priority = parseInt(document.getElementById('editClassificationPriority').value) || 0;

    if (!name.trim()) {
        toast.warning('请输入分类名称');
        return;
    }

    const data = {
        name: name.trim(),
        description: description.trim(),
        risk_level: riskLevel,
        color: color,
        priority: priority,
        icon_name: document.querySelector('input[name="editClassificationIcon"]:checked').value
    };

    http.put(`/account_classification/api/classifications/${id}`, data)
        .then(data => {
            if (data.success) {
                toast.success('分类更新成功');
                bootstrap.Modal.getInstance(document.getElementById('editClassificationModal')).hide();
                loadClassifications();
            } else {
                toast.error(data.error || '分类更新失败');
            }
        })
        .catch(error => {
            console.error('Error:', error);
            toast.error('更新分类失败');
        });
}

// 删除分类
function deleteClassification(id) {
    if (!confirm('确定要删除这个分类吗？')) {
        return;
    }

    http.delete(`/account_classification/api/classifications/${id}`)
        .then(data => {
            if (data.success) {
                toast.success(data.message || '分类删除成功');
                loadClassifications();
            } else {
                toast.error(data.error || '删除分类失败');
            }
        })
        .catch(error => {
            console.error('Error:', error);
            toast.error('删除分类失败');
        });
}

// ==================== 规则管理相关函数 ====================

// 加载规则
function loadRules() {
    http.get('/account_classification/api/rules')
        .then(data => {
            if (data.success) {
                const rulesByDbType = data?.data?.rules_by_db_type ?? data.rules_by_db_type ?? {};
                displayRules(rulesByDbType && typeof rulesByDbType === 'object' ? rulesByDbType : {});
            } else {
                toast.error('加载规则失败: ' + (data.error || '未知错误'));
            }
        })
        .catch(error => {
            console.error('Error:', error);
            toast.error('加载规则失败');
        });
}

// 根据分类名称获取对应的CSS类
function getClassificationClass(classificationName) {
    if (!classificationName) return 'normal';

    if (classificationName.includes('特权')) {
        return 'privileged';
    } else if (classificationName.includes('敏感')) {
        return 'sensitive';
    } else if (classificationName.includes('风险')) {
        return 'risk';
    } else if (classificationName.includes('只读')) {
        return 'readonly';
    }

    return 'normal'; // 默认普通账户
}

// 显示规则列表
function displayRules(rulesByDbType) {
    const container = document.getElementById('rulesList');

    const entries = Object.entries(rulesByDbType || {});

    if (entries.length === 0) {
        container.innerHTML = `
            <div class="empty-state">
                <i class="fas fa-info-circle"></i>
                <h5 class="mb-2">暂无规则</h5>
                <p class="mb-0">点击"新建规则"按钮创建第一个分类规则</p>
            </div>
        `;
        return;
    }

    let html = '';
    for (const [dbType, rulesRaw] of entries) {
        const rules = Array.isArray(rulesRaw) ? rulesRaw : [];
        // 数据库类型图标映射
        const dbIcons = {
            'mysql': 'fas fa-database',
            'postgresql': 'fas fa-elephant',
            'sqlserver': 'fas fa-server',
            'oracle': 'fas fa-database'
        };

        const dbIcon = dbIcons[dbType] || 'fas fa-database';

        html += `
            <div class="rule-group-card">
                <div class="card">
                    <div class="card-header">
                        <h5>
                            <i class="${dbIcon} me-2 text-primary"></i>${dbType.toUpperCase()} 规则
                            <span class="badge bg-primary ms-2 rounded-pill">${rules.length}</span>
                        </h5>
                    </div>
                    <div class="card-body">
                        ${rules.length > 0 ? `
                            <div class="rule-list">
                                ${rules.map(rule => `
                                    <div class="rule-item">
                                        <div class="rule-card">
                                            <div class="card-body">
                                                <div class="row align-items-center">
                                                    <div class="col-md-3">
                                                        <h6 class="card-title mb-0">${rule.rule_name}</h6>
                                                    </div>
                                                    <div class="col-md-4">
                                                        <div class="d-flex align-items-center justify-content-center gap-1">
                                                            <span class="rule-classification-badge ${getClassificationClass(rule.classification_name)}">${rule.classification_name || '未分类'}</span>
                                                            <span class="db-type-badge">${rule.db_type.toUpperCase()}</span>
                                                        </div>
                                                    </div>
                                                    <div class="col-md-2">
                                                        <span class="badge accounts-count-badge" 
                                                              data-count="${rule.matched_accounts_count || 0}">
                                                            <i class="fas fa-users me-1"></i>${rule.matched_accounts_count || 0} 个账户
                                                        </span>
                                                    </div>
                                                    <div class="col-md-3">
                                                        <div class="rule-actions">
                                                            <button class="btn btn-outline-info" onclick="viewRule(${rule.id})" title="查看详情">
                                                                <i class="fas fa-eye"></i>
                                                            </button>
                                                            ${window.currentUserRole === 'admin' ? `
                                                                <button class="btn btn-outline-primary" onclick="editRule(${rule.id})" title="编辑规则">
                                                                    <i class="fas fa-edit"></i>
                                                                </button>
                                                                <button class="btn btn-outline-danger" onclick="deleteRule(${rule.id})" title="删除规则">
                                                                    <i class="fas fa-trash"></i>
                                                                </button>
                                                            ` : `
                                                                <span class="btn btn-outline-secondary disabled" title="只读模式">
                                                                    <i class="fas fa-lock"></i>
                                                                </span>
                                                            `}
                                                        </div>
                                                    </div>
                                                </div>
                                            </div>
                                        </div>
                                    </div>
                                `).join('')}
                            </div>
                        ` : `
                            <div class="text-center text-muted py-5">
                                <i class="fas fa-info-circle fa-3x mb-3 text-muted"></i>
                                <p class="mb-0">暂无${dbType.toUpperCase()}规则</p>
                                <small class="text-muted">点击"新建规则"按钮创建第一个规则</small>
                            </div>
                        `}
                    </div>
                </div>
            </div>
        `;
    }

    container.innerHTML = html;
}

// 加载分类列表（用于规则创建）
function loadClassificationsForRules(prefix = '') {
    return http.get('/account_classification/api/classifications')
        .then(data => {
            if (data.success) {
                const classifications = data?.data?.classifications ?? data.classifications ?? [];
                const elementId = prefix ? `${prefix}RuleClassification` : 'ruleClassification';
                const select = document.getElementById(elementId);
                if (select) {
                    select.innerHTML = '<option value="">请选择分类</option>';
                    classifications.forEach(classification => {
                        const option = document.createElement('option');
                        option.value = classification.id;
                        option.textContent = classification.name;
                        select.appendChild(option);
                    });
                }
            }
            return data;
        });
}

// 加载权限配置
function loadPermissions(prefix = '') {
    const elementId = prefix ? `${prefix}RuleDbType` : 'ruleDbType';
    const dbTypeElement = document.getElementById(elementId);
    if (!dbTypeElement) {
        console.error('找不到数据库类型选择元素:', elementId);
        return Promise.resolve();
    }
    const dbType = dbTypeElement.value;
    const containerId = prefix ? `${prefix}PermissionsConfig` : 'permissionsConfig';

    return PermissionPolicyCenter.load(dbType, containerId, prefix)
        .catch(error => {
            console.error('加载权限配置失败:', error);
            toast.error('加载权限配置失败: ' + (error.message || '未知错误'));
        });
}

// 显示权限配置
// ==================== 规则CRUD操作 ====================

function createRule() {
    if (createRuleValidator) {
        createRuleValidator.revalidate();
        return;
    }

    const form = document.getElementById('createRuleForm');
    if (form) {
        submitCreateRule(form);
    }
}

function submitCreateRule(form) {
    const classificationId = form.querySelector('#ruleClassification')?.value;
    const ruleName = form.querySelector('#ruleName')?.value;
    const dbType = form.querySelector('#ruleDbType')?.value;
    const operator = form.querySelector('#ruleOperator')?.value;

    const selectedPermissions = PermissionPolicyCenter.collectSelected(dbType, 'permissionsConfig', '');
    if (!PermissionPolicyCenter.hasSelection(selectedPermissions)) {
        toast.warning('请至少选择一个权限');
        return;
    }

    const ruleExpression = PermissionPolicyCenter.buildExpression(dbType, selectedPermissions, operator);

    const data = {
        classification_id: parseInt(classificationId),
        rule_name: ruleName,
        db_type: dbType,
        rule_expression: ruleExpression
    };

    http.post('/account_classification/api/rules', data)
        .then(response => {
            if (response.success) {
                toast.success('规则创建成功');
                bootstrap.Modal.getInstance(document.getElementById('createRuleModal')).hide();
                document.getElementById('createRuleForm').reset();
                if (createRuleValidator && createRuleValidator.instance) {
                    createRuleValidator.instance.refresh();
                }
                loadRules();
            } else {
                toast.error(response.error || '规则创建失败');
            }
        })
        .catch(error => {
            console.error('Error:', error);
            toast.error('创建规则失败');
        });
}

// 编辑规则
function editRule(id) {
    http.get(`/account_classification/api/rules/${id}`)
        .then(data => {
            if (data.success) {
                const rule = data.data.rule;

                // 先加载分类列表，然后填充表单
                loadClassificationsForRules('edit').then(() => {
                    // 填充编辑表单
                    document.getElementById('editRuleId').value = rule.id;
                    document.getElementById('editRuleName').value = rule.rule_name;
                    document.getElementById('editRuleClassification').value = rule.classification_id;
                    document.getElementById('editRuleDbTypeHidden').value = rule.db_type;

                    // 设置数据库类型显示
                    document.getElementById('editRuleDbType').value = rule.db_type;

                    // 设置操作符
                    const ruleExpression = rule.rule_expression;
                    if (ruleExpression && ruleExpression.operator) {
                        document.getElementById('editRuleOperator').value = ruleExpression.operator;
                    } else {
                        document.getElementById('editRuleOperator').value = 'OR'; // 默认值
                    }

                    // 显示编辑模态框
                    const editModal = new bootstrap.Modal(document.getElementById('editRuleModal'));
                    editModal.show();

                    // 模态框显示后加载权限配置
                    document.getElementById('editRuleModal').addEventListener('shown.bs.modal', function () {
                        // 确保数据库类型字段有值
                        document.getElementById('editRuleDbType').value = rule.db_type;

                        // 加载权限配置
                        loadPermissions('edit').then(() => {
                            PermissionPolicyCenter.setSelected(
                                rule.db_type,
                                rule.rule_expression,
                                'editPermissionsConfig',
                                'edit'
                            );
                        }).catch(error => {
                            console.error('加载权限配置失败:', error);
                            toast.error('加载权限配置失败: ' + (error.message || '未知错误'));
                        });
                    }, { once: true });
                });
            } else {
                toast.error('获取规则信息失败: ' + data.error);
            }
        })
        .catch(error => {
            console.error('Error:', error);
            toast.error('获取规则信息失败');
        });
}

// 设置选中的权限
// 更新规则
function updateRule() {
    const ruleId = document.getElementById('editRuleId').value;
    const ruleName = document.getElementById('editRuleName').value;
    const classificationId = document.getElementById('editRuleClassification').value;
    const dbType = document.getElementById('editRuleDbTypeHidden').value;
    const operator = document.getElementById('editRuleOperator').value;

    if (!ruleName) {
        toast.warning('请输入规则名称');
        return;
    }

    if (!classificationId) {
        toast.warning('请选择分类');
        return;
    }

    if (!operator) {
        toast.warning('请选择匹配逻辑');
        return;
    }

    const selectedPermissions = PermissionPolicyCenter.collectSelected(dbType, 'editPermissionsConfig', 'edit');
    if (!PermissionPolicyCenter.hasSelection(selectedPermissions)) {
        toast.warning('请至少选择一个权限');
        return;
    }

    const ruleExpression = PermissionPolicyCenter.buildExpression(dbType, selectedPermissions, operator);

    const data = {
        classification_id: parseInt(classificationId),
        rule_name: ruleName,
        db_type: dbType,
        rule_expression: ruleExpression
    };

    http.put(`/account_classification/api/rules/${ruleId}`, data)
        .then(data => {
            if (data.success) {
                toast.success('规则更新成功');
                bootstrap.Modal.getInstance(document.getElementById('editRuleModal')).hide();
                loadRules();
            } else {
                toast.error(data.error);
            }
        })
        .catch(error => {
            console.error('Error:', error);
            toast.error('更新规则失败');
        });
}

// ==================== 其他功能函数 ====================

// 处理搜索框回车事件
document.addEventListener('DOMContentLoaded', function () {
    // 为搜索框添加回车事件监听
    document.addEventListener('keypress', function (e) {
        if (e.target.id === 'accountSearchInput' && e.key === 'Enter') {
            const ruleId = e.target.closest('.modal').dataset.ruleId;
            if (ruleId) {
                searchMatchedAccounts(parseInt(ruleId));
            }
        }
    });
});

// 查看规则
function viewRule(id) {
    http.get(`/account_classification/api/rules/${id}`)
        .then(data => {
            if (data.success) {
                const rule = data.data.rule;

                // 填充查看表单
                document.getElementById('viewRuleName').textContent = rule.rule_name;
                document.getElementById('viewRuleClassification').textContent = rule.classification_name || '未分类';
                document.getElementById('viewRuleDbType').textContent = rule.db_type.toUpperCase();

                // 显示操作符
                const ruleExpression = rule.rule_expression;
                const operator = ruleExpression && ruleExpression.operator ? ruleExpression.operator : 'OR';
                const operatorText = operator === 'AND' ? 'AND (所有条件都必须满足)' : 'OR (任一条件满足即可)';
                document.getElementById('viewRuleOperator').textContent = operatorText;

                document.getElementById('viewRuleStatus').innerHTML = rule.is_active ?
                    '<span class="badge bg-success">启用</span>' :
                    '<span class="badge bg-secondary">禁用</span>';
                // 使用统一的时间格式化
                document.getElementById('viewRuleCreatedAt').textContent = rule.created_at ?
                    timeUtils.formatDateTime(rule.created_at) : '-';
                document.getElementById('viewRuleUpdatedAt').textContent = rule.updated_at ?
                    timeUtils.formatDateTime(rule.updated_at) : '-';

                const permissionsContainer = document.getElementById('viewPermissionsConfig');
                if (permissionsContainer) {
                    permissionsContainer.innerHTML = PermissionPolicyCenter.renderDisplay(rule.db_type, rule.rule_expression);
                }

                // 显示查看模态框
                const viewModal = new bootstrap.Modal(document.getElementById('viewRuleModal'));
                viewModal.show();
            } else {
                toast.error('获取规则信息失败: ' + data.error);
            }
        })
        .catch(error => {
            console.error('Error:', error);
            toast.error('获取规则信息失败');
        });
}

// 删除规则
function deleteRule(id) {
    if (!confirm('确定要删除这个规则吗？')) {
        return;
    }

    http.delete(`/account_classification/rules/${id}`)
        .then(data => {
            if (data.success) {
                toast.success('规则删除成功');
                loadRules();
            } else {
                toast.error(data.error);
            }
        })
        .catch(error => {
            console.error('Error:', error);
            toast.error('删除规则失败');
        });
}

// 自动分类所有账户
function autoClassifyAll() {
    const btn = event.target;
    const originalText = btn.innerHTML;

    // 更新按钮状态
    btn.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>分类中...';
    btn.disabled = true;

    // 记录操作开始日志
    console.info('开始自动分类所有账户', { operation: 'auto_classify_all' });

    http.post('/account_classification/api/auto-classify', {})
        .then(data => {
            if (data.success) {
                // 记录成功日志
                console.info('自动分类所有账户成功', {
                    operation: 'auto_classify_all',
                    result: 'success',
                    message: data.message
                });
                toast.success(data.message);
                // 分类完成后刷新页面显示最新数据
                setTimeout(() => {
                    location.reload();
                }, 2000);
            } else {
                // 记录失败日志
                console.error('自动分类所有账户失败', {
                    operation: 'auto_classify_all',
                    result: 'failed',
                    error: data.error
                });
                toast.error(data.error);
            }
        })
        .catch(error => {
            // 记录异常日志
            logErrorWithContext(error, '自动分类所有账户异常', {
                operation: 'auto_classify_all',
                result: 'exception'
            });
            toast.error('自动分类失败');
        })
        .finally(() => {
            // 恢复按钮状态
            btn.innerHTML = originalText;
            btn.disabled = false;
        });
}

// 显示提示信息
// ==================== 颜色预览功能 ====================

// 初始化颜色预览功能
document.addEventListener('DOMContentLoaded', function () {
    // 创建分类的颜色预览
    const createColorSelect = document.getElementById('classificationColor');
    if (createColorSelect) {
        createColorSelect.addEventListener('change', function () {
            updateColorPreview('colorPreview', this);
        });
    }

    // 编辑分类的颜色预览
    const editColorSelect = document.getElementById('editClassificationColor');
    if (editColorSelect) {
        editColorSelect.addEventListener('change', function () {
            updateColorPreview('editColorPreview', this);
        });
    }
});

// 更新颜色预览
function updateColorPreview(previewId, selectElement) {
    const selectedOption = selectElement.options[selectElement.selectedIndex];
    const colorValue = selectedOption.dataset.color;
    const colorText = selectedOption.text;

    const preview = document.getElementById(previewId);
    if (!preview) return;

    if (colorValue && selectElement.value) {
        const dot = preview.querySelector('.color-preview-dot');
        const text = preview.querySelector('.color-preview-text');

        if (dot && text) {
            dot.style.backgroundColor = colorValue;
            text.textContent = colorText;
            preview.style.display = 'flex';
        }
    } else {
        preview.style.display = 'none';
    }
}

function initializeClassificationFormValidators() {
    if (!window.FormValidator || !window.ValidationRules) {
        console.error('表单校验模块未正确加载');
        return;
    }

    const createForm = document.getElementById('createClassificationForm');
    if (createForm) {
        createClassificationValidator = FormValidator.create('#createClassificationForm');
        createClassificationValidator
            .useRules('#classificationName', ValidationRules.classification.name)
            .useRules('#classificationColor', ValidationRules.classification.color)
            .useRules('#priority', ValidationRules.classification.priority)
            .onSuccess(function (event) {
                submitCreateClassification(event.target);
            })
            .onFail(function () {
                toast.error('请检查分类信息填写');
            });

        const nameInput = createForm.querySelector('#classificationName');
        if (nameInput) {
            nameInput.addEventListener('blur', function () {
                createClassificationValidator.revalidateField('#classificationName');
            });
        }
        const colorSelect = createForm.querySelector('#classificationColor');
        if (colorSelect) {
            colorSelect.addEventListener('change', function () {
                createClassificationValidator.revalidateField('#classificationColor');
            });
        }
        const priorityInput = createForm.querySelector('#priority');
        if (priorityInput) {
            priorityInput.addEventListener('input', function () {
                createClassificationValidator.revalidateField('#priority');
            });
        }
    }

    const editForm = document.getElementById('editClassificationForm');
    if (editForm) {
        editClassificationValidator = FormValidator.create('#editClassificationForm');
        editClassificationValidator
            .useRules('#editClassificationName', ValidationRules.classification.name)
            .useRules('#editClassificationColor', ValidationRules.classification.color)
            .useRules('#editClassificationPriority', ValidationRules.classification.priority)
            .onSuccess(function (event) {
                submitUpdateClassification(event.target);
            })
            .onFail(function () {
                toast.error('请检查分类信息填写');
            });

        const editNameInput = editForm.querySelector('#editClassificationName');
        if (editNameInput) {
            editNameInput.addEventListener('blur', function () {
                editClassificationValidator.revalidateField('#editClassificationName');
            });
        }
        const editColorSelect = editForm.querySelector('#editClassificationColor');
        if (editColorSelect) {
            editColorSelect.addEventListener('change', function () {
                editClassificationValidator.revalidateField('#editClassificationColor');
            });
        }
        const editPriorityInput = editForm.querySelector('#editClassificationPriority');
        if (editPriorityInput) {
            editPriorityInput.addEventListener('input', function () {
                editClassificationValidator.revalidateField('#editClassificationPriority');
            });
        }
    }

    const ruleForm = document.getElementById('createRuleForm');
    if (ruleForm) {
        createRuleValidator = FormValidator.create('#createRuleForm');
        createRuleValidator
            .useRules('#ruleClassification', ValidationRules.classificationRule.classification)
            .useRules('#ruleName', ValidationRules.classificationRule.name)
            .useRules('#ruleDbType', ValidationRules.classificationRule.dbType)
            .useRules('#ruleOperator', ValidationRules.classificationRule.operator)
            .onSuccess(function (event) {
                submitCreateRule(event.target);
            })
            .onFail(function () {
                toast.error('请检查规则信息填写');
            });

        const classificationSelect = ruleForm.querySelector('#ruleClassification');
        if (classificationSelect) {
            classificationSelect.addEventListener('change', function () {
                createRuleValidator.revalidateField('#ruleClassification');
            });
        }
        const ruleNameInput = ruleForm.querySelector('#ruleName');
        if (ruleNameInput) {
            ruleNameInput.addEventListener('blur', function () {
                createRuleValidator.revalidateField('#ruleName');
            });
        }
        const dbTypeSelect = ruleForm.querySelector('#ruleDbType');
        if (dbTypeSelect) {
            dbTypeSelect.addEventListener('change', function () {
                createRuleValidator.revalidateField('#ruleDbType');
            });
        }
        const operatorSelect = ruleForm.querySelector('#ruleOperator');
        if (operatorSelect) {
            operatorSelect.addEventListener('change', function () {
                createRuleValidator.revalidateField('#ruleOperator');
            });
        }
    }
}

function createClassification() {
    if (createClassificationValidator) {
        createClassificationValidator.revalidate();
        return;
    }

    const form = document.getElementById('createClassificationForm');
    if (form) {
        submitCreateClassification(form);
    }
}

function submitCreateClassification(form) {
    const nameInput = form.querySelector('#classificationName');
    const colorSelect = form.querySelector('#classificationColor');
    const priorityInput = form.querySelector('#priority');
    const descriptionInput = form.querySelector('#classificationDescription');
    const riskLevelSelect = form.querySelector('#riskLevel');
    const iconRadio = form.querySelector('input[name="classificationIcon"]:checked');

    const data = {
        name: nameInput ? nameInput.value.trim() : '',
        description: descriptionInput ? descriptionInput.value.trim() : '',
        risk_level: riskLevelSelect ? riskLevelSelect.value : 'medium',
        color: colorSelect ? colorSelect.value : '',
        priority: priorityInput && priorityInput.value !== '' ? parseInt(priorityInput.value, 10) || 0 : 0,
        icon_name: iconRadio ? iconRadio.value : 'fa-tag',
    };

    if (!data.name || !data.color) {
        toast.error('请填写完整的分类信息');
        return;
    }

    http.post('/account_classification/api/classifications', data)
        .then(response => {
            if (response.success) {
                toast.success('分类创建成功');
                bootstrap.Modal.getInstance(document.getElementById('createClassificationModal')).hide();
                form.reset();
                // 重置颜色预览
                const createColorPreview = document.getElementById('colorPreview');
                if (createColorPreview) {
                    createColorPreview.style.display = 'none';
                }
                loadClassifications();
                if (createClassificationValidator && createClassificationValidator.instance) {
                    createClassificationValidator.instance.refresh();
                }
            } else {
                toast.error(response.error || '创建分类失败');
            }
        })
        .catch(error => {
            console.error('Error:', error);
            toast.error('创建分类失败: ' + (error.message || '未知错误'));
        });
}

function updateClassification() {
    if (editClassificationValidator && editClassificationValidator.instance) {
        editClassificationValidator.instance.revalidate();
        return;
    }

    const form = document.getElementById('editClassificationForm');
    if (form) {
        submitUpdateClassification(form);
    }
}

function submitUpdateClassification(form) {
    const idInput = form.querySelector('#editClassificationId');
    const nameInput = form.querySelector('#editClassificationName');
    const colorSelect = form.querySelector('#editClassificationColor');
    const priorityInput = form.querySelector('#editClassificationPriority');
    const descriptionInput = form.querySelector('#editClassificationDescription');
    const riskLevelSelect = form.querySelector('#editClassificationRiskLevel');
    const iconRadio = form.querySelector('input[name="editClassificationIcon"]:checked');

    const data = {
        name: nameInput ? nameInput.value.trim() : '',
        description: descriptionInput ? descriptionInput.value.trim() : '',
        risk_level: riskLevelSelect ? riskLevelSelect.value : 'medium',
        color: colorSelect ? colorSelect.value : '',
        priority: priorityInput && priorityInput.value !== '' ? parseInt(priorityInput.value, 10) || 0 : 0,
        icon_name: iconRadio ? iconRadio.value : 'fa-tag',
    };

    if (!data.name || !data.color) {
        toast.error('请填写完整的分类信息');
        return;
    }

    const id = idInput ? idInput.value : '';

    http.put(`/account_classification/api/classifications/${id}`, data)
        .then(response => {
            if (response.success) {
                toast.success('分类更新成功');
                bootstrap.Modal.getInstance(document.getElementById('editClassificationModal')).hide();
                // 重置颜色预览
                const editColorPreview = document.getElementById('editColorPreview');
                if (editColorPreview) {
                    editColorPreview.style.display = 'none';
                }
                loadClassifications();
                if (editClassificationValidator && editClassificationValidator.instance) {
                    editClassificationValidator.instance.refresh();
                }
            } else {
                toast.error(response.error || '更新分类失败');
            }
        })
        .catch(error => {
            console.error('Error:', error);
            toast.error('更新分类失败: ' + (error.message || '未知错误'));
        });
}
