/**
 * 账户分类规则表单
 */
(function (window) {
  'use strict';

  const helpers = window.DOMHelpers;
  if (!helpers) {
    console.error('DOMHelpers 未初始化，无法加载账户分类规则表单脚本');
    return;
  }

  const { ready, selectOne } = helpers;

  ready(() => {
    const formWrapper = selectOne('#ruleForm');
    if (!formWrapper.length) {
      return;
    }

    const root = selectOne('#rule-form-root');
    const mode = root.length ? root.data('formMode') || root.attr('data-form-mode') || 'create' : 'create';

    if (window.ResourceFormController) {
      new window.ResourceFormController(formWrapper.first(), {
        loadingText: mode === 'edit' ? '保存中...' : '创建中...',
      });
    }
  });
})(window);
