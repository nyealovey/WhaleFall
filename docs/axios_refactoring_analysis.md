# Axios 重构分析报告

## 概述

项目当前使用原生 `fetch` API 进行网络请求，共有 **21 个文件**使用了 fetch，总计 **82 处调用**。

## 一、使用 fetch 的文件清单

### 按类别分组

#### 1. 核心工具类（2 个文件，6 次调用）

| 文件 | 调用次数 | 优先级 | 说明 |
|------|---------|--------|------|
| `common/csrf-utils.js` | 4 | 🔴 高 | CSRF token 获取和封装 fetch 方法 |
| `common/permission-viewer.js` | 2 | 🟡 中 | 权限查看工具 |

#### 2. 可复用组件（4 个文件，13 次调用）

| 文件 | 调用次数 | 优先级 | 说明 |
|------|---------|--------|------|
| `components/connection-manager.js` | 5 | 🟡 中 | 连接管理器 |
| `components/tag_selector.js` | 2 | 🟢 低 | 标签选择器 |
| `components/unified_search.js` | 2 | 🟢 低 | 统一搜索组件 |

#### 3. 页面模块 - 认证相关（1 个文件，4 次调用）

| 文件 | 调用次数 | 优先级 | 说明 |
|------|---------|--------|------|
| `pages/auth/list.js` | 4 | 🟡 中 | 用户列表管理 |

#### 4. 页面模块 - 实例管理（3 个文件，14 次调用）

| 文件 | 调用次数 | 优先级 | 说明 |
|------|---------|--------|------|
| `pages/instances/list.js` | 4 | 🔴 高 | 实例列表 |
| `pages/instances/detail.js` | 4 | 🔴 高 | 实例详情 |
| `pages/instances/statistics.js` | 1 | 🟢 低 | 实例统计 |

#### 5. 页面模块 - 账户管理（2 个文件，6 次调用）

| 文件 | 调用次数 | 优先级 | 说明 |
|------|---------|--------|------|
| `pages/accounts/account_classification.js` | 5 | 🟡 中 | 账户分类管理（大文件） |
| `pages/accounts/list.js` | 1 | 🟡 中 | 账户列表 |

#### 6. 页面模块 - 凭据管理（1 个文件，2 次调用）

| 文件 | 调用次数 | 优先级 | 说明 |
|------|---------|--------|------|
| `pages/credentials/list.js` | 2 | 🟡 中 | 凭据列表 |

#### 7. 页面模块 - 标签管理（2 个文件，5 次调用）

| 文件 | 调用次数 | 优先级 | 说明 |
|------|---------|--------|------|
| `pages/tags/index.js` | 1 | 🟡 中 | 标签管理 |
| `pages/tags/batch_assign.js` | 4 | 🟢 低 | 批量分配标签（809行，大文件） |

#### 8. 页面模块 - 历史记录（2 个文件，8 次调用）

| 文件 | 调用次数 | 优先级 | 说明 |
|------|---------|--------|------|
| `pages/history/logs.js` | 4 | 🔴 高 | 日志中心 |
| `pages/history/sync_sessions.js` | 4 | 🔴 高 | 同步会话 |

#### 9. 页面模块 - 仪表板（1 个文件，1 次调用）

| 文件 | 调用次数 | 优先级 | 说明 |
|------|---------|--------|------|
| `pages/dashboard/overview.js` | 1 | 🟡 中 | 仪表板概览 |

#### 10. 页面模块 - 管理功能（2 个文件，4 次调用）

| 文件 | 调用次数 | 优先级 | 说明 |
|------|---------|--------|------|
| `pages/admin/partitions.js` | 3 | 🟡 中 | 分区管理 |
| `pages/admin/aggregations_chart.js` | 1 | 🟢 低 | 聚合图表（575行，大文件） |

#### 11. 页面模块 - 容量统计（2 个文件，13 次调用）

| 文件 | 调用次数 | 优先级 | 说明 |
|------|---------|--------|------|
| `pages/capacity_stats/database_aggregations.js` | 5 | 🟢 低 | 数据库容量聚合 |
| `pages/capacity_stats/instance_aggregations.js` | 5 | 🟢 低 | 实例容量聚合 |

