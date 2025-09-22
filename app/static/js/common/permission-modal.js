/**
 * 权限模态框组件
 * 提供统一的权限显示模态框功能
 */

/**
 * 显示权限模态框
 * @param {Object} permissions - 权限数据
 * @param {Object} account - 账户数据
 */
function showPermissionsModal(permissions, account) {

    try {
        // 获取数据库类型
        const dbType = account.db_type;

        // 检查权限对象的所有属性

        // 创建或获取模态框
        let modal = document.getElementById('permissionsModal');
        if (!modal) {
            modal = createPermissionsModal();
            document.body.appendChild(modal);
        }

        // 更新模态框标题
        const titleElement = document.getElementById('permissionsModalTitle');
        if (titleElement) {
            titleElement.textContent = `账户权限详情 - ${account.username}`;
        }

        // 渲染权限内容
        const bodyElement = document.getElementById('permissionsModalBody');
        if (bodyElement) {
            bodyElement.innerHTML = renderPermissionsByType(permissions, dbType);
        }

        // 显示模态框
        const bsModal = new bootstrap.Modal(modal);
        bsModal.show();
    } catch (error) {
        console.error('showPermissionsModal 函数执行出错:', error);
        console.error('错误堆栈:', error.stack);
        if (window.showAlert) {
            window.showAlert('danger', '显示权限信息时发生错误: ' + error.message);
        }
    }
}

/**
 * 创建权限模态框HTML
 * @returns {HTMLElement} 模态框元素
 */
function createPermissionsModal() {
    const modalHtml = `
        <div class="modal fade" id="permissionsModal" tabindex="-1" aria-labelledby="permissionsModalLabel" aria-hidden="true">
            <div class="modal-dialog modal-xl">
                <div class="modal-content">
                    <div class="modal-header">
                        <h5 class="modal-title" id="permissionsModalLabel">
                            <i class="fas fa-shield-alt me-2"></i>
                            <span id="permissionsModalTitle">账户权限详情</span>
                        </h5>
                        <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                    </div>
                    <div class="modal-body" id="permissionsModalBody">
                        <!-- 权限内容将动态渲染 -->
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">关闭</button>
                    </div>
                </div>
            </div>
        </div>
    `;

    const tempDiv = document.createElement('div');
    tempDiv.innerHTML = modalHtml;
    return tempDiv.firstElementChild;
}

/**
 * 根据数据库类型渲染权限
 * @param {Object} permissions - 权限数据
 * @param {string} dbType - 数据库类型
 * @returns {string} 渲染的HTML
 */
function renderPermissionsByType(permissions, dbType) {
    switch (dbType) {
        case 'mysql':
            return renderMySQLPermissions(permissions);
        case 'postgresql':
            return renderPostgreSQLPermissions(permissions);
        case 'oracle':
            return renderOraclePermissions(permissions);
        case 'sqlserver':
            return renderSQLServerPermissions(permissions);
        default:
            return renderDefaultPermissions(permissions, dbType);
    }
}

/**
 * 渲染MySQL权限
 * @param {Object} permissions - 权限数据
 * @returns {string} 渲染的HTML
 */
