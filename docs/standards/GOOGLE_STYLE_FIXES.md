# 鲸落项目 Google 风格修复计划

> 创建日期：2025-11-24  
> 基于：[GOOGLE_STYLE_ANALYSIS.md](./GOOGLE_STYLE_ANALYSIS.md)  
> 状态：待执行

## 概述

本文档记录项目代码与 Google 风格指南的差异，并提供详细的修复计划。**注意：代码格式（缩进、行长度、引号）保持项目现有规范不变，仅修复文档、注释和命名问题。**

---

## 一、Python 代码修复

### 1.1 文档字符串修复

#### 问题描述

当前项目的 Python 文档字符串普遍缺少详细的 `Args`、`Returns`、`Raises` 部分，不符合 Google 风格指南要求。

#### 修复范围

**影响文件**：
- `app/services/**/*.py` - 所有服务层代码
- `app/models/**/*.py` - 所有模型代码
- `app/routes/**/*.py` - 所有路由代码
- `app/utils/**/*.py` - 所有工具函数
- `app/tasks/**/*.py` - 所有任务代码

#### 修复标准

每个公共函数/方法必须包含：

1. **单行摘要**：简洁描述功能（已有，保持）
2. **详细描述**：补充复杂逻辑的说明（新增）
3. **Args 部分**：列出所有参数及其说明（新增）
4. **Returns 部分**：详细说明返回值结构（新增）
5. **Raises 部分**：列出可能抛出的异常（新增）
6. **Example 部分**：复杂函数添加使用示例（可选）

#### 修复示例

**修复前**：
```python
def create_partition(self, partition_date: date) -> dict[str, Any]:
    """
    创建指定日期所在月份的分区（包含四张相关表）
    返回生成的分区信息；若任何分区创建失败将抛出 DatabaseError
    """
    pass
```

**修复后**：
```python
def create_partition(self, partition_date: date) -> dict[str, Any]:
    """创建指定日期所在月份的分区。

    为四张相关表（database_size_stats、database_size_aggregations、
    instance_size_stats、instance_size_aggregations）创建月度分区。
    如果分区已存在则跳过，如果创建失败则回滚所有操作。

    Args:
        partition_date: 分区日期，将创建该日期所在月份的分区。
            例如传入 2025-11-15，将创建 2025-11 月份的分区。

    Returns:
        包含分区创建结果的字典，格式如下：
        {
            'actions': [
                {
                    'table': 'stats',
                    'partition_name': 'database_size_stats_2025_11',
                    'status': 'created'
                },
                {
                    'table': 'aggregations',
                    'partition_name': 'database_size_aggregations_2025_11',
                    'status': 'skipped'
                }
            ],
            'failures': []
        }

    Raises:
        DatabaseError: 当分区创建失败时抛出，包含失败原因。
        ValueError: 当 partition_date 为 None 或无效日期时抛出。

    Example:
        >>> service = PartitionManagementService()
        >>> result = service.create_partition(date(2025, 11, 1))
        >>> len(result['actions'])
        4
    """
    pass
```

#### 修复清单

- [ ] `app/services/partition_management_service.py`
  - [ ] `create_partition()`
  - [ ] `cleanup_partitions()`
  - [ ] `_month_window()`
  - [ ] `_partition_exists()`
  
- [ ] `app/services/sync/accounts_sync_coordinator.py`
  - [ ] `sync_single_instance()`
  - [ ] `sync_batch_instances()`
  - [ ] `_validate_instance()`
  
- [ ] `app/services/statistics/*.py`
  - [ ] 所有统计服务的公共方法
  
- [ ] `app/models/*.py`
  - [ ] 所有模型的公共方法
  
- [ ] `app/utils/*.py`
  - [ ] 所有工具函数

### 1.2 类型注解补充

#### 问题描述

部分函数缺少类型注解，或类型注解不够详细。

#### 修复范围

**检查项**：
- 所有函数参数必须有类型注解
- 所有函数返回值必须有类型注解
- 复杂类型使用 `typing` 模块明确定义

#### 修复示例

**修复前**：
```python
def get_user_list(page=1, limit=10):
    """获取用户列表"""
    pass
```

**修复后**：
```python
from typing import Optional

def get_user_list(
    page: int = 1,
    limit: int = 10,
    filters: Optional[dict[str, Any]] = None
) -> list[dict[str, Any]]:
    """获取用户列表。

    Args:
        page: 页码，从 1 开始。
        limit: 每页数量，默认 10。
        filters: 可选的筛选条件字典。

    Returns:
        用户字典列表，每个字典包含用户的基本信息。

    Example:
        >>> users = get_user_list(page=1, limit=20)
        >>> len(users)
        20
    """
    pass
```

