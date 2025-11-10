/**
 * HTTP 客户端配置
 * 负责初始化 Axios 实例、注入 CSRF Token、统一处理响应错误。
 *
 * 旧文件名 `config.js` 改为 `http-client.js` 以凸显用途。
 */

if (typeof axios === "undefined") {
    console.error("Axios 未加载！请确保在 http-client.js 之前引入 axios.min.js");
} else {
    const http = axios.create({
        baseURL: "/",
        timeout: 120000,
        headers: {
            "Content-Type": "application/json",
            "X-Requested-With": "XMLHttpRequest",
        },
    });

    http.interceptors.request.use(
        (config) => {
            const csrfMeta = document.querySelector('meta[name="csrf-token"]');
            if (csrfMeta) {
                config.headers["X-CSRFToken"] = csrfMeta.content;
            }
            return config;
        },
        (error) => Promise.reject(error),
    );

    http.interceptors.response.use(
        (response) => response.data,
        (error) => {
            let message = "请求失败";
            if (error.response) {
                const status = error.response.status;
                const data = error.response.data;
                if (status === 401) {
                    message = "未授权，请重新登录";
                } else if (status === 403) {
                    message = "没有权限访问";
                } else if (status === 404) {
                    message = "请求的资源不存在";
                } else if (status >= 500) {
                    message = "服务器错误";
                } else if (data && data.message) {
                    message = data.message;
                }
            } else if (error.request) {
                message = "网络错误，请检查网络连接";
            } else {
                message = error.message || message;
            }
            console.error("HTTP Error:", message, error);
            return Promise.reject(new Error(message));
        },
    );

    window.http = http;

    window.confirmDelete = function (message) {
        return confirm(message || "确定要删除吗？此操作不可恢复！");
    };

    console.log("HTTP client 初始化完成（全局变量：http, confirmDelete）");
}
