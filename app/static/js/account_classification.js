/* 账户分类管理页面JavaScript */

// 引入console工具函数
if (typeof logErrorWithContext === 'undefined') {
    console.warn('console-utils.js not loaded, using fallback logging');
    window.logErrorWithContext = function(error, context, additionalContext) {
        console.error(`错误处理: ${context}`, error, additionalContext);
    };
}

// 全局变量
let currentClassificationId = null;
let currentDbType = null;

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
document.addEventListener('DOMContentLoaded', function() {
    loadClassifications();
    loadRules();
    loadClassificationsForRules(); // 为规则创建加载分类列表
});

// ==================== 分类管理相关函数 ====================

// 加载分类列表
function loadClassifications() {
    fetch('/account-classification/classifications')
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            displayClassifications(data.classifications);
        } else {
            showAlert('danger', '加载分类失败: ' + data.error);
        }
    })
    .catch(error => {
        logErrorWithContext(error, '加载分类失败', { action: 'load_classifications' });
        showAlert('danger', '加载分类失败');
    });
}

// 显示分类列表
function displayClassifications(classifications) {
    const container = document.getElementById('classificationsList');

    if (classifications.length === 0) {
        container.innerHTML = '<div class="text-center text-muted py-3"><i class="fas fa-info-circle me-2"></i>暂无分类</div>';
        return;
    }

    let html = '';
    classifications.forEach(classification => {
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
                            <span class="badge bg-${riskLevelClass} me-2" style="background-color: ${classification.color || '#6c757d'} !important;">
                                ${classification.name}
                            </span>
                            <small class="text-muted">${classification.rules_count > 0 ? classification.rules_count + ' 规则' : '无匹配'}</small>
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

    fetch('/account-classification/classifications', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(data)
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showAlert('success', data.message);
            bootstrap.Modal.getInstance(document.getElementById('createClassificationModal')).hide();
            form.reset();
            loadClassifications();
        } else {
            showAlert('danger', data.error);
        }
    })
    .catch(error => {
        console.error('Error:', error);
        showAlert('danger', '创建分类失败');
    });
}

// 编辑分类
function editClassification(id) {
    // 获取分类信息
    fetch(`/account-classification/classifications/${id}`)
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            const classification = data.classification;

            // 填充编辑表单
            document.getElementById('editClassificationId').value = classification.id;
            document.getElementById('editClassificationName').value = classification.name;
            document.getElementById('editClassificationDescription').value = classification.description || '';
            document.getElementById('editClassificationRiskLevel').value = classification.risk_level;
            document.getElementById('editClassificationColor').value = classification.color || '#6c757d';
            document.getElementById('editClassificationPriority').value = classification.priority || 0;
            
            // 显示编辑模态框
            const editModal = new bootstrap.Modal(document.getElementById('editClassificationModal'));
            
            // 在模态框显示后设置图标选择
            const modalElement = document.getElementById('editClassificationModal');
            const setIconSelection = () => {
                const iconName = classification.icon_name || 'fa-tag';
                console.log('设置编辑分类图标:', iconName);
                
                // 先清除所有图标选择的选中状态
                const allIconRadios = document.querySelectorAll('input[name="editClassificationIcon"]');
                console.log('找到的图标选择器数量:', allIconRadios.length);
                allIconRadios.forEach(radio => {
                    radio.checked = false;
                });
                
                // 然后选中对应的图标
                const iconRadio = document.querySelector(`input[name="editClassificationIcon"][value="${iconName}"]`);
                if (iconRadio) {
                    iconRadio.checked = true;
                    console.log('成功选中图标:', iconName);
                } else {
                    console.log('未找到图标:', iconName, '，使用默认标签图标');
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
            showAlert('danger', '获取分类信息失败: ' + data.error);
        }
    })
    .catch(error => {
        console.error('Error:', error);
        showAlert('danger', '获取分类信息失败');
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
        showAlert('warning', '请输入分类名称');
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

    fetch(`/account-classification/classifications/${id}`, {
        method: 'PUT',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': document.querySelector('meta[name="csrf-token"]').getAttribute('content')
        },
        body: JSON.stringify(data)
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showAlert('success', '分类更新成功');
            bootstrap.Modal.getInstance(document.getElementById('editClassificationModal')).hide();
            loadClassifications();
        } else {
            showAlert('danger', data.error);
        }
    })
    .catch(error => {
        console.error('Error:', error);
        showAlert('danger', '更新分类失败');
    });
}

// 删除分类
function deleteClassification(id) {
    if (!confirm('确定要删除这个分类吗？')) {
        return;
    }

    fetch(`/account-classification/classifications/${id}`, {
        method: 'DELETE'
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showAlert('success', data.message);
            loadClassifications();
        } else {
            showAlert('danger', data.error);
        }
    })
    .catch(error => {
        console.error('Error:', error);
        showAlert('danger', '删除分类失败');
    });
}

// ==================== 规则管理相关函数 ====================