function renderMySQLPermissions(permissions) {
    // 检查权限数据是否存在
    if (!permissions || typeof permissions !== 'object') {
        return '<p class="text-muted">无权限信息</p>';
    }

     // 处理全局权限 - 将字符串数组转换为权限列表
    let globalPrivilegesHtml = '<p class="text-muted">无全局权限</p>';
    if (permissions.global_privileges && Array.isArray(permissions.global_privileges) && permissions.global_privileges.length > 0) {
        const allPrivileges = [];
        permissions.global_privileges.forEach(permString => {
            if (typeof permString === 'string') {
                // 分割权限字符串并添加到列表中
                const privileges = permString.split(',').map(p => p.trim()).filter(p => p);
                allPrivileges.push(...privileges);
            }
        });

        if (allPrivileges.length > 0) {
            globalPrivilegesHtml = `
                <div class="row">
                    ${allPrivileges.map(perm => `
                        <div class="col-md-6 mb-2">
                            <span class="badge bg-primary me-2">
                                <i class="fas fa-shield-alt me-1"></i>${perm}
                            </span>
                        </div>
                    `).join('')}
                </div>
            `;
        }
    }

    return `
        <div class="mb-3">
            <h6><i class="fas fa-shield-alt text-primary me-2"></i>全局权限</h6>
            ${globalPrivilegesHtml}
        </div>
        <div class="mb-3">
            <h6><i class="fas fa-database text-success me-2"></i>数据库权限</h6>
            ${permissions.database_privileges && typeof permissions.database_privileges === 'object' && Object.keys(permissions.database_privileges).length > 0 ? `
                <div class="table-responsive">
                    <table class="table table-sm">
                        <thead>
                            <tr>
                                <th>数据库</th>
                                <th>权限</th>
                            </tr>
                        </thead>
                        <tbody>
                            ${Object.entries(permissions.database_privileges).map(([dbName, privileges]) => `
                                <tr>
                                    <td>${dbName}</td>
                                    <td>
                                        ${Array.isArray(privileges) ? privileges.map(priv => `
                                            <span class="badge bg-success me-1">${priv}</span>
                                        `).join('') : '<span class="text-muted">无权限</span>'}
                                    </td>
                                </tr>
                            `).join('')}
                        </tbody>
                    </table>
                </div>
            ` : '<p class="text-muted">无数据库权限</p>'}
        </div>
        <div class="mb-3">
            <h6><i class="fas fa-table text-info me-2"></i>表权限</h6>
            ${permissions.table_privileges && Array.isArray(permissions.table_privileges) && permissions.table_privileges.length > 0 ? `
                <div class="table-responsive">
                    <table class="table table-sm">
                        <thead>
                            <tr>
                                <th>数据库</th>
                                <th>表</th>
                                <th>权限</th>
                            </tr>
                        </thead>
                        <tbody>
                            ${permissions.table_privileges.map(table => `
                                <tr>
                                    <td>${table.database}</td>
                                    <td>${table.table}</td>
                                    <td>
                                        ${Array.isArray(table.privileges) ? table.privileges.map(priv => `
                                            <span class="badge bg-info me-1">${priv}</span>
                                        `).join('') : '<span class="text-muted">无权限</span>'}
                                    </td>
                                </tr>
                            `).join('')}
                        </tbody>
                    </table>
                </div>
            ` : '<p class="text-muted">无表权限</p>'}
        </div>
    `;
}

/**
 * 渲染PostgreSQL权限
 * @param {Object} permissions - 权限数据
 * @returns {string} 渲染的HTML
 */
function renderPostgreSQLPermissions(permissions) {
    // 检查权限数据是否存在
    if (!permissions || typeof permissions !== 'object') {
        return '<p class="text-muted">无权限信息</p>';
    }

    // 处理预定义角色
    let predefinedRolesHtml = '<p class="text-muted">无预定义角色</p>';
    if (permissions.predefined_roles && Array.isArray(permissions.predefined_roles) && permissions.predefined_roles.length > 0) {
        predefinedRolesHtml = `
            <div class="row">
                ${permissions.predefined_roles.map(role => `
                    <div class="col-md-6 mb-2">
                        <span class="badge bg-warning me-2">
                            <i class="fas fa-user-tag me-1"></i>${role}
                        </span>
                    </div>
                `).join('')}
            </div>
        `;
    }

    // 处理角色属性
    let roleAttributesHtml = '<p class="text-muted">无角色属性</p>';
    if (permissions.role_attributes) {
        if (Array.isArray(permissions.role_attributes)) {
            // 数组格式
            roleAttributesHtml = `
                <div class="row">
                    ${permissions.role_attributes.map(attr => `
                        <div class="col-md-6 mb-2">
                            <span class="badge bg-primary me-2">
                                <i class="fas fa-user-cog me-1"></i>${attr}
                            </span>
                        </div>
                    `).join('')}
                </div>
            `;
        } else if (typeof permissions.role_attributes === 'object') {
            // 对象格式 - 只显示true值的属性
            const attributes = Object.entries(permissions.role_attributes)
                .filter(([key, value]) => value === true);
            if (attributes.length > 0) {
                roleAttributesHtml = `
                    <div class="row">
                        ${attributes.map(([key, value]) => `
                            <div class="col-md-6 mb-2">
                                <span class="badge bg-primary me-2">
                                    <i class="fas fa-user-cog me-1"></i>${key}
                                </span>
                            </div>
                        `).join('')}
                    </div>
                `;
            } else {
                roleAttributesHtml = '<p class="text-muted">无角色属性</p>';
            }
        }
    }

    // 处理数据库权限
    let databasePrivilegesHtml = '<p class="text-muted">无数据库权限</p>';
    const dbPrivs = permissions.database_privileges_pg || permissions.database_permissions;
    if (dbPrivs && typeof dbPrivs === 'object' && Object.keys(dbPrivs).length > 0) {
        databasePrivilegesHtml = `
            <div class="table-responsive">
                <table class="table table-sm">
                    <thead>
                        <tr>
                            <th>数据库</th>
                            <th>权限</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${Object.entries(dbPrivs).map(([db, privs]) => `
                            <tr>
                                <td>${db}</td>
                                <td>
                                    ${Array.isArray(privs) ? privs.map(priv => `
                                        <span class="badge bg-success me-1">${priv}</span>
                                    `).join('') : '<span class="text-muted">无权限</span>'}
                                </td>
                            </tr>
                        `).join('')}
                    </tbody>
                </table>
            </div>
        `;
    }

    // 处理表空间权限
    let tablespacePrivilegesHtml = '<p class="text-muted">无表空间权限</p>';
    if (permissions.tablespace_privileges && Array.isArray(permissions.tablespace_privileges) && permissions.tablespace_privileges.length > 0) {
        tablespacePrivilegesHtml = `
            <div class="row">
                ${permissions.tablespace_privileges.map(priv => `
                    <div class="col-md-6 mb-2">
                        <span class="badge bg-info me-2">
                            <i class="fas fa-hdd me-1"></i>${priv}
                        </span>
                    </div>
                `).join('')}
            </div>
        `;
    }

    return `
        <div class="mb-3">
            <h6><i class="fas fa-user-tag text-warning me-2"></i>预定义角色</h6>
            ${predefinedRolesHtml}
        </div>
        <div class="mb-3">
            <h6><i class="fas fa-user-shield text-primary me-2"></i>角色属性</h6>
            ${roleAttributesHtml}
        </div>
        <div class="mb-3">
            <h6><i class="fas fa-database text-success me-2"></i>数据库权限</h6>
            ${databasePrivilegesHtml}
        </div>
        <div class="mb-3">
            <h6><i class="fas fa-hdd text-info me-2"></i>表空间权限</h6>
            ${tablespacePrivilegesHtml}
        </div>
    `;
}

