(function (global) {
  'use strict';

  if (global.ResourceFormController) {
    return;
  }

  const helpers = global.DOMHelpers;
  if (!helpers) {
    console.error('DOMHelpers 未初始化，无法注册 ResourceFormController');
    return;
  }
  const { select, selectOne, from } = helpers;

  class ResourceFormController {
    constructor(formSelector, options = {}) {
      this.form =
        typeof formSelector === 'string'
          ? selectOne(formSelector).first()
          : formSelector;

      if (!this.form) {
        console.warn('ResourceFormController: form not found', formSelector);
        return;
      }

      this.options = Object.assign(
        {
          submitButtonSelector: '[data-resource-submit]',
          loadingText: '保存中...',
          toast: global.toast || null,
          beforeSubmit: null,
          afterSubmit: null,
        },
        options,
      );

      this.submitButtons = select(
        this.options.submitButtonSelector,
        this.form,
      ).nodes;

      this._bindEvents();
    }

    _bindEvents() {
      from(this.form).on('submit', (event) => {
        if (typeof this.options.beforeSubmit === 'function') {
          const shouldContinue = this.options.beforeSubmit(event, this);
          if (shouldContinue === false) {
            event.preventDefault();
            return;
          }
        }

        this.toggleLoading(true);

        if (typeof this.options.afterSubmit === 'function') {
          Promise.resolve(this.options.afterSubmit(event, this)).finally(() => {
            this.toggleLoading(false);
          });
        }
      });
    }

    toggleLoading(isLoading) {
      this.submitButtons.forEach((button) => {
        if (isLoading) {
          button.dataset.originalText = button.innerHTML;
          button.innerHTML = `<span class="spinner-border spinner-border-sm me-2"></span>${this.options.loadingText}`;
          button.disabled = true;
        } else {
          if (button.dataset.originalText) {
            button.innerHTML = button.dataset.originalText;
            delete button.dataset.originalText;
          }
          button.disabled = false;
        }
      });
    }
  }

  global.ResourceFormController = ResourceFormController;
})(window);