// 加载规则
function loadRules() {
    fetch('/account-classification/rules')
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            displayRules(data.rules_by_db_type);
        } else {
            showAlert('danger', '加载规则失败: ' + data.error);
        }
    })
    .catch(error => {
        console.error('Error:', error);
        showAlert('danger', '加载规则失败');
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

    if (!rulesByDbType || Object.keys(rulesByDbType).length === 0) {
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
    for (const [dbType, rules] of Object.entries(rulesByDbType)) {
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
                                                        <button class="btn matched-accounts-btn" onclick="viewMatchedAccounts(${rule.id})" title="查看匹配的账户">
                                                            <i class="fas fa-users me-1"></i>${rule.matched_accounts_count || 0} 个账户
                                                        </button>
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
    return fetch('/account-classification/classifications')
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            const elementId = prefix ? `${prefix}RuleClassification` : 'ruleClassification';
            const select = document.getElementById(elementId);
            if (select) {
                select.innerHTML = '<option value="">请选择分类</option>';
                data.classifications.forEach(classification => {
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

    if (!dbType) {
        document.getElementById(containerId).innerHTML = `
            <div class="text-center text-muted py-3">
                <i class="fas fa-info-circle me-2"></i>请先选择数据库类型
            </div>
        `;
        return Promise.resolve();
    }

    return fetch(`/account-classification/permissions/${dbType}`)
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            displayPermissionsConfig(data.permissions, prefix, dbType);
        } else {
            showAlert('danger', '加载权限配置失败: ' + data.error);
        }
    })
    .catch(error => {
        console.error('Error loading permissions:', error);
        showAlert('danger', '加载权限配置失败: ' + error.message);
    });
}

// 显示权限配置
function displayPermissionsConfig(permissions, prefix = '', dbType = '') {
    const container = document.getElementById(prefix ? `${prefix}PermissionsConfig` : 'permissionsConfig');

    // 调试信息
    console.log('displayPermissionsConfig - permissions:', permissions);
    console.log('displayPermissionsConfig - dbType:', dbType);
    console.log('displayPermissionsConfig - server_roles:', permissions.server_roles);
    console.log('displayPermissionsConfig - database_roles:', permissions.database_roles);

    let html = '<div class="row">';

    // 根据数据库类型显示不同的权限配置
    if (dbType === 'mysql') {
        // MySQL结构：全局权限和数据库权限
        html += `
            <div class="col-md-6">
                <h6 class="text-primary mb-3"><i class="fas fa-globe me-2"></i>全局权限</h6>
                <div class="permission-section">
                    ${permissions.global_privileges.map(perm => `
                        <div class="form-check mb-2">
                            <input class="form-check-input" type="checkbox" value="${perm.name}" id="${prefix}global_${perm.name}">
                            <label class="form-check-label d-flex align-items-center" for="${prefix}global_${perm.name}">
                                <i class="fas fa-globe text-primary me-2"></i>
                                <div>
                                    <div class="fw-bold">${perm.name}</div>
                                    <small class="text-muted">${perm.description || '全局权限'}</small>
                                </div>
                            </label>
                        </div>
                    `).join('')}
                </div>
            </div>
            <div class="col-md-6">
                <h6 class="text-success mb-3"><i class="fas fa-database me-2"></i>数据库权限</h6>
                <div class="permission-section">
                    ${permissions.database_privileges.map(perm => `
                        <div class="form-check mb-2">
                            <input class="form-check-input" type="checkbox" value="${perm.name}" id="${prefix}db_${perm.name}">
                            <label class="form-check-label d-flex align-items-center" for="${prefix}db_${perm.name}">
                                <i class="fas fa-database text-success me-2"></i>
                                <div>
                                    <div class="fw-bold">${perm.name}</div>
                                    <small class="text-muted">${perm.description || '数据库权限'}</small>
                                </div>
                            </label>
                        </div>
                    `).join('')}
                </div>
            </div>
        `;
    } else if (dbType === 'sqlserver') {
        // SQL Server结构：服务器角色、数据库角色、服务器权限、数据库权限
        html += `
            <div class="col-md-6">
                <h6 class="text-info mb-3"><i class="fas fa-users me-2"></i>服务器角色</h6>
                <div class="permission-section">
                    ${permissions.server_roles ? permissions.server_roles.map(role => `
                        <div class="form-check mb-2">
                            <input class="form-check-input" type="checkbox" value="${role.name}" id="${prefix}server_role_${role.name}">
                            <label class="form-check-label d-flex align-items-center" for="${prefix}server_role_${role.name}">
                                <i class="fas fa-users text-info me-2"></i>
                                <div>
                                    <div class="fw-bold">${role.name}</div>
                                    <small class="text-muted">${role.description || '服务器角色'}</small>
                                </div>
                            </label>
                        </div>
                    `).join('') : '<div class="text-muted">无服务器角色</div>'}
                </div>

                <h6 class="text-warning mb-3 mt-3"><i class="fas fa-shield-alt me-2"></i>服务器权限</h6>
                <div class="permission-section">
                    ${permissions.server_permissions ? permissions.server_permissions.map(perm => `
                        <div class="form-check mb-2">
                            <input class="form-check-input" type="checkbox" value="${perm.name}" id="${prefix}server_perm_${perm.name}">
                            <label class="form-check-label d-flex align-items-center" for="${prefix}server_perm_${perm.name}">
                                <i class="fas fa-shield-alt text-warning me-2"></i>
                                <div>
                                    <div class="fw-bold">${perm.name}</div>
                                    <small class="text-muted">${perm.description || '服务器权限'}</small>
                                </div>
                            </label>
                        </div>
                    `).join('') : '<div class="text-muted">无服务器权限</div>'}
                </div>
            </div>
            <div class="col-md-6">
                <h6 class="text-primary mb-3"><i class="fas fa-database me-2"></i>数据库角色</h6>
                <div class="permission-section">
                    ${permissions.database_roles ? permissions.database_roles.map(role => `
                        <div class="form-check mb-2">
                            <input class="form-check-input" type="checkbox" value="${role.name}" id="${prefix}db_role_${role.name}">
                            <label class="form-check-label d-flex align-items-center" for="${prefix}db_role_${role.name}">
                                <i class="fas fa-database text-primary me-2"></i>
                                <div>
                                    <div class="fw-bold">${role.name}</div>
                                    <small class="text-muted">${role.description || '数据库角色'}</small>
                                </div>
                            </label>
                        </div>
                    `).join('') : '<div class="text-muted">无数据库角色</div>'}
                </div>

                <h6 class="text-success mb-3 mt-3"><i class="fas fa-key me-2"></i>数据库权限</h6>
                <div class="permission-section">
                    ${permissions.database_privileges ? permissions.database_privileges.map(perm => `
                        <div class="form-check mb-2">
                            <input class="form-check-input" type="checkbox" value="${perm.name}" id="${prefix}db_perm_${perm.name}">
                            <label class="form-check-label d-flex align-items-center" for="${prefix}db_perm_${perm.name}">
                                <i class="fas fa-key text-success me-2"></i>
                                <div>
                                    <div class="fw-bold">${perm.name}</div>
                                    <small class="text-muted">${perm.description || '数据库权限'}</small>
                                </div>
                            </label>
                        </div>
                    `).join('') : '<div class="text-muted">无数据库权限</div>'}
                </div>
            </div>
        `;
    } else if (dbType === 'postgresql') {
        // PostgreSQL结构：预定义角色、角色属性、数据库权限、表空间权限
        html += `
            <div class="col-md-6">
                <h6 class="text-warning mb-3"><i class="fas fa-users me-2"></i>预定义角色</h6>
                <div class="permission-section">
                    ${permissions.predefined_roles ? permissions.predefined_roles.map(role => `
                        <div class="form-check mb-2">
                            <input class="form-check-input" type="checkbox" value="${role.name}" id="${prefix}predefined_role_${role.name}">
                            <label class="form-check-label d-flex align-items-center" for="${prefix}predefined_role_${role.name}">
                                <i class="fas fa-users text-warning me-2"></i>
                                <div>
                                    <div class="fw-bold">${role.name}</div>
                                    <small class="text-muted">${role.description || '预定义角色'}</small>
                                </div>
                            </label>
                        </div>
                    `).join('') : '<div class="text-muted">无预定义角色</div>'}
                </div>

                <h6 class="text-primary mb-3 mt-3"><i class="fas fa-user-shield me-2"></i>角色属性</h6>
                <div class="permission-section">
                    ${permissions.role_attributes ? permissions.role_attributes.map(attr => {
                        // 角色属性显示名称映射
                        const roleAttributeDisplayNames = {
                            'can_super': '超级用户属性',
                            'can_create_db': '创建数据库属性',
                            'can_create_role': '创建角色属性',
                            'can_inherit': '继承权限属性',
                            'can_login': '登录属性',
                            'can_replicate': '复制属性',
                            'can_bypass_rls': '绕过行级安全属性',
                            'connection_limit': '连接限制属性'
                        };
                        const displayName = roleAttributeDisplayNames[attr.name] || attr.name;
                        return `
                            <div class="form-check mb-2">
                                <input class="form-check-input" type="checkbox" value="${attr.name}" id="${prefix}role_attr_${attr.name}">
                                <label class="form-check-label d-flex align-items-center" for="${prefix}role_attr_${attr.name}">
                                    <i class="fas fa-user-cog text-primary me-2"></i>
                                    <div>
                                        <div class="fw-bold">${displayName}</div>
                                        <small class="text-muted">${attr.description || '角色属性权限'}</small>
                                    </div>
                                </label>
                            </div>
                        `;
                    }).join('') : '<div class="text-muted">无角色属性</div>'}
                </div>
            </div>
            <div class="col-md-6">
                <h6 class="text-success mb-3"><i class="fas fa-database me-2"></i>数据库权限</h6>
                <div class="permission-section">
                    ${permissions.database_privileges ? permissions.database_privileges.map(perm => `
                        <div class="form-check mb-2">
                            <input class="form-check-input" type="checkbox" value="${perm.name}" id="${prefix}db_perm_${perm.name}">
                            <label class="form-check-label d-flex align-items-center" for="${prefix}db_perm_${perm.name}">
                                <i class="fas fa-database text-success me-2"></i>
                                <div>
                                    <div class="fw-bold">${perm.name}</div>
                                    <small class="text-muted">${perm.description || '数据库权限'}</small>
                                </div>
                            </label>
                        </div>
                    `).join('') : '<div class="text-muted">无数据库权限</div>'}
                </div>

                <h6 class="text-info mb-3 mt-3"><i class="fas fa-hdd me-2"></i>表空间权限</h6>
                <div class="permission-section">
                    ${permissions.tablespace_privileges ? permissions.tablespace_privileges.map(perm => `
                        <div class="form-check mb-2">
                            <input class="form-check-input" type="checkbox" value="${perm.name}" id="${prefix}tablespace_perm_${perm.name}">
                            <label class="form-check-label d-flex align-items-center" for="${prefix}tablespace_perm_${perm.name}">
                                <i class="fas fa-hdd text-info me-2"></i>
                                <div>
                                    <div class="fw-bold">${perm.name}</div>
                                    <small class="text-muted">${perm.description || '表空间权限'}</small>
                                </div>
                            </label>
                        </div>
                    `).join('') : '<div class="text-muted">无表空间权限</div>'}
                </div>
            </div>
        `;
    } else if (dbType === 'oracle') {
        // Oracle结构：左边系统权限，右边角色、表空间权限、表空间配额
        html += `
            <div class="col-md-6">
                <h6 class="text-primary mb-3"><i class="fas fa-shield-alt me-2"></i>系统权限</h6>
                <div class="permission-section">
                    ${permissions.system_privileges ? permissions.system_privileges.map(perm => `
                        <div class="form-check mb-2">
                            <input class="form-check-input" type="checkbox" value="${perm.name}" id="${prefix}sys_perm_${perm.name}">
                            <label class="form-check-label d-flex align-items-center" for="${prefix}sys_perm_${perm.name}">
                                <i class="fas fa-shield-alt text-primary me-2"></i>
                                <div>
                                    <div class="fw-bold">${perm.name}</div>
                                    <small class="text-muted">${perm.description || '系统权限'}</small>
                                </div>
                            </label>
                        </div>
                    `).join('') : '<div class="text-muted">无系统权限</div>'}
                </div>
            </div>
            <div class="col-md-6">
                <h6 class="text-danger mb-3"><i class="fas fa-users-cog me-2"></i>角色</h6>
                <div class="permission-section">
                    ${permissions.roles ? permissions.roles.map(role => `
                        <div class="form-check mb-2">
                            <input class="form-check-input" type="checkbox" value="${role.name}" id="${prefix}role_${role.name}">
                            <label class="form-check-label d-flex align-items-center" for="${prefix}role_${role.name}">
                                <i class="fas fa-users-cog text-danger me-2"></i>
                                <div>
                                    <div class="fw-bold">${role.name}</div>
                                    <small class="text-muted">${role.description || '数据库角色'}</small>
                                </div>
                            </label>
                        </div>
                    `).join('') : '<div class="text-muted">无角色</div>'}
                </div>

                <h6 class="text-info mb-3 mt-3"><i class="fas fa-hdd me-2"></i>表空间权限</h6>
                <div class="permission-section">
                    ${permissions.tablespace_privileges ? permissions.tablespace_privileges.map(perm => `
                        <div class="form-check mb-2">
                            <input class="form-check-input" type="checkbox" value="${perm.name}" id="${prefix}tablespace_perm_${perm.name}">
                            <label class="form-check-label d-flex align-items-center" for="${prefix}tablespace_perm_${perm.name}">
                                <i class="fas fa-hdd text-info me-2"></i>
                                <div>
                                    <div class="fw-bold">${perm.name}</div>
                                    <small class="text-muted">${perm.description || '表空间权限'}</small>
                                </div>
                            </label>
                        </div>
                    `).join('') : '<div class="text-muted">无表空间权限</div>'}
                </div>

                <h6 class="text-warning mb-3 mt-3"><i class="fas fa-chart-pie me-2"></i>表空间配额</h6>
                <div class="permission-section">
                    ${permissions.tablespace_quotas ? permissions.tablespace_quotas.map(quota => `
                        <div class="form-check mb-2">
                            <input class="form-check-input" type="checkbox" value="${quota.name}" id="${prefix}tablespace_quota_${quota.name}">
                            <label class="form-check-label d-flex align-items-center" for="${prefix}tablespace_quota_${quota.name}">
                                <i class="fas fa-chart-pie text-warning me-2"></i>
                                <div>
                                    <div class="fw-bold">${quota.name}</div>
                                    <small class="text-muted">${quota.description || '表空间配额'}</small>
                                </div>
                            </label>
                        </div>
                    `).join('') : '<div class="text-muted">无表空间配额</div>'}
                </div>
            </div>
        `;
    } else {
        // 其他数据库类型或旧格式
        html += `
            <div class="col-12">
                <h6 class="text-secondary mb-3"><i class="fas fa-list me-2"></i>权限列表</h6>
                <div class="permission-section">
                    ${permissions.permissions ? permissions.permissions.map(perm => `
                        <div class="form-check">
                            <input class="form-check-input" type="checkbox" value="${perm}" id="${prefix}perm_${perm}">
                            <label class="form-check-label" for="${prefix}perm_${perm}">
                                <span class="me-1">${perm}</span>
                            </label>
                        </div>
                    `).join('') : '<div class="text-muted">无权限配置</div>'}
                </div>
            </div>
        `;
    }

    html += '</div>';
    container.innerHTML = html;
}

// ==================== 规则CRUD操作 ====================

// 创建规则
function createRule() {
    const classificationId = document.getElementById('ruleClassification').value;
    const ruleName = document.getElementById('ruleName').value;
    const dbType = document.getElementById('ruleDbType').value;
    const operator = document.getElementById('ruleOperator').value;

    if (!classificationId || !ruleName || !dbType || !operator) {
        showAlert('warning', '请填写所有必填字段');
        return;
    }

    // 收集选中的权限
    const selectedPermissions = [];
    const checkboxes = document.querySelectorAll('#permissionsConfig input[type="checkbox"]:checked');
    checkboxes.forEach(checkbox => {
        selectedPermissions.push(checkbox.value);
    });

    if (selectedPermissions.length === 0) {
        showAlert('warning', '请至少选择一个权限');
        return;
    }

    // 根据数据库类型构建规则表达式
    let ruleExpression;
    if (dbType === 'mysql') {
        // MySQL新结构
        const selectedGlobalPermissions = [];
        const selectedDatabasePermissions = [];

        checkboxes.forEach(checkbox => {
            if (checkbox.id.startsWith('global_')) {
                selectedGlobalPermissions.push(checkbox.value);
            } else if (checkbox.id.startsWith('db_')) {
                selectedDatabasePermissions.push(checkbox.value);
            }
        });

        ruleExpression = {
            type: 'mysql_permissions',
            global_privileges: selectedGlobalPermissions,
            database_privileges: selectedDatabasePermissions,
            operator: operator
        };
    } else if (dbType === 'sqlserver') {
        // SQL Server结构
        const selectedServerRoles = [];
        const selectedServerPermissions = [];
        const selectedDatabaseRoles = [];
        const selectedDatabasePermissions = [];

        checkboxes.forEach(checkbox => {
            if (checkbox.id.startsWith('server_role_')) {
                selectedServerRoles.push(checkbox.value);
            } else if (checkbox.id.startsWith('server_perm_')) {
                selectedServerPermissions.push(checkbox.value);
            } else if (checkbox.id.startsWith('db_role_')) {
                selectedDatabaseRoles.push(checkbox.value);
            } else if (checkbox.id.startsWith('db_perm_')) {
                selectedDatabasePermissions.push(checkbox.value);
            }
        });

        ruleExpression = {
            type: 'sqlserver_permissions',
            server_roles: selectedServerRoles,
            server_permissions: selectedServerPermissions,
            database_roles: selectedDatabaseRoles,
            database_privileges: selectedDatabasePermissions,
            operator: operator
        };
    } else if (dbType === 'postgresql') {
        // PostgreSQL结构
        const selectedPredefinedRoles = [];
        const selectedRoleAttributes = [];
        const selectedDatabasePermissions = [];
        const selectedTablespacePermissions = [];

        checkboxes.forEach(checkbox => {
            if (checkbox.id.startsWith('predefined_role_')) {
                selectedPredefinedRoles.push(checkbox.value);
            } else if (checkbox.id.startsWith('role_attr_')) {
                selectedRoleAttributes.push(checkbox.value);
            } else if (checkbox.id.startsWith('db_perm_')) {
                selectedDatabasePermissions.push(checkbox.value);
            } else if (checkbox.id.startsWith('tablespace_perm_')) {
                selectedTablespacePermissions.push(checkbox.value);
            }
        });

        ruleExpression = {
            type: 'postgresql_permissions',
            predefined_roles: selectedPredefinedRoles,
            role_attributes: selectedRoleAttributes,
            database_privileges: selectedDatabasePermissions,
            tablespace_privileges: selectedTablespacePermissions,
            permissions: selectedPermissions, // 兼容性
            operator: operator
        };
    } else if (dbType === 'oracle') {
        // Oracle结构
        const selectedRoles = [];
        const selectedSystemPermissions = [];
        const selectedTablespacePermissions = [];
        const selectedTablespaceQuotas = [];

        checkboxes.forEach(checkbox => {
            if (checkbox.id.startsWith('role_')) {
                selectedRoles.push(checkbox.value);
            } else if (checkbox.id.startsWith('sys_perm_')) {
                selectedSystemPermissions.push(checkbox.value);
            } else if (checkbox.id.startsWith('tablespace_perm_')) {
                selectedTablespacePermissions.push(checkbox.value);
            } else if (checkbox.id.startsWith('tablespace_quota_')) {
                selectedTablespaceQuotas.push(checkbox.value);
            }
        });

        ruleExpression = {
            type: 'oracle_permissions',
            roles: selectedRoles,
            system_privileges: selectedSystemPermissions,
            tablespace_privileges: selectedTablespacePermissions,
            tablespace_quotas: selectedTablespaceQuotas,
            permissions: selectedPermissions, // 兼容性
            operator: operator
        };
    } else {
        // 其他数据库类型
        ruleExpression = {
            type: 'permissions',
            permissions: selectedPermissions,
            operator: operator
        };
    }

    const data = {
        classification_id: parseInt(classificationId),
        rule_name: ruleName,
        db_type: dbType,
        rule_expression: ruleExpression
    };

    fetch('/account-classification/rules', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': document.querySelector('meta[name="csrf-token"]').getAttribute('content')
        },
        body: JSON.stringify(data)
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showAlert('success', '规则创建成功');
            bootstrap.Modal.getInstance(document.getElementById('createRuleModal')).hide();
            document.getElementById('createRuleForm').reset();
            loadRules();
        } else {
            showAlert('danger', data.error);
        }
    })
    .catch(error => {
        console.error('Error:', error);
        showAlert('danger', '创建规则失败');
    });
}

