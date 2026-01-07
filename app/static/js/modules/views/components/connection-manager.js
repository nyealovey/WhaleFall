/**
 * 连接管理组件
 * 统一的数据库连接测试和管理功能
 */

/**
 * 提供统一连接测试/校验的前端控制器。
 *
 * 封装数据库连接测试和管理功能，提供统一的接口和错误处理。
 *
 * @class
 */
class ConnectionManager {
    /**
     * 构造函数。
     *
     * @constructor
     * @throws {Error} 当 ConnectionService 未初始化时抛出
     */
    constructor() {
        this.baseUrl = '/api/v1/instances';
        this.helpers = window.DOMHelpers;
        if (!this.helpers) {
            console.error('DOMHelpers 未初始化，连接管理组件无法渲染提示');
        }
        if (!window.ConnectionService) {
            throw new Error('ConnectionService 未初始化');
        }
        this.connectionService = new window.ConnectionService(window.httpU);
    }

    /**
     * 测试已存在实例的连接。
     *
     * @param {number} instanceId - 实例 ID
     * @param {Object} [options] - 选项配置
     * @param {Object} [options.payload] - 测试参数
     * @param {Function} [options.onSuccess] - 成功回调函数
     * @param {Function} [options.onError] - 错误回调函数
     * @return {Promise<Object>} 测试结果
     */
	    async testInstanceConnection(instanceId, options = {}) {
	        try {
	            const payload = options.payload || {};
	            const result = await this.connectionService.testInstanceConnection(instanceId, payload);

            if (options.onSuccess && result.success) {
                options.onSuccess(result);
            } else if (options.onError && !result.success) {
                options.onError(result);
            }

	            return result;
	        } catch (error) {
	            const response = error && typeof error === 'object' ? error.response : null;
	            const extra = response && typeof response === 'object' ? response.extra : null;
	            const connectionErrorId =
	                extra && typeof extra === 'object' && typeof extra.connection_error_id === 'string'
	                    ? extra.connection_error_id
	                    : null;
	            const message =
	                response && typeof response === 'object' && typeof response.message === 'string'
	                    ? response.message
	                    : error && typeof error === 'object' && typeof error.message === 'string'
	                        ? error.message
	                        : '连接测试失败';
	            const errorResult = {
	                success: false,
	                message,
	                error: message,
	                error_id: connectionErrorId,
	            };

	            if (options.onError) {
	                options.onError(errorResult);
	            }

            return errorResult;
        }
    }

    /**
     * 测试新连接参数
     * @param {Object} connectionParams - 连接参数
     * @param {Object} options - 选项
     * @returns {Promise<Object>} 测试结果
     */
    /**
     * 针对新建实例参数的连接测试。
     */
	    async testNewConnection(connectionParams, options = {}) {
	        try {
	            const result = await this.connectionService.testNewConnection(connectionParams);

            if (options.onSuccess && result.success) {
                options.onSuccess(result);
            } else if (options.onError && !result.success) {
                options.onError(result);
            }

	            return result;
	        } catch (error) {
	            const response = error && typeof error === 'object' ? error.response : null;
	            const extra = response && typeof response === 'object' ? response.extra : null;
	            const connectionErrorId =
	                extra && typeof extra === 'object' && typeof extra.connection_error_id === 'string'
	                    ? extra.connection_error_id
	                    : null;
	            const message =
	                response && typeof response === 'object' && typeof response.message === 'string'
	                    ? response.message
	                    : error && typeof error === 'object' && typeof error.message === 'string'
	                        ? error.message
	                        : '连接测试失败';
	            const errorResult = {
	                success: false,
	                message,
	                error: message,
	                error_id: connectionErrorId,
	            };

	            if (options.onError) {
	                options.onError(errorResult);
	            }

            return errorResult;
        }
    }

    /**
     * 验证连接参数
     * @param {Object} params - 连接参数
     * @returns {Promise<Object>} 验证结果
     */
    /**
     * 校验连接参数合法性。
     */
    async validateConnectionParams(params) {
        try {
            return await this.connectionService.validateConnectionParams(params);
        } catch (error) {
            return {
                success: false,
                error: `验证失败: ${error.message}`
            };
        }
    }

