(function (window, document) {
  "use strict";

  const AccountClassificationService = window.AccountClassificationService;
  if (!AccountClassificationService) {
    console.error("AccountClassificationService 未初始化，权限策略中心无法加载");
    return;
  }
  const accountClassificationService = new AccountClassificationService(window.httpU);

  /**
   * 渲染权限复选组。
   *
   * @param {string} prefix DOM id 前缀。
   * @param {Array<Object>} items 权限项。
   * @param {string} idPrefix 字段前缀。
   * @param {string} icon FontAwesome 图标类。
   * @param {string} color Bootstrap 颜色名。
   * @param {string} fallback 空态文本。
   * @returns {string} HTML 片段。
   */
  function renderPermissionGroup(prefix, items, idPrefix, icon, color, fallback) {
    return (
      items
        ?.map(
          (item) => `
        <div class="form-check mb-2">
          <input class="form-check-input" type="checkbox" value="${item.name}" id="${prefix}${idPrefix}_${item.name}">
          <label class="form-check-label d-flex align-items-center" for="${prefix}${idPrefix}_${item.name}">
            <i class="${icon} text-${color} me-2"></i>
            <div>
              <div class="fw-bold">${item.name}</div>
              <small class="text-muted">${item.description || fallback}</small>
            </div>
          </label>
        </div>
      `,
        )
        .join('') || `<div class="text-muted">${fallback}暂无配置</div>`
    );
  }

  /**
   * 基础策略类，提供默认渲染/选择逻辑。
   *
   * @class
   */
  class PermissionStrategy {
    /**
     * 构造函数。
     *
     * @constructor
     * @param {string} dbType - 数据库类型
     */
    constructor(dbType) {
      this.dbType = dbType;
    }

    /**
     * 渲染权限选择器。
     *
     * @return {string} 渲染的 HTML 字符串
     */
    renderSelector() {
      return `<div class="alert alert-info">当前数据库类型 (${this.dbType}) 暂未提供权限策略。</div>`;
    }

    /**
     * 收集选中的权限。
     *
     * @param {HTMLElement} container - 容器元素
     * @return {Object} 包含选中权限的对象
     */
    collectSelected(container) {
      const checkboxes = container.querySelectorAll('input[type="checkbox"]:checked');
      const permissions = Array.from(checkboxes).map((checkbox) => checkbox.value);
      return { permissions };
    }

    buildExpression(selected, operator) {
      return {
        type: "permissions",
        permissions: selected.permissions || [],
        operator: operator || "OR",
      };
    }

    /**
     * 设置选中的权限。
     *
     * @param {Object} ruleExpression - 规则表达式对象
     * @param {HTMLElement} container - 容器元素
     * @return {void}
     */
    setSelected(ruleExpression, container) {
      const permissions = ruleExpression?.permissions || [];
      permissions.forEach((perm) => {
        const checkbox = container.querySelector(`#perm_${perm}`);
        if (checkbox) checkbox.checked = true;
      });
    }

    /**
     * 渲染权限显示。
     *
     * @param {Object} ruleExpression - 规则表达式对象
     * @return {string} 渲染的 HTML 字符串
     */
    renderDisplay(ruleExpression) {
      const permissions = ruleExpression?.permissions || [];
      if (permissions.length === 0) {
        return '<div class="text-muted">无权限配置</div>';
      }
      return `
        <div class="row">
          <div class="col-12">
            <h6 class="mb-2"><i class="fas fa-key me-2"></i>权限</h6>
            <div class="mb-2">
              ${permissions.map((item) => `<span class="badge bg-primary me-1 mb-1">${item}</span>`).join("")}
            </div>
          </div>
        </div>
      `;
    }

    hasSelection(selected) {
      if (!selected) return false;
      return Object.values(selected).some((value) => Array.isArray(value) && value.length > 0);
    }
  }

  /**
   * MySQL 专属策略，支持全局/数据库权限选择。
   *
   * @class
   * @extends PermissionStrategy
   */
  class MySQLPermissionStrategy extends PermissionStrategy {
    /**
     * 构造函数。
     *
     * @constructor
     */
    constructor() {
      super("mysql");
    }

    /**
     * 渲染 MySQL 权限选择器。
     *
     * @param {Object} [permissions={}] - 权限配置对象
     * @param {string} [prefix=""] - ID 前缀
     * @return {string} 渲染的 HTML 字符串
     */
    renderSelector(permissions = {}, prefix = "") {
      const globals = Array.isArray(permissions.global_privileges) ? permissions.global_privileges : [];
      const databases = Array.isArray(permissions.database_privileges) ? permissions.database_privileges : [];

      return `
        <div class="row">
          <div class="col-6">
            <h6 class="text-primary mb-3"><i class="fas fa-globe me-2"></i>全局权限</h6>
            <div class="permission-section">
              ${globals
                .map(
                  (perm) => `
                <div class="form-check mb-2">
                  <input class="form-check-input" type="checkbox" value="${perm.name}" id="${prefix}global_${perm.name}">
                  <label class="form-check-label d-flex align-items-center" for="${prefix}global_${perm.name}">
                    <i class="fas fa-globe text-primary me-2"></i>
                    <div>
                      <div class="fw-bold">${perm.name}</div>
                      <small class="text-muted">${perm.description || "全局权限"}</small>
                    </div>
                  </label>
                </div>
              `
                )
                .join("") || '<div class="text-muted">暂无全局权限</div>'}
            </div>
          </div>
          <div class="col-6">
            <h6 class="text-success mb-3"><i class="fas fa-database me-2"></i>数据库权限</h6>
            <div class="permission-section">
              ${databases
                .map(
                  (perm) => `
                <div class="form-check mb-2">
                  <input class="form-check-input" type="checkbox" value="${perm.name}" id="${prefix}db_${perm.name}">
                  <label class="form-check-label d-flex align-items-center" for="${prefix}db_${perm.name}">
                    <i class="fas fa-database text-success me-2"></i>
                    <div>
                      <div class="fw-bold">${perm.name}</div>
                      <small class="text-muted">${perm.description || "数据库权限"}</small>
                    </div>
                  </label>
                </div>
              `
                )
                .join("") || '<div class="text-muted">暂无数据库权限</div>'}
            </div>
          </div>
        </div>
      `;
    }

    collectSelected(container, prefix = "") {
      const globalPrivileges = [];
      const databasePrivileges = [];
      const checkboxes = container.querySelectorAll('input[type="checkbox"]:checked');

      checkboxes.forEach((checkbox) => {
        if (checkbox.id.startsWith(`${prefix}global_`)) {
          globalPrivileges.push(checkbox.value);
        } else if (checkbox.id.startsWith(`${prefix}db_`)) {
          databasePrivileges.push(checkbox.value);
        }
      });

      return {
        global_privileges: globalPrivileges,
        database_privileges: databasePrivileges,
      };
    }

    buildExpression(selected, operator) {
      return {
        type: "mysql_permissions",
        global_privileges: selected.global_privileges || [],
        database_privileges: selected.database_privileges || [],
        operator: operator || "OR",
      };
    }

    setSelected(ruleExpression, container, prefix = "") {
      (ruleExpression.global_privileges || []).forEach((perm) => {
        const checkbox = container.querySelector(`#${prefix}global_${perm}`);
        if (checkbox) checkbox.checked = true;
      });
      (ruleExpression.database_privileges || []).forEach((perm) => {
        const checkbox = container.querySelector(`#${prefix}db_${perm}`);
        if (checkbox) checkbox.checked = true;
      });
    }

    renderDisplay(ruleExpression = {}) {
      const sections = [];
      if (Array.isArray(ruleExpression.global_privileges) && ruleExpression.global_privileges.length > 0) {
        sections.push({
          title: "全局权限",
          icon: "fas fa-globe",
          color: "primary",
          items: ruleExpression.global_privileges,
        });
      }
      if (Array.isArray(ruleExpression.database_privileges) && ruleExpression.database_privileges.length > 0) {
        sections.push({
          title: "数据库权限",
          icon: "fas fa-database",
          color: "success",
          items: ruleExpression.database_privileges,
        });
      }
      return renderDisplaySections(sections);
    }

    hasSelection(selected) {
      return (
        Array.isArray(selected.global_privileges) && selected.global_privileges.length > 0 ||
        Array.isArray(selected.database_privileges) && selected.database_privileges.length > 0
      );
    }
  }

  /**
   * SQL Server 权限策略。
   */
  class SQLServerPermissionStrategy extends PermissionStrategy {
    constructor() {
      super("sqlserver");
    }

    renderSelector(permissions = {}, prefix = "") {
      const serverRoles = Array.isArray(permissions.server_roles) ? permissions.server_roles : [];
      const databaseRoles = Array.isArray(permissions.database_roles) ? permissions.database_roles : [];
      const serverPermissions = Array.isArray(permissions.server_permissions) ? permissions.server_permissions : [];
      const databasePermissions = Array.isArray(permissions.database_privileges) ? permissions.database_privileges : [];

      /**
       * 渲染 SQL Server 权限复选组。
       */
      /**
       * 渲染 SQL Server 权限复选组。
       *
       * @param {Array<Object>} items 权限条目集合。
       * @param {string} idPrefix DOM id 前缀。
       * @param {string} icon FontAwesome 类名。
       * @param {string} color Bootstrap 颜色。
       * @param {string} fallback 当集合为空时展示的提示。
       * @returns {string} HTML 字符串。
       */
      /**
       * 渲染 SQL Server 权限复选组。
       *
       * @param {Array<Object>} items 权限项。
       * @param {string} idPrefix DOM id 前缀。
       * @param {string} icon 图标类。
       * @param {string} color Bootstrap 颜色。
       * @param {string} fallback 空态提示。
       * @returns {string} HTML 片段。
       */
      return `
        <div class="row">
          <div class="col-6">
            <h6 class="text-info mb-3"><i class="fas fa-users me-2"></i>服务器角色</h6>
            <div class="permission-section">
              ${renderPermissionGroup(prefix, serverRoles, "server_role", "fas fa-users", "info", "服务器角色")}
            </div>
          </div>
          <div class="col-6">
            <h6 class="text-warning mb-3"><i class="fas fa-user-shield me-2"></i>服务器权限</h6>
            <div class="permission-section">
              ${renderPermissionGroup(prefix, serverPermissions, "server_perm", "fas fa-user-shield", "warning", "服务器权限")}
            </div>
          </div>
          <div class="col-6">
            <h6 class="text-success mb-3"><i class="fas fa-database me-2"></i>数据库角色</h6>
            <div class="permission-section">
              ${renderPermissionGroup(prefix, databaseRoles, "db_role", "fas fa-database", "success", "数据库角色")}
            </div>
          </div>
          <div class="col-6">
            <h6 class="text-primary mb-3"><i class="fas fa-key me-2"></i>数据库权限</h6>
            <div class="permission-section">
              ${renderPermissionGroup(prefix, databasePermissions, "db_perm", "fas fa-key", "primary", "数据库权限")}
            </div>
          </div>
        </div>
      `;
    }

    collectSelected(container, prefix = "") {
      const checkboxes = container.querySelectorAll('input[type="checkbox"]:checked');
      const server_roles = [];
      const server_permissions = [];
      const database_roles = [];
      const database_privileges = [];

      checkboxes.forEach((checkbox) => {
        if (checkbox.id.startsWith(`${prefix}server_role_`)) {
          server_roles.push(checkbox.value);
        } else if (checkbox.id.startsWith(`${prefix}server_perm_`)) {
          server_permissions.push(checkbox.value);
        } else if (checkbox.id.startsWith(`${prefix}db_role_`)) {
          database_roles.push(checkbox.value);
        } else if (checkbox.id.startsWith(`${prefix}db_perm_`)) {
          database_privileges.push(checkbox.value);
        }
      });

      return {
        server_roles,
        server_permissions,
        database_roles,
        database_privileges,
      };
    }

    buildExpression(selected, operator) {
      return {
        type: "sqlserver_permissions",
        server_roles: selected.server_roles || [],
        server_permissions: selected.server_permissions || [],
        database_roles: selected.database_roles || [],
        database_privileges: selected.database_privileges || [],
        operator: operator || "OR",
      };
    }

    setSelected(ruleExpression, container, prefix = "") {
      (ruleExpression.server_roles || []).forEach((item) => {
        const checkbox = container.querySelector(`#${prefix}server_role_${item}`);
        if (checkbox) checkbox.checked = true;
      });
      (ruleExpression.server_permissions || []).forEach((item) => {
        const checkbox = container.querySelector(`#${prefix}server_perm_${item}`);
        if (checkbox) checkbox.checked = true;
      });
      (ruleExpression.database_roles || []).forEach((item) => {
        const checkbox = container.querySelector(`#${prefix}db_role_${item}`);
        if (checkbox) checkbox.checked = true;
      });
      (ruleExpression.database_privileges || []).forEach((item) => {
        const checkbox = container.querySelector(`#${prefix}db_perm_${item}`);
        if (checkbox) checkbox.checked = true;
      });
    }

    renderDisplay(ruleExpression = {}) {
      const sections = [];
      pushBadgeSection(sections, "服务器角色", "fas fa-users", "info", ruleExpression.server_roles);
      pushBadgeSection(sections, "服务器权限", "fas fa-user-shield", "warning", ruleExpression.server_permissions);
      pushBadgeSection(sections, "数据库角色", "fas fa-database", "success", ruleExpression.database_roles);
      pushBadgeSection(sections, "数据库权限", "fas fa-key", "primary", ruleExpression.database_privileges);
      return renderDisplaySections(sections);
    }

    hasSelection(selected) {
      return (
        (selected.server_roles && selected.server_roles.length > 0) ||
        (selected.server_permissions && selected.server_permissions.length > 0) ||
        (selected.database_roles && selected.database_roles.length > 0) ||
        (selected.database_privileges && selected.database_privileges.length > 0)
      );
    }
  }

  /**
   * PostgreSQL 权限策略，负责渲染/收集 PG 权限配置。
   */
  class PostgreSQLPermissionStrategy extends PermissionStrategy {
    constructor() {
      super("postgresql");
    }

    renderSelector(permissions = {}, prefix = "") {
      const predefinedRoles = Array.isArray(permissions.predefined_roles) ? permissions.predefined_roles : [];
      const roleAttributes = Array.isArray(permissions.role_attributes) ? permissions.role_attributes : [];
      const databasePrivileges = Array.isArray(permissions.database_privileges) ? permissions.database_privileges : [];
      const tablespacePrivileges = Array.isArray(permissions.tablespace_privileges) ? permissions.tablespace_privileges : [];

      /**
       * 渲染 PostgreSQL 权限复选组。
       *
       * @param {Array<Object>} items 权限条目集合。
       * @param {string} idPrefix DOM id 前缀。
       * @param {string} icon FontAwesome 图标类。
       * @param {string} color Bootstrap 颜色名。
       * @param {string} fallback 空态文案。
       * @returns {string} HTML 片段。
       */
      return `
        <div class="row">
          <div class="col-6">
            <h6 class="text-primary mb-3"><i class="fas fa-user-tag me-2"></i>预定义角色</h6>
            <div class="permission-section">
              ${renderPermissionGroup(prefix, predefinedRoles, "predefined_role", "fas fa-user-tag", "primary", "预定义角色")}
            </div>
          </div>
          <div class="col-6">
            <h6 class="text-success mb-3"><i class="fas fa-user-check me-2"></i>角色属性</h6>
            <div class="permission-section">
              ${renderPermissionGroup(prefix, roleAttributes, "role_attr", "fas fa-user-check", "success", "角色属性")}
            </div>
          </div>
          <div class="col-6">
            <h6 class="text-warning mb-3"><i class="fas fa-database me-2"></i>数据库权限</h6>
            <div class="permission-section">
              ${renderPermissionGroup(prefix, databasePrivileges, "db_perm", "fas fa-database", "warning", "数据库权限")}
            </div>
          </div>
          <div class="col-6">
            <h6 class="text-info mb-3"><i class="fas fa-layer-group me-2"></i>表空间权限</h6>
            <div class="permission-section">
              ${renderPermissionGroup(prefix, tablespacePrivileges, "tablespace_perm", "fas fa-layer-group", "info", "表空间权限")}
            </div>
          </div>
        </div>
      `;
    }

    collectSelected(container, prefix = "") {
      const checkboxes = container.querySelectorAll('input[type="checkbox"]:checked');
      const predefined_roles = [];
      const role_attributes = [];
      const database_privileges = [];
      const tablespace_privileges = [];

      checkboxes.forEach((checkbox) => {
        if (checkbox.id.startsWith(`${prefix}predefined_role_`)) {
          predefined_roles.push(checkbox.value);
        } else if (checkbox.id.startsWith(`${prefix}role_attr_`)) {
          role_attributes.push(checkbox.value);
        } else if (checkbox.id.startsWith(`${prefix}db_perm_`)) {
          database_privileges.push(checkbox.value);
        } else if (checkbox.id.startsWith(`${prefix}tablespace_perm_`)) {
          tablespace_privileges.push(checkbox.value);
        }
      });

      return {
        predefined_roles,
        role_attributes,
        database_privileges,
        tablespace_privileges,
      };
    }

    buildExpression(selected, operator) {
      return {
        type: "postgresql_permissions",
        predefined_roles: selected.predefined_roles || [],
        role_attributes: selected.role_attributes || [],
        database_privileges: selected.database_privileges || [],
        tablespace_privileges: selected.tablespace_privileges || [],
        operator: operator || "OR",
      };
    }

    setSelected(ruleExpression, container, prefix = "") {
      (ruleExpression.predefined_roles || []).forEach((item) => {
        const checkbox = container.querySelector(`#${prefix}predefined_role_${item}`);
        if (checkbox) checkbox.checked = true;
      });
      (ruleExpression.role_attributes || []).forEach((item) => {
        const checkbox = container.querySelector(`#${prefix}role_attr_${item}`);
        if (checkbox) checkbox.checked = true;
      });
      (ruleExpression.database_privileges || []).forEach((item) => {
        const checkbox = container.querySelector(`#${prefix}db_perm_${item}`);
        if (checkbox) checkbox.checked = true;
      });
      (ruleExpression.tablespace_privileges || []).forEach((item) => {
        const checkbox = container.querySelector(`#${prefix}tablespace_perm_${item}`);
        if (checkbox) checkbox.checked = true;
      });
    }

    renderDisplay(ruleExpression = {}) {
      const sections = [];
      pushBadgeSection(sections, "预定义角色", "fas fa-user-tag", "primary", ruleExpression.predefined_roles);
      pushBadgeSection(sections, "角色属性", "fas fa-user-check", "success", ruleExpression.role_attributes);
      pushBadgeSection(sections, "数据库权限", "fas fa-database", "warning", ruleExpression.database_privileges);
      pushBadgeSection(sections, "表空间权限", "fas fa-layer-group", "info", ruleExpression.tablespace_privileges);
      return renderDisplaySections(sections);
    }

    hasSelection(selected) {
      return (
        (selected.predefined_roles && selected.predefined_roles.length > 0) ||
        (selected.role_attributes && selected.role_attributes.length > 0) ||
        (selected.database_privileges && selected.database_privileges.length > 0) ||
        (selected.tablespace_privileges && selected.tablespace_privileges.length > 0)
      );
    }
  }

  /**
   * Oracle 权限策略，封装角色/系统权限等表单渲染。
   */
  class OraclePermissionStrategy extends PermissionStrategy {
    constructor() {
      super("oracle");
    }

    renderSelector(permissions = {}, prefix = "") {
      const roles = Array.isArray(permissions.roles) ? permissions.roles : [];
      const systemPermissions = Array.isArray(permissions.system_privileges) ? permissions.system_privileges : [];
      const tablespacePermissions = Array.isArray(permissions.tablespace_privileges) ? permissions.tablespace_privileges : [];
      const tablespaceQuotas = Array.isArray(permissions.tablespace_quotas) ? permissions.tablespace_quotas : [];

      return `
        <div class="row">
          <div class="col-6">
            <h6 class="text-primary mb-3"><i class="fas fa-user-shield me-2"></i>角色</h6>
            <div class="permission-section">
              ${renderPermissionGroup(prefix, roles, "role", "fas fa-user-shield", "primary", "角色")}
            </div>
          </div>
          <div class="col-6">
            <h6 class="text-success mb-3"><i class="fas fa-cogs me-2"></i>系统权限</h6>
            <div class="permission-section">
              ${renderPermissionGroup(prefix, systemPermissions, "sys_perm", "fas fa-cogs", "success", "系统权限")}
            </div>
          </div>
          <div class="col-6">
            <h6 class="text-warning mb-3"><i class="fas fa-layer-group me-2"></i>表空间权限</h6>
            <div class="permission-section">
              ${renderPermissionGroup(prefix, tablespacePermissions, "tablespace_perm", "fas fa-layer-group", "warning", "表空间权限")}
            </div>
          </div>
          <div class="col-6">
            <h6 class="text-info mb-3"><i class="fas fa-balance-scale me-2"></i>表空间配额</h6>
            <div class="permission-section">
              ${renderPermissionGroup(prefix, tablespaceQuotas, "tablespace_quota", "fas fa-balance-scale", "info", "表空间配额")}
            </div>
          </div>
        </div>
      `;
    }

    collectSelected(container, prefix = "") {
      const checkboxes = container.querySelectorAll('input[type="checkbox"]:checked');
      const roles = [];
      const system_privileges = [];
      const tablespace_privileges = [];
      const tablespace_quotas = [];

      checkboxes.forEach((checkbox) => {
        if (checkbox.id.startsWith(`${prefix}role_`)) {
          roles.push(checkbox.value);
        } else if (checkbox.id.startsWith(`${prefix}sys_perm_`)) {
          system_privileges.push(checkbox.value);
        } else if (checkbox.id.startsWith(`${prefix}tablespace_perm_`)) {
          tablespace_privileges.push(checkbox.value);
        } else if (checkbox.id.startsWith(`${prefix}tablespace_quota_`)) {
          tablespace_quotas.push(checkbox.value);
        }
      });

      return {
        roles,
        system_privileges,
        tablespace_privileges,
        tablespace_quotas,
      };
    }

    buildExpression(selected, operator) {
      return {
        type: "oracle_permissions",
        roles: selected.roles || [],
        system_privileges: selected.system_privileges || [],
        tablespace_privileges: selected.tablespace_privileges || [],
        tablespace_quotas: selected.tablespace_quotas || [],
        operator: operator || "OR",
      };
    }

    setSelected(ruleExpression, container, prefix = "") {
      (ruleExpression.roles || []).forEach((item) => {
        const checkbox = container.querySelector(`#${prefix}role_${item}`);
        if (checkbox) checkbox.checked = true;
      });
      (ruleExpression.system_privileges || []).forEach((item) => {
        const checkbox = container.querySelector(`#${prefix}sys_perm_${item}`);
        if (checkbox) checkbox.checked = true;
      });
      (ruleExpression.tablespace_privileges || []).forEach((item) => {
        const checkbox = container.querySelector(`#${prefix}tablespace_perm_${item}`);
        if (checkbox) checkbox.checked = true;
      });
      (ruleExpression.tablespace_quotas || []).forEach((item) => {
        const checkbox = container.querySelector(`#${prefix}tablespace_quota_${item}`);
        if (checkbox) checkbox.checked = true;
      });
    }

    renderDisplay(ruleExpression = {}) {
      const sections = [];
      pushBadgeSection(sections, "角色", "fas fa-user-shield", "primary", ruleExpression.roles);
      pushBadgeSection(sections, "系统权限", "fas fa-cogs", "success", ruleExpression.system_privileges);
      pushBadgeSection(sections, "表空间权限", "fas fa-layer-group", "warning", ruleExpression.tablespace_privileges);
      pushBadgeSection(sections, "表空间配额", "fas fa-balance-scale", "info", ruleExpression.tablespace_quotas);
      return renderDisplaySections(sections);
    }

    hasSelection(selected) {
      return (
        (selected.roles && selected.roles.length > 0) ||
        (selected.system_privileges && selected.system_privileges.length > 0) ||
        (selected.tablespace_privileges && selected.tablespace_privileges.length > 0) ||
        (selected.tablespace_quotas && selected.tablespace_quotas.length > 0)
      );
    }
  }

  /**
   * 将徽章区块推入数组。
   *
   * @param {Array} sections - 区块数组
   * @param {string} title - 标题
   * @param {string} icon - 图标类名
   * @param {string} color - 颜色类名
   * @param {Array} items - 项目数组
   * @return {void}
   */
  function pushBadgeSection(sections, title, icon, color, items) {
    if (Array.isArray(items) && items.length > 0) {
      sections.push({ title, icon, color, items });
    }
  }

  /**
   * 渲染显示区块。
   *
   * @param {Array} sections - 区块数组
   * @return {string} 渲染的 HTML 字符串
   */
  function renderDisplaySections(sections) {
    if (!Array.isArray(sections) || sections.length === 0) {
      return '<div class="rule-detail-empty">无权限配置</div>';
    }
    const blocks = sections
      .map(
        (section) => `
        <div class="rule-permission-block">
            <div class="rule-permission-block__header">
                <span class="chip-outline chip-outline--brand">
                    <i class="${section.icon} me-2"></i>${section.title}
                </span>
            </div>
            <div class="ledger-chip-stack">
                ${section.items
                  .map((item) => `<span class="ledger-chip">${item}</span>`)
                  .join("")}
            </div>
        </div>
    `
      )
      .join("");
    return `<div class="rule-permission-stack">${blocks}</div>`;
  }

  /**
   * 根据数据库类型获取对应的策略实例。
   *
   * @param {string} dbType - 数据库类型
   * @return {PermissionStrategy} 策略实例
   */
  function getStrategy(dbType) {
    switch (dbType) {
      case "mysql":
        return new MySQLPermissionStrategy();
      case "sqlserver":
        return new SQLServerPermissionStrategy();
      case "postgresql":
        return new PostgreSQLPermissionStrategy();
      case "oracle":
        return new OraclePermissionStrategy();
      default:
        return new PermissionStrategy(dbType);
    }
  }

  /**
   * 权限策略中心，负责加载和管理权限配置。
   *
   * @class
   */
  class PermissionPolicyCenter {
    /**
     * 加载权限配置。
     *
     * @param {string} dbType - 数据库类型
     * @param {string} containerId - 容器元素 ID
     * @param {string} [prefix=""] - ID 前缀
     * @return {Promise<void>}
     */
    static async load(dbType, containerId, prefix = "") {
      const container = document.getElementById(containerId);
      if (!container) {
        console.error(`PermissionPolicyCenter: 找不到容器元素 ${containerId}`);
        return Promise.resolve();
      }

      if (!dbType) {
        container.innerHTML = `
          <div class="text-center text-muted py-3">
            <i class="fas fa-info-circle me-2"></i>请先选择数据库类型
          </div>
        `;
        return Promise.resolve();
      }

      container.innerHTML = `
        <div class="text-center text-muted py-3">
          <i class="fas fa-spinner fa-spin me-2"></i>加载中...
        </div>
      `;

      try {
        const response = await accountClassificationService.fetchPermissions(dbType);
        if (response && response.success === false) {
          throw new Error(response.error || "加载权限配置失败");
        }
        const permissions = response?.data?.permissions ?? response.permissions ?? {};
        const strategy = getStrategy(dbType);
        container.innerHTML = strategy.renderSelector(permissions, prefix);
      } catch (error) {
        console.error("加载权限配置失败:", error);
        container.innerHTML = `
          <div class="alert alert-danger">
            <i class="fas fa-exclamation-triangle me-2"></i>
            加载权限配置失败：${error.message || "未知错误"}
          </div>
        `;
        throw error;
      }
    }

    /**
     * 收集选中的权限。
     *
     * @param {string} dbType - 数据库类型
     * @param {string} containerId - 容器元素 ID
     * @param {string} [prefix=""] - ID 前缀
     * @return {Object} 选中的权限对象
     */
    static collectSelected(dbType, containerId, prefix = "") {
      const container = document.getElementById(containerId);
      if (!container) {
        console.error(`PermissionPolicyCenter: collectSelected 时找不到容器 ${containerId}`);
        return {};
      }
      return getStrategy(dbType).collectSelected(container, prefix);
    }

    /**
     * 检查是否有选中的权限。
     *
     * @param {Object|Array} selected - 选中的权限对象或数组
     * @return {boolean} 如果有选中的权限返回 true
     */
    static hasSelection(selected) {
      if (!selected) return false;
      if (Array.isArray(selected)) {
        return selected.length > 0;
      }
      return Object.values(selected).some((value) => {
        if (Array.isArray(value)) {
          return value.length > 0;
        }
        if (value && typeof value === "object") {
          return PermissionPolicyCenter.hasSelection(value);
        }
        return Boolean(value);
      });
    }

    /**
     * 构建权限表达式。
     *
     * @param {string} dbType - 数据库类型
     * @param {Object} selectedPermissions - 选中的权限对象
     * @param {string} operator - 逻辑运算符
     * @return {Object} 权限表达式对象
     */
    static buildExpression(dbType, selectedPermissions, operator) {
      return getStrategy(dbType).buildExpression(selectedPermissions, operator);
    }

    /**
     * 设置选中的权限。
     *
     * @param {string} dbType - 数据库类型
     * @param {Object} ruleExpression - 规则表达式对象
     * @param {string} containerId - 容器元素 ID
     * @param {string} [prefix=""] - ID 前缀
     * @return {void}
     */
    static setSelected(dbType, ruleExpression, containerId, prefix = "") {
      const container = document.getElementById(containerId);
      if (!container) {
        console.error(`PermissionPolicyCenter: setSelected 时找不到容器 ${containerId}`);
        return;
      }
      getStrategy(dbType).setSelected(ruleExpression || {}, container, prefix);
    }

    /**
     * 渲染权限显示。
     *
     * @param {string} dbType - 数据库类型
     * @param {Object} ruleExpression - 规则表达式对象
     * @return {string} 渲染的 HTML 字符串
     */
    static renderDisplay(dbType, ruleExpression) {
      return getStrategy(dbType).renderDisplay(ruleExpression || {});
    }
  }

  window.PermissionPolicyCenter = PermissionPolicyCenter;
})(window, document);