// 编辑规则
function editRule(id) {
    fetch(`/account-classification/rules/${id}`)
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            const rule = data.rule;

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
                document.getElementById('editRuleModal').addEventListener('shown.bs.modal', function() {
                    // 确保数据库类型字段有值
                    document.getElementById('editRuleDbType').value = rule.db_type;

                    // 加载权限配置
                    loadPermissions('edit').then(() => {
                        setSelectedPermissions(rule.rule_expression, 'edit');
                    });
                }, { once: true });
            });
        } else {
            showAlert('danger', '获取规则信息失败: ' + data.error);
        }
    })
    .catch(error => {
        console.error('Error:', error);
        showAlert('danger', '获取规则信息失败');
    });
}

// 设置选中的权限
function setSelectedPermissions(ruleExpression, prefix = '') {
    if (!ruleExpression) return;

    // 根据规则类型设置选中的权限
    if (ruleExpression.type === 'mysql_permissions') {
        // MySQL新结构
        if (ruleExpression.global_privileges) {
            ruleExpression.global_privileges.forEach(perm => {
                const checkbox = document.getElementById(`${prefix}global_${perm}`);
                if (checkbox) checkbox.checked = true;
            });
        }
        if (ruleExpression.database_privileges) {
            ruleExpression.database_privileges.forEach(perm => {
                const checkbox = document.getElementById(`${prefix}db_${perm}`);
                if (checkbox) checkbox.checked = true;
            });
        }
    } else if (ruleExpression.type === 'sqlserver_permissions') {
        // SQL Server结构
        if (ruleExpression.server_roles) {
            ruleExpression.server_roles.forEach(role => {
                const checkbox = document.getElementById(`${prefix}server_role_${role}`);
                if (checkbox) checkbox.checked = true;
            });
        }
        if (ruleExpression.server_permissions) {
            ruleExpression.server_permissions.forEach(perm => {
                const checkbox = document.getElementById(`${prefix}server_perm_${perm}`);
                if (checkbox) checkbox.checked = true;
            });
        }
        if (ruleExpression.database_roles) {
            ruleExpression.database_roles.forEach(role => {
                const checkbox = document.getElementById(`${prefix}db_role_${role}`);
                if (checkbox) checkbox.checked = true;
            });
        }
        if (ruleExpression.database_privileges) {
            ruleExpression.database_privileges.forEach(perm => {
                const checkbox = document.getElementById(`${prefix}db_perm_${perm}`);
                if (checkbox) checkbox.checked = true;
            });
        }
    } else if (ruleExpression.type === 'postgresql_permissions') {
        // PostgreSQL结构
        if (ruleExpression.predefined_roles) {
            ruleExpression.predefined_roles.forEach(role => {
                const checkbox = document.getElementById(`${prefix}predefined_role_${role}`);
                if (checkbox) checkbox.checked = true;
            });
        }
        if (ruleExpression.role_attributes) {
            ruleExpression.role_attributes.forEach(attr => {
                const checkbox = document.getElementById(`${prefix}role_attr_${attr}`);
                if (checkbox) checkbox.checked = true;
            });
        }
        if (ruleExpression.database_privileges) {
            ruleExpression.database_privileges.forEach(perm => {
                const checkbox = document.getElementById(`${prefix}db_perm_${perm}`);
                if (checkbox) checkbox.checked = true;
            });
        }
        if (ruleExpression.tablespace_privileges) {
            ruleExpression.tablespace_privileges.forEach(perm => {
                const checkbox = document.getElementById(`${prefix}tablespace_perm_${perm}`);
                if (checkbox) checkbox.checked = true;
            });
        }
    } else if (ruleExpression.type === 'oracle_permissions') {
        // Oracle结构
        if (ruleExpression.roles) {
            ruleExpression.roles.forEach(role => {
                const checkbox = document.getElementById(`${prefix}role_${role}`);
                if (checkbox) checkbox.checked = true;
            });
        }
        if (ruleExpression.system_privileges) {
            ruleExpression.system_privileges.forEach(perm => {
                const checkbox = document.getElementById(`${prefix}sys_perm_${perm}`);
                if (checkbox) checkbox.checked = true;
            });
        }
        if (ruleExpression.tablespace_privileges) {
            ruleExpression.tablespace_privileges.forEach(perm => {
                const checkbox = document.getElementById(`${prefix}tablespace_perm_${perm}`);
                if (checkbox) checkbox.checked = true;
            });
        }
        if (ruleExpression.tablespace_quotas) {
            ruleExpression.tablespace_quotas.forEach(quota => {
                const checkbox = document.getElementById(`${prefix}tablespace_quota_${quota}`);
                if (checkbox) checkbox.checked = true;
            });
        }
    } else if (ruleExpression.permissions) {
        // 旧格式或其他数据库类型
        ruleExpression.permissions.forEach(perm => {
            const checkbox = document.getElementById(`${prefix}perm_${perm}`);
            if (checkbox) checkbox.checked = true;
        });
    }
}