/**
 * 渲染Oracle权限
 * @param {Object} permissions - 权限数据
 * @returns {string} 渲染的HTML
 */
function renderOraclePermissions(permissions) {
    // 检查权限数据是否存在
    if (!permissions || typeof permissions !== 'object') {
        return '<p class="text-muted">无权限信息</p>';
    }

    return `
        <div class="mb-3">
            <h6><i class="fas fa-crown text-primary me-2"></i>角色</h6>
            ${permissions.oracle_roles && Array.isArray(permissions.oracle_roles) && permissions.oracle_roles.length > 0 ? `
                <div class="row">
                    ${permissions.oracle_roles.map(role => `
                        <div class="col-md-6 mb-2">
                            <span class="badge bg-primary me-2">
                                <i class="fas fa-crown me-1"></i>${role}
                            </span>
                        </div>
                    `).join('')}
                </div>
            ` : '<p class="text-muted">无角色</p>'}
        </div>
        <div class="mb-3">
            <h6><i class="fas fa-shield-alt text-success me-2"></i>系统权限</h6>
            ${permissions.system_privileges && Array.isArray(permissions.system_privileges) && permissions.system_privileges.length > 0 ? `
                <div class="row">
                    ${permissions.system_privileges.map(priv => `
                        <div class="col-md-6 mb-2">
                            <span class="badge bg-success me-2">
                                <i class="fas fa-shield-alt me-1"></i>${priv}
                            </span>
                        </div>
                    `).join('')}
                </div>
            ` : '<p class="text-muted">无系统权限</p>'}
        </div>
        <div class="mb-3">
            <h6><i class="fas fa-hdd text-info me-2"></i>表空间权限</h6>
            ${permissions.tablespace_privileges_oracle && typeof permissions.tablespace_privileges_oracle === 'object' && Object.keys(permissions.tablespace_privileges_oracle).length > 0 ? `
                <div class="row">
                    ${Object.entries(permissions.tablespace_privileges_oracle).map(([tsName, privileges]) => `
                        <div class="col-md-12 mb-2">
                            <div class="d-flex align-items-center">
                                <span class="badge bg-info me-2">
                                    <i class="fas fa-hdd me-1"></i>${tsName}
                                </span>
                                <div class="ms-2">
                                    ${Array.isArray(privileges) ? privileges.map(priv => `
                                        <span class="badge bg-light text-dark me-1">${priv}</span>
                                    `).join('') : ''}
                                </div>
                            </div>
                        </div>
                    `).join('')}
                </div>
            ` : '<p class="text-muted">无表空间权限</p>'}
        </div>
        <div class="mb-3">
            <h6><i class="fas fa-chart-pie text-warning me-2"></i>表空间配额</h6>
            ${permissions.tablespace_quotas && Array.isArray(permissions.tablespace_quotas) && permissions.tablespace_quotas.length > 0 ? `
                <div class="row">
                    ${permissions.tablespace_quotas.map(quota => `
                        <div class="col-md-6 mb-2">
                            <span class="badge bg-warning me-2">
                                <i class="fas fa-chart-pie me-1"></i>${quota}
                            </span>
                        </div>
                    `).join('')}
                </div>
            ` : '<p class="text-muted">无表空间配额</p>'}
        </div>
    `;
}

