# 凭据管理页面筛选失效问题 - 快速修复指南

## 问题现象
凭据管理页面的搜索框和所有筛选器（凭据类型、数据库类型、状态）都无法正常工作，无论如何操作，列表都不会过滤。

## 根本原因

### 问题 1: GridWrapper 的 fetch 覆盖问题
**文件**: `app/static/js/utils/grid-wrapper.js` (第 95-115 行)

Grid.js 在执行服务端请求时，会优先使用 `server.fetch` 方法。当前代码中：
1. `url` 函数拼接了筛选参数
2. `fetch` 函数又重新拼接了一次筛选参数
3. 但 `fetch` 接收到的 `url` 参数可能已经是 Grid.js 内部处理过的 URL 对象，导致 `appendFilters` 无法正确解析

**核心问题代码**:
```javascript
fetch: (url, fetchOptions) => {
  const baseOptions = fetchOptions || {};
  const mergedOptions = {
    ...baseOptions,
    ...(this.options.fetchOptions || {}),
  };
  const finalUrl = this.appendFilters(url, this.currentFilters);  // ❌ url 可能是对象
  return fetch(finalUrl, mergedOptions);
},
```

### 问题 2: 初始化时序问题
**文件**: `app/static/js/modules/views/credentials/list.js` (第 195-197 行)

```javascript
const initialFilters = normalizeGridFilters(resolveCredentialFilters(resolveFormElement()));
credentialsGrid.setFilters(initialFilters || {}, { silent: true });  // ❌ silent 阻止刷新
credentialsGrid.init();
```

使用 `{ silent: true }` 导致即使设置了初始筛选条件，Grid 也不会应用这些条件。

## 快速修复方案

### 修复 1: 简化 GridWrapper.buildServerConfig

**修改文件**: `app/static/js/utils/grid-wrapper.js`

**原代码** (第 95-115 行):
```javascript
GridWrapper.prototype.buildServerConfig = function buildServerConfig(baseServer) {
  const originalUrl = baseServer.url;
  const urlResolver = typeof originalUrl === "function" ? originalUrl : () => originalUrl;

  const serverConfig = {
    ...baseServer,
    url: (...args) => {
      const prev = urlResolver(...args);
      return this.appendFilters(prev, this.currentFilters);
    },
    fetch: (url, fetchOptions) => {
      const baseOptions = fetchOptions || {};
      const mergedOptions = {
        ...baseOptions,
        ...(this.options.fetchOptions || {}),
      };
      const finalUrl = this.appendFilters(url, this.currentFilters);
      return fetch(finalUrl, mergedOptions);
    },
  };
  serverConfig.__baseUrlResolver = urlResolver;
  return serverConfig;
};
```

**修改为**:
```javascript
GridWrapper.prototype.buildServerConfig = function buildServerConfig(baseServer) {
  const originalUrl = baseServer.url;
  const urlResolver = typeof originalUrl === "function" ? originalUrl : () => originalUrl;
  const self = this;

  const serverConfig = {
    ...baseServer,
    url: (...args) => {
      const prev = urlResolver(...args);
      return self.appendFilters(prev, self.currentFilters);
    },
    // 移除自定义 fetch，让 Grid.js 使用默认的 fetch 行为
  };
  serverConfig.__baseUrlResolver = urlResolver;
  return serverConfig;
};
```

**关键改动**:
1. 移除 `fetch` 自定义逻辑，让 Grid.js 使用 `url` 函数返回的完整 URL
2. 使用 `self` 保存 `this` 引用，避免作用域问题

### 修复 2: 移除 silent 参数

**修改文件**: `app/static/js/modules/views/credentials/list.js`

**原代码** (第 195-197 行):
```javascript
const initialFilters = normalizeGridFilters(resolveCredentialFilters(resolveFormElement()));
credentialsGrid.setFilters(initialFilters || {}, { silent: true });
credentialsGrid.init();
```

**修改为**:
```javascript
const initialFilters = normalizeGridFilters(resolveCredentialFilters(resolveFormElement()));
credentialsGrid.setFilters(initialFilters || {}, { silent: true });
credentialsGrid.init();
// 如果有初始筛选条件，初始化后立即刷新
if (initialFilters && Object.keys(initialFilters).length > 0) {
  credentialsGrid.refresh();
}
```