// 更新规则
function updateRule() {
    const ruleId = document.getElementById('editRuleId').value;
    const ruleName = document.getElementById('editRuleName').value;
    const classificationId = document.getElementById('editRuleClassification').value;
    const dbType = document.getElementById('editRuleDbTypeHidden').value;
    const operator = document.getElementById('editRuleOperator').value;

    if (!ruleName) {
        showAlert('warning', '请输入规则名称');
        return;
    }

    if (!classificationId) {
        showAlert('warning', '请选择分类');
        return;
    }

    if (!operator) {
        showAlert('warning', '请选择匹配逻辑');
        return;
    }

    // 收集选中的权限
    const selectedPermissions = [];
    const checkboxes = document.querySelectorAll('#editPermissionsConfig input[type="checkbox"]:checked');
    checkboxes.forEach(checkbox => {
        selectedPermissions.push(checkbox.value);
    });

    if (selectedPermissions.length === 0) {
        showAlert('warning', '请至少选择一个权限');
        return;
    }

    // 根据数据库类型构建规则表达式
    let ruleExpression;
    if (dbType === 'mysql') {
        const selectedGlobalPermissions = [];
        const selectedDatabasePermissions = [];

        checkboxes.forEach(checkbox => {
            if (checkbox.id.startsWith('editglobal_')) {
                selectedGlobalPermissions.push(checkbox.value);
            } else if (checkbox.id.startsWith('editdb_')) {
                selectedDatabasePermissions.push(checkbox.value);
            }
        });

        ruleExpression = {
            type: 'mysql_permissions',
            global_privileges: selectedGlobalPermissions,
            database_privileges: selectedDatabasePermissions,
            operator: operator
        };
    } else if (dbType === 'sqlserver') {
        const selectedServerRoles = [];
        const selectedServerPermissions = [];
        const selectedDatabaseRoles = [];
        const selectedDatabasePermissions = [];

        checkboxes.forEach(checkbox => {
            if (checkbox.id.startsWith('editserver_role_')) {
                selectedServerRoles.push(checkbox.value);
            } else if (checkbox.id.startsWith('editserver_perm_')) {
                selectedServerPermissions.push(checkbox.value);
            } else if (checkbox.id.startsWith('editdb_role_')) {
                selectedDatabaseRoles.push(checkbox.value);
            } else if (checkbox.id.startsWith('editdb_perm_')) {
                selectedDatabasePermissions.push(checkbox.value);
            }
        });

        ruleExpression = {
            type: 'sqlserver_permissions',
            server_roles: selectedServerRoles,
            server_permissions: selectedServerPermissions,
            database_roles: selectedDatabaseRoles,
            database_privileges: selectedDatabasePermissions,
            operator: operator
        };
    } else if (dbType === 'postgresql') {
        const selectedPredefinedRoles = [];
        const selectedRoleAttributes = [];
        const selectedDatabasePermissions = [];
        const selectedTablespacePermissions = [];

        checkboxes.forEach(checkbox => {
            if (checkbox.id.startsWith('editpredefined_role_')) {
                selectedPredefinedRoles.push(checkbox.value);
            } else if (checkbox.id.startsWith('editrole_attr_')) {
                selectedRoleAttributes.push(checkbox.value);
            } else if (checkbox.id.startsWith('editdb_perm_')) {
                selectedDatabasePermissions.push(checkbox.value);
            } else if (checkbox.id.startsWith('edittablespace_perm_')) {
                selectedTablespacePermissions.push(checkbox.value);
            }
        });

        ruleExpression = {
            type: 'postgresql_permissions',
            predefined_roles: selectedPredefinedRoles,
            role_attributes: selectedRoleAttributes,
            database_privileges: selectedDatabasePermissions,
            tablespace_privileges: selectedTablespacePermissions,
            operator: operator
        };
    } else if (dbType === 'oracle') {
        const selectedRoles = [];
        const selectedSystemPermissions = [];
        const selectedTablespacePermissions = [];
        const selectedTablespaceQuotas = [];

        checkboxes.forEach(checkbox => {
            if (checkbox.id.startsWith('editrole_')) {
                selectedRoles.push(checkbox.value);
            } else if (checkbox.id.startsWith('editsys_perm_')) {
                selectedSystemPermissions.push(checkbox.value);
            } else if (checkbox.id.startsWith('edittablespace_perm_')) {
                selectedTablespacePermissions.push(checkbox.value);
            } else if (checkbox.id.startsWith('edittablespace_quota_')) {
                selectedTablespaceQuotas.push(checkbox.value);
            }
        });

        ruleExpression = {
            type: 'oracle_permissions',
            roles: selectedRoles,
            system_privileges: selectedSystemPermissions,
            tablespace_privileges: selectedTablespacePermissions,
            tablespace_quotas: selectedTablespaceQuotas,
            operator: operator
        };
    } else {
        ruleExpression = {
            type: 'permissions',
            permissions: selectedPermissions,
            operator: operator
        };
    }

    const data = {
        classification_id: parseInt(classificationId),
        rule_name: ruleName,
        rule_expression: ruleExpression
    };

    fetch(`/account-classification/rules/${ruleId}`, {
        method: 'PUT',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': document.querySelector('meta[name="csrf-token"]').getAttribute('content')
        },
        body: JSON.stringify(data)
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showAlert('success', '规则更新成功');
            bootstrap.Modal.getInstance(document.getElementById('editRuleModal')).hide();
            loadRules();
        } else {
            showAlert('danger', data.error);
        }
    })
    .catch(error => {
        console.error('Error:', error);
        showAlert('danger', '更新规则失败');
    });
}

