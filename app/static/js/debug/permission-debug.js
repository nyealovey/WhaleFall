/**
 * 权限调试工具
 * 用于诊断权限按钮无法弹出的问题
 */

// 调试函数：检查权限相关函数是否已加载
function debugPermissionFunctions() {
    console.log('=== 权限函数调试 ===');
    
    // 检查关键函数是否存在
    const functions = [
        'viewAccountPermissions',
        'showPermissionsModal',
        'fetchAccountPermissions',
        'renderPermissionsByType'
    ];
    
    functions.forEach(funcName => {
        const exists = typeof window[funcName] === 'function';
        console.log(`${funcName}: ${exists ? '✅ 已加载' : '❌ 未找到'}`);
    });
    
    // 检查Bootstrap是否可用
    const bootstrapExists = typeof window.bootstrap !== 'undefined';
    console.log(`Bootstrap: ${bootstrapExists ? '✅ 已加载' : '❌ 未找到'}`);
    
    // 检查jQuery是否可用
    const jqueryExists = typeof window.$ !== 'undefined';
    console.log(`jQuery: ${jqueryExists ? '✅ 已加载' : '❌ 未找到'}`);
}

// 调试函数：测试权限按钮点击
function debugPermissionButtonClick(accountId) {
    console.log('=== 权限按钮调试 ===');
    console.log(`测试账户ID: ${accountId}`);
    
    try {
        // 检查viewAccountPermissions函数
        if (typeof window.viewAccountPermissions === 'function') {
            console.log('调用 viewAccountPermissions...');
            window.viewAccountPermissions(accountId);
        } else {
            console.error('viewAccountPermissions 函数不存在');
        }
    } catch (error) {
        console.error('调用 viewAccountPermissions 时出错:', error);
    }
}

// 调试函数：检查模态框元素
function debugModalElements() {
    console.log('=== 模态框元素调试 ===');
    
    const modal = document.getElementById('permissionsModal');
    console.log(`权限模态框: ${modal ? '✅ 找到' : '❌ 未找到'}`);
    
    if (modal) {
        const title = document.getElementById('permissionsModalTitle');
        const body = document.getElementById('permissionsModalBody');
        console.log(`模态框标题: ${title ? '✅ 找到' : '❌ 未找到'}`);
        console.log(`模态框内容: ${body ? '✅ 找到' : '❌ 未找到'}`);
    }
}

// 调试函数：检查CSRF token
function debugCSRFToken() {
    console.log('=== CSRF Token 调试 ===');
    
    const metaToken = document.querySelector('meta[name="csrf-token"]')?.getAttribute('content');
    const inputToken = document.querySelector('input[name="csrf_token"]')?.value;
    
    console.log(`Meta CSRF Token: ${metaToken ? '✅ 找到' : '❌ 未找到'}`);
    console.log(`Input CSRF Token: ${inputToken ? '✅ 找到' : '❌ 未找到'}`);
    
    return metaToken || inputToken;
}

// 调试函数：测试API调用
function debugAPICall(accountId) {
    console.log('=== API 调用调试 ===');
    
    const csrfToken = debugCSRFToken();
    const apiUrl = `/account/api/${accountId}/permissions`;
    
    console.log(`API URL: ${apiUrl}`);
    console.log(`CSRF Token: ${csrfToken ? '已获取' : '未获取'}`);
    
    fetch(apiUrl, {
        method: 'GET',
        headers: {
            'X-CSRFToken': csrfToken || '',
            'Content-Type': 'application/json'
        },
        credentials: 'same-origin'
    })
    .then(response => {
        console.log(`API 响应状态: ${response.status}`);
        return response.json();
    })
    .then(data => {
        console.log('API 响应数据:', data);
        if (data.success) {
            console.log('✅ API 调用成功');
        } else {
            console.error('❌ API 调用失败:', data.error);
        }
    })
    .catch(error => {
        console.error('❌ API 调用出错:', error);
    });
}

// 导出到全局作用域
window.debugPermissionFunctions = debugPermissionFunctions;
window.debugPermissionButtonClick = debugPermissionButtonClick;
window.debugModalElements = debugModalElements;
window.debugCSRFToken = debugCSRFToken;
window.debugAPICall = debugAPICall;

// 页面加载完成后自动运行调试
document.addEventListener('DOMContentLoaded', function() {
    console.log('权限调试工具已加载');
    console.log('使用方法:');
    console.log('1. debugPermissionFunctions() - 检查函数是否加载');
    console.log('2. debugModalElements() - 检查模态框元素');
    console.log('3. debugAPICall(账户ID) - 测试API调用');
    console.log('4. debugPermissionButtonClick(账户ID) - 测试按钮点击');
});
