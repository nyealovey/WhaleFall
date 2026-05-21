# AD 域账户同步设计文档

> **目标**：新增定时任务，从 Active Directory 同步域用户状态，与 WhaleFall 中管理的 SQLServer 账户进行匹配，标记已停用的域账户，供人工处理。
>
> **原则**：只读标记，不做自动禁用/删除。

---

## 1. 整体流程

```mermaid
flowchart TD
    subgraph 定时触发
        A[sync_ad_accounts 任务<br/>每天 03:00] --> B[遍历 ad_domain_configs<br/>is_enabled=True]
    end

    subgraph 每个域
        B --> C[LdapConnector<br/>ldap3 连接域控]
        C --> D[搜索 (objectClass=user)<br/>取 sAMAccountName, userAccountControl]
        D --> E[构建 {sAMAccountName: is_disabled} 映射表]
    end

    subgraph 匹配 SQLServer 账户
        E --> F[查询所有 InstanceAccount<br/>username LIKE 'NETBIOS\\%']
        F --> G{提取 NETBIOS\\name}
        G --> H[在映射表中查找 name]
        H -->|找到 且 已禁用| I[ad_domain_config_id=对应域<br/>ad_disabled_at=now<br/>ad_orphaned_at=NULL]
        H -->|找到 且 启用| J[ad_domain_config_id=对应域<br/>ad_disabled_at=NULL<br/>ad_orphaned_at=NULL]
        H -->|未找到| K[ad_domain_config_id=对应域<br/>ad_disabled_at=NULL<br/>ad_orphaned_at=now]
    end

    subgraph 清理旧标记
        F --> L[对未出现在本次同步中的<br/>已有标记的账户 → 维持不变<br/>（避免误清除）]
    end
```

### 1.1 同步粒度

- 每次任务执行时，针对每个启用的域配置，**全量**拉取 AD 用户列表
- 逐域匹配该域 NETBIOS 前缀的 InstanceAccount
- 匹配结果：更新 `ad_disabled_at` / `ad_orphaned_at`，设置 `ad_domain_config_id`

### 1.2 关键约定

| 场景 | 行为 |
|------|------|
| AD 中用户存在且启用 | `ad_disabled_at=NULL`, `ad_orphaned_at=NULL` |
| AD 中用户存在但已禁用 | `ad_disabled_at=now` |
| AD 中用户不存在（已删除/未搜索到） | `ad_orphaned_at=now` |
| 该 NETBIOS 无对应的域配置 | 跳过，不做任何标记变更 |
| 历史标记保持不变 | 即使本次同步未匹配到某账户，不自动清除其标记（避免因域控临时不可达导致误清除） |

---

## 2. 新增数据模型

### 2.1 `AdDomainConfig` — 域配置

```python
# app/models/ad_domain_config.py
class AdDomainConfig(db.Model):
    """AD 域配置."""
    __tablename__ = "ad_domain_configs"

    id               = db.Column(db.Integer, primary_key=True)
    name             = db.Column(db.String(255), unique=True, nullable=False, comment="域名, 如 corp.example.com")
    netbios_name     = db.Column(db.String(64), nullable=False, comment="NetBIOS 名称, 如 CORP")
    domain_controller = db.Column(db.String(255), nullable=False, comment="域控地址, 支持逗号分隔多个")
    ldap_port        = db.Column(db.Integer, nullable=False, default=389)
    use_ssl          = db.Column(db.Boolean, nullable=False, default=True, comment="是否使用 LDAPS")
    base_dn          = db.Column(db.String(512), nullable=False, comment="搜索根 DN, 如 DC=corp,DC=example,DC=com")
    credential_id    = db.Column(db.Integer, db.ForeignKey("credentials.id"), nullable=True, comment="域管理员凭据 ID")
    is_enabled       = db.Column(db.Boolean, nullable=False, default=True, comment="是否启用同步")
    description      = db.Column(db.Text, nullable=True)
    last_sync_at     = db.Column(db.DateTime(timezone=True), nullable=True, comment="最近同步时间")
    last_sync_status = db.Column(db.String(20), nullable=True, comment="最近同步状态: success/failed")
    last_error       = db.Column(db.Text, nullable=True, comment="最近同步错误信息")
    created_at       = db.Column(db.DateTime(timezone=True), nullable=False, default=time_utils.now)
    updated_at       = db.Column(db.DateTime(timezone=True), nullable=False, default=time_utils.now, onupdate=time_utils.now)

    credential = db.relationship("Credential", foreign_keys=[credential_id])
```