// ==================== 其他功能函数 ====================

// 查看匹配的账户
function viewMatchedAccounts(ruleId) {
    fetch(`/account-classification/rules/${ruleId}/matched-accounts`)
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            displayMatchedAccounts(data.accounts, data.rule_name);
        } else {
            showAlert('danger', '获取匹配账户失败: ' + data.error);
        }
    })
    .catch(error => {
        console.error('Error:', error);
        showAlert('danger', '获取匹配账户失败');
    });
}

// 显示匹配的账户
function displayMatchedAccounts(accounts, ruleName) {
    const container = document.getElementById('matchedAccountsList');

    if (!accounts || accounts.length === 0) {
        container.innerHTML = `
            <div class="text-center text-muted py-5">
                <i class="fas fa-users fa-3x mb-3 text-muted"></i>
                <p class="mb-0">没有匹配的账户</p>
            </div>
        `;
    } else {
        let html = `
            <div class="mb-3">
                <div class="d-flex justify-content-between align-items-center">
                    <h6 class="mb-0 text-muted">
                        <i class="fas fa-info-circle me-2"></i>共找到 ${accounts.length} 个匹配的账户
                    </h6>
                </div>
            </div>
            <div class="table-responsive">
                <table class="table table-hover">
                    <thead>
                        <tr>
                            <th style="font-size: 0.8rem;">账户名称</th>
                            <th style="font-size: 0.8rem;">实例名称</th>
                            <th style="font-size: 0.8rem;">实例IP</th>
                            <th style="font-size: 0.8rem;">环境</th>
                            <th style="font-size: 0.8rem;">锁定状态</th>
                        </tr>
                    </thead>
                    <tbody>
        `;

        accounts.forEach(account => {
            // 环境标签
            const envClass = account.instance_environment === 'production' ? 'danger' :
                            account.instance_environment === 'development' ? 'warning' : 'info';
            const envLabel = account.instance_environment === 'production' ? '生产' :
                            account.instance_environment === 'development' ? '开发' :
                            account.instance_environment === 'testing' ? '测试' : account.instance_environment;


            // 锁定状态
            const lockStatus = account.is_locked
                ? '<span class="badge bg-danger" style="font-size: 0.7rem;">已禁用</span>'
                : '<span class="badge bg-success" style="font-size: 0.7rem;">正常</span>';

            html += `
                <tr class="small">
                    <td>
                        <div class="d-flex align-items-center">
                            <i class="fas fa-user text-primary me-1" style="font-size: 0.8rem;"></i>
                            <strong style="font-size: 0.85rem;">${account.display_name || account.username || '-'}</strong>
                        </div>
                    </td>
                    <td>
                        <div class="d-flex align-items-center">
                            <i class="fas fa-database text-info me-1" style="font-size: 0.8rem;"></i>
                            <span style="font-size: 0.8rem;">${account.instance_name || '-'}</span>
                        </div>
                    </td>
                    <td>
                        <span class="badge bg-primary" style="font-size: 0.7rem;">${account.instance_host || '-'}</span>
                    </td>
                    <td>
                        <span class="badge bg-${envClass}" style="font-size: 0.7rem;">${envLabel}</span>
                    </td>
                    <td>
                        ${lockStatus}
                    </td>
                </tr>
            `;
        });

        html += `
                    </tbody>
                </table>
            </div>
        `;

        container.innerHTML = html;
    }

    // 更新模态框标题
    document.getElementById('matchedAccountsModalLabel').textContent = `规则 "${ruleName}" 匹配的账户`;

    // 显示模态框
    const modal = new bootstrap.Modal(document.getElementById('matchedAccountsModal'));
    modal.show();
}

