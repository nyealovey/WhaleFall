/**
 * 账户分类表单
 */
(function (window) {
  'use strict';

  const helpers = window.DOMHelpers;
  if (!helpers) {
    console.error('DOMHelpers 未初始化，无法加载账户分类表单脚本');
    return;
  }

  const { ready, selectOne, from } = helpers;

  ready(() => {
    const formWrapper = selectOne('#classificationForm');
    if (!formWrapper.length) {
      return;
    }

    const root = selectOne('#classification-form-root');
    const mode = root.length ? root.data('formMode') || root.attr('data-form-mode') || 'create' : 'create';

    if (window.ResourceFormController) {
      new window.ResourceFormController(formWrapper.first(), {
        loadingText: mode === 'edit' ? '保存中...' : '创建中...',
      });
    }

    const colorSelect = selectOne('#color');
    const preview = selectOne('#colorPreview');
    if (colorSelect.length && preview.length) {
      colorSelect.on('change', () => updatePreview(preview.first(), colorSelect.first()));
      updatePreview(preview.first(), colorSelect.first());
    }
  });

  function updatePreview(container, select) {
    if (!container || !select) {
      return;
    }
    const selectedOption = select.options[select.selectedIndex];
    if (!selectedOption) {
      container.style.display = 'none';
      return;
    }
    container.style.display = 'flex';
    const dot = container.querySelector('.color-preview-dot');
    const text = container.querySelector('.color-preview-text');
    if (dot) {
      dot.style.backgroundColor = selectedOption.dataset.color || '#18bc9c';
    }
    if (text) {
      text.textContent = selectedOption.text;
    }
  }
})(window);
