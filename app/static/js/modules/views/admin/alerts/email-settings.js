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
        smtpReadyText: document.getElementById('smtpReadyText'),
        smtpReadyBadge: document.getElementById('smtpReadyBadge'),
        fromAddressText: document.getElementById('fromAddressText'),
        globalEnabledBadge: document.getElementById('globalEnabledBadge'),
        enabledRulesCountText: document.getElementById('enabledRulesCountText'),
        ruleSummaryText: document.getElementById('ruleSummaryText'),
        recipientCountText: document.getElementById('recipientCountText'),
        recipientSummaryText: document.getElementById('recipientSummaryText'),
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

    const channelState = {
        smtpReady: false,
        fromAddress: '-',
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

    function buildRuleSummary(globalEnabled, enabledRulesCount) {
        if (enabledRulesCount === 0) {
            return globalEnabled ? '当前没有启用规则' : '总开关关闭，当前无规则待命';
        }

        if (!globalEnabled) {
            return `${enabledRulesCount} 条规则已待命，开启总开关后开始发送`;
        }

        return `${enabledRulesCount} 条规则正在参与每日汇总`;
    }

    function buildRecipientSummary(recipientCount, globalEnabled) {
        if (recipientCount === 0) {
            return globalEnabled ? '未填写收件人，启用后将无法完成实际发送' : '开启总开关前请先补齐收件人';
        }

        return `测试邮件与正式汇总将发送给 ${recipientCount} 位收件人`;
    }

    function readFormState() {
        const recipients = linesToRecipients(elements.recipientsInput?.value);
        const enabledRulesCount = rules.filter((rule) => Boolean(rule.input?.checked)).length;

        return {
            globalEnabled: Boolean(elements.globalEnabled?.checked),
            recipientCount: recipients.length,
            enabledRulesCount,
        };
    }

    function syncChannelState() {
        elements.smtpReadyText.textContent = channelState.smtpReady ? '已就绪' : '未就绪';
        elements.fromAddressText.textContent = channelState.fromAddress || '-';

        setStatusPill(elements.smtpReadyBadge, {
            tone: channelState.smtpReady ? 'success' : 'warning',
            iconClass: 'fas fa-satellite-dish',
            text: channelState.smtpReady ? 'SMTP 已就绪' : 'SMTP 未就绪',
        });
    }

    function syncRuleState(globalEnabled) {
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

    function syncDerivedState() {
        const { globalEnabled, recipientCount, enabledRulesCount } = readFormState();

        pageRoot.dataset.globalEnabled = globalEnabled ? 'true' : 'false';

        elements.enabledRulesCountText.textContent = `${enabledRulesCount} / ${rules.length}`;
        elements.recipientCountText.textContent = String(recipientCount);
        elements.ruleSummaryText.textContent = buildRuleSummary(globalEnabled, enabledRulesCount);
        elements.recipientSummaryText.textContent = buildRecipientSummary(recipientCount, globalEnabled);

        setStatusPill(elements.globalEnabledBadge, {
            tone: globalEnabled ? 'success' : 'muted',
            iconClass: 'fas fa-power-off',
            text: globalEnabled ? '总开关已启用' : '总开关关闭',
        });

        syncRuleState(globalEnabled);
    }

    function fillForm(data) {
        const settings = data?.settings || {};

        channelState.smtpReady = Boolean(data?.smtp_ready);
        channelState.fromAddress = data?.from_address || '-';

        elements.globalEnabled.checked = Boolean(settings.global_enabled);
        elements.recipientsInput.value = recipientsToLines(settings.recipients);
        elements.databaseCapacityEnabled.checked = Boolean(settings.database_capacity_enabled);
        elements.databaseCapacityPercentThreshold.value = settings.database_capacity_percent_threshold || 30;
        elements.databaseCapacityAbsoluteGbThreshold.value = settings.database_capacity_absolute_gb_threshold || 20;
        elements.accountSyncFailureEnabled.checked = Boolean(settings.account_sync_failure_enabled);
        elements.databaseSyncFailureEnabled.checked = Boolean(settings.database_sync_failure_enabled);
        elements.privilegedAccountEnabled.checked = Boolean(settings.privileged_account_enabled);

        syncChannelState();
        syncDerivedState();
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
            elements.recipientsInput,
            elements.databaseCapacityEnabled,
            elements.accountSyncFailureEnabled,
            elements.databaseSyncFailureEnabled,
            elements.privilegedAccountEnabled,
        ];

        stateInputs.forEach((node) => {
            if (!node) {
                return;
            }

            const eventName = node.tagName === 'TEXTAREA' ? 'input' : 'change';
            node.addEventListener(eventName, syncDerivedState);
        });
    }

    elements.form?.addEventListener('submit', handleSubmit);
    elements.sendTestButton?.addEventListener('click', handleSendTestEmail);
    bindLiveState();
    syncChannelState();
    syncDerivedState();
    loadSettings().catch((error) => {
        toast?.error?.(error?.message || '加载邮件告警配置失败');
    });
})(window);
