/**
 * 前端库配置文件
 * 配置 Axios 实例和全局工具函数
 */

// 检查 axios 是否已加载
if (typeof axios === 'undefined') {
    console.error('Axios 未加载！请确保在 config.js 之前引入 axios.min.js');
} else {
    // 创建 Axios 实例（全局变量）
    var http = axios.create({
        baseURL: '/',
        timeout: 120000,
        headers: {
            'Content-Type': 'application/json',
            'X-Requested-With': 'XMLHttpRequest'
        }
    });

    // 请求拦截器 - 添加 CSRF Token
    http.interceptors.request.use(
        function(config) {
            // 从 meta 标签或 cookie 中获取 CSRF token
            var csrfToken = document.querySelector('meta[name="csrf-token"]');
            if (csrfToken) {
                config.headers['X-CSRFToken'] = csrfToken.content;
            }
            return config;
        },
        function(error) {
            return Promise.reject(error);
        }
    );

    // 响应拦截器 - 统一处理响应
    http.interceptors.response.use(
        function(response) {
            // 直接返回 data 部分
            return response.data;
        },
        function(error) {
            // 统一错误处理
            var errorMessage = '请求失败';

            if (error.response) {
                // 服务器返回错误状态码
                var status = error.response.status;
                var data = error.response.data;

                if (status === 401) {
                    errorMessage = '未授权，请重新登录';
                    // 可以在这里跳转到登录页
                    // window.location.href = '/login';
                } else if (status === 403) {
                    errorMessage = '没有权限访问';
                } else if (status === 404) {
                    errorMessage = '请求的资源不存在';
                } else if (status === 500) {
                    errorMessage = '服务器错误';
                } else if (data && data.message) {
                    errorMessage = data.message;
                }
            } else if (error.request) {
                // 请求已发送但没有收到响应
                errorMessage = '网络错误，请检查网络连接';
            } else {
                // 其他错误
                errorMessage = error.message || '未知错误';
            }

            console.error('HTTP Error:', errorMessage, error);
            return Promise.reject(new Error(errorMessage));
        }
    );

    // 全局确认删除函数
    window.confirmDelete = function(message) {
        message = message || '确定要删除吗？此操作不可恢复！';
        return confirm(message);
    };

    console.log('=================================');
    console.log('前端库配置加载完成');
    console.log('可用对象:');
    console.log('  - http (Axios 实例)');
    console.log('  - confirmDelete()');
    console.log('=================================');
}
