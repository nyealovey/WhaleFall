(function initRiskCenterRuleSettingsService(global) {
    const ensureHttpClient = global.ServiceUtils?.ensureHttpClient;
    if (typeof ensureHttpClient !== 'function') {
        throw new Error('RiskCenterRuleSettingsService: ServiceUtils 未初始化');
    }

    class RiskCenterRuleSettingsService {
        constructor(apiUrl, httpClient) {
            this.apiUrl = apiUrl;
            this.httpClient = ensureHttpClient(httpClient, 'RiskCenterRuleSettingsService');
        }

        async load() {
            return this.httpClient.get(this.apiUrl, {
                headers: { Accept: 'application/json' },
            });
        }

        async update(payload) {
            return this.httpClient.put(this.apiUrl, payload, {
                headers: { Accept: 'application/json' },
            });
        }
    }

    global.RiskCenterRuleSettingsService = RiskCenterRuleSettingsService;
})(window);
