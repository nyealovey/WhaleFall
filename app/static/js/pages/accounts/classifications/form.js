/**
 * 账户分类表单
 */
(function (window, document) {
  'use strict';

  document.addEventListener('DOMContentLoaded', () => {
    const form = document.getElementById('classificationForm');
    if (!form) return;

    const root = document.getElementById('classification-form-root');
    const mode = root?.dataset.formMode || 'create';

    if (window.ResourceFormController) {
      new window.ResourceFormController(form, {
        loadingText: mode === 'edit' ? '保存中...' : '创建中...',
      });
    }

    const colorSelect = document.getElementById('color');
    const preview = document.getElementById('colorPreview');
    if (colorSelect && preview) {
      colorSelect.addEventListener('change', () => updatePreview(preview, colorSelect));
      updatePreview(preview, colorSelect);
    }
  });

  function updatePreview(container, select) {
    const option = select.options[select.selectedIndex];
    if (!option || !container) {
      container.style.display = 'none';
      return;
    }
    container.style.display = 'flex';
    container.querySelector('.color-preview-dot').style.backgroundColor = option.dataset.color || '#18bc9c';
    container.querySelector('.color-preview-text').textContent = option.text;
  }
})(window, document);
