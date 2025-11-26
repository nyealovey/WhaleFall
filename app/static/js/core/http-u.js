(function (global) {
    'use strict';

    const DEFAULT_TIMEOUT = 120000;

    if (typeof global.u === 'undefined') {
        console.error('Umbrella JS 未加载，无法初始化 httpU');
        return;
    }

    const umbrella = global.u;

    /**
     * 将对象/数组/URLSearchParams 转成查询字符串。
     *
     * @param {string|Object|URLSearchParams} data 待序列化数据。
     * @returns {string} 可直接拼接到 URL 的查询字符串。
     */
    function serializeParams(data) {
        if (!data) {
            return '';
        }
        if (typeof data === 'string') {
            return data;
        }
        if (data instanceof URLSearchParams) {
            return data.toString();
        }
        const params = new URLSearchParams();
        Object.entries(data).forEach(([key, value]) => {
            if (Array.isArray(value)) {
                value.forEach((item) => params.append(key, item));
            } else if (typeof value === 'boolean' || value === 0 || value) {
                params.append(key, value);
            }
        });
        return params.toString();
    }

    /**
     * 确保 umbrella 上存在 ajax 实现，若无则注入。
     *
     * @param {Object} [instance=umbrella] umbrella 实例。
     * @returns {Function} ajax 实现。
     */
    function ensureAjax(instance) {
        const host = instance || umbrella;
        if (typeof host.ajax === 'function') {
            return host.ajax;
        }

        host.ajax = function ajax(options = {}) {
            const {
                url = '/',
                method = 'GET',
                data = null,
                headers = {},
                timeout = DEFAULT_TIMEOUT,
                withCredentials = false,
            } = options;

            const request = new XMLHttpRequest();
            const normalizedMethod = method.toUpperCase();
            const finalHeaders = Object.assign({}, headers);
            let finalUrl = url;
            let body = null;

            if ((normalizedMethod === 'GET' || normalizedMethod === 'HEAD') && data) {
                const queryString = serializeParams(data);
                if (queryString) {
                    finalUrl += (finalUrl.includes('?') ? '&' : '?') + queryString;
                }
            } else if (data instanceof FormData) {
                body = data;
            } else if (typeof data === 'string') {
                body = data;
                if (!finalHeaders['Content-Type']) {
                    finalHeaders['Content-Type'] = 'application/x-www-form-urlencoded;charset=UTF-8';
                }
            } else if (data) {
                body = JSON.stringify(data);
                if (!finalHeaders['Content-Type']) {
                    finalHeaders['Content-Type'] = 'application/json;charset=UTF-8';
                }
            }

            return new Promise((resolve, reject) => {
                request.open(normalizedMethod, finalUrl, true);
                request.timeout = timeout;
                request.withCredentials = withCredentials;

                Object.keys(finalHeaders || {}).forEach((key) => {
                    const value = finalHeaders[key];
                    if (value !== undefined && value !== null) {
                        request.setRequestHeader(key, value);
                    }
                });

                request.onload = function () {
                    const payload = {
                        response: request.responseText,
                        status: request.status,
                        request,
                    };
                    if (request.status >= 200 && request.status < 300) {
                        resolve(payload);
                    } else {
                        reject(payload);
                    }
                };

                request.onerror = function () {
                    reject({
                        response: null,
                        status: request.status || 0,
                        request,
                    });
                };

                request.ontimeout = function () {
                    reject({
                        response: null,
                        status: 0,
                        timeout: true,
                        request,
                    });
                };

                request.send(body);
            });
        };

        return host.ajax;
    }

    const ajax = ensureAjax(umbrella);

    /**
     * 将 query 参数拼接到 URL。
     *
     * @param {string} url 基础地址。
     * @param {Object|URLSearchParams|string} params 查询参数。
     * @returns {string} 拼接后的 URL。
     */
    function appendParams(url, params) {
        if (!params || (typeof params === 'object' && !Object.keys(params).length)) {
            return url;
        }
        const serialized = params instanceof URLSearchParams ? params.toString() : serializeParams(params);
        if (!serialized) {
            return url;
        }
        return url + (url.includes('?') ? '&' : '?') + serialized;
    }

    /**
     * JSON.parse 封装，失败时返回原字符串。
     *
     * @param {string} raw 原始响应文本。
     * @returns {Object|string|null} 解析结果或原始文本。
     */
    function parseJSON(raw) {
        if (!raw) {
            return null;
        }
        try {
            return JSON.parse(raw);
        } catch (error) {
            return raw;
        }
    }

    /**
     * 根据 responseType 解析响应体。
     *
     * @param {string} raw 原始响应文本。
     * @param {'json'|'text'|'raw'} responseType 期望的响应类型。
     * @returns {*}
     */
    function parseResponseBody(raw, responseType) {
        if (responseType === 'text') {
            return raw;
        }
        if (responseType === 'json') {
            return parseJSON(raw);
        }
        if (responseType === 'raw') {
            return raw;
        }
        return parseJSON(raw);
    }

    /**
     * 解析接口返回的错误消息。
     *
     * @param {Object|string|null} body 已解析的响应体。
     * @param {number} fallbackStatus HTTP 状态码，用于推断消息。
     * @returns {string} 终端错误提示。
     */
    function resolveErrorMessage(body, fallbackStatus) {
        if (!body) {
            return fallbackStatus >= 500 ? '服务器错误' : '请求失败';
        }
        if (typeof body === 'string') {
            return body;
        }
        return body.message || body.error || (fallbackStatus >= 500 ? '服务器错误' : '请求失败');
    }

    /**
     * 将底层 ajax 错误包装成统一的 Error 对象。
     *
     * @param {Object} payload umbrella.ajax 的错误负载。
     * @param {'json'|'text'|'raw'} responseType 响应类型。
     * @returns {Error} 包含响应信息的错误对象。
     */
    function buildError(payload, responseType) {
        const body = parseResponseBody(payload && payload.response, responseType);
        const error = new Error(resolveErrorMessage(body, payload ? payload.status : 0));
        error.status = payload ? payload.status : 0;
        error.response = body;
        error.raw = payload ? payload.response : null;
        error.request = payload ? payload.request : null;
        return error;
    }

    /**
     * 基础请求封装，注入 CSRF 与默认头。
     *
     * @param {Object} [config={}] 请求配置。
     * @param {string} config.url 请求地址。
     * @param {string} [config.method='GET'] HTTP 方法。
     * @param {*} [config.data=null] 请求体。
     * @param {Object} [config.headers={}] 自定义请求头。
     * @param {number} [config.timeout=DEFAULT_TIMEOUT] 超时时间。
     * @param {boolean} [config.withCredentials=false] 是否发送凭证。
     * @param {'json'|'text'|'raw'} [config.responseType='json'] 期望返回类型。
     * @returns {Promise<*>} 解析后的响应。
     */
    function request(config = {}) {
        const {
            url,
            method = 'GET',
            data = null,
            headers = {},
            timeout = DEFAULT_TIMEOUT,
            withCredentials = false,
            responseType = 'json',
        } = config;

        if (!url) {
            return Promise.reject(new Error('URL 不能为空'));
        }

        const meta = document.querySelector('meta[name="csrf-token"]');
        const finalHeaders = Object.assign(
            {
                'X-Requested-With': 'XMLHttpRequest',
            },
            headers,
        );

        if (meta && !finalHeaders['X-CSRFToken']) {
            finalHeaders['X-CSRFToken'] = meta.getAttribute('content');
        }

        return ajax({
            url,
            method,
            data,
            headers: finalHeaders,
            timeout,
            withCredentials,
        })
            .then((result) => parseResponseBody(result.response, responseType))
            .catch((error) => {
                throw buildError(error, responseType);
            });
    }

    /**
     * 生成便捷方法（get/post/put...），支持 params 拼接。
     *
     * @param {'GET'|'POST'|'PUT'|'PATCH'|'DELETE'} method HTTP 方法。
     * @returns {Function} 绑定方法的请求函数。
     */
    function createRequest(method) {
        return (url, dataOrConfig, maybeConfig) => {
            if (method === 'GET' || method === 'DELETE') {
                const config = dataOrConfig || {};
                const finalUrl = appendParams(url, config.params);
                const rest = Object.assign({}, config);
                delete rest.params;
                return request({
                    url: finalUrl,
                    method,
                    responseType: rest.responseType || 'json',
                    headers: rest.headers || {},
                    timeout: rest.timeout || DEFAULT_TIMEOUT,
                    withCredentials: rest.withCredentials || false,
                });
            }

            const data = dataOrConfig;
            const config = maybeConfig || {};
            const finalUrl = appendParams(url, config.params);
            return request({
                url: finalUrl,
                method,
                data,
                responseType: config.responseType || 'json',
                headers: config.headers || {},
                timeout: config.timeout || DEFAULT_TIMEOUT,
                withCredentials: config.withCredentials || false,
            });
        };
    }

    const httpU = {
        get: createRequest('GET'),
        delete: createRequest('DELETE'),
        post: createRequest('POST'),
        put: createRequest('PUT'),
        patch: createRequest('PATCH'),
        request: (method, url, data, config = {}) =>
            request({
                url,
                method,
                data,
                responseType: config.responseType || 'json',
                headers: config.headers || {},
                timeout: config.timeout || DEFAULT_TIMEOUT,
                withCredentials: config.withCredentials || false,
            }),
    };

    global.httpU = httpU;
})(window);
