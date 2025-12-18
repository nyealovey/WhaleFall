/**
 * 权限模态框组件
 * 提供统一的权限显示模态框功能
 */

const PRIVILEGE_EMPTY_TEXT = '暂无权限信息';
const toast = window.toast;

function normalizePrivilegeLabel(label) {
    if (label == null) {
        return '';
    }
    const text = String(label).trim();
    if (!text) {
        return '';
    }
    return text
        .split(/[_\s]+/)
        .filter(Boolean)
        .map((part) => part.charAt(0).toUpperCase() + part.slice(1).toLowerCase())
        .join(' ');
}

function renderEmptyPill(text = PRIVILEGE_EMPTY_TEXT) {
    return `<span class="status-pill status-pill--muted">${text}</span>`;
}

function renderPermissionSection(title, icon, bodyHtml, metaText = '') {
    return `
        <section class="permission-section">
            <div class="permission-section-heading">
                <span class="chip-outline chip-outline--brand">
                    ${icon ? `<i class="${icon} me-2"></i>` : ''}${title}
                </span>
                ${metaText ? `<span class="status-pill status-pill--muted">${metaText}</span>` : ''}
            </div>
            <div class="permission-section-body">${bodyHtml}</div>
        </section>
    `;
}

function renderLedgerChips(items, { emptyLabel = PRIVILEGE_EMPTY_TEXT } = {}) {
    if (!Array.isArray(items) || items.length === 0) {
        return renderEmptyPill(emptyLabel);
    }
    return `
        <div class="ledger-chip-stack">
            ${items
                .map((item) => {
                    if (typeof item === 'object' && item !== null) {
                        const text = normalizePrivilegeLabel(item.label ?? '');
                        const iconHtml = item.icon ? `<i class="${item.icon} me-1"></i>` : '';
                        const extraClass = item.muted ? ' ledger-chip--muted' : '';
                        return `<span class="ledger-chip${extraClass}">${iconHtml}${text}</span>`;
                    }
                    return `<span class="ledger-chip">${normalizePrivilegeLabel(item)}</span>`;
                })
                .join('')}
        </div>
    `;
}

function renderStackRow(label, icon, valueHtml) {
    return `
        <div class="permission-stack-row">
            <div class="permission-stack-label">
                <span class="chip-outline chip-outline--muted">
                    ${icon ? `<i class="${icon} me-2"></i>` : ''}${label}
                </span>
            </div>
            <div class="permission-stack-value">${valueHtml}</div>
        </div>
    `;
}

function renderStack(rows, emptyLabel) {
    if (!rows || rows.length === 0) {
        return renderEmptyPill(emptyLabel);
    }
    return `<div class="permission-stack">${rows.join('')}</div>`;
}

function flattenPrivilegeStrings(rawPrivileges) {
    if (!Array.isArray(rawPrivileges)) {
        return [];
    }
    const values = [];
    rawPrivileges.forEach((item) => {
        if (typeof item === 'string') {
            item
                .split(',')
                .map((part) => part.trim())
                .filter(Boolean)
                .forEach((value) => values.push(value));
        }
    });
    return values;
}

/**
 * 显示权限模态框
 * @param {Object} permissions - 权限数据
 * @param {Object} account - 账户数据
 * @returns {void}
 */
function showPermissionsModal(permissions, account) {

    try {
        if (!account || typeof account !== 'object') {
            console.error('showPermissionsModal 需要有效的 account 参数');
            toast.error('无法获取账户信息，请稍后重试', { title: '错误' });
            return;
        }

        if (!permissions || typeof permissions !== 'object') {
            console.error('showPermissionsModal 需要有效的 permissions 参数');
            toast.error('无法获取权限信息，请稍后重试', { title: '错误' });
            return;
        }

        // 获取数据库类型
        const dbType = account.db_type || (account.instance_name ? account.instance_name : 'unknown');

        // 检查权限对象的所有属性

        ensurePermissionModal();
        updateModalContent(permissions, account, dbType);
        openPermissionModal();
    } catch (error) {
        console.error('showPermissionsModal 函数执行出错:', error);
        console.error('错误堆栈:', error.stack);
        toast.error('获取权限信息失败，请稍后重试', { title: '错误' });
    }
}

/**
 * 创建权限模态框HTML
 * @param {void} 无参数。内部缓存 window.PermissionModalInstance。
 * @returns {HTMLElement} 模态框元素
 */
function ensurePermissionModal() {
    if (window.PermissionModalInstance) {
        return window.PermissionModalInstance;
    }
    const factory = window.UI?.createModal;
    if (!factory) {
        throw new Error('UI.createModal 未加载，无法初始化权限模态框');
    }
    window.PermissionModalInstance = factory({
        modalSelector: '#permissionsModal',
        onClose: resetPermissionModal,
    });
    return window.PermissionModalInstance;
}

/**
 * 打开权限模态框。
 *
 * @param {void} 无参数。依赖 ensurePermissionModal。
 * @returns {void}
 */
