(function (global, document) {
  'use strict';

  const REFRESH_SELECTOR = '[data-action="refresh-stats"]';
  const API_ENDPOINT = '/accounts/api/statistics';

  document.addEventListener('DOMContentLoaded', () => {
    const refreshButton = document.querySelector(REFRESH_SELECTOR);
    if (refreshButton) {
      refreshButton.addEventListener('click', handleRefreshClick);
    }
  });

  function handleRefreshClick(event) {
    event.preventDefault();
    const button = event.currentTarget;
    toggleLoading(button, true);
    fetch(API_ENDPOINT, { headers: { Accept: 'application/json' } })
      .then(assertOk)
      .then((response) => response.json())
      .then((payload) => {
        const stats = payload?.data?.stats || payload?.stats || {};
        applyStats(stats);
        notify('统计数据已刷新', 'success');
      })
      .catch((error) => {
        console.error('刷新账户统计失败:', error);
        notify('刷新失败，请稍后再试', 'error');
      })
      .finally(() => toggleLoading(button, false));
  }

  function assertOk(response) {
    if (!response?.ok) {
      throw new Error(`请求失败: ${response?.status}`);
    }
    return response;
  }

  function applyStats(stats) {
    setValue('total_accounts', stats.total_accounts);
    setValue('active_accounts', stats.active_accounts);
    setValue('locked_accounts', stats.locked_accounts);
    setValue('total_instances', stats.total_instances);
    updateDbTypeTable(stats.db_type_stats, stats.total_accounts);
    updateClassificationTable(stats.classification_stats, stats.total_accounts);
  }

  function setValue(key, value) {
    const nodes = document.querySelectorAll(`[data-stat-value="${key}"]`);
    if (!nodes.length) {
      return;
    }
    const formatted = formatInteger(value);
    nodes.forEach((node) => {
      node.textContent = formatted;
    });
  }

  function updateDbTypeTable(dbTypeStats, totalAccounts) {
    if (!dbTypeStats) {
      return;
    }
    const normalizedTotal = Number(totalAccounts) || 0;
    Object.entries(dbTypeStats).forEach(([type, meta]) => {
      const key = String(type || '').toLowerCase();
      const row = document.querySelector(`[data-db-type-row="${key}"]`);
      if (!row) {
        return;
      }
      const totalCell = row.querySelector('[data-field="db-type-count"]');
      if (totalCell) {
        totalCell.textContent = formatInteger(meta?.total);
      }
      const percent = resolvePercent(meta?.total, normalizedTotal);
      const progress = row.querySelector('[data-field="db-type-progress"]');
      if (progress) {
        progress.style.width = `${percent}%`;
      }
      const percentLabel = row.querySelector('[data-field="db-type-percent"]');
      if (percentLabel) {
        percentLabel.textContent = `${percent.toFixed(1)}%`;
      }
      updateStatusPill(row, 'success', meta?.active);
      updateStatusPill(row, 'warning', meta?.locked);
      updateStatusPill(row, 'muted', meta?.deleted ?? 0);
    });
  }

  function updateClassificationTable(classStats, totalAccounts) {
    if (!classStats) {
      return;
    }
    const normalizedTotal = Number(totalAccounts) || 0;
    Object.entries(classStats).forEach(([classification, meta]) => {
      const key = String(classification || '').toLowerCase().replace(/\s+/g, '-');
      const row = document.querySelector(`[data-classification-row="${key}"]`);
      if (!row) {
        return;
      }
      const countNode = row.querySelector('[data-field="classification-count"]');
      if (countNode) {
        countNode.textContent = formatInteger(meta?.account_count);
      }
      const percent = resolvePercent(meta?.account_count, normalizedTotal);
      const progress = row.querySelector('[data-field="classification-progress"]');
      if (progress) {
        progress.style.width = `${percent}%`;
      }
      const percentLabel = row.querySelector('[data-field="classification-percent"]');
      if (percentLabel) {
        percentLabel.textContent = `${percent.toFixed(1)}%`;
      }
    });
  }

  function updateStatusPill(row, tone, value) {
    if (!row) {
      return;
    }
    const selector = `.status-pill--${tone}`;
    const node = row.querySelector(selector);
    if (node) {
      node.textContent = `${tone === 'success' ? '活跃' : tone === 'warning' ? '禁用' : '删除'} ${formatInteger(value)}`;
    }
  }

  function resolvePercent(count, total) {
    const numericCount = Number(count) || 0;
    if (!total || total <= 0) {
      return 0;
    }
    return Math.min(100, Math.max(0, (numericCount / total) * 100));
  }

  function toggleLoading(button, loading) {
    if (!button) {
      return;
    }
    if (loading) {
      button.dataset.originalContent = button.innerHTML;
      button.setAttribute('disabled', 'disabled');
      button.innerHTML = '<i class="fas fa-spinner fa-spin"></i>';
      return;
    }
    button.innerHTML = button.dataset.originalContent || '<i class="fas fa-sync-alt"></i>';
    button.removeAttribute('disabled');
  }

  function formatInteger(value) {
    if (value === null || value === undefined) {
      return '-';
    }
    if (global.NumberFormat?.formatInteger) {
      return global.NumberFormat.formatInteger(value, { fallback: value });
    }
    const numberValue = Number(value);
    if (Number.isNaN(numberValue)) {
      return String(value);
    }
    return numberValue.toLocaleString();
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
})(window, document);
