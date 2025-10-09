/**
 * 权限按钮组件
 * 提供统一的权限查看按钮创建功能
 */

/**
 * 创建权限查看按钮
 * @param {number} accountId - 账户ID
 * @param {Object} options - 选项
 * @param {string} options.buttonClass - 按钮CSS类，默认为 'btn btn-outline-primary btn-sm'
 * @param {string} options.icon - 图标类，默认为 'fas fa-eye'
 * @param {string} options.text - 按钮文本，默认为 '权限'
 * @param {string} options.title - 按钮标题，默认为 '查看权限'
 * @param {string} options.apiUrl - API URL，默认为 `/account/api/${accountId}/permissions`
 * @param {Object} options.attributes - 额外的HTML属性
 * @returns {HTMLElement} 按钮元素
 */
function createPermissionButton(accountId, options = {}) {
    const {
        buttonClass = 'btn btn-outline-primary btn-sm',
        icon = 'fas fa-eye',
        text = '权限',
        title = '查看权限',
        apiUrl = `/account/api/${accountId}/permissions`,
        attributes = {}
    } = options;
    
    // 创建按钮元素
    const button = document.createElement('a');
    button.href = 'javascript:void(0)';
    button.className = buttonClass;
    button.title = title;
    button.setAttribute('data-account-id', accountId);
    
    // 设置额外的HTML属性
    Object.entries(attributes).forEach(([key, value]) => {
        button.setAttribute(key, value);
    });
    
    // 设置按钮内容
    button.innerHTML = `<i class="${icon} me-1"></i>${text}`;
    
    // 绑定点击事件
    button.addEventListener('click', function(event) {
        event.preventDefault();
        viewAccountPermissions(accountId, { apiUrl });
    });
    
    return button;
}

/**
 * 创建权限查看按钮并插入到指定容器
 * @param {string|HTMLElement} container - 容器选择器或元素
 * @param {number} accountId - 账户ID
 * @param {Object} options - 选项
 * @returns {HTMLElement} 按钮元素
 */
function createPermissionButtonInContainer(container, accountId, options = {}) {
    const containerElement = typeof container === 'string' ? 
        document.querySelector(container) : container;
    
    if (!containerElement) {
        console.error('容器元素未找到:', container);
        return null;
    }
    
    const button = createPermissionButton(accountId, options);
    containerElement.appendChild(button);
    
    return button;
}

/**
 * 批量创建权限查看按钮
 * @param {Array} accounts - 账户数组，每个元素包含 {id, ...} 属性
 * @param {Object} options - 选项
 * @param {string} options.containerSelector - 容器选择器
 * @param {string} options.buttonClass - 按钮CSS类
 * @param {string} options.icon - 图标类
 * @param {string} options.text - 按钮文本
 * @param {string} options.title - 按钮标题
 * @returns {Array} 按钮元素数组
 */
function createPermissionButtons(accounts, options = {}) {
    const {
        containerSelector,
        buttonClass = 'btn btn-outline-primary btn-sm',
        icon = 'fas fa-eye',
        text = '权限',
        title = '查看权限'
    } = options;
    
    const buttons = [];
    
    accounts.forEach(account => {
        const buttonOptions = {
            ...options,
            buttonClass,
            icon,
            text,
            title: title.replace('{username}', account.username || account.id)
        };
        
        const button = createPermissionButton(account.id, buttonOptions);
        buttons.push(button);
        
        // 如果指定了容器选择器，则插入到容器中
        if (containerSelector) {
            const container = document.querySelector(containerSelector);
            if (container) {
                container.appendChild(button);
            }
        }
    });
    
    return buttons;
}

/**
 * 更新权限按钮的API URL
 * @param {HTMLElement} button - 按钮元素
 * @param {string} apiUrl - 新的API URL
 */
function updatePermissionButtonApiUrl(button, apiUrl) {
    if (button && button.hasAttribute('data-account-id')) {
        const accountId = button.getAttribute('data-account-id');
        
        // 移除旧的事件监听器
        const newButton = button.cloneNode(true);
        button.parentNode.replaceChild(newButton, button);
        
        // 添加新的事件监听器
        newButton.addEventListener('click', function(event) {
            event.preventDefault();
            viewAccountPermissions(accountId, { apiUrl });
        });
    }
}

// 导出到全局作用域
window.createPermissionButton = createPermissionButton;
window.createPermissionButtonInContainer = createPermissionButtonInContainer;
window.createPermissionButtons = createPermissionButtons;
window.updatePermissionButtonApiUrl = updatePermissionButtonApiUrl;