function openPermissionModal() {
    const instance = ensurePermissionModal();
    instance.open();
}

/**
 * 重置模态内容，显示加载状态。
 *
 * @param {void} 无参数。直接更新模态 DOM。
 * @returns {void}
 */
function resetPermissionModal() {
    const helpers = window.DOMHelpers;
    if (!helpers) {
        return;
    }
    const body = helpers.selectOne('#permissionsModalBody');
    if (body.length) {
        body.html(`
            <div class="permission-modal__loading text-center">
                <div class="spinner-border text-primary" role="status">
                    <span class="visually-hidden">加载中...</span>
                </div>
                <p class="mt-2 text-muted">正在加载权限信息...</p>
            </div>
        `);
    }
    const title = helpers.selectOne('#permissionsModalTitle');
    if (title.length) {
        title.text('账户权限详情');
    }
    const meta = helpers.selectOne('#permissionsModalMeta');
    if (meta.length) {
        meta.text('加载中...');
    }
}

/**
 * 根据账户和数据库类型渲染权限详情。
 *
 * @param {Object} permissions 权限数据。
 * @param {Object} account 账户信息。
 * @param {string} dbType 数据库类型。
 * @returns {void}
 */
function updateModalContent(permissions, account, dbType) {
    const helpers = window.DOMHelpers;
    if (!helpers) {
        throw new Error('DOMHelpers 未初始化');
    }
    const title = helpers.selectOne('#permissionsModalTitle');
    title.text('账户权限详情');
    const meta = helpers.selectOne('#permissionsModalMeta');
    if (meta.length) {
        const metaParts = [];
        if (account.username) {
            metaParts.push(account.username);
        }
        if (dbType) {
            metaParts.push(dbType.toUpperCase());
        }
        if (account.instance_name) {
            metaParts.push(account.instance_name);
        }
        meta.text(metaParts.length ? metaParts.join(' · ') : '账号信息缺失');
    }
    const body = helpers.selectOne('#permissionsModalBody');
    body.html(renderPermissionsByType(permissions, dbType));
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
        return renderEmptyPill();
    }

    const globalPrivileges = flattenPrivilegeStrings(permissions.global_privileges);
    const globalSection = renderPermissionSection(
        '全局权限',
        'fas fa-globe',
        renderLedgerChips(globalPrivileges, { emptyLabel: '无全局权限' })
    );

    const dbRows = [];
    if (permissions.database_privileges && typeof permissions.database_privileges === 'object') {
        Object.entries(permissions.database_privileges).forEach(([dbName, privs]) => {
            dbRows.push(
                renderStackRow(
                    dbName,
                    'fas fa-database',
                    renderLedgerChips(Array.isArray(privs) ? privs : [], { emptyLabel: '无权限' })
                )
            );
        });
    }
    const databaseSection = renderPermissionSection(
        '数据库权限',
        'fas fa-database',
        renderStack(dbRows, '无数据库权限')
    );

    const tableRows = [];
    if (Array.isArray(permissions.table_privileges)) {
        permissions.table_privileges.forEach((table) => {
            const label = `${table.database || '*'}.${table.table || '*'}`;
            tableRows.push(
                renderStackRow(
                    label,
                    'fas fa-table',
                    renderLedgerChips(Array.isArray(table.privileges) ? table.privileges : [], { emptyLabel: '无表权限' })
                )
            );
        });
    }
    const tableSection = renderPermissionSection(
        '表权限',
        'fas fa-table',
        renderStack(tableRows, '无表权限')
    );

    return [globalSection, databaseSection, tableSection].join('');
}

/**
 * 渲染PostgreSQL权限
 * @param {Object} permissions - 权限数据
 * @returns {string} 渲染的HTML
 */
function renderPostgreSQLPermissions(permissions) {
    if (!permissions || typeof permissions !== 'object') {
        return renderEmptyPill();
    }

    const predefinedRoles = renderPermissionSection(
        '预定义角色',
        'fas fa-user-tag',
        renderLedgerChips(permissions.predefined_roles, { emptyLabel: '无预定义角色' })
    );

    let roleAttributes = [];
    if (Array.isArray(permissions.role_attributes)) {
        roleAttributes = permissions.role_attributes;
    } else if (typeof permissions.role_attributes === 'object' && permissions.role_attributes !== null) {
        roleAttributes = Object.entries(permissions.role_attributes)
            .filter(([, value]) => value === true)
            .map(([key]) => key);
    }
    const attributesSection = renderPermissionSection(
        '角色属性',
        'fas fa-user-shield',
        renderLedgerChips(roleAttributes, { emptyLabel: '无角色属性' })
    );

    const dbRows = [];
    const dbPrivs = permissions.database_privileges_pg || permissions.database_permissions;
    if (dbPrivs && typeof dbPrivs === 'object') {
        Object.entries(dbPrivs).forEach(([dbName, privs]) => {
            dbRows.push(
                renderStackRow(
                    dbName,
                    'fas fa-database',
                    renderLedgerChips(Array.isArray(privs) ? privs : [], { emptyLabel: '无权限' })
                )
            );
        });
    }
    const databaseSection = renderPermissionSection(
        '数据库权限',
        'fas fa-database',
        renderStack(dbRows, '无数据库权限')
    );

    const tablespaceSection = renderPermissionSection(
        '表空间权限',
        'fas fa-hdd',
        renderLedgerChips(permissions.tablespace_privileges, { emptyLabel: '无表空间权限' })
    );

    return [predefinedRoles, attributesSection, databaseSection, tablespaceSection].join('');
}

