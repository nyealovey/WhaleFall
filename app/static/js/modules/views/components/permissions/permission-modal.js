(function (global, document) {
  'use strict';

  function showPermissionsModal(permissions, account) {
    try {
      const modal = ensurePermissionModal();
      const renderer = ensurePermissionRenderer();
      renderer.render({ permissions, account });
      modal.open();
    } catch (error) {
      console.error('展示权限详情失败:', error);
      notify('获取权限信息失败，请稍后重试', 'error');
    }
  }

  function ensurePermissionModal() {
    if (global.PermissionModalInstance) {
      return global.PermissionModalInstance;
    }
    const factory = global.UI?.createModal;
    if (!factory) {
      throw new Error('UI.createModal 未加载，无法创建权限模态');
    }
    global.PermissionModalInstance = factory({
      modalSelector: '#permissionsModal',
      onClose: resetPermissionModal,
    });
    return global.PermissionModalInstance;
  }

  function ensurePermissionRenderer() {
    if (global.PermissionModalRenderer) {
      return global.PermissionModalRenderer;
    }
    const container = document.querySelector('#permissionsModalBody');
    const template = document.querySelector('#permission-detail-template');
    if (!container || !template) {
      throw new Error('权限模态模板缺失');
    }

    function render(payload) {
      const { permissions = {}, account = {} } = payload || {};
      const fragment = template.content.cloneNode(true);
      const root = fragment.querySelector('[data-permission-root]');
      if (!root) {
        throw new Error('权限模态模板缺少根节点');
      }
      fillHeader(root, account);
      fillSummary(root, account);
      fillGlobalPrivileges(root, permissions);
      fillDatabasePrivileges(root, permissions);
      fillHistory(root, permissions);
      fillJson(root, permissions);
      container.innerHTML = '';
      container.appendChild(fragment);
      bindActions(container, permissions);
    }

    global.PermissionModalRenderer = { render };
    return global.PermissionModalRenderer;
  }

  function fillHeader(root, account) {
    const title = root.querySelector('[data-field="title"]');
    const subtitle = root.querySelector('[data-field="subtitle"]');
    const pill = root.querySelector('[data-field="status-pill"]');
    const meta = resolveStatusMeta(account);
    if (title) {
      title.textContent = account?.username ? `账户权限 - ${account.username}` : '账户权限详情';
    }
    if (subtitle) {
      const instanceName = account?.instance_name || account?.instance_id || '未知实例';
      subtitle.textContent = `${instanceName} · ${account?.db_type || '未知类型'}`;
    }
    if (pill) {
      pill.className = `status-pill status-pill--${meta.variant}`;
      pill.innerHTML = `${meta.icon ? `<i class="${meta.icon}"></i>` : ''}${meta.text}`;
    }
  }

  function fillSummary(root, account = {}) {
    setText(root, 'account-username', account?.username || '-');
    setText(root, 'account-instance', account?.instance_name || account?.instance_id || '-');
    setText(root, 'account-dbtype', account?.db_type || '-');
    setText(root, 'account-role', account?.role || account?.source || '-');
  }

  function fillGlobalPrivileges(root, permissions = {}) {
    const chipStack = root.querySelector('[data-field="global-privileges"]');
    const empty = root.querySelector('[data-field="global-empty"]');
    const privileges = extractGlobalPrivileges(permissions);
    if (!chipStack || !empty) {
      return;
    }
    if (!privileges.length) {
      chipStack.innerHTML = '';
      empty.classList.remove('d-none');
      return;
    }
    empty.classList.add('d-none');
    chipStack.innerHTML = privileges
      .map((priv) => `<span class="chip-outline chip-outline--brand"><i class="fas fa-shield-alt"></i>${escapeHtml(priv)}</span>`)
      .join('');
  }

  function fillDatabasePrivileges(root, permissions = {}) {
    const wrapper = root.querySelector('[data-field="database-table-wrapper"]');
    const tbody = root.querySelector('[data-field="database-permissions"]');
    const empty = root.querySelector('[data-field="database-empty"]');
    if (!wrapper || !tbody || !empty) {
      return;
    }
    const entries = Object.entries(permissions?.database_privileges || {});
    if (!entries.length) {
      wrapper.classList.add('d-none');
      empty.classList.remove('d-none');
      return;
    }
    wrapper.classList.remove('d-none');
    empty.classList.add('d-none');
    tbody.innerHTML = entries
      .map(([dbName, privList]) => {
        const privileges = Array.isArray(privList)
          ? privList
          : typeof privList === 'string'
            ? privList.split(',')
            : [];
        const chips = privileges
          .filter(Boolean)
          .map((priv) => `<span class="chip-outline chip-outline--muted">${escapeHtml(priv.trim())}</span>`)
          .join('');
        return `<tr><td>${escapeHtml(dbName)}</td><td>${chips || '<span class="text-muted">-</span>'}</td></tr>`;
      })
      .join('');
  }

  function fillHistory(root, permissions = {}) {
    const container = root.querySelector('[data-field="history-list"]');
    const empty = root.querySelector('[data-field="history-empty"]');
    if (!container || !empty) {
      return;
    }
    const history = Array.isArray(permissions?.history) ? permissions.history : [];
    if (!history.length) {
      container.innerHTML = '';
      empty.classList.remove('d-none');
      return;
    }
    empty.classList.add('d-none');
    container.innerHTML = history
      .map((item) => {
        const statusMeta = resolveHistoryMeta(item?.change_type);
        return `
          <div class="permission-history__item">
            <div class="permission-history__meta">
              <span>${escapeHtml(formatTime(item?.changed_at))}</span>
              <span>${escapeHtml(item?.changed_by || '系统')}</span>
              <span class="status-pill status-pill--${statusMeta.variant}">${statusMeta.icon ? `<i class="${statusMeta.icon}"></i>` : ''}${statusMeta.text}</span>
            </div>
            <div class="permission-history__desc">${escapeHtml(item?.summary || item?.description || '无描述')}</div>
          </div>`;
      })
      .join('');
  }

  function fillJson(root, permissions = {}) {
    const block = root.querySelector('[data-field="json-block"]');
    if (!block) {
      return;
    }
    block.textContent = safeStringify(permissions);
  }

  function bindActions(container, permissions) {
    const copyBtn = container.querySelector('[data-action="copy-json"]');
    if (copyBtn) {
      copyBtn.addEventListener('click', () => {
        copyText(safeStringify(permissions));
      });
    }
  }

  function resetPermissionModal() {
    const body = document.querySelector('#permissionsModalBody');
    if (body) {
      body.innerHTML = `
        <div class="permission-modal__placeholder text-center text-muted py-4">
            <div class="spinner-border text-primary" role="status">
                <span class="visually-hidden">加载中...</span>
            </div>
            <p class="mt-2">正在加载权限信息...</p>
        </div>`;
    }
  }

  function extractGlobalPrivileges(permissions = {}) {
    if (Array.isArray(permissions?.global_privileges)) {
      return permissions.global_privileges
        .flatMap((value) => (typeof value === 'string' ? value.split(',') : value))
        .map((text) => (typeof text === 'string' ? text.trim() : ''))
        .filter(Boolean);
    }
    return [];
  }

  function resolveStatusMeta(account = {}) {
    if (account?.status === 'locked') {
      return { text: '锁定', variant: 'warning', icon: 'fas fa-lock' };
    }
    if (account?.status === 'deleted') {
      return { text: '已删除', variant: 'muted', icon: 'fas fa-trash' };
    }
    return { text: '活跃', variant: 'success', icon: 'fas fa-check' };
  }

  function resolveHistoryMeta(type) {
    const map = {
      add: { text: '新增', variant: 'success', icon: 'fas fa-plus' },
      modify_privilege: { text: '权限变更', variant: 'info', icon: 'fas fa-exchange-alt' },
      delete: { text: '删除', variant: 'muted', icon: 'fas fa-trash' },
      error: { text: '失败', variant: 'danger', icon: 'fas fa-exclamation-circle' },
    };
    return map[type] || { text: '变更', variant: 'muted', icon: 'fas fa-history' };
  }

  function formatTime(value) {
    if (!value) {
      return '-';
    }
    if (global.timeUtils?.formatTime) {
      try {
        return global.timeUtils.formatTime(value, 'datetime');
      } catch (error) {
        return String(value);
      }
    }
    try {
      return new Date(value).toLocaleString();
    } catch (error) {
      return String(value);
    }
  }

  function safeStringify(data) {
    try {
      return JSON.stringify(data ?? {}, null, 2);
    } catch (error) {
      return String(data ?? '');
    }
  }

  function copyText(text) {
    if (!text) {
      notify('暂无可复制内容', 'warn');
      return;
    }
    if (navigator.clipboard?.writeText) {
      navigator.clipboard.writeText(text).then(
        () => notify('JSON 已复制', 'success'),
        () => fallbackCopy(text),
      );
      return;
    }
    fallbackCopy(text);
  }

  function fallbackCopy(text) {
    try {
      const textarea = document.createElement('textarea');
      textarea.value = text;
      textarea.style.position = 'fixed';
      textarea.style.opacity = '0';
      document.body.appendChild(textarea);
      textarea.select();
      document.execCommand('copy');
      document.body.removeChild(textarea);
      notify('JSON 已复制', 'success');
    } catch (error) {
      notify('复制失败，请手动选择文本', 'error');
    }
  }

  function setText(root, field, value) {
    const node = root.querySelector(`[data-field="${field}"]`);
    if (node) {
      node.textContent = value ?? '-';
    }
  }

  function escapeHtml(value) {
    if (value === null || value === undefined) {
      return '';
    }
    return String(value)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
  }

  function notify(message, tone) {
    if (!message) {
      return;
    }
    if (global.toast) {
      if (tone === 'success' && global.toast.success) {
        global.toast.success(message);
        return;
      }
      if (tone === 'error' && global.toast.error) {
        global.toast.error(message);
        return;
      }
      if (global.toast.info) {
        global.toast.info(message);
        return;
      }
    }
    if (tone === 'error') {
      console.error(message);
    } else {
      console.info(message);
    }
  }

  global.showPermissionsModal = showPermissionsModal;
})(window, document);
