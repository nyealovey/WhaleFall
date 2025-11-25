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
        this.baseUrl = '/connections/api';
        this.csrfToken = this.getCSRFToken();
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
     * 获取CSRF令牌 - 使用全局函数。
     *
     * @return {string} CSRF 令牌
     */
    getCSRFToken() {
        return window.getCSRFToken();
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
            const errorResult = {
                success: false,
                error: `网络错误: ${error.message}`
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
            const errorResult = {
                success: false,
                error: `网络错误: ${error.message}`
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
            return {
                success: false,
                error: `获取状态失败: ${error.message}`
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
        
        container.html(`
            <div class="alert ${alertClass} alert-dismissible fade show" role="alert">
                <i class="fas ${icon} me-2"></i>
                <strong>${result.success ? '连接成功' : '连接失败'}</strong>
                <p class="mb-0">${result.message || result.error}</p>
                ${result.version ? `<small class="text-muted">数据库版本: ${result.version}</small>` : ''}
                <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
            </div>
        `);
    }

    // showBatchTestProgress 已废弃，保留空实现兼容老代码
    showBatchTestProgress() {}
}

// 创建全局实例
window.connectionManager = new ConnectionManager();

// 导出类（如果使用模块系统）
if (typeof module !== 'undefined' && module.exports) {
    module.exports = ConnectionManager;
}
