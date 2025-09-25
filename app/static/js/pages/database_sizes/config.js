/**
 * 数据库大小监控 - 配置管理页面脚本
 * 提供配置管理、状态监控和快速操作功能
 */

class DatabaseSizeConfigManager {
    constructor() {
        this.config = {};
        this.status = {};
        this.stats = {};
        this.isLoading = false;
        this.init();
    }

    /**
     * 初始化配置管理页面
     */
    init() {
        console.log('数据库大小监控配置管理页面：开始初始化...');
        
        this.bindEvents();
        this.loadConfig();
        this.loadStatus();
        this.loadStats();
        
        console.log('数据库大小监控配置管理页面：初始化完成！');
    }

    /**
     * 绑定事件监听器
     */
    bindEvents() {
        // 刷新配置按钮
        document.getElementById('refreshConfig')?.addEventListener('click', () => {
            this.refreshAll();
        });

        // 保存配置按钮
        document.getElementById('saveConfig')?.addEventListener('click', () => {
            this.saveConfig();
        });

        // 快速操作按钮
        document.getElementById('testConnection')?.addEventListener('click', () => {
            this.testConnection();
        });

        document.getElementById('manualCollect')?.addEventListener('click', () => {
            this.manualCollect();
        });

        document.getElementById('manualAggregate')?.addEventListener('click', () => {
            this.manualAggregate();
        });

        document.getElementById('cleanupPartitions')?.addEventListener('click', () => {
            this.cleanupPartitions();
        });

        // 表单变化监听
        const form = document.getElementById('configForm');
        if (form) {
            form.addEventListener('change', () => {
                this.markFormAsChanged();
            });
        }

        // 确认操作模态框
        document.getElementById('confirmAction')?.addEventListener('click', () => {
            this.executeConfirmedAction();
        });
    }

    /**
     * 加载配置数据
     */
    async loadConfig() {
        try {
            this.showLoading('加载配置中...');
            
            const response = await fetch('/api/database_sizes/config', {
                method: 'GET',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCSRFToken()
                }
            });

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }

            const data = await response.json();
            this.config = data.config || {};
            this.populateConfigForm();
            