/**
 * 渲染SQL Server权限
 * @param {Object} permissions - 权限数据
 * @returns {string} 渲染的HTML
 */
function renderSQLServerPermissions(permissions) {
    // 检查权限数据是否存在
    if (!permissions || typeof permissions !== 'object') {
        return '<p class="text-muted">无权限信息</p>';
    }

    return `
        <div class="mb-3">
            <h6><i class="fas fa-crown text-primary me-2"></i>服务器角色</h6>
            ${permissions.server_roles && Array.isArray(permissions.server_roles) && permissions.server_roles.length > 0 ? `
                <div class="row">
                    ${permissions.server_roles.map(role => `
                        <div class="col-md-6 mb-2">
                            <span class="badge bg-primary me-2">
                                <i class="fas fa-crown me-1"></i>${role}
                            </span>
                        </div>
                    `).join('')}
                </div>
            ` : '<p class="text-muted">无服务器角色</p>'}
        </div>
        <div class="mb-3">
            <h6><i class="fas fa-database text-info me-2"></i>数据库角色</h6>
            ${permissions.database_roles && typeof permissions.database_roles === 'object' && Object.keys(permissions.database_roles).length > 0 ? `
                <div class="table-responsive">
                    <table class="table table-sm">
                        <thead>
                            <tr>
                                <th>数据库</th>
                                <th>角色</th>
                            </tr>
                        </thead>
                        <tbody>
                            ${Object.entries(permissions.database_roles).map(([dbName, roles]) => `
                                <tr>
                                    <td>${dbName}</td>
                                    <td>
                                        ${Array.isArray(roles) ? roles.map(role => `
                                            <span class="badge bg-info me-1">${role}</span>
                                        `).join('') : '<span class="text-muted">无角色</span>'}
                                    </td>
                                </tr>
                            `).join('')}
                        </tbody>
                    </table>
                </div>
            ` : '<p class="text-muted">无数据库角色</p>'}
        </div>
        <div class="mb-3">
            <h6><i class="fas fa-shield-alt text-success me-2"></i>服务器权限</h6>
            ${permissions.server_permissions && Array.isArray(permissions.server_permissions) && permissions.server_permissions.length > 0 ? `
                <div class="row">
                    ${permissions.server_permissions.map(perm => `
                        <div class="col-md-6 mb-2">
                            <span class="badge bg-success me-2">
                                <i class="fas fa-shield-alt me-1"></i>${perm}
                            </span>
                        </div>
                    `).join('')}
                </div>
            ` : '<p class="text-muted">无服务器权限</p>'}
        </div>
        <div class="mb-3">
            <h6><i class="fas fa-database text-warning me-2"></i>数据库权限</h6>
            ${permissions.database_permissions && typeof permissions.database_permissions === 'object' && Object.keys(permissions.database_permissions).length > 0 ? `
                <div class="table-responsive">
                    <table class="table table-sm">
                        <thead>
                            <tr>
                                <th>数据库</th>
                                <th>权限</th>
                            </tr>
                        </thead>
                        <tbody>
                            ${Object.entries(permissions.database_permissions).map(([dbName, perms]) => `
                                <tr>
                                    <td>${dbName}</td>
                                    <td>
                                        ${Array.isArray(perms) ? perms.map(perm => `
                                            <span class="badge bg-warning me-1">${perm}</span>
                                        `).join('') : '<span class="text-muted">无权限</span>'}
                                    </td>
                                </tr>
                            `).join('')}
                        </tbody>
                    </table>
                </div>
            ` : '<p class="text-muted">无数据库权限</p>'}
        </div>
    `;
}

/**
 * 渲染默认权限（未知数据库类型）
 * @param {Object} permissions - 权限数据
 * @param {string} dbType - 数据库类型
 * @returns {string} 渲染的HTML
 */
function renderDefaultPermissions(permissions, dbType) {
    // 检查权限数据是否存在
    if (!permissions || typeof permissions !== 'object') {
        return '<p class="text-muted">无权限信息</p>';
    }

    return `
        <div class="alert alert-warning">
            <i class="fas fa-exclamation-triangle me-2"></i>
            未知的数据库类型: ${dbType}
        </div>
        <div class="mb-3">
            <h6>权限数据</h6>
            <pre class="bg-light p-3">${JSON.stringify(permissions, null, 2)}</pre>
        </div>
    `;
}

// 导出到全局作用域
window.showPermissionsModal = showPermissionsModal;
window.createPermissionsModal = createPermissionsModal;
window.renderPermissionsByType = renderPermissionsByType;
