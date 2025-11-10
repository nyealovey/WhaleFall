/**
 * Account Classification domain-specific API helpers.
 * Provides thin wrappers around the HTTP client plus consistent error logging.
 */
(function registerAccountClassificationAPI(global) {
    'use strict';

    const http = global.http;
    if (!http) {
        console.error('AccountClassificationAPI: http client is required.');
        return;
    }

    const logError =
        global.logErrorWithContext ||
        function fallbackLogger(error, context, extras) {
            console.error(`[AccountClassificationAPI] ${context}`, error, extras || {});
        };

    function request(promise, context) {
        return promise
            .then(response => {
                if (response && response.success === false) {
                    const error = new Error(response.error || `${context}失败`);
                    error.response = response;
                    throw error;
                }
                return response;
            })
            .catch(error => {
                logError(error, context, { scope: 'AccountClassificationAPI' });
                throw error;
            });
    }

    const classifications = {
        list() {
            return request(http.get('/account_classification/api/classifications'), '加载分类');
        },
        detail(id) {
            return request(
                http.get(`/account_classification/api/classifications/${id}`),
                '获取分类详情'
            );
        },
        create(payload) {
            return request(
                http.post('/account_classification/api/classifications', payload),
                '创建分类'
            );
        },
        update(id, payload) {
            return request(
                http.put(`/account_classification/api/classifications/${id}`, payload),
                '更新分类'
            );
        },
        remove(id) {
            return request(
                http.delete(`/account_classification/api/classifications/${id}`),
                '删除分类'
            );
        }
    };

    const rules = {
        list() {
            return request(http.get('/account_classification/api/rules'), '加载规则');
        },
        detail(id) {
            return request(
                http.get(`/account_classification/api/rules/${id}`),
                '获取规则详情'
            );
        },
        create(payload) {
            return request(http.post('/account_classification/api/rules', payload), '创建规则');
        },
        update(id, payload) {
            return request(
                http.put(`/account_classification/api/rules/${id}`, payload),
                '更新规则'
            );
        },
        remove(id) {
            return request(
                http.delete(`/account_classification/api/rules/${id}`),
                '删除规则'
            );
        },
        stats(ruleIds = []) {
            if (!Array.isArray(ruleIds) || ruleIds.length === 0) {
                return Promise.resolve({ rule_stats: [] });
            }
            const query = encodeURIComponent(ruleIds.join(','));
            return request(
                http.get(`/account_classification/api/rules/stats?rule_ids=${query}`),
                '加载规则统计'
            );
        }
    };

    const automation = {
        trigger(payload) {
            return request(
                http.post('/account_classification/api/auto-classify', payload || {}),
                '触发自动分类'
            );
        }
    };

    global.AccountClassificationAPI = {
        classifications,
        rules,
        automation
    };
})(window);
