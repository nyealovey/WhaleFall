/**
 * CSRF令牌管理工具
 * 提供CSRF令牌的获取和管理功能
 */

class CSRFManager {
    constructor() {
        this.token = null;
        this.tokenPromise = null;
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
        try {
            const response = await fetch('/api/csrf-token', {
                method: 'GET',
                credentials: 'same-origin',
                headers: {
                    'Content-Type': 'application/json'
                }
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const data = await response.json();
            return data.csrf_token;
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
        
        const headers = {
            ...options.headers,
            'X-CSRFToken': token
        };

        return {
            ...options,
            headers
        };
    }

    /**
     * 发送带有CSRF令牌的POST请求
     * @param {string} url - 请求URL
     * @param {Object} data - 请求数据
     * @param {Object} options - 额外选项
     * @returns {Promise<Response>} 响应对象
     */
    async post(url, data, options = {}) {
        const token = await this.getToken();
        
        const requestOptions = {
            method: 'POST',
            credentials: 'same-origin',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': token,
                ...options.headers
            },
            body: JSON.stringify(data),
            ...options
        };

        return fetch(url, requestOptions);
    }

    /**
     * 发送带有CSRF令牌的PUT请求
     * @param {string} url - 请求URL
     * @param {Object} data - 请求数据
     * @param {Object} options - 额外选项
     * @returns {Promise<Response>} 响应对象
     */
    async put(url, data, options = {}) {
        const token = await this.getToken();
        
        const requestOptions = {
            method: 'PUT',
            credentials: 'same-origin',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': token,
                ...options.headers
            },
            body: JSON.stringify(data),
            ...options
        };

        return fetch(url, requestOptions);
    }

    /**
     * 发送带有CSRF令牌的DELETE请求
     * @param {string} url - 请求URL
     * @param {Object} options - 额外选项
     * @returns {Promise<Response>} 响应对象
     */
    async delete(url, options = {}) {
        const token = await this.getToken();
        
        const requestOptions = {
            method: 'DELETE',
            credentials: 'same-origin',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': token,
                ...options.headers
            },
            ...options
        };

        return fetch(url, requestOptions);
    }
}

// 创建全局实例
window.csrfManager = new CSRFManager();

// 导出供模块使用
if (typeof module !== 'undefined' && module.exports) {
    module.exports = CSRFManager;
}