#### 修复清单

- [ ] 检查所有 `app/services/**/*.py` 文件
- [ ] 检查所有 `app/routes/**/*.py` 文件
- [ ] 检查所有 `app/utils/**/*.py` 文件
- [ ] 使用 `mypy` 进行类型检查

### 1.3 异常处理文档化

#### 问题描述

函数抛出的异常未在文档字符串中说明。

#### 修复标准

所有可能抛出异常的函数必须在 `Raises` 部分列出：
- 异常类型
- 抛出条件
- 异常信息示例（可选）

#### 修复示例

**修复前**：
```python
def delete_user(user_id: int) -> bool:
    """删除用户"""
    if not user_id:
        raise ValueError("user_id 不能为空")
    user = User.query.get(user_id)
    if not user:
        raise NotFoundError("用户不存在")
    db.session.delete(user)
    db.session.commit()
    return True
```

**修复后**：
```python
def delete_user(user_id: int) -> bool:
    """删除用户。

    Args:
        user_id: 用户 ID。

    Returns:
        删除成功返回 True。

    Raises:
        ValueError: 当 user_id 为空或无效时抛出。
        NotFoundError: 当用户不存在时抛出。
        DatabaseError: 当数据库操作失败时抛出。
    """
    if not user_id:
        raise ValueError("user_id 不能为空")
    user = User.query.get(user_id)
    if not user:
        raise NotFoundError("用户不存在")
    db.session.delete(user)
    db.session.commit()
    return True
```

---

## 二、JavaScript 代码修复

### 2.1 JSDoc 注释补充

#### 问题描述

JavaScript 代码普遍缺少完整的 JSDoc 注释，特别是：
- 缺少 `@param` 参数说明
- 缺少 `@return` 返回值说明
- 缺少 `@throws` 异常说明
- 缺少类型注解

#### 修复范围

**影响文件**：
- `app/static/js/modules/**/*.js` - 所有模块代码
- `app/static/js/modules/views/**/*.js` - 所有视图代码
- `app/static/js/modules/services/**/*.js` - 所有服务代码
- `app/static/js/modules/stores/**/*.js` - 所有状态管理代码

#### 修复标准

每个函数必须包含：

1. **函数摘要**：简洁描述功能
2. **详细描述**：补充复杂逻辑说明（可选）
3. **@param 标签**：列出所有参数、类型和说明
4. **@return 标签**：说明返回值类型和含义
5. **@throws 标签**：列出可能抛出的异常（如有）

每个类必须包含：

1. **类摘要**：简洁描述类的职责
2. **详细描述**：说明类的用途和依赖
3. **@class 标签**：标记为类
4. **@constructor 标签**：构造函数说明
5. **@example 标签**：使用示例（可选）

#### 修复示例 - 函数

**修复前**：
```javascript
/**
 * 校验 service 是否实现分区接口。
 */
function ensureService(service) {
    if (!service) {
        throw new Error("createPartitionStore: service is required");
    }
    ["fetchInfo", "createPartition"].forEach(function (method) {
        if (typeof service[method] !== "function") {
            throw new Error("service." + method + " 未实现");
        }
    });
    return service;
}
```

**修复后**：
```javascript
/**
 * 校验 service 是否实现分区接口。
 *
 * 检查服务对象是否存在，并验证是否实现了所有必需的方法。
 * 如果校验失败，将抛出错误并阻止 store 初始化。
 *
 * @param {Object} service - 服务对象
 * @param {Function} service.fetchInfo - 获取分区信息的方法
 * @param {Function} service.createPartition - 创建分区的方法
 * @param {Function} service.cleanupPartitions - 清理分区的方法
 * @param {Function} service.fetchCoreMetrics - 获取核心指标的方法
 * @return {Object} 校验后的服务对象
 * @throws {Error} 当 service 为空或缺少必需方法时抛出
 *
 * @example
 * const service = new PartitionService();
 * const validated = ensureService(service);
 */
function ensureService(service) {
    if (!service) {
        throw new Error("createPartitionStore: service is required");
    }
    ["fetchInfo", "createPartition", "cleanupPartitions", "fetchCoreMetrics"].forEach(function (method) {
        if (typeof service[method] !== "function") {
            throw new Error("createPartitionStore: service." + method + " 未实现");
        }
    });
    return service;
}
```