// 查看规则
function viewRule(id) {
    fetch(`/account-classification/rules/${id}`)
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            const rule = data.rule;

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
            document.getElementById('viewRuleCreatedAt').textContent = rule.created_at ?
                new Date(rule.created_at).toLocaleString() : '-';
            document.getElementById('viewRuleUpdatedAt').textContent = rule.updated_at ?
                new Date(rule.updated_at).toLocaleString() : '-';

            // 显示权限配置
            displayViewPermissions(rule.rule_expression, rule.db_type);

            // 显示查看模态框
            const viewModal = new bootstrap.Modal(document.getElementById('viewRuleModal'));
            viewModal.show();
        } else {
            showAlert('danger', '获取规则信息失败: ' + data.error);
        }
    })
    .catch(error => {
        console.error('Error:', error);
        showAlert('danger', '获取规则信息失败');
    });
}

// 显示查看权限配置
function displayViewPermissions(ruleExpression, dbType) {
    const container = document.getElementById('viewPermissionsConfig');

    if (!ruleExpression) {
        container.innerHTML = '<div class="text-muted">无权限配置</div>';
        return;
    }

    let html = '<div class="row">';

    if (ruleExpression.type === 'mysql_permissions') {
        // MySQL新结构
        if (ruleExpression.global_privileges && ruleExpression.global_privileges.length > 0) {
            html += `
                <div class="col-md-6">
                    <h6 class="text-primary mb-2"><i class="fas fa-globe me-2"></i>全局权限</h6>
                    <div class="mb-3">
                        ${ruleExpression.global_privileges.map(perm =>
                            `<span class="badge bg-primary me-1 mb-1">${perm}</span>`
                        ).join('')}
                    </div>
                </div>
            `;
        }
        if (ruleExpression.database_privileges && ruleExpression.database_privileges.length > 0) {
            html += `
                <div class="col-md-6">
                    <h6 class="text-success mb-2"><i class="fas fa-database me-2"></i>数据库权限</h6>
                    <div class="mb-3">
                        ${ruleExpression.database_privileges.map(perm =>
                            `<span class="badge bg-success me-1 mb-1">${perm}</span>`
                        ).join('')}
                    </div>
                </div>
            `;
        }
    } else if (ruleExpression.type === 'sqlserver_permissions') {
        // SQL Server结构
        if (ruleExpression.server_roles && ruleExpression.server_roles.length > 0) {
            html += `
                <div class="col-md-6">
                    <h6 class="text-info mb-2"><i class="fas fa-users me-2"></i>服务器角色</h6>
                    <div class="mb-3">
                        ${ruleExpression.server_roles.map(role =>
                            `<span class="badge bg-info me-1 mb-1">${role}</span>`
                        ).join('')}
                    </div>
                </div>
            `;
        }
        if (ruleExpression.database_roles && ruleExpression.database_roles.length > 0) {
            html += `
                <div class="col-md-6">
                    <h6 class="text-primary mb-2"><i class="fas fa-database me-2"></i>数据库角色</h6>
                    <div class="mb-3">
                        ${ruleExpression.database_roles.map(role =>
                            `<span class="badge bg-primary me-1 mb-1">${role}</span>`
                        ).join('')}
                    </div>
                </div>
            `;
        }
        if (ruleExpression.server_permissions && ruleExpression.server_permissions.length > 0) {
            html += `
                <div class="col-md-6">
                    <h6 class="text-warning mb-2"><i class="fas fa-shield-alt me-2"></i>服务器权限</h6>
                    <div class="mb-3">
                        ${ruleExpression.server_permissions.map(perm =>
                            `<span class="badge bg-warning me-1 mb-1">${perm}</span>`
                        ).join('')}
                    </div>
                </div>
            `;
        }
        if (ruleExpression.database_privileges && ruleExpression.database_privileges.length > 0) {
            html += `
                <div class="col-md-6">
                    <h6 class="text-success mb-2"><i class="fas fa-key me-2"></i>数据库权限</h6>
                    <div class="mb-3">
                        ${ruleExpression.database_privileges.map(perm =>
                            `<span class="badge bg-success me-1 mb-1">${perm}</span>`
                        ).join('')}
                    </div>
                </div>
            `;
        }
    } else if (ruleExpression.type === 'postgresql_permissions') {
        // PostgreSQL结构：预定义角色、角色属性、数据库权限、表空间权限
        if (ruleExpression.predefined_roles && ruleExpression.predefined_roles.length > 0) {
            html += `
                <div class="col-md-6">
                    <h6 class="text-warning mb-2"><i class="fas fa-users me-2"></i>预定义角色</h6>
                    <div class="mb-3">
                        ${ruleExpression.predefined_roles.map(role =>
                            `<span class="badge bg-warning me-1 mb-1">${role}</span>`
                        ).join('')}
                    </div>
                </div>
            `;
        }
        if (ruleExpression.role_attributes && ruleExpression.role_attributes.length > 0) {
            // 角色属性显示名称映射
            const roleAttributeDisplayNames = {
                'can_super': '超级用户属性',
                'can_create_db': '创建数据库属性',
                'can_create_role': '创建角色属性',
                'can_inherit': '继承权限属性',
                'can_login': '登录属性',
                'can_replicate': '复制属性',
                'can_bypass_rls': '绕过行级安全属性',
                'connection_limit': '连接限制属性'
            };
            
            html += `
                <div class="col-md-6">
                    <h6 class="text-primary mb-2"><i class="fas fa-user-shield me-2"></i>角色属性</h6>
                    <div class="mb-3">
                        ${ruleExpression.role_attributes.map(attr => {
                            const displayName = roleAttributeDisplayNames[attr] || attr;
                            return `<span class="badge bg-primary me-1 mb-1">${displayName}</span>`;
                        }).join('')}
                    </div>
                </div>
            `;
        }
        if (ruleExpression.database_privileges && ruleExpression.database_privileges.length > 0) {
            html += `
                <div class="col-md-6">
                    <h6 class="text-success mb-2"><i class="fas fa-database me-2"></i>数据库权限</h6>
                    <div class="mb-3">
                        ${ruleExpression.database_privileges.map(perm =>
                            `<span class="badge bg-success me-1 mb-1">${perm}</span>`
                        ).join('')}
                    </div>
                </div>
            `;
        }
        if (ruleExpression.tablespace_privileges && ruleExpression.tablespace_privileges.length > 0) {
            html += `
                <div class="col-md-6">
                    <h6 class="text-info mb-2"><i class="fas fa-hdd me-2"></i>表空间权限</h6>
                    <div class="mb-3">
                        ${ruleExpression.tablespace_privileges.map(perm =>
                            `<span class="badge bg-info me-1 mb-1">${perm}</span>`
                        ).join('')}
                    </div>
                </div>
            `;
        }
    } else if (ruleExpression.type === 'oracle_permissions') {
        // Oracle结构：角色、系统权限、表空间权限、表空间配额
        if (ruleExpression.roles && ruleExpression.roles.length > 0) {
            html += `
                <div class="col-md-6">
                    <h6 class="text-danger mb-2"><i class="fas fa-users-cog me-2"></i>角色</h6>
                    <div class="mb-3">
                        ${ruleExpression.roles.map(role =>
                            `<span class="badge bg-danger me-1 mb-1">${role}</span>`
                        ).join('')}
                    </div>
                </div>
            `;
        }
        if (ruleExpression.system_privileges && ruleExpression.system_privileges.length > 0) {
            html += `
                <div class="col-md-6">
                    <h6 class="text-primary mb-2"><i class="fas fa-shield-alt me-2"></i>系统权限</h6>
                    <div class="mb-3">
                        ${ruleExpression.system_privileges.map(perm =>
                            `<span class="badge bg-primary me-1 mb-1">${perm}</span>`
                        ).join('')}
                    </div>
                </div>
            `;
        }
        if (ruleExpression.tablespace_privileges && ruleExpression.tablespace_privileges.length > 0) {
            html += `
                <div class="col-md-6">
                    <h6 class="text-info mb-2"><i class="fas fa-hdd me-2"></i>表空间权限</h6>
                    <div class="mb-3">
                        ${ruleExpression.tablespace_privileges.map(perm =>
                            `<span class="badge bg-info me-1 mb-1">${perm}</span>`
                        ).join('')}
                    </div>
                </div>
            `;
        }
        if (ruleExpression.tablespace_quotas && ruleExpression.tablespace_quotas.length > 0) {
            html += `
                <div class="col-md-6">
                    <h6 class="text-warning mb-2"><i class="fas fa-chart-pie me-2"></i>表空间配额</h6>
                    <div class="mb-3">
                        ${ruleExpression.tablespace_quotas.map(quota =>
                            `<span class="badge bg-warning me-1 mb-1">${quota}</span>`
                        ).join('')}
                    </div>
                </div>
            `;
        }
    } else if (ruleExpression.permissions) {
        // 旧格式或其他数据库类型
        html += `
            <div class="col-12">
                <h6 class="text-secondary mb-2"><i class="fas fa-list me-2"></i>权限列表</h6>
                <div class="mb-3">
                    ${ruleExpression.permissions.map(perm =>
                        `<span class="badge bg-secondary me-1 mb-1">${perm}</span>`
                    ).join('')}
                </div>
            </div>
        `;
    }

    html += '</div>';
    container.innerHTML = html;
}

