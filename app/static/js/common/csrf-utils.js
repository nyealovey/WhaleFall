/**
 * CSRF令牌管理工具
 * 提供CSRF令牌的获取和管理功能
 */

class CSRFManager {
    constructor() {
        this.token = null;
        this.tokenPromise = null;
        this.httpClient = window.httpU || null;
    }

    ensureHttpClient() {
        if (!this.httpClient) {
            throw new Error('httpU 未初始化');
        }
    }

    /**
     * 获取CSRF令牌
     * @returns {Promise<string>} CSRF令牌
     */
    async getToken() {
        // 如果已有令牌且未过期，直接返回
        if (this.token) {
            return this.token;
        }

        // 如果正在获取令牌，等待完成
        if (this.tokenPromise) {
            return this.tokenPromise;
        }

        // 创建新的令牌获取请求
        this.tokenPromise = this._fetchToken();
        
        try {
            this.token = await this.tokenPromise;
            return this.token;
        } finally {
            this.tokenPromise = null;
        }
    }

    /**
     * 从服务器获取CSRF令牌
     * @private
     * @returns {Promise<string>} CSRF令牌
     */
    async _fetchToken() {
        if (!this.httpClient || typeof this.httpClient.get !== 'function') {
            throw new Error('httpU 未初始化，无法获取 CSRF 令牌');
        }
        try {
            const data = await this.httpClient.get('/api/csrf-token', {
                responseType: 'json',
                withCredentials: true,
            });
            const token = data?.csrf_token ?? data?.data?.csrf_token;
            if (!token) {
                throw new Error('响应中缺少 CSRF 令牌');
            }
            return token;
        } catch (error) {
            console.error('获取CSRF令牌失败:', error);
            throw error;
        }
    }

    /**
     * 清除缓存的令牌
     */
    clearToken() {
        this.token = null;
        this.tokenPromise = null;
    }

    /**
     * 为请求添加CSRF令牌
     * @param {Object} options - fetch选项
     * @returns {Promise<Object>} 包含CSRF令牌的选项
     */
    async addTokenToRequest(options = {}) {
        const token = await this.getToken();
        const headers = Object.assign({}, options.headers, {
            'X-CSRFToken': token,
        });
        return Object.assign({}, options, { headers });
    }

    /**
     * 发送带有CSRF令牌的POST请求
     * @param {string} url - 请求URL
     * @param {Object} data - 请求数据
     * @param {Object} options - 额外选项
     * @returns {Promise<Response>} 响应对象
     */
    async post(url, data, options = {}) {
        this.ensureHttpClient();
        const token = await this.getToken();
        const config = this._normalizeRequestConfig(options, token);
        return this.httpClient.post(url, data, config);
    }

    /**
     * 发送带有CSRF令牌的PUT请求
     * @param {string} url - 请求URL
     * @param {Object} data - 请求数据
     * @param {Object} options - 额外选项
     * @returns {Promise<Response>} 响应对象
     */
    async put(url, data, options = {}) {
        this.ensureHttpClient();
        const token = await this.getToken();
        const config = this._normalizeRequestConfig(options, token);
        return this.httpClient.put(url, data, config);
    }

    /**
     * 发送带有CSRF令牌的DELETE请求
     * @param {string} url - 请求URL
     * @param {Object} options - 额外选项
     * @returns {Promise<Response>} 响应对象
     */
    async delete(url, options = {}) {
        this.ensureHttpClient();
        const token = await this.getToken();
        const config = this._normalizeRequestConfig(options, token);
        return this.httpClient.delete(url, config);
    }

    _normalizeRequestConfig(options = {}, token) {
        const headers = Object.assign(
            {
                'Content-Type': 'application/json',
                'X-CSRFToken': token,
            },
            options.headers || {}
        );
        return {
            params: options.params,
            responseType: options.responseType || 'json',
            withCredentials:
                typeof options.withCredentials === 'boolean' ? options.withCredentials : true,
            headers,
            timeout: options.timeout,
        };
    }
}

// 创建全局实例
window.csrfManager = new CSRFManager();

// 提供向后兼容的全局函数
window.getCSRFToken = function() {
    const helpers = window.DOMHelpers;
    const query = (selector) => {
        if (helpers && typeof helpers.selectOne === 'function') {
            return helpers.selectOne(selector).first();
        }
        return document.querySelector(selector);
    };

    const metaToken = query('meta[name="csrf-token"]');
    if (metaToken) {
        return metaToken.getAttribute('content');
    }

    const inputToken = query('input[name="csrf_token"]');
    if (inputToken) {
        return inputToken.value;
    }

    console.warn('CSRF token not found');
    return '';
};

// 导出供模块使用
if (typeof module !== 'undefined' && module.exports) {
    module.exports = CSRFManager;
}
