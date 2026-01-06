# 账户分类域(Classification) 研发图表包

> 状态: Draft
> 负责人: WhaleFall Team
> 创建: 2026-01-06
> 更新: 2026-01-06
> 范围: classifications + rules + assignments + auto-classify + cache
> 关联: ./accounts-permissions-domain.md; ./spec.md; ./account-classification-v2-design.md

## 1. 目标

- 让研发快速回答: "规则怎么生效, 会改哪些表, 缓存怎么参与, 失败怎么定位".
- 图表与代码落点一一对应, 用于 code review, 拆域重构, 排障.

## 2. 域边界

### 2.1 In scope

- 分类元数据: `account_classifications`
- 分类规则: `classification_rules`(DSL v4)
- 分类分配: `account_classification_assignments`(auto/manual, is_active)
- 自动分类: 以 `account_permission.permission_facts` 作为事实输入, 规则匹配后 upsert 分配
- 缓存: Redis 缓存分类规则(全量 + 按 db_type)

### 2.2 Out of scope(但有依赖)

- 权限同步写入: `account_permission.permission_snapshot(version=4)` 与 `permission_facts`(见 `docs/architecture/accounts-permissions-domain.md`)
- facts 构建: 当 `permission_facts` 缺失或格式无效时, 使用 `build_permission_snapshot_view` + `build_permission_facts`
- 缓存运维入口: `app/api/v1/namespaces/cache.py` 的 classification clear/stats endpoints

## 3. 组件与依赖(代码落点)

```mermaid
flowchart LR
  subgraph API["API (Flask-RESTX)"]
    ClsList["GET /api/v1/accounts/classifications"]
    ClsWrite["POST/PUT/DELETE /api/v1/accounts/classifications/{id}"]
    RuleApi["/api/v1/accounts/classifications/rules*"]
    AssignApi["/api/v1/accounts/classifications/assignments*"]
    Auto["POST /api/v1/accounts/classifications/actions/auto-classify"]
    CacheApi["/api/v1/cache/classification/*"]
  end

  subgraph Services["Services"]
    ReadSvc["services.accounts.AccountClassificationsReadService"]
    WriteSvc["services.accounts.AccountClassificationsWriteService"]
    AutoSvc["services.account_classification.AutoClassifyService"]
    Orchestrator["services.account_classification.AccountClassificationService"]
    RepoEngine["services.account_classification.ClassificationRepository"]
    CacheEngine["services.account_classification.ClassificationCache"]
    Dsl["services.account_classification.DslV4Evaluator"]
    Facts["services.accounts_permissions.facts_builder"]
    Snapshot["services.accounts_permissions.snapshot_view"]
  end

  subgraph Repos["Repositories"]
    RepoCrud["repositories.AccountsClassificationsRepository"]
  end

  subgraph Cache["Cache"]
    Redis["Redis (CacheService)"]
  end

  subgraph DB["PostgreSQL (主库)"]
    TClass["account_classifications"]
    TRule["classification_rules"]
    TAssign["account_classification_assignments"]
    TPerm["account_permission"]
    TInst["instances"]
    TIA["instance_accounts"]
  end

  ClsList --> ReadSvc --> RepoCrud --> TClass
  ClsWrite --> WriteSvc --> RepoCrud --> TClass
  RuleApi --> ReadSvc --> RepoCrud --> TRule
  RuleApi --> WriteSvc --> RepoCrud --> TRule
  WriteSvc --> Orchestrator --> CacheEngine --> Redis

  Auto --> AutoSvc --> Orchestrator
  Orchestrator --> CacheEngine --> Redis
  Orchestrator --> RepoEngine --> TRule
  RepoEngine --> TPerm
  TPerm --- TInst
  TPerm --- TIA
  Orchestrator --> TAssign
  Orchestrator --> Snapshot --> Facts --> Dsl

  CacheApi --> Orchestrator
```

