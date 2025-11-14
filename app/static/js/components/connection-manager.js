/**
 * 连接管理组件
 * 统一的数据库连接测试和管理功能
 */

class ConnectionManager {
    constructor() {
        this.baseUrl = '/connections/api';
        this.csrfToken = this.getCSRFToken();
        this.helpers = window.DOMHelpers;
        if (!this.helpers) {
            console.error('DOMHelpers 未初始化，连接管理组件无法渲染提示');
        }
    }

    /**
     * 获取CSRF令牌 - 使用全局函数
     */
    getCSRFToken() {
        return window.getCSRFToken();
    }

    /**
     * 测试现有实例连接
     * @param {number} instanceId - 实例ID
     * @param {Object} options - 选项
     * @returns {Promise<Object>} 测试结果
     */
    async testInstanceConnection(instanceId, options = {}) {
        try {
            const result = await httpU.post(`${this.baseUrl}/test`, {
                instance_id: instanceId,
                ...options
            });
            
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
    async testNewConnection(connectionParams, options = {}) {
        try {
            const result = await httpU.post(`${this.baseUrl}/test`, connectionParams);
            
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
    async validateConnectionParams(params) {
        try {
            return await httpU.post(`${this.baseUrl}/validate-params`, params);
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
    async batchTestConnections(instanceIds, options = {}) {
        try {
            const result = await httpU.post(`${this.baseUrl}/batch-test`, {
                instance_ids: instanceIds
            });
            
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
    async getConnectionStatus(instanceId) {
        try {
            return await httpU.get(`${this.baseUrl}/status/${instanceId}`);

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