**唯一约束**：`name` 唯一。`netbios_name` + credential 不设唯一——同一个域可能有多个域控配置（容灾场景），但建议 UI 层约束。

### 2.2 `InstanceAccount` 新增字段

```python
# app/models/instance_account.py — 追加字段
ad_domain_config_id = db.Column(
    db.Integer, db.ForeignKey("ad_domain_configs.id"), nullable=True, index=True,
    comment="匹配到的 AD 域配置 ID",
)
ad_disabled_at = db.Column(
    db.DateTime(timezone=True), nullable=True,
    comment="AD 中账户停用时间(非空=已在 AD 停用)",
)
ad_orphaned_at = db.Column(
    db.DateTime(timezone=True), nullable=True,
    comment="标记为 AD 孤账户时间(非空=AD 中已删除该账户)",
)

ad_domain_config = db.relationship("AdDomainConfig", foreign_keys=[ad_domain_config_id])
```

**说明**：
- `ad_disabled_at` 和 `ad_orphaned_at` **互斥**——同一账户不会同时处于两种状态
- `is_active` 保持原语义不变（数据库级活跃状态），不做修改
- 新增索引：`ix_instance_accounts_ad_status` → `ad_domain_config_id, ad_disabled_at, ad_orphaned_at`

### 2.3 凭据 `credential_type` 处理

`_ALLOWED_CREDENTIAL_TYPES` 已包含 `"ldap"`。`_validate_username` 中对 `ldap` 类型无需特别处理——域管理员账号（如 `administrator`）符合当前正则 `^[a-zA-Z0-9_.-]+$`。

---

## 3. LDAP 连接器

```python
# app/services/ad_sync/ldap_connector.py
class LdapConnector:
    """LDAP 连接器，负责连接域控并查询用户信息。"""

    def __init__(self, config: AdDomainConfig, credential: Credential):
        self.config = config
        self.credential = credential

    def fetch_all_users(self) -> dict[str, bool]:
        """
        查询域中所有用户。
        返回: {sAMAccountName: is_disabled} 映射表
        """

    def _build_ldap_uri(self) -> str:
        """根据配置构建 LDAP URI，支持多域控故障转移。"""

    def _check_user_account_control(self, uac: int) -> bool:
        """检查 UF_ACCOUNTDISABLE (0x0002) 标志位。"""
        return bool(uac & 0x0002)
```

### 3.1 `userAccountControl` 判断

| 标志 | 值 | 含义 |
|------|-----|------|
| `UF_ACCOUNTDISABLE` | `0x0002` | 账户已禁用 |
| `UF_LOCKOUT` | `0x0010` | 账户已锁定 |
| `UF_PASSWORD_EXPIRED` | `0x800000` | 密码已过期 |

同步关键标志位：**`UF_ACCOUNTDISABLE`**，其他标志位记录到 `attributes` JSON 中供参考。

### 3.2 LDAP 查询过滤

全量用户列表（含已禁用）：

```
(&(objectClass=user)(objectCategory=person))
```

### 3.3 返回属性

| 属性 | 用途 |
|------|------|
| `sAMAccountName` | 匹配键 |
| `userAccountControl` | 判断禁用状态 |
| `displayName` | 参考信息，记录到 `attributes` |
| `mail` | 参考信息，记录到 `attributes` |
| `whenChanged` | 参考信息 |

---

## 4. 定时任务

### 4.1 任务函数

```python
# app/tasks/ad_sync_tasks.py
def sync_ad_accounts(
    *,
    manual_run: bool = False,
    created_by: int | None = None,
    run_id: str | None = None,
    session_id: str | None = None,
    **_: object,
) -> None:
    """AD 域账户同步任务 - 同步所有域配置的用户状态，匹配 SQLServer 账户。"""
    app = create_app(init_scheduler_on_start=False)
    with app.app_context():
        # 1. 创建 TaskRun 记录 (task_key="sync_ad_accounts")
        # 2. 查询所有 is_enabled=True 的 AdDomainConfig
        # 3. 每个域创建一个 TaskRunItem
        # 4. 每个域执行: connect AD → fetch users → match InstanceAccount → update
        # 5. finalize TaskRun
```

### 4.2 注册方式

**`app/scheduler.py` — `TASK_FUNCTIONS`** 新增：