代码入口参考:

- 自动分类: `app/api/v1/namespaces/accounts_classifications.py` -> `AccountClassificationAutoClassifyActionResource.post` -> `AutoClassifyService.auto_classify` -> `AccountClassificationService.auto_classify_accounts`.
- 规则 CRUD: `app/api/v1/namespaces/accounts_classifications.py` -> `AccountClassificationsWriteService`(create/update/delete rule) -> `_invalidate_cache` -> `AccountClassificationService.invalidate_cache`.
- 缓存清理/统计: `app/api/v1/namespaces/cache.py` -> `AccountClassificationService.invalidate_cache`/`CacheService.get_classification_rules_by_db_type_cache`.

## 4. 数据模型(ERD)

```mermaid
erDiagram
  ACCOUNT_CLASSIFICATIONS ||--o{ CLASSIFICATION_RULES : defines
  ACCOUNT_CLASSIFICATIONS ||--o{ ACCOUNT_CLASSIFICATION_ASSIGNMENTS : groups
  ACCOUNT_PERMISSION ||--o{ ACCOUNT_CLASSIFICATION_ASSIGNMENTS : assigned
  CLASSIFICATION_RULES ||--o{ ACCOUNT_CLASSIFICATION_ASSIGNMENTS : via_rule

  ACCOUNT_CLASSIFICATIONS {
    int id PK
    string name UK
    string risk_level
    string color
    string icon_name
    int priority
    bool is_system
    bool is_active
  }

  CLASSIFICATION_RULES {
    int id PK
    int classification_id FK
    string db_type
    string rule_name
    text rule_expression
    bool is_active
  }

  ACCOUNT_CLASSIFICATION_ASSIGNMENTS {
    int id PK
    int account_id FK
    int classification_id FK
    int rule_id FK "nullable"
    string assignment_type
    string batch_id "nullable"
    bool is_active
  }

  ACCOUNT_PERMISSION {
    int id PK
    int instance_id FK
    int instance_account_id FK
    json permission_snapshot
    json permission_facts
  }
```

关键约束(落库一致性):

- `account_classifications.name` 唯一.
- `account_classification_assignments` 唯一约束: `(account_id, classification_id, batch_id)`(见 `AccountClassificationAssignment.__table_args__`).
- 规则表达式契约: `classification_rules.rule_expression` 仅支持 DSL v4(对象 JSON, version=4), 且写入前会 canonicalize(ensure_ascii=False, sort_keys=True).

## 5. 主流程图(Flow)

场景: "点一次按钮"触发全量或单实例自动分类.

入口: `POST /api/v1/accounts/classifications/actions/auto-classify`

```mermaid
flowchart TD
  Start["User click: Auto classify"] --> API["AccountsClassifications API: /actions/auto-classify"]
  API --> Safe["safe_route_call (rollback/commit + error envelope)"]
  Safe --> Svc["AutoClassifyService.auto_classify(instance_id?, use_optimized?)"]
  Svc --> Normalize["normalize instance_id + coerce use_optimized"]
  Normalize --> Orchestrator["AccountClassificationService.auto_classify_accounts"]

  Orchestrator --> CacheGet["ClassificationCache.get_rules()"]
  CacheGet --> Hit{"cache hit?"}
  Hit -->|yes| Hydrate["repository.hydrate_rules(cached)"]
  Hit -->|no| LoadDb["repository.fetch_active_rules() from DB"]
  LoadDb --> CacheSet["cache.set_rules(serialized)"]
  CacheSet --> Hydrate

  Hydrate --> RulesOk{"rules empty?"}
  RulesOk -->|yes| FailNoRules["return success=false"]
  RulesOk -->|no| FetchAcc["repository.fetch_accounts(instance_id?)"]

  FetchAcc --> AccOk{"accounts empty?"}
  AccOk -->|yes| FailNoAcc["return success=false"]
  AccOk -->|no| Cleanup["cleanup_all_assignments() (DELETE all)"]

  Cleanup --> Group["group accounts/rules by db_type"]
  Group --> LoopDb["for each db_type"]
  LoopDb --> LoopRule["for each rule(priority order)"]
  LoopRule --> Eval["DslV4Evaluator(facts).evaluate(rule_expression)"]
  Eval --> Match{"matched?"}
  Match -->|no| LoopRule
  Match -->|yes| Upsert["upsert assignments (delete + bulk insert)"]
  Upsert --> LoopRule
  LoopRule --> LoopDb

  LoopDb --> Done["aggregate stats + return success=true"]
  Done --> Resp["return 200 envelope"]

  FailNoRules --> Err["AutoClassifyService raises AutoClassifyError"]
  FailNoAcc --> Err
  Err --> RespErr["global error handler -> unified error response"]
```

