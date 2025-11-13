/**
 * 实例表单页面（新建 & 编辑）
 */
(function (window, document) {
  'use strict';

  let instanceFormValidator = null;
  let formController = null;

  document.addEventListener('DOMContentLoaded', () => {
    const form = document.getElementById('instanceForm');
    if (!form) {
      return;
    }

    const root = document.getElementById('instance-form-root');
    const mode = root?.dataset.formMode || 'create';

    if (window.ResourceFormController) {
      formController = new window.ResourceFormController(form, {
        loadingText: mode === 'edit' ? '保存中...' : '创建中...',
      });
    }

    initializeFormValidation();
    initializeDbTypeBehavior();
    initializeTagSelector();
    bindConnectionTestButton();
  });

  function initializeFormValidation() {
    if (!window.FormValidator || !window.ValidationRules) {
      console.warn('表单校验模块未加载');
      return;
    }

    instanceFormValidator = window.FormValidator.create('#instanceForm');
    if (!instanceFormValidator) {
      return;
    }

    instanceFormValidator
      .useRules('#name', window.ValidationRules.instance.name)
      .useRules('#db_type', window.ValidationRules.instance.dbType)
      .useRules('#host', window.ValidationRules.instance.host)
      .useRules('#port', window.ValidationRules.instance.port)
      .useRules('#credential_id', window.ValidationRules.instance.credential)
      .onSuccess((event) => {
        formController?.toggleLoading(true);
        event.target.submit();
      })
      .onFail(() => {
        window.toast.error('请检查实例表单填写');
      });

    const dbTypeSelect = document.getElementById('db_type');
    const nameInput = document.getElementById('name');
    const hostInput = document.getElementById('host');
    const portInput = document.getElementById('port');
    const credentialSelect = document.getElementById('credential_id');

    dbTypeSelect?.addEventListener('change', (event) => {
      handleDbTypeChange(event.currentTarget);
      instanceFormValidator.revalidateField('#db_type');
      instanceFormValidator.revalidateField('#port');
    });
    nameInput?.addEventListener('blur', () => instanceFormValidator.revalidateField('#name'));
    hostInput?.addEventListener('blur', () => instanceFormValidator.revalidateField('#host'));
    portInput?.addEventListener('input', () => instanceFormValidator.revalidateField('#port'));
    credentialSelect?.addEventListener('change', () =>
      instanceFormValidator.revalidateField('#credential_id'),
    );
  }

  function initializeDbTypeBehavior() {
    const select = document.getElementById('db_type');
    if (select) {
      handleDbTypeChange(select);
    }
  }

  function handleDbTypeChange(selectElement) {
    const select = selectElement || document.getElementById('db_type');
    if (!select) {
      return;
    }

    const portInput = document.getElementById('port');
    const databaseNameInput = document.getElementById('database_name');
    const selectedOption = select.options[select.selectedIndex];
    const dbType = select.value;

    if (selectedOption?.dataset.port && portInput && !portInput.value) {
      portInput.value = selectedOption.dataset.port;
    }

    if (databaseNameInput && !databaseNameInput.value) {
      const defaultNames = {
        mysql: 'mysql',
        postgresql: 'postgres',
        sqlserver: 'master',
        oracle: 'orcl',
      };
      if (defaultNames[dbType]) {
        databaseNameInput.value = defaultNames[dbType];
      }
    }
  }

  function initializeTagSelector() {
    if (!window.TagSelectorHelper) {
      console.warn('TagSelectorHelper 未加载，跳过标签选择器初始化');
      return;
    }

    const hiddenInput = document.getElementById('selected-tag-names');
    const initialValues = hiddenInput?.value
      ? hiddenInput.value.split(',').map((value) => value.trim()).filter(Boolean)
      : [];

    window.TagSelectorHelper.setupForForm({
      modalSelector: '#tagSelectorModal',
      rootSelector: '[data-tag-selector]',
      openButtonSelector: '#open-tag-selector-btn',
      previewSelector: '#selected-tags-preview',
      countSelector: '#selected-tags-count',
      chipsSelector: '#selected-tags-chips',
      hiddenInputSelector: '#selected-tag-names',
      hiddenValueKey: 'name',
      initialValues,
    });
  }

  function bindConnectionTestButton() {
    const button = document.querySelector('button[data-action="test-connection"]');
    if (!button || !window.connectionManager) {
      return;
    }

    button.addEventListener('click', () => {
      const root = document.getElementById('instance-form-root');
      const instanceId = root?.dataset.instanceId;
      if (!instanceId) {
        return;
      }

      const originalText = button.innerHTML;
      button.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>测试中...';
      button.disabled = true;

      window.connectionManager
        .testInstanceConnection(instanceId, {
          onSuccess: (data) => showConnectionResult(data),
          onError: (error) => showConnectionResult(error),
        })
        .finally(() => {
          button.innerHTML = originalText;
          button.disabled = false;
        });
    });
  }

  function showConnectionResult(result) {
    const container = document.getElementById('testResult');
    if (!container) {
      return;
    }
    container.style.display = 'block';
    window.connectionManager.showTestResult(result, 'testResultContent');
  }
})(window, document);