    /**
     * 批量测试连接
     * @param {Array<number>} instanceIds - 实例ID列表
     * @param {Object} options - 选项
     * @returns {Promise<Object>} 批量测试结果
     */
    /**
     * 批量连接测试。
     */
    async batchTestConnections(instanceIds, options = {}) {
        try {
            const result = await this.connectionService.batchTestConnections(instanceIds);

            if (options.onProgress) {
                options.onProgress(result);
            }

            return result;
        } catch (error) {
            const errorResult = {
                success: false,
                error: `批量测试失败: ${error.message}`
            };

            if (options.onError) {
                options.onError(errorResult);
            }

            return errorResult;
        }
    }

    /**
     * 获取连接状态
     * @param {number} instanceId - 实例ID
     * @returns {Promise<Object>} 连接状态
     */
    /**
     * 查询实例当前连接状态。
     */
	    async getConnectionStatus(instanceId) {
	        try {
	            return await this.connectionService.getConnectionStatus(instanceId);

	        } catch (error) {
	            const message =
	                error && typeof error === 'object' && typeof error.message === 'string' ? error.message : '获取状态失败';
	            return {
	                success: false,
	                message,
	                error: message,
	            };
	        }
	    }

    /**
     * 显示连接测试结果
     * @param {Object} result - 测试结果
     * @param {string} containerId - 容器ID
     */
    /**
     * 在指定容器渲染测试结果提示。
     */
	    showTestResult(result, containerId = 'connection-test-result') {
	        if (!this.helpers) {
	            return;
	        }

        const container = this.helpers.selectOne(`#${containerId}`);
        if (!container.length) {
            return;
        }

	        const alertClass = result.success ? 'alert-success' : 'alert-danger';
	        const icon = result.success ? 'fa-check-circle' : 'fa-exclamation-circle';

	        let message = '';
	        if (result && typeof result === 'object') {
	            if (typeof result.message === 'string') {
	                message = result.message;
	            } else if (typeof result.error === 'string') {
	                message = result.error;
	            }
	        }

	        const containerNode = container.first();
	        if (!containerNode) {
	            return;
	        }
	        containerNode.innerHTML = '';

	        const wrapper = document.createElement('div');
	        wrapper.className = `alert ${alertClass} alert-dismissible fade show`;
	        wrapper.setAttribute('role', 'alert');

	        const iconEl = document.createElement('i');
	        iconEl.className = `fas ${icon} me-2`;

	        const titleEl = document.createElement('strong');
	        titleEl.textContent = result.success ? '连接成功' : '连接失败';

	        const messageEl = document.createElement('p');
	        messageEl.className = 'mb-0';
	        messageEl.textContent = message;

	        wrapper.appendChild(iconEl);
	        wrapper.appendChild(titleEl);
	        wrapper.appendChild(messageEl);

	        if (result && typeof result === 'object' && typeof result.version === 'string' && result.version) {
	            const versionEl = document.createElement('small');
	            versionEl.className = 'text-muted';
	            versionEl.textContent = `数据库版本: ${result.version}`;
	            wrapper.appendChild(versionEl);
	        }

	        if (!result.success && result && typeof result === 'object' && typeof result.error_id === 'string' && result.error_id) {
	            const errorIdEl = document.createElement('small');
	            errorIdEl.className = 'text-muted d-block mt-1';
	            errorIdEl.textContent = `错误ID: ${result.error_id}`;
	            wrapper.appendChild(errorIdEl);
	        }

	        const closeButton = document.createElement('button');
	        closeButton.type = 'button';
	        closeButton.className = 'btn-close';
	        closeButton.setAttribute('data-bs-dismiss', 'alert');
	        closeButton.setAttribute('aria-label', '关闭');
	        wrapper.appendChild(closeButton);

	        containerNode.appendChild(wrapper);
	    }

}

// 创建全局实例
window.connectionManager = new ConnectionManager();
