(function mountEmailAlertSettingsPage(global) {
    const pageRoot = document.getElementById('email-alert-settings-page');
    if (!pageRoot) {
        return;
    }

    const toast = global.toast;
    const apiUrl = pageRoot.dataset.apiUrl;
    const testApiUrl = pageRoot.dataset.testApiUrl;
    const csrfToken = document.getElementById('email-alert-csrf-token')?.value || '';
    const service = new global.EmailAlertSettingsService(apiUrl, testApiUrl);

    const elements = {
        smtpReadyText: document.getElementById('smtpReadyText'),
        fromAddressText: document.getElementById('fromAddressText'),
        form: document.getElementById('email-alert-settings-form'),
        globalEnabled: document.getElementById('globalEnabled'),
        recipientsInput: document.getElementById('recipientsInput'),
        databaseCapacityEnabled: document.getElementById('databaseCapacityEnabled'),
        databaseCapacityPercentThreshold: document.getElementById('databaseCapacityPercentThreshold'),
        databaseCapacityAbsoluteGbThreshold: document.getElementById('databaseCapacityAbsoluteGbThreshold'),
        accountSyncFailureEnabled: document.getElementById('accountSyncFailureEnabled'),
        databaseSyncFailureEnabled: document.getElementById('databaseSyncFailureEnabled'),
        privilegedAccountEnabled: document.getElementById('privilegedAccountEnabled'),
        sendTestButton: document.getElementById('sendTestEmailBtn'),
        saveButton: document.getElementById('saveEmailAlertSettingsBtn'),
    };

    function recipientsToLines(recipients) {
        if (!Array.isArray(recipients)) {
            return '';
        }
        return recipients.join('\n');
    }

    function linesToRecipients(value) {
        return String(value || '')
            .split('\n')
            .map((item) => item.trim())
            .filter(Boolean);
    }

    function fillForm(data) {
        const settings = data?.settings || {};
        elements.smtpReadyText.textContent = data?.smtp_ready ? '已配置' : '未配置';
        elements.fromAddressText.textContent = data?.from_address || '-';
        elements.globalEnabled.checked = Boolean(settings.global_enabled);
        elements.recipientsInput.value = recipientsToLines(settings.recipients);
        elements.databaseCapacityEnabled.checked = Boolean(settings.database_capacity_enabled);
        elements.databaseCapacityPercentThreshold.value = settings.database_capacity_percent_threshold || 30;
        elements.databaseCapacityAbsoluteGbThreshold.value = settings.database_capacity_absolute_gb_threshold || 20;
        elements.accountSyncFailureEnabled.checked = Boolean(settings.account_sync_failure_enabled);
        elements.databaseSyncFailureEnabled.checked = Boolean(settings.database_sync_failure_enabled);
        elements.privilegedAccountEnabled.checked = Boolean(settings.privileged_account_enabled);
    }

    async function loadSettings() {
        const payload = await service.load();
        if (!payload?.success) {
            throw new Error(payload?.message || '加载配置失败');
        }
        fillForm(payload.data || {});
    }

    async function handleSubmit(event) {
        event.preventDefault();
        const originalLabel = elements.saveButton.innerHTML;
        elements.saveButton.disabled = true;
        elements.saveButton.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>保存中';

        try {
            const payload = {
                global_enabled: elements.globalEnabled.checked,
                recipients: linesToRecipients(elements.recipientsInput.value),
                database_capacity_enabled: elements.databaseCapacityEnabled.checked,
                database_capacity_percent_threshold: Number(elements.databaseCapacityPercentThreshold.value || 30),
                database_capacity_absolute_gb_threshold: Number(elements.databaseCapacityAbsoluteGbThreshold.value || 20),
                account_sync_failure_enabled: elements.accountSyncFailureEnabled.checked,
                database_sync_failure_enabled: elements.databaseSyncFailureEnabled.checked,
                privileged_account_enabled: elements.privilegedAccountEnabled.checked,
            };
            const response = await service.update(payload, csrfToken);
            if (!response?.success) {
                throw new Error(response?.message || '保存失败');
            }
            fillForm(response.data || {});
            toast?.success?.('邮件告警配置已保存');
        } catch (error) {
            toast?.error?.(error?.message || '保存邮件告警配置失败');
        } finally {
            elements.saveButton.disabled = false;
            elements.saveButton.innerHTML = originalLabel;
        }
    }

    async function handleSendTestEmail() {
        const originalLabel = elements.sendTestButton.innerHTML;
        elements.sendTestButton.disabled = true;
        elements.sendTestButton.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>发送中';

        try {
            const response = await service.sendTest(
                {
                    recipients: linesToRecipients(elements.recipientsInput.value),
                },
                csrfToken,
            );
            if (!response?.success) {
                throw new Error(response?.message || '发送测试邮件失败');
            }
            toast?.success?.('测试邮件已发送');
        } catch (error) {
            toast?.error?.(error?.message || '发送测试邮件失败');
        } finally {
            elements.sendTestButton.disabled = false;
            elements.sendTestButton.innerHTML = originalLabel;
        }
    }

    elements.form?.addEventListener('submit', handleSubmit);
    elements.sendTestButton?.addEventListener('click', handleSendTestEmail);
    loadSettings().catch((error) => {
        toast?.error?.(error?.message || '加载邮件告警配置失败');
    });
})(window);
