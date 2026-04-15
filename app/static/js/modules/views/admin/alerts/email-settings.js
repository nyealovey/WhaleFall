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
    const setButtonLoading = global.UI?.setButtonLoading;
    const clearButtonLoading = global.UI?.clearButtonLoading;

    const elements = {
        form: document.getElementById('email-alert-settings-form'),
        globalEnabled: document.getElementById('globalEnabled'),
        recipientsInput: document.getElementById('recipientsInput'),
        databaseCapacityEnabled: document.getElementById('databaseCapacityEnabled'),
        databaseCapacityPercentThreshold: document.getElementById('databaseCapacityPercentThreshold'),
        databaseCapacityAbsoluteGbThreshold: document.getElementById('databaseCapacityAbsoluteGbThreshold'),
        accountSyncFailureEnabled: document.getElementById('accountSyncFailureEnabled'),
        databaseSyncFailureEnabled: document.getElementById('databaseSyncFailureEnabled'),
        privilegedAccountEnabled: document.getElementById('privilegedAccountEnabled'),
        backupIssueEnabled: document.getElementById('backupIssueEnabled'),
        sendTestButton: document.getElementById('sendTestEmailBtn'),
        saveButton: document.getElementById('saveEmailAlertSettingsBtn'),
    };

    const rules = [
        {
            input: elements.databaseCapacityEnabled,
            card: pageRoot.querySelector('[data-rule-card="databaseCapacity"]'),
            iconClass: 'fas fa-wave-square',
            activeHint: '双阈值监测已生效',
            idleHint: '双阈值联动',
        },
        {
            input: elements.accountSyncFailureEnabled,
            card: pageRoot.querySelector('[data-rule-card="accountSyncFailure"]'),
            iconClass: 'fas fa-right-left',
            activeHint: '账户同步异常将进入汇总',
            idleHint: '同步质量信号',
        },
        {
            input: elements.databaseSyncFailureEnabled,
            card: pageRoot.querySelector('[data-rule-card="databaseSyncFailure"]'),
            iconClass: 'fas fa-database',
            activeHint: '数据库同步异常将进入汇总',
            idleHint: '同步链路信号',
        },
        {
            input: elements.privilegedAccountEnabled,
            card: pageRoot.querySelector('[data-rule-card="privilegedAccount"]'),
            iconClass: 'fas fa-shield-alt',
            activeHint: '高权限账户新增将进入汇总',
            idleHint: '权限变化信号',
        },
        {
            input: elements.backupIssueEnabled,
            card: pageRoot.querySelector('[data-rule-card="backupIssue"]'),
            iconClass: 'fas fa-hard-drive',
            activeHint: '未备份与备份异常实例将进入汇总',
            idleHint: '备份状态信号',
        },
    ].map((rule) => ({
        ...rule,
        statusElement: rule.card?.querySelector('[data-role="rule-status"]'),
        statusTextElement: rule.card?.querySelector('[data-role="rule-status-text"]'),
    }));

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

    function setStatusPill(node, { tone, iconClass, text }) {
        if (!node) {
            return;
        }

        node.className = `status-pill status-pill--${tone}`;
        node.innerHTML = `<i class="${iconClass}" aria-hidden="true"></i>${text}`;
    }

    function syncRuleState() {
        const globalEnabled = Boolean(elements.globalEnabled?.checked);
        pageRoot.dataset.globalEnabled = globalEnabled ? 'true' : 'false';

        rules.forEach((rule) => {
            const enabled = Boolean(rule.input?.checked);
            if (rule.card) {
                rule.card.dataset.enabled = enabled ? 'true' : 'false';
            }

            if (enabled && globalEnabled) {
                setStatusPill(rule.statusElement, {
                    tone: 'success',
                    iconClass: rule.iconClass,
                    text: '已启用',
                });
                if (rule.statusTextElement) {
                    rule.statusTextElement.textContent = rule.activeHint;
                }
                return;
            }

            if (enabled) {
                setStatusPill(rule.statusElement, {
                    tone: 'warning',
                    iconClass: rule.iconClass,
                    text: '待命',
                });
                if (rule.statusTextElement) {
                    rule.statusTextElement.textContent = '总开关关闭，规则保持待命';
                }
                return;
            }

            setStatusPill(rule.statusElement, {
                tone: 'muted',
                iconClass: rule.iconClass,
                text: '未启用',
            });
            if (rule.statusTextElement) {
                rule.statusTextElement.textContent = rule.idleHint;
            }
        });
    }

    function fillForm(data) {
        const settings = data?.settings || {};

        elements.globalEnabled.checked = Boolean(settings.global_enabled);
        elements.recipientsInput.value = recipientsToLines(settings.recipients);
        elements.databaseCapacityEnabled.checked = Boolean(settings.database_capacity_enabled);
        elements.databaseCapacityPercentThreshold.value = settings.database_capacity_percent_threshold || 30;
        elements.databaseCapacityAbsoluteGbThreshold.value = settings.database_capacity_absolute_gb_threshold || 20;
        elements.accountSyncFailureEnabled.checked = Boolean(settings.account_sync_failure_enabled);
        elements.databaseSyncFailureEnabled.checked = Boolean(settings.database_sync_failure_enabled);
        elements.privilegedAccountEnabled.checked = Boolean(settings.privileged_account_enabled);
        elements.backupIssueEnabled.checked = Boolean(settings.backup_issue_enabled);

        syncRuleState();
    }

    async function loadSettings() {
        const payload = await service.load();
        if (!payload?.success) {
            throw new Error(payload?.message || '加载配置失败');
        }
        fillForm(payload.data || {});
    }

    function startButtonLoading(button, loadingText) {
        const hasLoadingApi = typeof setButtonLoading === 'function' && typeof clearButtonLoading === 'function';

        if (hasLoadingApi) {
            setButtonLoading(button, { loadingText });
            return () => clearButtonLoading(button);
        }

        const originalHtml = button.innerHTML;
        button.disabled = true;
        button.setAttribute('aria-busy', 'true');
        button.innerHTML = `<span class="spinner-border spinner-border-sm me-2"></span>${loadingText}`;
        return () => {
            button.disabled = false;
            button.removeAttribute('aria-busy');
            button.innerHTML = originalHtml;
        };
    }

    function buildPayload() {
        return {
            global_enabled: elements.globalEnabled.checked,
            recipients: linesToRecipients(elements.recipientsInput.value),
            database_capacity_enabled: elements.databaseCapacityEnabled.checked,
            database_capacity_percent_threshold: Number(elements.databaseCapacityPercentThreshold.value || 30),
            database_capacity_absolute_gb_threshold: Number(elements.databaseCapacityAbsoluteGbThreshold.value || 20),
            account_sync_failure_enabled: elements.accountSyncFailureEnabled.checked,
            database_sync_failure_enabled: elements.databaseSyncFailureEnabled.checked,
            privileged_account_enabled: elements.privilegedAccountEnabled.checked,
            backup_issue_enabled: elements.backupIssueEnabled.checked,
        };
    }

    async function handleSubmit(event) {
        event.preventDefault();
        const stopLoading = startButtonLoading(elements.saveButton, '保存中...');

        try {
            const response = await service.update(buildPayload(), csrfToken);
            if (!response?.success) {
                throw new Error(response?.message || '保存失败');
            }

            fillForm(response.data || {});
            toast?.success?.('邮件告警配置已保存');
        } catch (error) {
            toast?.error?.(error?.message || '保存邮件告警配置失败');
        } finally {
            stopLoading();
        }
    }

    async function handleSendTestEmail() {
        const stopLoading = startButtonLoading(elements.sendTestButton, '发送中...');

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
            stopLoading();
        }
    }

    function bindLiveState() {
        const stateInputs = [
            elements.globalEnabled,
            elements.databaseCapacityEnabled,
            elements.accountSyncFailureEnabled,
            elements.databaseSyncFailureEnabled,
            elements.privilegedAccountEnabled,
            elements.backupIssueEnabled,
        ];

        stateInputs.forEach((node) => {
            node?.addEventListener('change', syncRuleState);
        });
    }

    elements.form?.addEventListener('submit', handleSubmit);
    elements.sendTestButton?.addEventListener('click', handleSendTestEmail);
    bindLiveState();
    syncRuleState();
    loadSettings().catch((error) => {
        toast?.error?.(error?.message || '加载邮件告警配置失败');
    });
})(window);
