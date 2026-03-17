(function initEmailAlertSettingsService(global) {
    class EmailAlertSettingsService {
        constructor(apiUrl, testApiUrl) {
            this.apiUrl = apiUrl;
            this.testApiUrl = testApiUrl;
        }

        async load() {
            const response = await fetch(this.apiUrl, {
                method: 'GET',
                credentials: 'same-origin',
                headers: { Accept: 'application/json' },
            });
            return response.json();
        }

        async update(payload, csrfToken) {
            const response = await fetch(this.apiUrl, {
                method: 'PUT',
                credentials: 'same-origin',
                headers: {
                    'Content-Type': 'application/json',
                    Accept: 'application/json',
                    'X-CSRFToken': csrfToken,
                },
                body: JSON.stringify(payload),
            });
            return response.json();
        }

        async sendTest(payload, csrfToken) {
            const response = await fetch(this.testApiUrl, {
                method: 'POST',
                credentials: 'same-origin',
                headers: {
                    'Content-Type': 'application/json',
                    Accept: 'application/json',
                    'X-CSRFToken': csrfToken,
                },
                body: JSON.stringify(payload),
            });
            return response.json();
        }
    }

    global.EmailAlertSettingsService = EmailAlertSettingsService;
})(window);