            console.log('配置加载成功:', this.config);
            
        } catch (error) {
            console.error('加载配置失败:', error);
            this.showError('加载配置失败: ' + error.message);
        } finally {
            this.hideLoading();
        }
    }

    /**
     * 加载系统状态
     */
    async loadStatus() {
        try {
            const response = await fetch('/api/database_sizes/status', {
                method: 'GET',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCSRFToken()
                }
            });

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }

            const data = await response.json();
            this.status = data.status || {};
            this.updateStatusDisplay();
            
            console.log('状态加载成功:', this.status);
            
        } catch (error) {
            console.error('加载状态失败:', error);
            this.showError('加载状态失败: ' + error.message);
        }
    }

    /**
     * 加载统计信息
     */
    async loadStats() {
        try {
            const response = await fetch('/api/database_sizes/stats', {
                method: 'GET',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCSRFToken()
                }
            });

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }

            const data = await response.json();
            this.stats = data.stats || {};
            this.updateStatsDisplay();
            
            console.log('统计信息加载成功:', this.stats);
            
        } catch (error) {
            console.error('加载统计信息失败:', error);
            this.showError('加载统计信息失败: ' + error.message);
        }
    }

    /**
     * 填充配置表单
     */
    populateConfigForm() {
        const config = this.config;
        
        // 数据采集配置
        document.getElementById('collectEnabled').checked = config.collect_enabled !== false;
        document.getElementById('collectHour').value = config.collect_hour || 3;
        document.getElementById('collectTimeout').value = config.collect_timeout || 300;
        document.getElementById('collectBatchSize').value = config.collect_batch_size || 10;

        // 统计聚合配置
        document.getElementById('aggregationEnabled').checked = config.aggregation_enabled !== false;
        document.getElementById('aggregationHour').value = config.aggregation_hour || 5;

        // 分区管理配置
        document.getElementById('partitionCleanupEnabled').checked = config.partition_cleanup_enabled !== false;
        document.getElementById('partitionCleanupHour').value = config.partition_cleanup_hour || 4;
        document.getElementById('retentionDays').value = config.retention_days || 365;
        document.getElementById('retentionMonths').value = config.retention_months || 12;

        // 性能配置
        document.getElementById('collectTimeoutPerInstance').value = config.collect_timeout_per_instance || 30;
        document.getElementById('retryCount').value = config.retry_count || 3;
    }

    /**
     * 更新状态显示
     */
    updateStatusDisplay() {
        const status = this.status;
        
        // 更新状态徽章
        this.updateStatusBadge('collectStatus', status.collect_status || 'unknown');
        this.updateStatusBadge('aggregationStatus', status.aggregation_status || 'unknown');
        this.updateStatusBadge('partitionStatus', status.partition_status || 'unknown');
        
        // 更新最后执行时间
        document.getElementById('lastCollectTime').textContent = 
            status.last_collect_time ? this.formatDateTime(status.last_collect_time) : '-';
        document.getElementById('lastAggregationTime').textContent = 
            status.last_aggregation_time ? this.formatDateTime(status.last_aggregation_time) : '-';
    }

    /**
     * 更新统计信息显示
     */
    updateStatsDisplay() {
        const stats = this.stats;
        
        document.getElementById('totalInstances').textContent = stats.total_instances || 0;
        document.getElementById('totalDatabases').textContent = stats.total_databases || 0;
        document.getElementById('totalStorageSize').textContent = this.formatSize(stats.total_storage_size || 0);
        document.getElementById('partitionCount').textContent = stats.partition_count || 0;
    }

    /**
     * 更新状态徽章
     */
    updateStatusBadge(elementId, status) {
        const element = document.getElementById(elementId);
        if (!element) return;

        element.className = 'badge';
        
        switch (status) {
            case 'running':
                element.classList.add('bg-success');
                element.textContent = '运行中';
                break;
            case 'stopped':
                element.classList.add('bg-danger');
                element.textContent = '已停止';
                break;
            case 'error':
                element.classList.add('bg-danger');
                element.textContent = '错误';
                break;
            case 'warning':
                element.classList.add('bg-warning');
                element.textContent = '警告';
                break;
            default:
                element.classList.add('bg-secondary');
                element.textContent = '未知';
        }
    }

    /**
     * 保存配置
     */
    async saveConfig() {
        try {
            this.showLoading('保存配置中...');
            
            const config = this.collectConfigFromForm();
            
            const response = await fetch('/api/database_sizes/config', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCSRFToken()
                },
                body: JSON.stringify({ config })
            });

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }

            const data = await response.json();
            
            if (data.success) {
                this.showSuccess('配置保存成功！');
                this.markFormAsSaved();
            } else {
                throw new Error(data.message || '保存失败');
            }
            
        } catch (error) {
            console.error('保存配置失败:', error);
            this.showError('保存配置失败: ' + error.message);
        } finally {
            this.hideLoading();
        }
    }

    /**
     * 从表单收集配置
     */
    collectConfigFromForm() {
        return {
            collect_enabled: document.getElementById('collectEnabled').checked,
            collect_hour: parseInt(document.getElementById('collectHour').value),
            collect_timeout: parseInt(document.getElementById('collectTimeout').value),
            collect_batch_size: parseInt(document.getElementById('collectBatchSize').value),
            aggregation_enabled: document.getElementById('aggregationEnabled').checked,
            aggregation_hour: parseInt(document.getElementById('aggregationHour').value),
            partition_cleanup_enabled: document.getElementById('partitionCleanupEnabled').checked,
            partition_cleanup_hour: parseInt(document.getElementById('partitionCleanupHour').value),
            retention_days: parseInt(document.getElementById('retentionDays').value),
            retention_months: parseInt(document.getElementById('retentionMonths').value),
            collect_timeout_per_instance: parseInt(document.getElementById('collectTimeoutPerInstance').value),
            retry_count: parseInt(document.getElementById('retryCount').value)
        };
    }

    /**
     * 测试连接
     */
    async testConnection() {
        try {
            this.showProgressModal('测试连接中...', '正在测试数据库连接，请稍候...');
            
            const response = await fetch('/api/database_sizes/test_connection', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCSRFToken()
                }
            });

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }

            const data = await response.json();
            
            this.hideProgressModal();
            
            if (data.success) {
                this.showSuccess('连接测试成功！');
            } else {
                this.showError('连接测试失败: ' + (data.message || '未知错误'));
            }
            
        } catch (error) {
            console.error('测试连接失败:', error);
            this.hideProgressModal();
            this.showError('测试连接失败: ' + error.message);
        }
    }

    /**
     * 手动采集
     */
    async manualCollect() {
        this.showConfirmModal(
            '确认手动采集',
            '确定要立即执行数据库大小采集吗？这可能需要几分钟时间。',
            () => this.executeManualCollect()
        );
    }

    /**
     * 执行手动采集
     */
    async executeManualCollect() {
        try {
            this.showProgressModal('执行手动采集...', '正在采集数据库大小数据，请稍候...');
            
            const response = await fetch('/api/database_sizes/manual_collect', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCSRFToken()
                }
            });

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }

            const data = await response.json();
            
            this.hideProgressModal();
            
            if (data.success) {
                this.showSuccess(`手动采集完成！处理了 ${data.processed_instances || 0} 个实例`);
                this.refreshAll();
            } else {
                this.showError('手动采集失败: ' + (data.message || '未知错误'));
            }
            
        } catch (error) {
            console.error('手动采集失败:', error);
            this.hideProgressModal();
            this.showError('手动采集失败: ' + error.message);
        }
    }

    /**
     * 手动聚合
     */
    async manualAggregate() {
        this.showConfirmModal(
            '确认手动聚合',
            '确定要立即执行统计聚合计算吗？这可能需要几分钟时间。',
            () => this.executeManualAggregate()
        );
    }

    /**
     * 执行手动聚合
     */
    async executeManualAggregate() {
        try {
            this.showProgressModal('执行手动聚合...', '正在计算统计聚合数据，请稍候...');
            
            const response = await fetch('/api/database_sizes/manual_aggregate', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCSRFToken()
                }
            });

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }

            const data = await response.json();
            
            this.hideProgressModal();
            
            if (data.success) {
                this.showSuccess(`手动聚合完成！处理了 ${data.processed_instances || 0} 个实例`);
                this.refreshAll();
            } else {
                this.showError('手动聚合失败: ' + (data.message || '未知错误'));
            }
            
        } catch (error) {
            console.error('手动聚合失败:', error);
            this.hideProgressModal();
            this.showError('手动聚合失败: ' + error.message);
        }
    }

    /**
     * 清理分区
     */
    async cleanupPartitions() {
        this.showConfirmModal(
            '确认清理分区',
            '确定要清理旧的分区数据吗？此操作不可逆，请谨慎操作。',
            () => this.executeCleanupPartitions()
        );
    }

    /**
     * 执行清理分区
     */
    async executeCleanupPartitions() {
        try {
            this.showProgressModal('清理分区中...', '正在清理旧的分区数据，请稍候...');
            
            const response = await fetch('/api/database_sizes/cleanup_partitions', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCSRFToken()
                }
            });

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }

            const data = await response.json();
            
            this.hideProgressModal();
            
            if (data.success) {
                this.showSuccess(`分区清理完成！清理了 ${data.cleaned_partitions || 0} 个分区`);
                this.refreshAll();
            } else {
                this.showError('分区清理失败: ' + (data.message || '未知错误'));
            }
            
        } catch (error) {
            console.error('分区清理失败:', error);
            this.hideProgressModal();
            this.showError('分区清理失败: ' + error.message);
        }
    }

    /**
     * 刷新所有数据
     */
    async refreshAll() {
        await Promise.all([
            this.loadConfig(),
            this.loadStatus(),
            this.loadStats()
        ]);
    }

    /**
     * 标记表单为已更改
     */
    markFormAsChanged() {
        const saveBtn = document.getElementById('saveConfig');
        if (saveBtn) {
            saveBtn.classList.add('btn-warning');
            saveBtn.innerHTML = '<i class="fas fa-save me-1"></i>保存配置 (已修改)';
        }
    }

    /**
     * 标记表单为已保存
     */
    markFormAsSaved() {
        const saveBtn = document.getElementById('saveConfig');
        if (saveBtn) {
            saveBtn.classList.remove('btn-warning');
            saveBtn.classList.add('btn-success');
            saveBtn.innerHTML = '<i class="fas fa-check me-1"></i>已保存';
            
            setTimeout(() => {
                saveBtn.classList.remove('btn-success');
                saveBtn.innerHTML = '<i class="fas fa-save me-1"></i>保存配置';
            }, 2000);
        }
    }

    /**
     * 显示确认模态框
     */
    showConfirmModal(title, message, callback) {
        document.getElementById('confirmMessage').textContent = message;
        this.confirmCallback = callback;
        
        const modal = new bootstrap.Modal(document.getElementById('confirmModal'));
        modal.show();
    }

    /**
     * 执行确认的操作
     */
    executeConfirmedAction() {
        if (this.confirmCallback) {
            this.confirmCallback();
        }
        
        const modal = bootstrap.Modal.getInstance(document.getElementById('confirmModal'));
        modal.hide();
    }

    /**
     * 显示进度模态框
     */
    showProgressModal(title, message) {
        document.getElementById('progressMessage').textContent = message;
        
        const modal = new bootstrap.Modal(document.getElementById('progressModal'));
        modal.show();
        
        // 模拟进度条
        this.simulateProgress();
    }

    /**
     * 隐藏进度模态框
     */
    hideProgressModal() {
        const modal = bootstrap.Modal.getInstance(document.getElementById('progressModal'));
        if (modal) {
            modal.hide();
        }
    }

    /**
     * 模拟进度条
     */
    simulateProgress() {
        const progressBar = document.querySelector('#progressModal .progress-bar');
        let progress = 0;
        
        const interval = setInterval(() => {
            progress += Math.random() * 10;
            if (progress > 100) progress = 100;
            
            progressBar.style.width = progress + '%';
            
            if (progress >= 100) {
                clearInterval(interval);
            }
        }, 200);
    }

    /**
     * 显示加载状态
     */
    showLoading(message = '加载中...') {
        this.isLoading = true;
        // 可以在这里添加全局加载指示器
    }

    /**
     * 隐藏加载状态
     */
    hideLoading() {
        this.isLoading = false;
        // 可以在这里移除全局加载指示器
    }

    /**
     * 显示成功消息
     */
    showSuccess(message) {
        this.showAlert(message, 'success');
    }

    /**
     * 显示错误消息
     */
    showError(message) {
        this.showAlert(message, 'danger');
    }

    /**
     * 显示警告消息
     */
    showWarning(message) {
        this.showAlert(message, 'warning');
    }

    /**
     * 显示信息消息
     */
    showInfo(message) {
        this.showAlert(message, 'info');
    }

    /**
     * 显示警告框
     */
    showAlert(message, type) {
        // 创建警告框元素
        const alertDiv = document.createElement('div');
        alertDiv.className = `alert alert-${type} alert-dismissible fade show`;
        alertDiv.innerHTML = `
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;
        
        // 插入到页面顶部
        const container = document.querySelector('.container-fluid');
        if (container) {
            container.insertBefore(alertDiv, container.firstChild);
            
            // 自动移除
            setTimeout(() => {
                if (alertDiv.parentNode) {
                    alertDiv.remove();
                }
            }, 5000);
        }
    }

    /**
     * 格式化日期时间
     */
    formatDateTime(dateString) {
        if (!dateString) return '-';
        
        try {
            const date = new Date(dateString);
            return date.toLocaleString('zh-CN', {
                year: 'numeric',
                month: '2-digit',
                day: '2-digit',
                hour: '2-digit',
                minute: '2-digit',
                second: '2-digit'
            });
        } catch (error) {
            return dateString;
        }
    }

    /**
     * 格式化文件大小
     */
    formatSize(bytes) {
        if (bytes === 0) return '0 B';
        
        const k = 1024;
        const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }

    /**
     * 获取CSRF令牌
     */
    getCSRFToken() {
        const token = document.querySelector('meta[name="csrf-token"]');
        return token ? token.getAttribute('content') : '';
    }
}

// 页面加载完成后初始化
document.addEventListener('DOMContentLoaded', function() {
    // 防止重复初始化
    if (window.databaseSizeConfigManager) {
        return;
    }
    
    window.databaseSizeConfigManager = new DatabaseSizeConfigManager();
});

// 导出类供其他模块使用
if (typeof module !== 'undefined' && module.exports) {
    module.exports = DatabaseSizeConfigManager;
}