```python
"sync_ad_accounts": "app.tasks.ad_sync_tasks:sync_ad_accounts",
```

**`app/core/constants/scheduler_jobs.py` — `BUILTIN_TASK_IDS`** 新增：

```python
"sync_ad_accounts",
```

**`app/config/scheduler_tasks.yaml`** 新增：

```yaml
- id: sync_ad_accounts
  name: AD 域账户同步
  function: sync_ad_accounts
  trigger_type: cron
  trigger_params:
    second: 0
    minute: 0
    hour: 3
  description: 每日同步 AD 域账户状态，匹配 SQLServer 账户并标记停用/孤账户
```

### 4.3 TaskRun/TaskRunItem 使用模式

参照 `accounts_sync_tasks.py`：

| 阶段 | 操作 |
|------|------|
| 创建运行记录 | `task_runs_service.start_run(run_id, task_key="sync_ad_accounts", task_name="AD 域账户同步", task_category="ad_sync", trigger_source="scheduler"/"manual")` |
| 初始化子项 | `task_runs_service.init_items(items=[TaskRunItemInit(item_type="domain", item_key=domain.name, item_name=domain.name)])` |
| 开始处理某域 | `task_runs_service.start_item(run_id, "domain", domain.name)` |
| 完成处理某域 | `task_runs_service.complete_item(run_id, "domain", domain.name, metrics={"total": n, "matched": m, "disabled": d, "orphaned": o})` |
| 完成运行 | `task_runs_service.finalize_run(run_id, summary_json={...})` |
| 失败处理 | `task_runs_service.fail_item(...)` + `finalize_run(run_id, status="failed")` |

---

## 5. 同步核心逻辑

### 5.1 匹配服务

```python
# app/services/ad_sync/ad_account_match_service.py
class AdAccountMatchService:
    """AD 账户匹配服务，将 AD 用户状态更新到 InstanceAccount。"""

    def __init__(self, domain_config: AdDomainConfig):
        self.domain_config = domain_config
        self.netbios_prefix = f"{domain_config.netbios_name}\\"

    def match_and_update(self, ad_users: dict[str, bool]) -> MatchResult:
        """
        匹配并更新 InstanceAccount。
        ad_users: {sAMAccountName: is_disabled}
        返回匹配统计。
        """
        # 1. 查询所有 username LIKE 'NETBIOS\\%' 的 InstanceAccount
        # 2. 逐条匹配:
        #    - 取 username 中 NETBIOS\ 后面的部分
        #    - 在 ad_users 中查找
        #    - 根据结果设置 ad_disabled_at / ad_orphaned_at
        # 3. 批量更新
        # 4. 返回 MatchResult

@dataclass
class MatchResult:
    total: int
    matched_enabled: int
    matched_disabled: int
    orphaned: int
```

### 5.2 匹配策略

```
SELECT id, username, ad_domain_config_id, ad_disabled_at, ad_orphaned_at
FROM instance_accounts
WHERE username LIKE 'CORP\\%'
```

对每条记录：

```python
name_part = username.split("\\", 1)[1]  # CORP\zhangsan → zhangsan
if name_part in ad_users:
    is_disabled = ad_users[name_part]
    new_disabled_at = now if is_disabled else None
    new_orphaned_at = None
else:
    new_disabled_at = None
    new_orphaned_at = now

# 只有值变化时才更新（减少写操作）
if (new_disabled_at != old_disabled_at) or (new_orphaned_at != old_orphaned_at):
    instance_account.ad_domain_config_id = domain_config.id
    instance_account.ad_disabled_at = new_disabled_at
    instance_account.ad_orphaned_at = new_orphaned_at
```

### 5.3 批量优化

- 每次同步一个域，使用 `instance_accounts` 表的 `username` 索引（已有 `ix_instance_accounts_username`）
- 对同域账户使用 `bulk_update` 批量更新，减少事务开销

---

## 6. 异常处理

| 异常场景 | 处理方式 |
|---------|---------|
| 域控不可达 | 记录 `last_sync_status=failed` + `last_error`，不影响已有标记 |
| 凭据无效 | 记录 `last_sync_status=failed` + `last_error`，不影响已有标记 |
| AD 查询超时 | 记录 `last_sync_status=failed` + `last_error`，不影响已有标记 |
| 部分域失败 | 其他域继续执行，最终 TaskRun 标记为 `completed_with_errors` |
| 全部域失败 | TaskRun 标记为 `failed` |

