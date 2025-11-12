(function (window, document) {
  'use strict';

  if (window.ResourceFormController) {
    return;
  }

  class ResourceFormController {
    constructor(formSelector, options = {}) {
      this.form =
        typeof formSelector === 'string'
          ? document.querySelector(formSelector)
          : formSelector;

      if (!this.form) {
        console.warn('ResourceFormController: form not found', formSelector);
        return;
      }

      this.options = Object.assign(
        {
          submitButtonSelector: '[data-resource-submit]',
          loadingText: '保存中...',
          toast: window.toast || null,
          beforeSubmit: null,
          afterSubmit: null,
        },
        options,
      );

      this.submitButtons = Array.from(
        this.form.querySelectorAll(this.options.submitButtonSelector),
      );

      this._bindEvents();
    }

    _bindEvents() {
      this.form.addEventListener('submit', (event) => {
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

  window.ResourceFormController = ResourceFormController;
})(window, document);
