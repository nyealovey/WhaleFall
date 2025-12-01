# WhaleFall 测试与账户自动分类流程（Mermaid 版）
**版本**：v0.1｜2025-12-01｜聚焦连接测试、批量测试及账户自动分类链路。  
**目的**：记录所有“测试/校验”类入口及自动分类任务，协助排查权限、校验与任务调度问题。

## 目录
1. [实例连接测试](#1-实例连接测试)
2. [批量连接测试](#2-批量连接测试)
3. [账户自动分类](#3-账户自动分类)

---

## 1. 实例连接测试
### 1.1 代码路径与职责
- `app/routes/connections.py::test_connection`（`connections_bp` → `/connections/api/test`）提供统一测试入口。
- `_test_existing_instance`：根据 `instance_id` 读取 `Instance`，调用 `ConnectionTestService.test_connection`。
- `_test_new_connection`：根据传入参数构造临时 `Instance` 与凭据对象，用于测试未落库连接。

### 1.2 流程图
```mermaid
flowchart TD
    Req[POST /connections/api/test] --> Guard[login_required + view_required + require_csrf]
    Guard --> Parse[request.get_json]
    Parse --> HasInst{包含 instance_id?}
    HasInst -->|是| LoadInst[Instance.query.get]
    LoadInst --> Exists?{实例存在?}
    Exists? -->|否| RaiseNotFound
    Exists? -->|是| CallExisting[连接测试服务 - 现有实例]
    HasInst -->|否| ValidateParams[校验 db_type/host/port/credential]
    ValidateParams --> BuildTemp[构建临时 Instance + Credential]
    BuildTemp --> CallNew[连接测试服务 - 临时实例]
    CallExisting --> Result
    CallNew --> Result
    Result --> Success?{result.success?}
    Success? -->|是| RespOK[返回统一成功响应]
    Success? -->|否| RaiseSystemError
```

### 1.3 控制点与风险
- 仅登录且具备视图权限的用户可调用；若要开放给 API Token，需要新增轻量权限或排除 CSRF。
- `_test_new_connection` 会创建内存实例并引用凭据对象，若凭据被禁用/删除会抛出 `NotFoundError`，前端需提前过滤。
- 驱动异常需由 `ConnectionTestService` 捕获并转成人类可读 `error` 字段，避免将原始堆栈泄露给前端。

---

## 2. 批量连接测试
### 2.1 代码路径与职责
- `app/routes/connections.py::batch_test_connections`（`/connections/api/batch-test`）。
- 循环调用 `ConnectionTestService.test_connection`，并按实例记录成功/失败。
- 使用 `log_info/log_warning/log_error` 输出统计，便于定位单个实例失败原因。

### 2.2 流程图
```mermaid
flowchart TD
    BatchReq[POST /connections/api/batch-test]
    BatchReq --> GuardBatch[login_required + view_required + require_csrf]
    GuardBatch --> ValidateList[instance_ids 校验（列表且数量 1-50）]
    ValidateList --> LoopInst[for instance_id in instance_ids]
    LoopInst --> FetchInst[Instance.query.get]
    FetchInst --> Exists?{实例存在?}
    Exists? -->|否| AppendMissing[记录 not_found 结果]
    Exists? -->|是| CallTest[连接测试服务执行测试]
    CallTest --> AppendResult[记录 success/error]
    AppendResult --> LoopDone{还有实例?}
    LoopDone -->|是| LoopInst
    LoopDone -->|否| Summary[统计 success/failed]
    Summary --> RespBatch[返回 results+summary JSON 响应]
```

### 2.3 控制点与风险
- `instance_ids` 被限制为最多 50 条，防止接口长时间占用；若需要全量巡检，建议走异步任务。
- 单个实例异常（驱动报错、网络失败）不会中断整体流程，但会将错误字符串写入 `results`，调用方需展示具体失败原因。
- 未找到实例、ID 非法等都会写入结果数组，测试人员在比对成功比例时需剔除这些“输入问题”。

---

## 3. 账户自动分类
### 3.1 代码路径与职责
- `app/routes/accounts/classifications.py::auto_classify`（`/accounts/classifications/api/auto-classify`）。
- 服务层 `_auto_classify_service` 使用 `AutoClassifyService`，其内部委托 `AccountClassificationOrchestrator` 读取规则并执行匹配。
- `AutoClassifyService.auto_classify` 支持传入 `instance_id`（仅分类某实例）或留空（对全量账户重跑）。

### 3.2 流程图
```mermaid
flowchart TD
    AutoReq[POST /accounts/classifications/api/auto-classify]
    AutoReq --> GuardAuto[login_required + update_required + require_csrf]
    GuardAuto --> PayloadAuto[request.get_json]
    PayloadAuto --> ServiceAuto[调用 AutoClassifyService 执行分类]
    ServiceAuto --> Orchestrator[AccountClassificationOrchestrator.auto_classify_accounts]
    Orchestrator --> FetchRules[加载缓存中的 ClassificationRule 列表]
    FetchRules --> FetchAccounts[读取账户快照]
    FetchAccounts --> CleanupAssign[清理所有旧分配记录]
    CleanupAssign --> MatchLoop[逐条匹配规则]
    MatchLoop --> ApplyAssign[写入 AccountClassificationAssignment]
    ApplyAssign --> Stats[统计 matched/updated/skipped]
    Stats --> ResultObj[封装 AutoClassifyResult payload]
    ResultObj --> RespAuto[返回统一成功响应]
```

### 3.3 控制点与风险
- 路由层只做参数解析，具体校验（是否允许“优化模式”）在服务层完成；若需加入角色限制，可在 `AutoClassifyService` 中追加。
- `AutoClassifyService` 捕获 `AutoClassifyError` 并转换为 `SystemError`，需要配套审计日志来追踪失败原因。
- 自动分类可能大批量更新 `AccountClassificationAssignment`，务必在调用前确保数据库锁/事务配置可承受。

---

> 如需继续扩展测试类流程（例如性能压测、SQL 计划校验），请在本文件追加章节并保持命名、CSRF、色彩等规范。
