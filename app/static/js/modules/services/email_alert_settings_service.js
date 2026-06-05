(function initEmailAlertSettingsService(global) {
    const ensureHttpClient = global.ServiceUtils?.ensureHttpClient;
    if (typeof ensureHttpClient !== 'function') {
        throw new Error('EmailAlertSettingsService: ServiceUtils 未初始化');
    }

    class EmailAlertSettingsService {
        constructor(apiUrl, testApiUrl, feishuTestApiUrl, httpClient) {
            this.apiUrl = apiUrl;
            this.testApiUrl = testApiUrl;
            this.feishuTestApiUrl = feishuTestApiUrl;
            this.httpClient = ensureHttpClient(httpClient, 'EmailAlertSettingsService');
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

        async sendTest(payload) {
            return this.httpClient.post(this.testApiUrl, payload, {
                headers: { Accept: 'application/json' },
            });
        }

        async sendFeishuTest(payload) {
            return this.httpClient.post(this.feishuTestApiUrl, payload, {
                headers: { Accept: 'application/json' },
            });
        }
    }

    global.EmailAlertSettingsService = EmailAlertSettingsService;
})(window);