#### 修复示例 - 类

**修复前**：
```javascript
/**
 * 聚合数据图表管理器
 * 基于 Chart.js 4.4.0 和 jQuery 3.7.1
 */
class AggregationsChartManager {
    constructor() {
        this.chart = null;
        this.currentData = [];
        this.currentChartType = 'line';
    }
    
    /**
     * 创建图例说明
     */
    createLegend() {
        // ...
    }
}
```

**修复后**：
```javascript
/**
 * 聚合数据图表管理器。
 *
 * 负责聚合数据图表的创建、更新和销毁，支持多种周期类型（日/周/月/季）
 * 和图表类型（折线图/柱状图）。基于 Chart.js 4.4.0 实现。
 *
 * @class
 *
 * @example
 * const manager = new AggregationsChartManager();
 * manager.loadChartData('daily');
 * manager.updateChart(data, 'line');
 */
class AggregationsChartManager {
    /**
     * 构造函数。
     *
     * 初始化图表管理器，设置默认配置和状态。
     *
     * @constructor
     */
    constructor() {
        /** @type {Chart|null} Chart.js 图表实例 */
        this.chart = null;
        
        /** @type {Array} 当前图表数据 */
        this.currentData = [];
        
        /** @type {string} 当前图表类型，可选值：'line'、'bar' */
        this.currentChartType = 'line';
        
        /** @type {string} 当前统计周期，可选值：'daily'、'weekly'、'monthly'、'quarterly' */
        this.currentPeriodType = 'daily';
    }
    
    /**
     * 创建图例说明。
     *
     * 根据当前统计周期生成对应的图例 HTML，并插入到页面中。
     * 如果图例容器不存在，则静默返回。
     *
     * @return {void}
     */
    createLegend() {
        const legendContainer = selectOne('#chartLegend');
        if (!legendContainer.length) return;
        // ...
    }
}
```

#### 修复清单

- [ ] `app/static/js/modules/stores/`
  - [ ] `partition_store.js` - 所有函数
  - [ ] `credentials_store.js` - 所有函数
  - [ ] `instance_store.js` - 所有函数
  
- [ ] `app/static/js/modules/services/`
  - [ ] `partition_service.js` - 所有方法
  - [ ] `credentials_service.js` - 所有方法
  - [ ] `instance_service.js` - 所有方法
  
- [ ] `app/static/js/modules/views/`
  - [ ] `capacity/aggregations-chart.js` - 所有函数和类
  - [ ] `instances/list.js` - 所有函数
  - [ ] `credentials/list.js` - 所有函数
  - [ ] `accounts/list.js` - 所有函数
  - [ ] `history/logs/logs.js` - 所有函数
  - [ ] `history/sessions/sync-sessions.js` - 所有函数

### 2.2 类型定义补充

#### 问题描述

JavaScript 代码缺少类型定义（`@typedef`），导致复杂对象结构不清晰。

#### 修复标准

为项目中常用的数据结构添加 `@typedef` 定义：

#### 修复示例

**在文件开头添加类型定义**：

```javascript
/**
 * @typedef {Object} PartitionInfo
 * @property {string} name - 分区名称，格式：table_name_YYYY_MM
 * @property {string} table_name - 表名
 * @property {string} status - 分区状态：'active'、'archived'、'pending'
 * @property {number} size_bytes - 分区大小（字节）
 * @property {string} created_at - 创建时间，ISO 8601 格式
 * @property {number} row_count - 行数
 */

/**
 * @typedef {Object} ChartConfig
 * @property {string} type - 图表类型：'line'、'bar'
 * @property {Array<ChartDataset>} datasets - 数据集数组
 * @property {Object} options - Chart.js 配置选项
 */

/**
 * @typedef {Object} ChartDataset
 * @property {string} label - 数据集标签
 * @property {Array<number>} data - 数据点数组
 * @property {string} borderColor - 边框颜色
 * @property {string} backgroundColor - 背景颜色
 */

/**
 * @typedef {Object} FilterValues
 * @property {string} [search] - 搜索关键词
 * @property {string} [db_type] - 数据库类型
 * @property {string} [status] - 状态筛选
 * @property {Array<string>} [tags] - 标签筛选
 */

/**
 * @typedef {Object} GridResponse
 * @property {Array<Object>} items - 数据项数组
 * @property {number} total - 总数
 * @property {number} page - 当前页码
 * @property {number} limit - 每页数量
 */
```

#### 修复清单