/**
 * 渲染Oracle权限
 * @param {Object} permissions - 权限数据
 * @returns {string} 渲染的HTML
 */
function renderOraclePermissions(permissions) {
    // 检查权限数据是否存在
    if (!permissions || typeof permissions !== 'object') {
        return renderEmptyPill();
    }

    const roleSection = renderPermissionSection(
        '角色',
        'fas fa-crown',
        renderLedgerChips(permissions.oracle_roles, { emptyLabel: '无角色' })
    );

    const systemSection = renderPermissionSection(
        '系统权限',
        'fas fa-shield-alt',
        renderLedgerChips(permissions.oracle_system_privileges, { emptyLabel: '无系统权限' })
    );

    const tablespaceRows = [];
    if (permissions.oracle_tablespace_privileges && typeof permissions.oracle_tablespace_privileges === 'object') {
        Object.entries(permissions.oracle_tablespace_privileges).forEach(([name, list]) => {
            tablespaceRows.push(
                renderStackRow(
                    name,
                    'fas fa-database',
                    renderLedgerChips(Array.isArray(list) ? list : [], { emptyLabel: '无表空间权限' })
                )
            );
        });
    }
    const tablespaceSection = renderPermissionSection(
        '表空间权限',
        'fas fa-hdd',
        renderStack(tablespaceRows, '无表空间权限')
    );

    const quotaSection = renderPermissionSection(
        '表空间配额',
        'fas fa-chart-pie',
        renderLedgerChips(permissions.tablespace_quotas, { emptyLabel: '无表空间配额' })
    );

    return [roleSection, systemSection, tablespaceSection, quotaSection].join('');
}

/**
 * 渲染SQL Server权限
 * @param {Object} permissions - 权限数据
 * @returns {string} 渲染的HTML
 */
function renderSQLServerPermissions(permissions) {
    // 检查权限数据是否存在
    if (!permissions || typeof permissions !== 'object') {
        return renderEmptyPill();
    }

    const serverRoles = renderPermissionSection(
        '服务器角色',
        'fas fa-crown',
        renderLedgerChips(permissions.server_roles, { emptyLabel: '无服务器角色' })
    );

    const dbRoleRows = [];
    if (permissions.database_roles && typeof permissions.database_roles === 'object') {
        Object.entries(permissions.database_roles).forEach(([dbName, roles]) => {
            dbRoleRows.push(
                renderStackRow(
                    dbName,
                    'fas fa-database',
                    renderLedgerChips(Array.isArray(roles) ? roles : [], { emptyLabel: '无角色' })
                )
            );
        });
    }
    const databaseRoles = renderPermissionSection(
        '数据库角色',
        'fas fa-database',
        renderStack(dbRoleRows, '无数据库角色')
    );

    const serverPermissions = renderPermissionSection(
        '服务器权限',
        'fas fa-shield-alt',
        renderLedgerChips(permissions.server_permissions, { emptyLabel: '无服务器权限' })
    );

    const dbPermissionRows = [];
    if (permissions.database_permissions && typeof permissions.database_permissions === 'object') {
        Object.entries(permissions.database_permissions).forEach(([dbName, perms]) => {
            dbPermissionRows.push(
                renderStackRow(
                    dbName,
                    'fas fa-database',
                    renderLedgerChips(Array.isArray(perms) ? perms : [], { emptyLabel: '无权限' })
                )
            );
        });
    }
    const databasePermissions = renderPermissionSection(
        '数据库权限',
        'fas fa-database',
        renderStack(dbPermissionRows, '无数据库权限')
    );

    return [serverRoles, databaseRoles, serverPermissions, databasePermissions].join('');
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
        return renderEmptyPill();
    }

    const notice = renderPermissionSection(
        '提示',
        'fas fa-exclamation-triangle',
        `<p class="mb-0">未知的数据库类型：${dbType || '未提供'}。以下为原始权限数据。</p>`
    );

    const payload = renderPermissionSection(
        '原始权限',
        'fas fa-code',
        `<pre class="bg-light p-3 rounded">${JSON.stringify(permissions, null, 2)}</pre>`
    );

    return notice + payload;
}

// 导出到全局作用域
function getOrCreateModal() {
    return ensurePermissionModal();
}

window.showPermissionsModal = showPermissionsModal;
window.createPermissionsModal = function () {
    return getOrCreateModal();
};
window.renderPermissionsByType = renderPermissionsByType;
