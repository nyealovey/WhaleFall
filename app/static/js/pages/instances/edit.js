/**
 * 编辑实例页面脚本
 * 负责表单校验、标签选择器初始化与连接测试。
 */

let instanceEditValidator = null;

document.addEventListener('DOMContentLoaded', () => {
  initializeTagSelector();
  initializeForm();
});

function initializeForm() {
  initializeFormValidation();

  const dbTypeSelect = document.getElementById('db_type');
  if (dbTypeSelect) {
    dbTypeSelect.addEventListener('change', function () {
      handleDbTypeChange(this);
      if (instanceEditValidator) {
        instanceEditValidator.revalidateField('#db_type');
        instanceEditValidator.revalidateField('#port');
      }
    });

    if (dbTypeSelect.value) {
      handleDbTypeChange(dbTypeSelect);
    }
  }

  const nameInput = document.getElementById('name');
  if (nameInput) {
    nameInput.addEventListener('blur', () => {
      instanceEditValidator?.revalidateField('#name');
    });
  }

  const hostInput = document.getElementById('host');
  if (hostInput) {
    hostInput.addEventListener('blur', () => {
      instanceEditValidator?.revalidateField('#host');
    });
  }

  const portInput = document.getElementById('port');
  if (portInput) {
    portInput.addEventListener('input', () => {
      instanceEditValidator?.revalidateField('#port');
    });
  }

  const credentialSelect = document.getElementById('credential_id');
  if (credentialSelect) {
    credentialSelect.addEventListener('change', () => {
      instanceEditValidator?.revalidateField('#credential_id');
    });
  }
}

function initializeFormValidation() {
  if (!window.FormValidator || !window.ValidationRules) {
    console.error('表单校验模块未正确加载');
    return;
  }

  instanceEditValidator = window.FormValidator.create('#instanceForm');
  if (!instanceEditValidator) {
    return;
  }

  instanceEditValidator
    .useRules('#name', window.ValidationRules.instance.name)
    .useRules('#db_type', window.ValidationRules.instance.dbType)
    .useRules('#host', window.ValidationRules.instance.host)
    .useRules('#port', window.ValidationRules.instance.port)
    .useRules('#credential_id', window.ValidationRules.instance.credential)
    .onSuccess((event) => {
      const form = event.target;
      showLoadingState(form, '保存中...');
      form.submit();
    })
    .onFail(() => {
      toast.error('请检查实例表单填写');
    });
}

function handleDbTypeChange(selectElement) {
  const select = selectElement || document.getElementById('db_type');
  if (!select) {
    return;
  }

  const portInput = document.getElementById('port');
  const databaseNameInput = document.getElementById('database_name');
  const oracleSidRow = document.getElementById('oracle-sid-row');
  const selectedOption = select.options[select.selectedIndex];
  const dbType = select.value;

  if (selectedOption?.dataset.port && portInput) {
    portInput.value = selectedOption.dataset.port;
  }

  if (databaseNameInput && !databaseNameInput.value) {
    const defaultDatabaseNames = {
      mysql: 'mysql',
      postgresql: 'postgres',
      sqlserver: 'master',
      oracle: 'orcl',
    };
    if (defaultDatabaseNames[dbType]) {
      databaseNameInput.value = defaultDatabaseNames[dbType];
    }
  }

  if (oracleSidRow) {
    if (dbType === 'oracle') {
      oracleSidRow.style.display = 'block';
      oracleSidRow.classList.add('fade-in');
    } else {
      oracleSidRow.style.display = 'none';
      oracleSidRow.classList.remove('fade-in');
    }
  }
}

function showLoadingState(form, text) {
  const submitBtn = form.querySelector('button[type="submit"]');
  if (submitBtn) {
    submitBtn.dataset.originalText =
      submitBtn.dataset.originalText || submitBtn.innerHTML;
    submitBtn.innerHTML = `<i class="fas fa-spinner fa-spin me-2"></i>${text}`;
    submitBtn.disabled = true;
  }
}

function restoreLoadingState(form) {
  const submitBtn = form.querySelector('button[type="submit"]');
  if (submitBtn && submitBtn.dataset.originalText) {
    submitBtn.innerHTML = submitBtn.dataset.originalText;
    submitBtn.disabled = false;
  }
}

function testConnection(evt) {
  const eventObj = evt || window.event || null;
  const testBtn =
    (eventObj && (eventObj.currentTarget || eventObj.target)) ||
    document.querySelector('button[onclick*="testConnection"]');

  if (!testBtn) {
    return;
  }

  const originalText = testBtn.innerHTML;
  testBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>测试中...';
  testBtn.disabled = true;

  const instanceId = getInstanceId();

  connectionManager
    .testInstanceConnection(instanceId, {
      onSuccess: (data) => {
        const resultDiv = document.getElementById('testResult');
        connectionManager.showTestResult(data, 'testResultContent');
        if (resultDiv) {
          resultDiv.style.display = 'block';
        }
      },
      onError: (error) => {
        const resultDiv = document.getElementById('testResult');
        connectionManager.showTestResult(error, 'testResultContent');
        if (resultDiv) {
          resultDiv.style.display = 'block';
        }
      },
    })
    .finally(() => {
      testBtn.innerHTML = originalText;
      testBtn.disabled = false;
    });
}

function initializeTagSelector() {
  if (!window.TagSelectorHelper) {
    console.warn('TagSelectorHelper 未加载，跳过标签选择器初始化');
    return;
  }

  const initialValues = Array.isArray(window.currentTagNames)
    ? window.currentTagNames
    : [];

  TagSelectorHelper.setupForForm({
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

function getInstanceId() {
  const urlParts = window.location.pathname.split('/');
  let instanceId = urlParts[urlParts.length - 1];
  if (instanceId === 'edit') {
    instanceId = urlParts[urlParts.length - 2];
  }
  return instanceId;
}

window.testConnection = testConnection;
