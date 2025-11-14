/**
 * 实例表单页面（新建 & 编辑）
 */
(function (window) {
  'use strict';

  const helpers = window.DOMHelpers;
  if (!helpers) {
    console.error('DOMHelpers 未初始化，无法加载实例表单脚本');
    return;
  }

  const { ready, selectOne, from } = helpers;

  let instanceFormValidator = null;
  let formController = null;

  ready(() => {
    const formWrapper = selectOne('#instanceForm');
    if (!formWrapper.length) {
      return;
    }
    const form = formWrapper.first();

    const root = selectOne('#instance-form-root');
    const mode = root.length ? root.data('formMode') || root.attr('data-form-mode') || 'create' : 'create';

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

    const dbTypeSelect = selectOne('#db_type');
    const nameInput = selectOne('#name');
    const hostInput = selectOne('#host');
    const portInput = selectOne('#port');
    const credentialSelect = selectOne('#credential_id');

    if (dbTypeSelect.length) {
      dbTypeSelect.on('change', (event) => {
        handleDbTypeChange(event.currentTarget);
        instanceFormValidator.revalidateField('#db_type');
        instanceFormValidator.revalidateField('#port');
      });
    }
    if (nameInput.length) {
      nameInput.on('blur', () => instanceFormValidator.revalidateField('#name'));
    }
    if (hostInput.length) {
      hostInput.on('blur', () => instanceFormValidator.revalidateField('#host'));
    }
    if (portInput.length) {
      portInput.on('input', () => instanceFormValidator.revalidateField('#port'));
    }
    if (credentialSelect.length) {
      credentialSelect.on('change', () => instanceFormValidator.revalidateField('#credential_id'));
    }
  }

  function initializeDbTypeBehavior() {
    const select = selectOne('#db_type');
    if (select.length) {
      handleDbTypeChange(select.first());
    }
  }

  function handleDbTypeChange(selectElement) {
    const select = selectElement || selectOne('#db_type').first();
    if (!select) {
      return;
    }

    const portInput = selectOne('#port').first();
    const databaseNameInput = selectOne('#database_name').first();
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

    const hiddenInput = selectOne('#selected-tag-names');
    const initialValues = hiddenInput.length && hiddenInput.first().value
      ? hiddenInput
          .first()
          .value.split(',')
          .map((value) => value.trim())
          .filter(Boolean)
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
    const buttonWrapper = selectOne('button[data-action="test-connection"]');
    if (!buttonWrapper.length || !window.connectionManager) {
      return;
    }
    const button = buttonWrapper.first();

    buttonWrapper.on('click', () => {
      const root = selectOne('#instance-form-root');
      const instanceId = root.length ? root.attr('data-instance-id') : null;
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
    const containerWrapper = selectOne('#testResult');
    if (!containerWrapper.length) {
      return;
    }
    const container = containerWrapper.first();
    container.style.display = 'block';
    window.connectionManager.showTestResult(result, 'testResultContent');
  }
})(window);