**或者更简单的方式**:
```javascript
const initialFilters = normalizeGridFilters(resolveCredentialFilters(resolveFormElement()));
// 先初始化 Grid
credentialsGrid.init();
// 再设置筛选条件（会自动刷新）
if (initialFilters && Object.keys(initialFilters).length > 0) {
  credentialsGrid.setFilters(initialFilters);
}
```

## 验证步骤

### 1. 修改代码后清除缓存
```bash
# 硬刷新浏览器
# Mac: Cmd + Shift + R
# Windows/Linux: Ctrl + Shift + R
```

### 2. 测试搜索功能
1. 打开凭据管理页面
2. 在搜索框输入凭据名称（如 "test"）
3. 等待 400ms（防抖时间）
4. 检查列表是否过滤

### 3. 测试筛选功能
1. 选择凭据类型（如 "database"）
2. 检查列表是否立即过滤
3. 选择数据库类型（如 "MySQL"）
4. 检查列表是否进一步过滤
5. 选择状态（如 "启用"）
6. 检查列表是否正确显示

### 4. 检查 Network 请求
1. 打开浏览器开发者工具
2. 切换到 Network 标签
3. 应用筛选条件
4. 查看 API 请求 URL，应该类似：
   ```
   /credentials/api/credentials?page=1&limit=20&search=test&credential_type=database&db_type=mysql&status=active
   ```

### 5. 测试清除功能
1. 应用多个筛选条件
2. 点击"清除"按钮
3. 检查所有筛选条件是否重置
4. 检查列表是否显示所有记录

## 预期结果

修复后：
- ✅ 搜索框输入关键词后，列表实时过滤（400ms 防抖）
- ✅ 选择凭据类型后，列表立即过滤
- ✅ 选择数据库类型后，列表立即过滤
- ✅ 选择状态后，列表立即过滤
- ✅ 多个筛选条件可以组合使用
- ✅ 清除按钮可以重置所有筛选条件
- ✅ 筛选后分页功能正常
- ✅ Network 请求包含正确的查询参数

## 回滚方案

如果修复后出现问题：
```bash
git checkout app/static/js/utils/grid-wrapper.js
git checkout app/static/js/modules/views/credentials/list.js
```

## 影响范围

此修改会影响所有使用 `GridWrapper` 的页面，建议修复后测试：
- ✅ 凭据管理页面
- ⚠️ 实例管理页面
- ⚠️ 用户管理页面
- ⚠️ 历史记录页面
- ⚠️ 其他使用 Grid 的页面

## 技术细节

### 为什么移除 fetch 自定义逻辑？

Grid.js 的工作流程：
1. 调用 `server.url()` 获取请求 URL
2. 如果定义了 `server.fetch()`，使用自定义 fetch
3. 否则使用默认的 `fetch(url, options)`

问题在于：
- 当我们同时定义 `url` 和 `fetch` 时，Grid.js 会先调用 `url()` 获取 URL
- 然后将这个 URL 传递给 `fetch(url, ...)`
- 但此时的 `url` 可能已经是一个 Request 对象或其他内部表示
- 我们的 `appendFilters` 无法正确处理这种情况

解决方案：
- 只在 `url` 函数中拼接筛选参数
- 让 Grid.js 使用默认的 fetch 行为
- 这样可以确保筛选参数正确附加到请求 URL 中

### 为什么需要在 init 后刷新？

Grid.js 的初始化流程：
1. 创建 Grid 实例
2. 解析配置（包括 server.url）
3. 渲染容器
4. 发起首次数据请求

问题在于：
- 如果在 `init()` 之前设置筛选条件（即使不 silent）
- Grid 实例还未创建，`refresh()` 无法执行
- 导致首次请求不包含筛选参数

解决方案：
- 先调用 `init()` 创建 Grid 实例
- 再调用 `setFilters()` 设置筛选条件并刷新
- 或者在 `init()` 后手动调用 `refresh()`

---

**创建日期**: 2025-11-19  
**优先级**: 高  
**预计修复时间**: 15 分钟