- [ ] 为每个模块文件添加常用类型定义
- [ ] 在函数注释中引用这些类型定义
- [ ] 确保类型定义与实际数据结构一致

### 2.3 异常处理文档化

#### 问题描述

JavaScript 函数抛出的异常未在 JSDoc 中说明。

#### 修复标准

所有可能抛出异常的函数必须使用 `@throws` 标签说明。

#### 修复示例

**修复前**：
```javascript
/**
 * 初始化图表
 */
function initChart(container, data) {
    if (!container) {
        throw new Error('容器元素不存在');
    }
    if (!data || !data.length) {
        throw new Error('数据为空');
    }
    // ...
}
```

**修复后**：
```javascript
/**
 * 初始化图表。
 *
 * @param {HTMLElement} container - 图表容器元素
 * @param {Array<Object>} data - 图表数据数组
 * @return {Chart} Chart.js 实例
 * @throws {Error} 当容器元素不存在时抛出
 * @throws {Error} 当数据为空或无效时抛出
 */
function initChart(container, data) {
    if (!container) {
        throw new Error('容器元素不存在');
    }
    if (!data || !data.length) {
        throw new Error('数据为空');
    }
    // ...
}
```

---

## 三、修复优先级

### P0 - 高优先级（2 周内完成）

**影响范围**：核心业务逻辑和公共 API

1. **Python 服务层文档**
   - `app/services/partition_management_service.py`
   - `app/services/sync/accounts_sync_coordinator.py`
   - `app/services/statistics/*.py`

2. **JavaScript 核心模块**
   - `app/static/js/modules/stores/*.js`
   - `app/static/js/modules/services/*.js`

### P1 - 中优先级（4 周内完成）

**影响范围**：视图层和工具函数

1. **Python 路由和工具**
   - `app/routes/**/*.py`
   - `app/utils/**/*.py`

2. **JavaScript 视图层**
   - `app/static/js/modules/views/**/*.js`

### P2 - 低优先级（持续改进）

**影响范围**：模型层和辅助代码

1. **Python 模型和任务**
   - `app/models/**/*.py`
   - `app/tasks/**/*.py`

2. **JavaScript 辅助模块**
   - `app/static/js/modules/utils/*.js`

---

## 四、修复流程

### 4.1 单个文件修复流程

1. **阅读代码**：理解函数/类的功能和参数
2. **编写文档**：按照修复标准补充文档字符串/JSDoc
3. **自我审查**：检查文档是否完整、准确
4. **代码审查**：提交 PR，由团队成员审查
5. **合并代码**：审查通过后合并

### 4.2 批量修复流程

1. **选择模块**：按优先级选择要修复的模块
2. **创建分支**：`git checkout -b docs/fix-module-name`
3. **批量修复**：修复该模块下的所有文件
4. **运行测试**：确保修改不影响功能
5. **提交 PR**：提交 PR 并说明修复范围
6. **代码审查**：团队审查
7. **合并代码**：审查通过后合并

### 4.3 质量检查

#### Python 检查工具

```bash
# 检查文档字符串
pydocstyle app/services/

# 检查类型注解
mypy app/services/

# 代码质量检查
pylint app/services/
```

#### JavaScript 检查工具

```bash
# 检查 JSDoc 完整性
npm run lint:jsdoc

# 代码质量检查
npm run lint
```

---

## 五、修复模板

### 5.1 Python 函数模板

```python
def function_name(
    param1: Type1,
    param2: Type2,
    param3: Optional[Type3] = None
) -> ReturnType:
    """单行摘要，简洁描述功能。

    详细描述（可选），说明复杂逻辑、算法、注意事项等。
    可以分多段描述。

    Args:
        param1: 参数1的说明，包括类型、含义、取值范围等。
        param2: 参数2的说明。
        param3: 可选参数的说明，说明默认值的含义。

    Returns:
        返回值的详细说明，包括类型、结构、含义。
        如果返回复杂对象，可以展示示例：
        {
            'key1': 'value1',
            'key2': 123
        }

    Raises:
        ExceptionType1: 异常1的抛出条件。
        ExceptionType2: 异常2的抛出条件。

    Example:
        >>> result = function_name(arg1, arg2)
        >>> result['key1']
        'value1'
    """
    pass
```

### 5.2 Python 类模板

```python
class ClassName:
    """类的单行摘要。

    类的详细描述，说明类的职责、用途、依赖等。

    Attributes:
        attr1: 属性1的说明。
        attr2: 属性2的说明。

    Example:
        >>> obj = ClassName()
        >>> obj.method()
    """

    def __init__(self, param1: Type1) -> None:
        """构造函数。

        Args:
            param1: 参数说明。
        """
        self.attr1 = param1
```

