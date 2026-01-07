# 凭据与连接适配域(Credentials + Connections)研发图表包

> 状态: Draft
> 负责人: WhaleFall Team
> 创建: 2026-01-06
> 更新: 2026-01-06
> 范围: credentials CRUD, connections test/status, ConnectionFactory adapters
> 关联: ./instances-domain.md; ./spec.md

## 1. 主流程图(Flow)

场景: "点一次按钮"执行连接测试.

入口: `POST /api/v1/connections/actions/test`

```mermaid
flowchart TD
  Start["User click: Test connection"] --> API["Connections API: /actions/test"]
  API --> Mode{"payload has instance_id?"}

  Mode -->|yes| LoadInst["Load Instance from PostgreSQL"]
  LoadInst --> InstOK{"instance exists?"}
  InstOK -->|no| E404["Raise NotFoundError -> 404 error envelope"]
  InstOK -->|yes| CTS1["ConnectionTestService.test_connection(instance)"]

  Mode -->|no| Validate["Validate payload fields: db_type, host, port, credential_id"]
  Validate --> ValidOK{"valid?"}
  ValidOK -->|no| E400["Raise ValidationError -> 400 error envelope"]
  ValidOK -->|yes| LoadCred["Load Credential from PostgreSQL"]
  LoadCred --> CredOK{"credential exists?"}
  CredOK -->|no| E404b["Raise NotFoundError -> 404 error envelope"]
  CredOK -->|yes| TempInst["Build temp Instance (not persisted)"]
  TempInst --> CTS2["ConnectionTestService.test_connection(temp_instance)"]

  CTS1 --> Factory["ConnectionFactory.create_connection(db_type)"]
  CTS2 --> Factory
  Factory --> Supported{"db_type supported?"}
  Supported -->|no| FailUnsupported["Return failure result (no connection object)"]
  Supported -->|yes| Decrypt["Credential.get_plain_password() decrypt"]
  Decrypt --> Connect["Adapter.connect() to External DB"]
  Connect --> ConnOK{"connected?"}
  ConnOK -->|no| FailConn["Update instance.last_connected, return 409 error envelope (DATABASE_CONNECTION_ERROR)"]
  ConnOK -->|yes| Version["Adapter.get_version() query"]
  Version --> Parse["VersionParser.parse + format"]
  Parse --> Update["Update instance.last_connected + version fields"]
  Update --> Done["Return 200 success envelope"]
```

关键分支:

- payload mode: `instance_id` -> 测试已存在实例; 无 `instance_id` -> 测试新连接参数(临时实例,不落库).
- connect failed: 返回 409 错误封套,但仍会更新 `instances.last_connected`(用于诊断).
- details exposure: 仅在 debug 或管理员场景下返回 `details`(见 `ConnectionTestService._should_expose_details`).

## 2. 主时序图(Sequence)

场景: 测试已存在实例连接(`instance_id` mode).

```mermaid
sequenceDiagram
  autonumber
  participant U as User/Browser
  participant API as Connections API
  participant Safe as safe_route_call
  participant PG as PostgreSQL
  participant CTS as ConnectionTestService
  participant CF as ConnectionFactory
  participant PM as PasswordManager
  participant EXT as External DB
  participant R as Redis (not used)

  U->>API: POST /connections/actions/test {instance_id}
  API->>Safe: execute()
  Safe->>PG: SELECT instances WHERE id=instance_id
  alt instance not found
    Safe-->>U: 404 error envelope
  else instance found
    Safe->>CTS: test_connection(instance)
    CTS->>CF: create_connection(instance)
    alt unsupported db_type
      CTS-->>Safe: {success:false, error:"unsupported"}
      Safe->>PG: COMMIT (last_connected may be updated)
      Safe-->>U: 409 error envelope
    else adapter created
      CTS->>PM: decrypt credential password (PASSWORD_ENCRYPTION_KEY)
      CTS->>EXT: adapter.connect()
      alt connect failed
        CTS->>PG: set instances.last_connected = now()
        CTS-->>Safe: {success:false, error_id, error_code}
        Safe->>PG: COMMIT
        Safe-->>U: 409 error envelope (DATABASE_CONNECTION_ERROR)
      else connected
        CTS->>EXT: get_version()
        CTS->>PG: set instances.last_connected + version fields
        CTS-->>Safe: {success:true, version,...}
        Safe->>PG: COMMIT
        Safe-->>U: 200 success envelope
      end
    end
  end
```

## 3. 状态机(Optional but valuable)

### 3.1 Instance connection health (derived)

连接状态不落库,由 `InstanceConnectionStatusService` 基于 `instances.last_connected` 计算:

- last_connected missing: unknown
- delta < 1 hour: good
- delta < 1 day: warning
- else: poor

```mermaid
stateDiagram-v2
  [*] --> unknown: last_connected is null
  unknown --> good: test succeeds and sets last_connected

  good --> warning: now - last_connected >= 1h
  warning --> poor: now - last_connected >= 24h

  poor --> good: next test succeeds
  warning --> good: next test succeeds
```

## 4. API 契约(Optional)

说明:

- response envelope: 通过 `BaseResource.success`/`safe_call` 返回统一成功封套.
- error envelope: 校验错误/NotFoundError 等会透传; 其他异常会包装为 `public_error`.
- secrets: credential password 默认 masked, 不直接返回明文.

| Method | Path | Purpose | Idempotency | Pagination | Notes |
| --- | --- | --- | --- | --- | --- |
| GET | /api/v1/credentials | list credentials | yes (read) | page/limit | search + filters in query string |
| POST | /api/v1/credentials | create credential | no | - | password encrypted before write |
| GET | /api/v1/credentials/{id} | credential detail | yes (read) | - | password masked in response |
| PUT | /api/v1/credentials/{id} | update credential | no | - | password optional; if provided re-encrypt |
| DELETE | /api/v1/credentials/{id} | delete credential | no | - | physical delete; may fail if referenced |
| POST | /api/v1/connections/actions/test | test connection | no (updates last_connected) | - | supports instance_id or temp params |
| POST | /api/v1/connections/actions/validate-params | validate db_type/port/credential_id | yes | - | no external DB access |
| POST | /api/v1/connections/actions/batch-test | batch test connections | no (updates last_connected per instance) | - | max 50 instances per request |
| GET | /api/v1/connections/status/{instance_id} | derived connection status | yes (read) | - | uses last_connected to compute status |
