(function mountRiskRuleSettingsPage(global) {
    const pageRoot = document.getElementById('risk-rule-settings-page');
    if (!pageRoot || typeof global.RiskCenterRuleSettingsService !== 'function') {
        return;
    }

    const escapeHtml = global.UI?.escapeHtml || ((value) => String(value ?? ''));
    const toast = global.toast;
    const setButtonLoading = global.UI?.setButtonLoading;
    const clearButtonLoading = global.UI?.clearButtonLoading;
    const csrfToken = document.getElementById('risk-rule-csrf-token')?.value || '';
    const service = new global.RiskCenterRuleSettingsService(pageRoot.dataset.apiUrl);
    const list = pageRoot.querySelector('[data-risk-rule-list]');
    const empty = pageRoot.querySelector('[data-risk-rule-empty]');
    const saveButton = document.getElementById('saveRiskRuleSettingsBtn');

    const severityLabels = {
        high: '高',
        medium: '中',
        low: '低',
    };

    function startButtonLoading(button, loadingText) {
        const hasLoadingApi = typeof setButtonLoading === 'function' && typeof clearButtonLoading === 'function';
        if (hasLoadingApi) {
            setButtonLoading(button, { loadingText });
            return () => clearButtonLoading(button);
        }
        const originalHtml = button.innerHTML;
        button.disabled = true;
        button.innerHTML = `<span class="spinner-border spinner-border-sm me-2"></span>${loadingText}`;
        return () => {
            button.disabled = false;
            button.innerHTML = originalHtml;
        };
    }

    function renderRule(rule) {
        const ruleKey = escapeHtml(rule.rule_key || '');
        const enabled = Boolean(rule.enabled);
        const severity = String(rule.severity || rule.default_severity || 'medium');
        return `
            <section class="risk-rule-item" data-risk-rule-key="${ruleKey}">
                <div class="risk-rule-item__main">
                    <span class="risk-rule-item__category">${escapeHtml(rule.category || '-')}</span>
                    <strong>${escapeHtml(rule.label || rule.rule_key || '-')}</strong>
                    <p>${escapeHtml(rule.description || '')}</p>
                </div>
                <label class="risk-rule-switch">
                    <input class="form-check-input" type="checkbox" data-risk-rule-enabled ${enabled ? 'checked' : ''}>
                    <span>展示</span>
                </label>
                <div class="risk-rule-severity" role="group" aria-label="${escapeHtml(rule.label || '')} 风险等级">
                    ${Object.entries(severityLabels)
                        .map(([value, label]) => `
                            <label class="risk-rule-severity__option risk-rule-severity__option--${value}">
                                <input type="radio" name="risk-rule-${ruleKey}" value="${value}" ${severity === value ? 'checked' : ''}>
                                <span>${label}</span>
                            </label>
                        `)
                        .join('')}
                </div>
            </section>
        `;
    }

    function renderRules(rules) {
        const safeRules = Array.isArray(rules) ? rules : [];
        if (list) {
            list.innerHTML = safeRules.map(renderRule).join('');
        }
        if (empty) {
            empty.classList.toggle('d-none', safeRules.length > 0);
        }
    }

    function collectRules() {
        return Array.from(pageRoot.querySelectorAll('[data-risk-rule-key]')).map((item) => {
            const selectedSeverity = item.querySelector('input[type="radio"]:checked');
            return {
                rule_key: item.dataset.riskRuleKey || '',
                enabled: Boolean(item.querySelector('[data-risk-rule-enabled]')?.checked),
                severity: selectedSeverity?.value || 'medium',
            };
        });
    }

    async function loadRules() {
        const payload = await service.load();
        if (!payload?.success) {
            throw new Error(payload?.message || '加载风险规则失败');
        }
        renderRules(payload.data?.rules || []);
    }

    async function saveRules() {
        const stopLoading = startButtonLoading(saveButton, '保存中...');
        try {
            const payload = await service.update({ rules: collectRules() }, csrfToken);
            if (!payload?.success) {
                throw new Error(payload?.message || '保存风险规则失败');
            }
            renderRules(payload.data?.rules || []);
            toast?.success?.('风险规则已保存');
        } catch (error) {
            toast?.error?.(error?.message || '保存风险规则失败');
        } finally {
            stopLoading();
        }
    }

    saveButton?.addEventListener('click', saveRules);
    loadRules().catch((error) => {
        toast?.error?.(error?.message || '加载风险规则失败');
    });
})(window);
