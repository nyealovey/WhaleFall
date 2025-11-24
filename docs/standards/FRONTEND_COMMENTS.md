# 鲸落项目前端注释规范

> 最后更新：2025-11-21  
> 本文档定义前端 JavaScript 代码的注释标准，基于项目实际代码风格。

## 1. 文件头部注释

### 1.1 模块文件

每个 JavaScript 模块文件应包含文件头部注释，说明模块用途和依赖：

```javascript
/**
 * 聚合数据图表管理器
 * 基于 Chart.js 4.4.0 和 jQuery 3.7.1
 */
```

### 1.2 IIFE 模块

使用 IIFE 包装的模块：

```javascript
(function (global) {
    'use strict';

    /**
     * DOM 操作辅助工具
     * 封装 Umbrella JS，提供统一的 DOM 操作接口
     */
    
    // 模块代码...
    
})(window);
```

## 2. 函数注释

### 2.1 公共函数

公共函数必须包含 JSDoc 风格的注释：

```javascript
/**
 * 将输入转换为 umbrella 对象，支持选择器、Element 与现有实例
 * 
 * @param {string|Element|Object} target - 目标元素或选择器
 * @param {Element|Object} [context] - 可选的上下文
 * @returns {Object} umbrella 对象
 */
function toUmbrella(target, context) {
    // 实现代码...
}
```

### 2.2 简单函数

简单功能的函数可使用单行注释：

```javascript
/**
 * 便捷方法：返回 umbrella 选择结果
 */
function select(selector, context) {
    return toUmbrella(selector, context);
}
```

### 2.3 内部函数

内部辅助函数使用简洁注释：

```javascript
// 构建查询参数
function buildQueryParams(values) {
    const params = new URLSearchParams();
    // 实现代码...
    return params;
}
```

## 3. 类注释

### 3.1 类定义

类必须包含用途说明：

```javascript
/**
 * 图表管理器
 * 
 * 负责图表的创建、更新和销毁，支持多种图表类型
 */
class ChartManager {
    constructor() {
        // 初始化代码...
    }
}
```

### 3.2 类方法

公共方法需要注释：

```javascript
class ChartManager {
    /**
     * 创建图例说明
     * 
     * 根据当前统计周期生成对应的图例 HTML
     */
    createLegend() {
        // 实现代码...
    }
    
    /**
     * 加载图表数据
     * 
     * @param {string} periodType - 周期类型 (daily/weekly/monthly)
     * @returns {Promise} 数据加载 Promise
     */
    async loadChartData(periodType) {
        // 实现代码...
    }
}
```

### 3.3 私有方法

私有方法使用简洁注释：

```javascript
class ChartManager {
    // 绑定事件监听器
    _bindEvents() {
        // 实现代码...
    }
}
```

## 4. 变量注释

### 4.1 重要变量

重要的变量需要注释说明：

```javascript
// 图表颜色配置
const CHART_COLORS = {
    primary: 'rgba(54, 162, 235, 0.7)',
    success: 'rgba(75, 192, 192, 0.7)',
    danger: 'rgba(255, 99, 132, 0.7)'
};

// 为不同类型的聚合数据定义颜色和样式
this.dataTypeStyles = {
    '数据库聚合': { color: '#FF6384', borderDash: [], pointStyle: 'circle' },
    '实例聚合': { color: '#36A2EB', borderDash: [5, 5], pointStyle: 'rect' }
};
```

### 4.2 行内注释

复杂逻辑使用行内注释：

```javascript
const params = new URLSearchParams();
Object.entries(values || {}).forEach(([key, value]) => {
    // 跳过空值
    if (value === undefined || value === null) {
        return;
    }
    
    // 处理数组类型
    if (Array.isArray(value)) {
        value.forEach((item) => {
            if (item !== undefined && item !== null) {
                params.append(key, item);
            }
        });
    } else {
        params.append(key, value);
    }
});
```

## 5. 常量和配置