关键分支:

- cache miss: 从 DB 加载启用规则并写入 Redis 缓存.
- rules/accounts empty: 编排器返回 success=false, 服务层抛 `AutoClassifyError`, 整体请求回滚.
- 单条规则异常: 在 db_type 循环内 catch, 记录错误并计入 failed_count, 不中断其他 db_type.

## 6. 主时序图(Sequence)

场景: `POST /accounts/classifications/actions/auto-classify` 的完整链路.

说明: 本链路不访问 External DB, 仅使用 PostgreSQL + Redis(规则缓存). `permission_facts` 缺失时会走本地 facts 构建(基于快照).

```mermaid
sequenceDiagram
  autonumber
  participant U as User/Browser
  participant API as AccountsClassifications API
  participant Safe as safe_route_call
  participant Svc as AutoClassifyService
  participant Or as AccountClassificationService
  participant C as ClassificationCache
  participant R as Redis(CacheService)
  participant Repo as ClassificationRepository
  participant PG as PostgreSQL
  participant Snap as build_permission_snapshot_view
  participant Facts as build_permission_facts
  participant Dsl as DslV4Evaluator

  U->>API: POST /accounts/classifications/actions/auto-classify {instance_id?, use_optimized?}
  API->>Safe: execute()
  Safe->>Svc: auto_classify(...)
  Svc->>Or: auto_classify_accounts(instance_id)

  Or->>C: get_rules()
  alt cache hit
    C->>R: GET classification_rules_cache
    R-->>C: cached rules payload
    C-->>Or: rules(list[dict])
    Or->>Repo: hydrate_rules(cached)
  else cache miss
    C->>R: GET classification_rules_cache
    R-->>C: nil
    Or->>Repo: fetch_active_rules()
    Repo->>PG: SELECT classification_rules WHERE is_active=true
    PG-->>Repo: rows
    Or->>C: set_rules(serialized)
    C->>R: SET classification_rules_cache
  end

  Or->>Repo: fetch_accounts(instance_id?)
  Repo->>PG: SELECT account_permission JOIN instances JOIN instance_accounts
  PG-->>Repo: accounts

  Or->>Repo: cleanup_all_assignments()
  Repo->>PG: DELETE FROM account_classification_assignments

  loop each db_type
    loop each rule
      loop each account in db_type group
        Or->>Or: _get_permission_facts(account)
        alt account.permission_facts is dict
          Or-->>Dsl: evaluate(facts, rule_expression)
        else facts missing
          Or->>Snap: build(snapshot_view)
          Or->>Facts: build(record, snapshot)
          Or-->>Dsl: evaluate(facts, rule_expression)
        end
        alt matched
          Or->>Repo: upsert_assignments(matched_accounts, classification_id, rule_id)
          Repo->>PG: DELETE existing assignments for (classification_id, account_ids)
          Repo->>PG: BULK INSERT new assignments
        end
      end
    end
  end

  Svc-->>Safe: AutoClassifyResult payload
  Safe->>PG: COMMIT
  Safe-->>U: 200 success envelope
```