// View helper: AccountClassificationPermissionView (wrapped into permission-policy-center.js)
(function (global) {
  "use strict";

  /**
   * 创建权限视图。
   *
   * @param {Object} options - 配置选项
   * @param {Object} options.PermissionPolicyCenter - 权限策略中心实例
   * @param {Object} options.toast - Toast 通知实例
   * @param {Function} options.handleRequestError - 错误处理函数
   * @return {Object} 视图对象
   */
    function createView(options) {
      const {
        PermissionPolicyCenter = global.PermissionPolicyCenter,
        handleRequestError,
      } = options || {};

    if (!PermissionPolicyCenter) {
      throw new Error("policy-center-view: PermissionPolicyCenter 未加载");
    }

    /**
     * 根据前缀加载权限配置。
     *
     * @param {string} [prefix=""] - ID 前缀
     * @return {Promise<void>}
     */
    function loadByPrefix(prefix = "") {
      const elementId = prefix ? `${prefix}RuleDbType` : "ruleDbType";
      const dbTypeElement = document.getElementById(elementId);
      if (!dbTypeElement) {
        console.error("找不到数据库类型选择元素:", elementId);
        return Promise.resolve();
      }

      const dbType = dbTypeElement.value;
      const containerId = prefix ? `${prefix}PermissionsConfig` : "permissionsConfig";

      return PermissionPolicyCenter.load(dbType, containerId, prefix).catch(error => {
        handleRequestError?.(error, "加载权限配置失败", "load_permissions");
      });
    }

    return {
      loadByPrefix,
      load: PermissionPolicyCenter.load?.bind(PermissionPolicyCenter),
      reset: PermissionPolicyCenter.reset?.bind(PermissionPolicyCenter),
      collectSelected: PermissionPolicyCenter.collectSelected?.bind(PermissionPolicyCenter),
      hasSelection: PermissionPolicyCenter.hasSelection?.bind(PermissionPolicyCenter),
      buildExpression: PermissionPolicyCenter.buildExpression?.bind(PermissionPolicyCenter),
      renderDisplay: PermissionPolicyCenter.renderDisplay?.bind(PermissionPolicyCenter),
      setSelected: PermissionPolicyCenter.setSelected?.bind(PermissionPolicyCenter),
    };
  }

  global.AccountClassificationPermissionView = {
    createView,
  };
})(window);