### 5.1 常量定义

常量需要注释说明用途：

```javascript
// 事件名称常量
const EVENT_NAMES = {
    loading: 'partitions:loading',
    infoUpdated: 'partitions:infoUpdated',
    metricsUpdated: 'partitions:metricsUpdated'
};

// 默认配置
const DEFAULT_CONFIG = {
    timeout: 30000,      // 请求超时时间（毫秒）
    retryCount: 3,       // 重试次数
    cacheEnabled: true   // 是否启用缓存
};
```

## 6. 事件处理

### 6.1 事件监听器

事件监听器需要注释：

```javascript
// 周期类型切换事件
const periodInputs = document.querySelectorAll('input[name="periodType"]');
periodInputs.forEach((input) => {
    input.addEventListener('change', (event) => {
        this.currentPeriodType = event.target.value;
        this.updateChartInfo();
        this.loadChartData();
    });
});

// 刷新按钮点击事件
const refreshButton = document.getElementById('refreshAggregations');
if (refreshButton) {
    refreshButton.addEventListener('click', () => this.refreshAllData());
}
```

## 7. 异步操作

### 7.1 Promise 和 async/await

异步操作需要注释说明：

```javascript
/**
 * 加载图表数据
 * 
 * 从服务器获取图表数据并渲染
 * 
 * @returns {Promise<void>}
 */
async loadChartData() {
    this.showChartLoading(true);
    
    try {
        // 构建查询参数
        const params = buildChartQueryParams({
            periodType: this.currentPeriodType,
            days: 7
        });
        
        // 获取数据
        const response = await partitionService.fetchCoreMetrics(params);
        
        // 渲染图表
        if (response.success) {
            this.renderChart(response.data);
        }
    } catch (error) {
        console.error('加载图表数据失败:', error);
        this.showError('加载数据失败');
    } finally {
        this.showChartLoading(false);
    }
}
```

## 8. 错误处理

### 8.1 try-catch 块

错误处理需要注释：

```javascript
try {
    // 尝试初始化服务
    this.service = new PartitionService();
} catch (error) {
    // 初始化失败，使用降级方案
    console.error('服务初始化失败:', error);
    this.service = null;
}
```

## 9. TODO 和 FIXME

### 9.1 待办事项

使用标准标记：

```javascript
// TODO: 添加数据缓存功能
// FIXME: 修复图表在移动端的显示问题
// HACK: 临时解决方案，等待上游库修复
// NOTE: 这里的逻辑比较复杂，需要仔细维护
```

## 10. 注释风格规范

### 10.1 基本规则

- **使用中文注释**：项目统一使用中文注释
- **简洁明了**：注释应简洁，避免冗余
- **及时更新**：代码变更时同步更新注释
- **避免废话**：不要注释显而易见的代码

### 10.2 正确示例

```javascript
// 正确：说明业务逻辑
// 根据用户权限过滤可见的菜单项
const visibleMenus = menus.filter(menu => hasPermission(menu.permission));

// 正确：说明复杂算法
// 使用二分查找提高性能
const index = binarySearch(sortedArray, target);
```

### 10.3 错误示例

```javascript
// 错误：注释显而易见的代码
// 定义变量 i
let i = 0;

// 错误：注释与代码不符
// 获取用户列表
const products = getProducts();

// 错误：过时的注释
// 使用 jQuery 实现
const element = document.querySelector('#myElement'); // 实际已改用原生 JS
```

## 11. JSDoc 标签

### 11.1 常用标签

```javascript
/**
 * 用户服务类
 * 
 * @class UserService
 * @description 提供用户相关的业务逻辑
 */
class UserService {
    /**
     * 获取用户列表
     * 
     * @param {Object} options - 查询选项
     * @param {number} [options.page=1] - 页码
     * @param {number} [options.limit=10] - 每页数量
     * @param {string} [options.search] - 搜索关键词
     * @returns {Promise<Array>} 用户列表
     * @throws {Error} 当请求失败时抛出错误
     * 
     * @example
     * const users = await userService.getUsers({ page: 1, limit: 20 });
     */
    async getUsers(options = {}) {
        // 实现代码...
    }
}
```