## 7. 状态机(Optional but valuable)

### 7.1 Classification rules cache lifecycle

```mermaid
stateDiagram-v2
  [*] --> cold
  cold --> warm: set_rules()/set_rules_by_db_type()
  warm --> cold: invalidate_cache()
  warm --> warm: cache hit
```

## 8. API 契约(Optional)

说明:

- response envelope: 所有 endpoints 通过 `BaseResource.success`/`safe_call` 返回统一封套.
- csrf: 写接口通常要求 `@require_csrf`.
- auto-classify: 同步执行, 可能耗时较长, 默认全量会清理并重建全部分配.

| Method | Path | Purpose | Idempotency | Notes |
| --- | --- | --- | --- | --- |
| GET | /api/v1/accounts/classifications/colors | list color options | yes (read) | ThemeColors |
| GET | /api/v1/accounts/classifications | list classifications | yes (read) | sorted by priority desc |
| POST | /api/v1/accounts/classifications | create classification | no | csrf required |
| GET | /api/v1/accounts/classifications/{id} | classification detail | yes (read) | - |
| PUT | /api/v1/accounts/classifications/{id} | update classification | no | csrf required |
| DELETE | /api/v1/accounts/classifications/{id} | delete classification | no | csrf required, may 409 CLASSIFICATION_IN_USE |
| GET | /api/v1/accounts/classifications/rules | list rules | yes (read) | grouped by db_type |
| POST | /api/v1/accounts/classifications/rules | create rule | no | csrf required, invalidates cache |
| GET | /api/v1/accounts/classifications/rules/filter | filter rules | yes (read) | query: classification_id, db_type |
| POST | /api/v1/accounts/classifications/rules/actions/validate-expression | validate rule expression | no | csrf required |
| GET | /api/v1/accounts/classifications/rules/stats | rules match stats | yes (read) | query: rule_ids=1,2,3 |
| GET | /api/v1/accounts/classifications/rules/{id} | rule detail | yes (read) | parse_expression=true |
| PUT | /api/v1/accounts/classifications/rules/{id} | update rule | no | csrf required, invalidates cache |
| DELETE | /api/v1/accounts/classifications/rules/{id} | delete rule | no | csrf required |
| GET | /api/v1/accounts/classifications/assignments | list assignments | yes (read) | only is_active=true |
| DELETE | /api/v1/accounts/classifications/assignments/{id} | deactivate assignment | no | csrf required, sets is_active=false |
| GET | /api/v1/accounts/classifications/permissions/{db_type} | permissions options | yes (read) | backed by PermissionConfig |
| POST | /api/v1/accounts/classifications/actions/auto-classify | run auto classify | no | csrf required, heavy write |

## 9. 失败模式与排查线索(研发版)

| 现象 | 常见原因 | 关键日志/事件(event) | 落点 |
| --- | --- | --- | --- |
| auto-classify 返回错误 | rules 为空, accounts 为空, instance_id/use_optimized 非法 | `auto_classify_failed` / `auto_classify_service_failed` | `app/services/account_classification/auto_classify_service.py` |
| 规则更新后自动分类仍使用旧规则 | Redis 不可用导致 invalidate 失败, 或缓存未清 | `清除分类缓存失败` | `app/services/accounts/account_classifications_write_service.py::_invalidate_cache` |
| validate-expression 返回 400 | rule_expression 缺失, JSON 解析失败, 非 DSL v4 | `validate_rule_expression执行失败` | `app/api/v1/namespaces/accounts_classifications.py::AccountClassificationRuleExpressionValidateResource` |
| 删除分类返回 409 | 分类仍被规则/分配引用, 或是系统分类 | message_key: `CLASSIFICATION_IN_USE` / `SYSTEM_CLASSIFICATION` | `app/api/v1/namespaces/accounts_classifications.py::AccountClassificationDetailResource.delete` |
