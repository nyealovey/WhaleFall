/**
 * 账户分类规则表单
 */
(function (window, document) {
  'use strict';

  document.addEventListener('DOMContentLoaded', () => {
    const form = document.getElementById('ruleForm');
    if (!form) {
      return;
    }

    const root = document.getElementById('rule-form-root');
    const mode = root?.dataset.formMode || 'create';

    if (window.ResourceFormController) {
      new window.ResourceFormController(form, {
        loadingText: mode === 'edit' ? '保存中...' : '创建中...',
      });
    }
  });
})(window, document);