// 删除规则
function deleteRule(id) {
    if (!confirm('确定要删除这个规则吗？')) {
        return;
    }

    fetch(`/account-classification/rules/${id}`, {
        method: 'DELETE',
        headers: {
            'X-CSRFToken': document.querySelector('meta[name="csrf-token"]').getAttribute('content')
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showAlert('success', '规则删除成功');
            loadRules();
        } else {
            showAlert('danger', data.error);
        }
    })
    .catch(error => {
        console.error('Error:', error);
        showAlert('danger', '删除规则失败');
    });
}

// 自动分类所有账户
function autoClassifyAll() {
    if (!confirm('确定要对所有账户进行自动分类吗？')) {
        return;
    }

    // 记录操作开始日志
    logUserAction('开始自动分类所有账户', { operation: 'auto_classify_all' });

    fetch('/account-classification/auto-classify', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': document.querySelector('meta[name="csrf-token"]').getAttribute('content')
        },
        body: JSON.stringify({})
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            // 记录成功日志
            logUserAction('自动分类所有账户成功', {
                operation: 'auto_classify_all',
                result: 'success',
                message: data.message
            });
            showAlert('success', data.message);
        } else {
            // 记录失败日志
            logError('自动分类所有账户失败', {
                operation: 'auto_classify_all',
                result: 'failed',
                error: data.error
            });
            showAlert('danger', data.error);
        }
    })
    .catch(error => {
        // 记录异常日志
        logErrorWithContext(error, '自动分类所有账户异常', {
            operation: 'auto_classify_all',
            result: 'exception'
        });
        showAlert('danger', '自动分类失败');
    });
}

// 显示提示信息
function showAlert(type, message) {
    const alertDiv = document.createElement('div');
    alertDiv.className = `alert alert-${type} alert-dismissible fade show`;
    alertDiv.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;

    // 插入到页面顶部
    const container = document.querySelector('.container-fluid');
    container.insertBefore(alertDiv, container.firstChild);

    // 3秒后自动消失
    setTimeout(() => {
        if (alertDiv.parentNode) {
            alertDiv.remove();
        }
    }, 3000);
}