---

## 二、重构优先级建议

### 🔴 第一优先级（核心功能，高频使用）

1. **common/csrf-utils.js** (4 次调用)
   - ⚠️ 最关键：封装了所有 fetch 请求
   - 建议：创建 Axios 实例，配置 CSRF 拦截器
   - 影响：修改后所有使用 `safeFetch` 的地方自动受益

2. **pages/instances/list.js** (4 次调用)
   - 实例列表是核心功能
   - 建议：第二个重构，验证 Axios 工作正常

3. **pages/instances/detail.js** (4 次调用)
   - 实例详情页面，功能复杂
   - 建议：第三个重构

4. **pages/history/logs.js** (4 次调用)
   - 日志中心，高频使用
   - 建议：第四个重构

5. **pages/history/sync_sessions.js** (4 次调用)
   - 同步会话管理
   - 建议：第五个重构

### 🟡 第二优先级（常用功能）

6. **pages/auth/list.js** (4 次调用)
7. **pages/accounts/list.js** (1 次调用)
8. **pages/credentials/list.js** (2 次调用)
9. **pages/tags/index.js** (1 次调用)
10. **pages/dashboard/overview.js** (1 次调用)
11. **pages/admin/partitions.js** (3 次调用)
12. **components/connection-manager.js** (5 次调用)
13. **common/permission-viewer.js** (2 次调用)

### 🟢 第三优先级（辅助功能或大文件）

14. **pages/accounts/account_classification.js** (5 次调用) - 大文件
15. **pages/tags/batch_assign.js** (4 次调用) - 大文件
16. **pages/admin/aggregations_chart.js** (1 次调用) - 大文件
17. **pages/capacity_stats/database_aggregations.js** (5 次调用)
18. **pages/capacity_stats/instance_aggregations.js** (5 次调用)
19. **pages/instances/statistics.js** (1 次调用)
20. **components/tag_selector.js** (2 次调用)
21. **components/unified_search.js** (2 次调用)

---

## 三、Axios 重构方案

### 阶段 0：准备工作

1. ✅ **Axios 已本地化**
   - 文件：`app/static/vendor/axios/axios.min.js`
   - 版本：1.7.7
   - 大小：33KB (gzipped: 13KB)

2. **创建 Axios 配置文件**
   ```javascript
   // app/static/js/common/axios-config.js
   
   // 创建 Axios 实例
   const http = axios.create({
       timeout: 30000,
       headers: {
           'Content-Type': 'application/json'
       }
   });
   
   // 请求拦截器 - 自动添加 CSRF Token
   http.interceptors.request.use(config => {
       const csrfToken = getCSRFToken();
       if (csrfToken) {
           config.headers['X-CSRFToken'] = csrfToken;
       }
       return config;
   });
   
   // 响应拦截器 - 统一错误处理
   http.interceptors.response.use(
       response => response.data,
       error => {
           console.error('Request failed:', error);
           if (error.response) {
               notify.error(error.response.data?.error || '请求失败');
           } else if (error.request) {
               notify.error('网络错误，请检查连接');
           } else {
               notify.error('请求配置错误');
           }
           return Promise.reject(error);
       }
   );
   
   // 导出全局对象
   window.http = http;
   ```

### 阶段 1：重构核心工具（第 1 周）

**目标**：创建统一的 HTTP 请求层

- [x] ~~创建 `axios-config.js`~~（配置已存在于 config.js）
- [ ] 重构 `csrf-utils.js`（可选，因为 Axios 拦截器已处理）
- [ ] 验证 CSRF Token 自动添加
- [ ] 验证错误统一处理

**验收标准**：
- Axios 实例可用
- CSRF Token 自动添加
- 错误统一弹窗提示
- 不影响现有功能

### 阶段 2：重构实例管理（第 2 周）

**顺序**：
1. `pages/instances/list.js` - 列表页
2. `pages/instances/detail.js` - 详情页