### 5.3 JavaScript 函数模板

```javascript
/**
 * 函数的单行摘要。
 *
 * 函数的详细描述（可选），说明复杂逻辑、算法、注意事项等。
 *
 * @param {Type1} param1 - 参数1的说明
 * @param {Type2} param2 - 参数2的说明
 * @param {Type3} [param3=defaultValue] - 可选参数的说明
 * @return {ReturnType} 返回值的说明
 * @throws {Error} 异常的抛出条件
 *
 * @example
 * const result = functionName(arg1, arg2);
 * console.log(result);
 */
function functionName(param1, param2, param3 = defaultValue) {
    // ...
}
```

### 5.4 JavaScript 类模板

```javascript
/**
 * 类的单行摘要。
 *
 * 类的详细描述，说明类的职责、用途、依赖等。
 *
 * @class
 *
 * @example
 * const obj = new ClassName();
 * obj.method();
 */
class ClassName {
    /**
     * 构造函数。
     *
     * @constructor
     * @param {Type1} param1 - 参数说明
     */
    constructor(param1) {
        /** @type {Type1} 属性说明 */
        this.attr1 = param1;
    }
    
    /**
     * 方法的单行摘要。
     *
     * @param {Type2} param - 参数说明
     * @return {ReturnType} 返回值说明
     */
    method(param) {
        // ...
    }
}
```

---

## 六、进度跟踪

### 6.1 Python 修复进度

| 模块 | 文件数 | 已修复 | 进度 | 负责人 | 截止日期 |
|------|--------|--------|------|--------|----------|
| services/partition | 1 | 0 | 0% | - | - |
| services/sync | 3 | 0 | 0% | - | - |
| services/statistics | 5 | 0 | 0% | - | - |
| routes | 15 | 0 | 0% | - | - |
| utils | 8 | 0 | 0% | - | - |
| models | 12 | 0 | 0% | - | - |
| tasks | 6 | 0 | 0% | - | - |

**总计**：50 个文件，0% 完成

### 6.2 JavaScript 修复进度

| 模块 | 文件数 | 已修复 | 进度 | 负责人 | 截止日期 |
|------|--------|--------|------|--------|----------|
| stores | 5 | 0 | 0% | - | - |
| services | 8 | 0 | 0% | - | - |
| views/capacity | 3 | 0 | 0% | - | - |
| views/instances | 2 | 0 | 0% | - | - |
| views/credentials | 2 | 0 | 0% | - | - |
| views/accounts | 2 | 0 | 0% | - | - |
| views/history | 4 | 0 | 0% | - | - |
| utils | 6 | 0 | 0% | - | - |

**总计**：32 个文件，0% 完成

---

## 七、注意事项

### 7.1 不需要修复的内容

以下内容保持项目现有规范，**不需要修改**：

1. **代码格式**
   - Python：保持 4 空格缩进、120 字符行长度
   - JavaScript：保持 4 空格缩进、120 字符行长度、双引号

2. **命名规范**
   - Python：已符合 Google 风格，无需修改
   - JavaScript：已符合 camelCase 规范，无需修改

3. **注释语言**
   - 保持使用中文注释

### 7.2 修复原则

1. **不破坏现有功能**：修复仅涉及文档和注释，不修改代码逻辑
2. **保持一致性**：同一模块内的文档风格保持一致
3. **准确性优先**：文档必须准确反映代码行为
4. **简洁明了**：避免冗长的描述，突出重点

### 7.3 审查要点

代码审查时重点检查：

1. **完整性**：是否包含所有必需的部分（Args/Returns/Raises）
2. **准确性**：文档是否与代码实现一致
3. **清晰性**：描述是否清晰易懂
4. **示例**：复杂函数是否提供了使用示例

---

## 八、相关文档

- [GOOGLE_STYLE_ANALYSIS.md](./GOOGLE_STYLE_ANALYSIS.md) - Google 风格对比分析
- [CODING_STANDARDS.md](./CODING_STANDARDS.md) - 编码规范
- [FRONTEND_COMMENTS.md](./FRONTEND_COMMENTS.md) - 前端注释规范
- [TERMINOLOGY.md](./TERMINOLOGY.md) - 术语表

---

**最后更新**：2025-11-24  
**文档状态**：待执行  
**预计完成时间**：6-8 周