### 11.2 类型定义

```javascript
/**
 * @typedef {Object} ChartConfig
 * @property {string} type - 图表类型
 * @property {Array} data - 图表数据
 * @property {Object} options - 图表选项
 */

/**
 * 创建图表
 * 
 * @param {ChartConfig} config - 图表配置
 * @returns {Chart} Chart.js 实例
 */
function createChart(config) {
    // 实现代码...
}
```

## 12. 模块导出

### 12.1 导出注释

模块导出需要注释：

```javascript
// 导出公共 API
window.DOMHelpers = {
    select,      // 选择元素
    selectOne,   // 选择单个元素
    from,        // 包装元素
    ready,       // DOM 就绪
    text,        // 文本操作
    html,        // HTML 操作
    on,          // 事件绑定
    off          // 事件解绑
};

// 导出页面挂载函数
window.AggregationsChartPage = {
    mount: mountAggregationsChart
};
```

## 13. 代码审查清单

提交前端代码前，确保：

- [ ] 所有公共函数都有注释
- [ ] 类和方法都有用途说明
- [ ] 复杂逻辑有行内注释
- [ ] 使用中文注释
- [ ] 注释与代码保持同步
- [ ] 没有注释显而易见的代码
- [ ] TODO/FIXME 标记清晰
- [ ] JSDoc 标签使用正确

## 14. 参考示例

### 14.1 完整示例

```javascript
/**
 * 用户管理页面
 * 基于 Bootstrap 5 和 Umbrella JS
 */

(function (global) {
    'use strict';

    // 依赖检查
    if (!global.DOMHelpers) {
        console.error('DOMHelpers 未加载');
        return;
    }

    const { selectOne, ready } = global.DOMHelpers;
    const httpU = global.httpU;

    /**
     * 用户管理器
     * 
     * 负责用户列表的加载、创建、编辑和删除
     */
    class UserManager {
        constructor() {
            this.users = [];
            this.currentPage = 1;
            this.init();
        }

        /**
         * 初始化
         */
        init() {
            this.bindEvents();
            this.loadUsers();
        }

        /**
         * 绑定事件
         */
        bindEvents() {
            // 创建按钮点击事件
            selectOne('#createUserBtn').on('click', () => {
                this.openCreateModal();
            });

            // 搜索输入事件（防抖）
            selectOne('#searchInput').on('input', 
                this.debounce(() => this.handleSearch(), 300)
            );
        }

        /**
         * 加载用户列表
         * 
         * @param {number} [page=1] - 页码
         * @returns {Promise<void>}
         */
        async loadUsers(page = 1) {
            try {
                const response = await httpU.get('/api/users', {
                    params: { page, limit: 20 }
                });

                if (response.success) {
                    this.users = response.data.items;
                    this.renderUsers();
                }
            } catch (error) {
                console.error('加载用户失败:', error);
                this.showError('加载用户列表失败');
            }
        }

        /**
         * 防抖函数
         * 
         * @param {Function} func - 要防抖的函数
         * @param {number} wait - 等待时间（毫秒）
         * @returns {Function} 防抖后的函数
         */
        debounce(func, wait) {
            let timeout;
            return function(...args) {
                clearTimeout(timeout);
                timeout = setTimeout(() => func.apply(this, args), wait);
            };
        }
    }

    // 页面加载完成后初始化
    ready(() => {
        global.userManager = new UserManager();
    });

})(window);
```

---

**相关文档**:
- [CODING_STANDARDS.md](./CODING_STANDARDS.md) - 编码规范
- [FRONTEND_STYLE_GUIDE.md](./FRONTEND_STYLE_GUIDE.md) - 前端样式指南
- [TERMINOLOGY.md](./TERMINOLOGY.md) - 术语表