**重构模式**：
```javascript
// ❌ 旧代码
fetch('/api/endpoint', {
    method: 'POST',
    headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': csrfToken
    },
    body: JSON.stringify(data)
})
.then(response => response.json())
.then(data => {
    if (data.success) {
        // 处理成功
    } else {
        notify.error(data.error);
    }
})
.catch(error => {
    console.error(error);
    notify.error('请求失败');
});

// ✅ 新代码
try {
    const data = await http.post('/api/endpoint', requestData);
    if (data.success) {
        // 处理成功
    }
} catch (error) {
    // 错误已在拦截器中处理
}
```

**验收标准**：
- 功能完全一致
- 代码更简洁
- 错误处理统一
- 完整测试所有功能

### 阶段 3：重构历史记录（第 3 周）

**顺序**：
1. `pages/history/logs.js`
2. `pages/history/sync_sessions.js`

### 阶段 4：重构其他页面（第 4-6 周）

按优先级逐个重构剩余文件。

---

## 四、重构原则

### ✅ 应该做的

1. **只改网络请求代码**
   - 将 `fetch` 改为 `http.get/post/put/delete`
   - 简化 then/catch 链

2. **保持功能完全一致**
   - 不改变任何 UI
   - 不改变任何交互逻辑
   - 不改变任何业务逻辑

3. **渐进式重构**
   - 一次只改一个文件
   - 改完立即测试
   - 发现问题立即回滚

4. **完整测试**
   - 测试所有按钮和表单
   - 测试成功和失败场景
   - 检查浏览器控制台

### ❌ 不应该做的

1. **不要改变 UI 样式**
   - 不要从表格改成卡片
   - 不要从模态框改成弹窗
   - 不要改变任何布局

2. **不要重构其他代码**
   - 不要顺便优化其他逻辑
   - 不要顺便添加新功能
   - 专注于 fetch → Axios

3. **不要跳过测试**
   - 每个文件改完必须测试
   - 不要批量改多个文件

---

## 五、预期收益

### 代码量减少

- **减少样板代码**：每个 fetch 调用减少 5-10 行
- **预计总减少**：约 300-500 行代码

### 代码质量提升

- **统一错误处理**：不再需要每个地方都写 catch
- **自动 CSRF**：不再需要手动添加 Token
- **类型安全**：Axios 提供更好的类型推断
- **调试友好**：Axios 提供更好的错误信息

### 维护性提升

- **统一配置**：超时、拦截器、默认头部
- **易于扩展**：添加 loading、重试、缓存等功能
- **更好的测试**：Axios 更容易 mock

---

## 六、风险控制

### 回滚策略

1. **保留 Git 提交点**
   - 每个文件一个提交
   - 随时可以回滚

2. **并行运行**
   - 保留原有的 fetch 代码（注释）
   - 验证无误后再删除

3. **增量发布**
   - 先在测试环境验证
   - 然后逐步发布到生产

### 测试清单

每个文件重构后必须测试：

- [ ] 页面正常加载
- [ ] 所有按钮可点击
- [ ] 表单可提交
- [ ] 数据正确显示
- [ ] 错误正确提示
- [ ] 控制台无错误

---

## 七、时间估算

| 阶段 | 文件数 | 预计时间 | 说明 |
|------|--------|---------|------|
| 准备工作 | 1 | 0.5 天 | 配置 Axios |
| 核心工具 | 2 | 1 天 | csrf-utils + 验证 |
| 实例管理 | 2 | 2 天 | list + detail |
| 历史记录 | 2 | 2 天 | logs + sync_sessions |
| 其他页面 | 15 | 7-10 天 | 逐个重构 |
| **总计** | **21** | **12-15 天** | 约 2-3 周 |

---

## 八、下一步行动

### 立即行动

1. **确认 Axios 配置正确**
   - 检查 `config.js` 中的 Axios 配置
   - 验证 CSRF 拦截器工作
   - 测试简单的 GET/POST 请求

2. **选择第一个重构文件**
   - 建议：`pages/instances/list.js`
   - 原因：核心功能，代码适中，便于验证

3. **创建测试计划**
   - 列出所有需要测试的功能
   - 准备测试数据

### 征求意见

在开始之前，请确认：
- ✅ 是否同意这个重构计划？
- ✅ 是否从 `instances/list.js` 开始？
- ✅ 是否需要调整优先级？

---

**生成时间**: 2025-10-28
**作者**: Droid