**关键原则**：任何域同步失败时，**不清除**该域已有账户的标记。防止因域控临时故障导致误清除。

---

## 7. 数据库迁移

### 7.1 变更清单

1. **新建表**：`ad_domain_configs`
2. **修改表**：`instance_accounts` 追加 `ad_domain_config_id`, `ad_disabled_at`, `ad_orphaned_at`
3. **新增索引**：
   - `ix_instance_accounts_ad_status` → `ad_domain_config_id, ad_disabled_at, ad_orphaned_at`

### 7.2 迁移文件命名

遵循现有约定：`YYYYMMDDHHMMSS_add_ad_domain_sync_fields.py`

### 7.3 SQL DDL 参考

```sql
CREATE TABLE ad_domain_configs (
    id                SERIAL PRIMARY KEY,
    name              VARCHAR(255) NOT NULL UNIQUE,
    netbios_name      VARCHAR(64) NOT NULL,
    domain_controller VARCHAR(255) NOT NULL,
    ldap_port         INTEGER NOT NULL DEFAULT 389,
    use_ssl           BOOLEAN NOT NULL DEFAULT TRUE,
    base_dn           VARCHAR(512) NOT NULL,
    credential_id     INTEGER REFERENCES credentials(id),
    is_enabled        BOOLEAN NOT NULL DEFAULT TRUE,
    description       TEXT,
    last_sync_at      TIMESTAMPTZ,
    last_sync_status  VARCHAR(20),
    last_error        TEXT,
    created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at        TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

ALTER TABLE instance_accounts
    ADD COLUMN ad_domain_config_id INTEGER REFERENCES ad_domain_configs(id),
    ADD COLUMN ad_disabled_at      TIMESTAMPTZ,
    ADD COLUMN ad_orphaned_at      TIMESTAMPTZ;

CREATE INDEX ix_instance_accounts_ad_status
    ON instance_accounts (ad_domain_config_id, ad_disabled_at, ad_orphaned_at);
```

---

## 8. 新建/修改文件清单

| 操作 | 文件路径 | 说明 |
|------|---------|------|
| **新增** | `app/models/ad_domain_config.py` | AdDomainConfig 模型 |
| **修改** | `app/models/instance_account.py` | 追加 ad_domain_config_id/ad_disabled_at/ad_orphaned_at |
| **修改** | `app/models/__init__.py` | 注册 AdDomainConfig 到 _MODEL_MODULE_MAP |
| **新增** | `app/services/ad_sync/ldap_connector.py` | LDAP 连接器 |
| **新增** | `app/services/ad_sync/ad_account_match_service.py` | AD-InstanceAccount 匹配服务 |
| **新增** | `app/tasks/ad_sync_tasks.py` | 定时任务函数 |
| **修改** | `app/scheduler.py` | TASK_FUNCTIONS 新增 sync_ad_accounts |
| **修改** | `app/core/constants/scheduler_jobs.py` | BUILTIN_TASK_IDS 新增 |
| **修改** | `app/config/scheduler_tasks.yaml` | 新增任务配置 |
| **新增** | `migrations/versions/YYYYMMDDHHMMSS_add_ad_domain_sync_fields.py` | 数据库迁移 |

---

## 9. 依赖

在 `pyproject.toml` 或 `requirements.txt` 中新增：

```
ldap3>=2.9.1
```

`ldap3` 是纯 Python 实现，无需系统级 LDAP 库，跨平台兼容。

---

## 10. 后续扩展

### 10.1 UI 展示（建议事项）

在账户列表页面增加：

| 功能 | 说明 |
|------|------|
| 筛选器 | "AD 状态 = 已停用 / 孤账户 / 正常" |
| 列展示 | AD 状态标签（正常/已停用/孤账户）、所属域、停用时间 |
| 批量清除标记 | 人工确认处理后，批量重置 `ad_disabled_at`/`ad_orphaned_at` |
| 域配置管理 | AdDomainConfig 的 CRUD 页面（凭据关联使用已有 ldap 类型） |

### 10.2 可能的优化

- **增量同步**：如果域账户数量大（>10万），可改用 `uSNChanged` 增量同步
- **多域控负载均衡**：`domain_controller` 支持逗号分隔，连接器随机选择或故障转移
- **缓存**：AD 用户列表短时间内不变，可考虑缓存减少每次同步的查询压力