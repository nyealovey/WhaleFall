# 鲸落项目常量文档

## 📋 文档信息

- **生成时间**: 2025-09-21 22:09:55
- **项目路径**: /Users/shiyijiufei/WahleFall/TaifishingV4
- **常量总数**: 33
- **使用文件数**: 4

## 🔍 常量使用统计

### 使用频率统计

| 常量名 | 使用次数 | 使用文件 |
|--------|----------|----------|
| PASSWORD_HASH_ROUNDS | 2 | 2 |
| DEFAULT_CACHE_TIMEOUT | 2 | 2 |
| MAX_FILE_SIZE | 2 | 2 |
| SESSION_LIFETIME | 2 | 2 |
| CONNECTION_TIMEOUT | 1 | 1 |
| MAX_CONNECTIONS | 1 | 1 |
| LOG_MAX_SIZE | 1 | 1 |
| LOG_BACKUP_COUNT | 1 | 1 |
| JWT_ACCESS_TOKEN_EXPIRES | 1 | 1 |
| JWT_REFRESH_TOKEN_EXPIRES | 1 | 1 |
| LOG_LEVEL | 1 | 1 |
| LOG_FILE | 1 | 1 |
| UPLOAD_FOLDER | 1 | 1 |
| SQL_SERVER_HOST | 1 | 1 |
| SQL_SERVER_PORT | 1 | 1 |
| MYSQL_HOST | 1 | 1 |
| MYSQL_PORT | 1 | 1 |
| ORACLE_HOST | 1 | 1 |
| ORACLE_PORT | 1 | 1 |
| DEFAULT_PAGE_SIZE | 1 | 1 |
| MAX_PAGE_SIZE | 1 | 1 |
| MIN_PAGE_SIZE | 1 | 1 |
| USER_PREFIX | 1 | 1 |
| INSTANCE_PREFIX | 1 | 1 |
| DASHBOARD_PREFIX | 1 | 1 |
| API_PREFIX | 1 | 1 |
| DEFAULT_PAGE | 1 | 1 |
| MAX_PER_PAGE | 1 | 1 |
| MIN_PER_PAGE | 1 | 1 |
| RATE_LIMIT_REQUESTS | 1 | 1 |
| RATE_LIMIT_WINDOW | 1 | 1 |
| LOGIN_RATE_LIMIT | 1 | 1 |
| LOGIN_RATE_WINDOW | 1 | 1 |

### 常量定义详情

### SystemConstants

| 常量名 | 值 | 类型 | 使用次数 | 描述 |
|--------|----|----|----------|------|
| DEFAULT_PAGE_SIZE | 20 | int | 1 | 默认分页大小 |
| MAX_PAGE_SIZE | 100 | int | 1 | 最大分页大小 |
| MIN_PAGE_SIZE | 1 | int | 1 | 无描述 |
| MIN_PASSWORD_LENGTH | 8 | int | 0 | 最小密码长度 |
| MAX_PASSWORD_LENGTH | 128 | int | 0 | 最大密码长度 |
| PASSWORD_HASH_ROUNDS | 12 | int | 2 | 密码哈希轮数 |
| DEFAULT_CACHE_TIMEOUT | 300 | int | 2 | 默认缓存超时时间 |
| LONG_CACHE_TIMEOUT | 3600 | int | 0 | 无描述 |
| SHORT_CACHE_TIMEOUT | 60 | int | 0 | 无描述 |
| MAX_FILE_SIZE | <ast.BinOp object at 0x1008f5c90> | str | 2 | 无描述 |
| ALLOWED_EXTENSIONS | <ast.Set object at 0x1008f5b40> | str | 0 | 无描述 |
| CONNECTION_TIMEOUT | 30 | int | 1 | 数据库连接超时时间 |
| QUERY_TIMEOUT | 60 | int | 0 | 无描述 |
| MAX_CONNECTIONS | 20 | int | 1 | 无描述 |
| CONNECTION_RETRY_ATTEMPTS | 3 | int | 0 | 无描述 |
| RATE_LIMIT_REQUESTS | 1000 | int | 1 | 无描述 |
| RATE_LIMIT_WINDOW | 300 | int | 1 | 无描述 |
| LOGIN_RATE_LIMIT | 999999 | int | 1 | 无描述 |
| LOGIN_RATE_WINDOW | 300 | int | 1 | 无描述 |
| LOG_MAX_SIZE | <ast.BinOp object at 0x1008f5510> | str | 1 | 无描述 |
| LOG_BACKUP_COUNT | 5 | int | 1 | 无描述 |
| LOG_RETENTION_DAYS | 30 | int | 0 | 无描述 |
| JWT_ACCESS_TOKEN_EXPIRES | 3600 | int | 1 | JWT访问令牌过期时间 |
| JWT_REFRESH_TOKEN_EXPIRES | 2592000 | int | 1 | 无描述 |
| SESSION_LIFETIME | 3600 | int | 2 | 会话生命周期 |
| REMEMBER_ME_LIFETIME | 2592000 | int | 0 | 无描述 |
| MAX_RETRY_ATTEMPTS | 3 | int | 0 | 最大重试次数 |
| RETRY_BASE_DELAY | 1.0 | float | 0 | 无描述 |
| RETRY_MAX_DELAY | 60.0 | float | 0 | 无描述 |
| SLOW_QUERY_THRESHOLD | 1.0 | float | 0 | 无描述 |
| SLOW_API_THRESHOLD | 2.0 | float | 0 | 无描述 |
| MEMORY_WARNING_THRESHOLD | 80 | int | 0 | 无描述 |
| CPU_WARNING_THRESHOLD | 80 | int | 0 | 无描述 |
| CSRF_TOKEN_LIFETIME | 3600 | int | 0 | 无描述 |
| PASSWORD_RESET_TOKEN_LIFETIME | 1800 | int | 0 | 无描述 |
| EMAIL_VERIFICATION_TOKEN_LIFETIME | 3600 | int | 0 | 无描述 |
| HEALTH_CHECK_INTERVAL | 30 | int | 0 | 无描述 |
| METRICS_COLLECTION_INTERVAL | 60 | int | 0 | 无描述 |
| ALERT_CHECK_INTERVAL | 300 | int | 0 | 无描述 |

### DefaultConfig

| 常量名 | 值 | 类型 | 使用次数 | 描述 |
|--------|----|----|----------|------|
| DATABASE_URL | None | NoneType | 0 | 无描述 |
| REDIS_URL | None | NoneType | 0 | 无描述 |
| SECRET_KEY | None | NoneType | 0 | 无描述 |
| JWT_SECRET_KEY | None | NoneType | 0 | 无描述 |
| DEBUG | True | bool | 0 | 无描述 |
| TESTING | False | bool | 0 | 无描述 |
| LOG_LEVEL | <ast.Attribute object at 0x1007c9a50> | str | 1 | 无描述 |
| LOG_FILE | userdata/logs/app.log | str | 1 | 无描述 |
| CACHE_TYPE | redis | str | 0 | 无描述 |
| CACHE_DEFAULT_TIMEOUT | <ast.Attribute object at 0x1007ca830> | str | 0 | 无描述 |
| BCRYPT_LOG_ROUNDS | <ast.Attribute object at 0x1007c9870> | str | 0 | 无描述 |
| WTF_CSRF_ENABLED | True | bool | 0 | 无描述 |
| SESSION_COOKIE_SECURE | False | bool | 0 | 无描述 |
| SESSION_COOKIE_HTTPONLY | True | bool | 0 | 无描述 |
| SESSION_COOKIE_SAMESITE | Lax | str | 0 | 无描述 |
| UPLOAD_FOLDER | userdata/uploads | str | 1 | 无描述 |
| MAX_CONTENT_LENGTH | <ast.Attribute object at 0x1007c94b0> | str | 0 | 无描述 |
| SQL_SERVER_HOST | localhost | str | 1 | 无描述 |
| SQL_SERVER_PORT | 1433 | int | 1 | 无描述 |
| MYSQL_HOST | localhost | str | 1 | 无描述 |
| MYSQL_PORT | 3306 | int | 1 | 无描述 |
| POSTGRES_HOST | localhost | str | 0 | 无描述 |
| POSTGRES_PORT | 5432 | int | 0 | 无描述 |
| ORACLE_HOST | localhost | str | 1 | 无描述 |
| ORACLE_PORT | 1521 | int | 1 | 无描述 |

### ErrorMessages

| 常量名 | 值 | 类型 | 使用次数 | 描述 |
|--------|----|----|----------|------|
| INTERNAL_ERROR | 服务器内部错误 | str | 0 | 无描述 |
| VALIDATION_ERROR | 数据验证失败 | str | 0 | 无描述 |
| PERMISSION_DENIED | 权限不足 | str | 0 | 无描述 |
| RESOURCE_NOT_FOUND | 资源不存在 | str | 0 | 无描述 |
| INVALID_REQUEST | 无效的请求 | str | 0 | 无描述 |
| INVALID_CREDENTIALS | 用户名或密码错误 | str | 0 | 无描述 |
| TOKEN_EXPIRED | 令牌已过期 | str | 0 | 无描述 |
| TOKEN_INVALID | 无效的令牌 | str | 0 | 无描述 |
| ACCOUNT_DISABLED | 账户已被禁用 | str | 0 | 无描述 |
| ACCOUNT_LOCKED | 账户已被锁定 | str | 0 | 无描述 |
| DATABASE_CONNECTION_ERROR | 数据库连接失败 | str | 0 | 无描述 |
| DATABASE_QUERY_ERROR | 数据库查询错误 | str | 0 | 无描述 |
| DATABASE_TIMEOUT | 数据库操作超时 | str | 0 | 无描述 |
| CONSTRAINT_VIOLATION | 数据约束错误 | str | 0 | 无描述 |
| FILE_TOO_LARGE | 文件过大 | str | 0 | 无描述 |
| INVALID_FILE_TYPE | 无效的文件类型 | str | 0 | 无描述 |
| FILE_UPLOAD_ERROR | 文件上传失败 | str | 0 | 无描述 |
| FILE_NOT_FOUND | 文件不存在 | str | 0 | 无描述 |
| INSTANCE_NOT_FOUND | 数据库实例不存在 | str | 0 | 无描述 |
| CREDENTIAL_INVALID | 凭据无效 | str | 0 | 无描述 |
| TASK_EXECUTION_FAILED | 任务执行失败 | str | 0 | 无描述 |
| SYNC_DATA_ERROR | 数据同步错误 | str | 0 | 无描述 |

### SuccessMessages

| 常量名 | 值 | 类型 | 使用次数 | 描述 |
|--------|----|----|----------|------|
| OPERATION_SUCCESS | 操作成功 | str | 0 | 无描述 |
| DATA_SAVED | 数据保存成功 | str | 0 | 无描述 |
| DATA_DELETED | 数据删除成功 | str | 0 | 无描述 |
| DATA_UPDATED | 数据更新成功 | str | 0 | 无描述 |
| LOGIN_SUCCESS | 登录成功 | str | 0 | 无描述 |
| LOGOUT_SUCCESS | 登出成功 | str | 0 | 无描述 |
| PASSWORD_CHANGED | 密码修改成功 | str | 0 | 无描述 |
| PROFILE_UPDATED | 资料更新成功 | str | 0 | 无描述 |
| INSTANCE_CREATED | 实例创建成功 | str | 0 | 无描述 |
| INSTANCE_UPDATED | 实例更新成功 | str | 0 | 无描述 |
| INSTANCE_DELETED | 实例删除成功 | str | 0 | 无描述 |
| TASK_CREATED | 任务创建成功 | str | 0 | 无描述 |
| TASK_EXECUTED | 任务执行成功 | str | 0 | 无描述 |
| SYNC_COMPLETED | 同步完成 | str | 0 | 无描述 |

### RegexPatterns

| 常量名 | 值 | 类型 | 使用次数 | 描述 |
|--------|----|----|----------|------|
| USERNAME_PATTERN | ^[a-zA-Z0-9_]{3,20}$ | str | 0 | 无描述 |
| EMAIL_PATTERN | ^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$ | str | 0 | 无描述 |
| PASSWORD_PATTERN | ^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)[a-zA-Z\d@$!%*?&]{8,}$ | str | 0 | 无描述 |
| IP_PATTERN | ^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$ | str | 0 | 无描述 |
| DATABASE_URL_PATTERN | ^(mysql|postgresql|sqlite|oracle|mssql)://.*$ | str | 0 | 无描述 |
| PORT_PATTERN | ^([1-9][0-9]{0,3}|[1-5][0-9]{4}|6[0-4][0-9]{3}|65[0-4][0-9]{2}|655[0-2][0-9]|6553[0-5])$ | str | 0 | 无描述 |

### DangerousPatterns

| 常量名 | 值 | 类型 | 使用次数 | 描述 |
|--------|----|----|----------|------|
| XSS_PATTERNS | ['<script[^>]*>.*?</script>', 'javascript:', 'vbscript:', 'on\\w+\\s*=', '<iframe[^>]*>', '<object[^>]*>', '<embed[^>]*>', '<link[^>]*>', '<meta[^>]*>', '<style[^>]*>'] | list | 0 | 无描述 |
| SQL_INJECTION_PATTERNS | ['(\\b(SELECT|INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|EXEC|UNION|SCRIPT)\\b)', '(\\b(OR|AND)\\b\\s+\\d+\\s*=\\s*\\d+)', "(\\b(OR|AND)\\b\\s+\\'\\w+\\'\\s*=\\s*\\'\\w+\\')", '(\\b(OR|AND)\\b\\s+\\w+\\s*=\\s*\\w+)'] | list | 0 | 无描述 |
| PATH_TRAVERSAL_PATTERNS | ['\\.\\./', '\\.\\.\\\\', '%2e%2e%2f', '%2e%2e%5c'] | list | 0 | 无描述 |

### FieldLengths

| 常量名 | 值 | 类型 | 使用次数 | 描述 |
|--------|----|----|----------|------|
| USERNAME_MAX_LENGTH | 255 | int | 0 | 无描述 |
| PASSWORD_HASH_LENGTH | 255 | int | 0 | 无描述 |
| ROLE_MAX_LENGTH | 50 | int | 0 | 无描述 |
| INSTANCE_NAME_MAX_LENGTH | 255 | int | 0 | 无描述 |
| INSTANCE_TYPE_MAX_LENGTH | 50 | int | 0 | 无描述 |
| HOST_MAX_LENGTH | 255 | int | 0 | 无描述 |
| PORT_MAX_LENGTH | 10 | int | 0 | 无描述 |
| DATABASE_NAME_MAX_LENGTH | 255 | int | 0 | 无描述 |
| CREDENTIAL_NAME_MAX_LENGTH | 255 | int | 0 | 无描述 |
| PASSWORD_MAX_LENGTH | 255 | int | 0 | 无描述 |
| LOG_LEVEL_MAX_LENGTH | 20 | int | 0 | 无描述 |
| LOG_TYPE_MAX_LENGTH | 50 | int | 0 | 无描述 |
| MODULE_MAX_LENGTH | 100 | int | 0 | 无描述 |
| IP_ADDRESS_MAX_LENGTH | 45 | int | 0 | 无描述 |
| TASK_NAME_MAX_LENGTH | 255 | int | 0 | 无描述 |
| TASK_TYPE_MAX_LENGTH | 50 | int | 0 | 无描述 |
| STATUS_MAX_LENGTH | 20 | int | 0 | 无描述 |
| PARAM_NAME_MAX_LENGTH | 255 | int | 0 | 无描述 |
| PARAM_TYPE_MAX_LENGTH | 50 | int | 0 | 无描述 |
| CATEGORY_MAX_LENGTH | 100 | int | 0 | 无描述 |

### CacheKeys

| 常量名 | 值 | 类型 | 使用次数 | 描述 |
|--------|----|----|----------|------|
| USER_PREFIX | user: | str | 1 | 无描述 |
| INSTANCE_PREFIX | instance: | str | 1 | 无描述 |
| CREDENTIAL_PREFIX | credential: | str | 0 | 无描述 |
| TASK_PREFIX | task: | str | 0 | 无描述 |
| LOG_PREFIX | log: | str | 0 | 无描述 |
| DASHBOARD_PREFIX | dashboard: | str | 1 | 无描述 |
| API_PREFIX | api: | str | 1 | 无描述 |
| HEALTH_PREFIX | health: | str | 0 | 无描述 |

### TimeFormats

| 常量名 | 值 | 类型 | 使用次数 | 描述 |
|--------|----|----|----------|------|
| DATETIME_FORMAT | %Y-%m-%d %H:%M:%S | str | 0 | 无描述 |
| DATE_FORMAT | %Y-%m-%d | str | 0 | 无描述 |
| TIME_FORMAT | %H:%M:%S | str | 0 | 无描述 |
| ISO_FORMAT | %Y-%m-%dT%H:%M:%S.%fZ | str | 0 | 无描述 |
| CHINESE_DATETIME_FORMAT | %Y年%m月%d日 %H:%M:%S | str | 0 | 无描述 |
| CHINESE_DATE_FORMAT | %Y年%m月%d日 | str | 0 | 无描述 |

### Pagination

| 常量名 | 值 | 类型 | 使用次数 | 描述 |
|--------|----|----|----------|------|
| DEFAULT_PAGE | 1 | int | 1 | 无描述 |
| DEFAULT_PER_PAGE | <ast.Attribute object at 0x1008f0130> | str | 0 | 无描述 |
| MAX_PER_PAGE | <ast.Attribute object at 0x1008f0070> | str | 1 | 无描述 |
| MIN_PER_PAGE | <ast.Attribute object at 0x100903f70> | str | 1 | 无描述 |

### LogLevel

| 常量名 | 值 | 类型 | 使用次数 | 描述 |
|--------|----|----|----------|------|
| DEBUG | DEBUG | str | 0 | 无描述 |
| INFO | INFO | str | 0 | 无描述 |
| WARNING | WARNING | str | 0 | 无描述 |
| ERROR | ERROR | str | 0 | 无描述 |
| CRITICAL | CRITICAL | str | 0 | 无描述 |

### LogType

| 常量名 | 值 | 类型 | 使用次数 | 描述 |
|--------|----|----|----------|------|
| OPERATION | operation | str | 0 | 无描述 |
| SYSTEM | system | str | 0 | 无描述 |
| ERROR | error | str | 0 | 无描述 |
| SECURITY | security | str | 0 | 无描述 |
| API | api | str | 0 | 无描述 |
| DATABASE | database | str | 0 | 无描述 |

### UserRole

| 常量名 | 值 | 类型 | 使用次数 | 描述 |
|--------|----|----|----------|------|
| ADMIN | admin | str | 0 | 无描述 |
| USER | user | str | 0 | 无描述 |
| VIEWER | viewer | str | 0 | 无描述 |

### TaskStatus

| 常量名 | 值 | 类型 | 使用次数 | 描述 |
|--------|----|----|----------|------|
| PENDING | pending | str | 0 | 无描述 |
| RUNNING | running | str | 0 | 无描述 |
| COMPLETED | completed | str | 0 | 无描述 |
| FAILED | failed | str | 0 | 无描述 |
| CANCELLED | cancelled | str | 0 | 无描述 |

### SyncType

| 常量名 | 值 | 类型 | 使用次数 | 描述 |
|--------|----|----|----------|------|
| MANUAL_SINGLE | manual_single | str | 0 | 无描述 |
| MANUAL_BATCH | manual_batch | str | 0 | 无描述 |
| MANUAL_TASK | manual_task | str | 0 | 无描述 |
| SCHEDULED_TASK | scheduled_task | str | 0 | 无描述 |


## 🚀 使用建议

### 高频使用常量

暂无高频使用常量

### 未使用常量

以下常量未被使用，建议考虑删除：

- `ACCOUNT_DISABLED`
- `ACCOUNT_LOCKED`
- `ALERT_CHECK_INTERVAL`
- `ALLOWED_EXTENSIONS`
- `BCRYPT_LOG_ROUNDS`
- `CACHE_DEFAULT_TIMEOUT`
- `CACHE_TYPE`
- `CATEGORY_MAX_LENGTH`
- `CHINESE_DATETIME_FORMAT`
- `CHINESE_DATE_FORMAT`
- `CONNECTION_RETRY_ATTEMPTS`
- `CONSTRAINT_VIOLATION`
- `CPU_WARNING_THRESHOLD`
- `CREDENTIAL_INVALID`
- `CREDENTIAL_NAME_MAX_LENGTH`
- `CREDENTIAL_PREFIX`
- `CSRF_TOKEN_LIFETIME`
- `DATABASE_CONNECTION_ERROR`
- `DATABASE_NAME_MAX_LENGTH`
- `DATABASE_QUERY_ERROR`
- `DATABASE_TIMEOUT`
- `DATABASE_URL`
- `DATABASE_URL_PATTERN`
- `DATA_DELETED`
- `DATA_SAVED`
- `DATA_UPDATED`
- `DATETIME_FORMAT`
- `DATE_FORMAT`
- `DEBUG`
- `DEFAULT_PER_PAGE`
- `EMAIL_PATTERN`
- `EMAIL_VERIFICATION_TOKEN_LIFETIME`
- `FILE_NOT_FOUND`
- `FILE_TOO_LARGE`
- `FILE_UPLOAD_ERROR`
- `HEALTH_CHECK_INTERVAL`
- `HEALTH_PREFIX`
- `HOST_MAX_LENGTH`
- `INSTANCE_CREATED`
- `INSTANCE_DELETED`
- `INSTANCE_NAME_MAX_LENGTH`
- `INSTANCE_NOT_FOUND`
- `INSTANCE_TYPE_MAX_LENGTH`
- `INSTANCE_UPDATED`
- `INTERNAL_ERROR`
- `INVALID_CREDENTIALS`
- `INVALID_FILE_TYPE`
- `INVALID_REQUEST`
- `IP_ADDRESS_MAX_LENGTH`
- `IP_PATTERN`
- `ISO_FORMAT`
- `JWT_SECRET_KEY`
- `LOGIN_SUCCESS`
- `LOGOUT_SUCCESS`
- `LOG_LEVEL_MAX_LENGTH`
- `LOG_PREFIX`
- `LOG_RETENTION_DAYS`
- `LOG_TYPE_MAX_LENGTH`
- `LONG_CACHE_TIMEOUT`
- `MAX_CONTENT_LENGTH`
- `MAX_PASSWORD_LENGTH`
- `MAX_RETRY_ATTEMPTS`
- `MEMORY_WARNING_THRESHOLD`
- `METRICS_COLLECTION_INTERVAL`
- `MIN_PASSWORD_LENGTH`
- `MODULE_MAX_LENGTH`
- `OPERATION_SUCCESS`
- `PARAM_NAME_MAX_LENGTH`
- `PARAM_TYPE_MAX_LENGTH`
- `PASSWORD_CHANGED`
- `PASSWORD_HASH_LENGTH`
- `PASSWORD_MAX_LENGTH`
- `PASSWORD_PATTERN`
- `PASSWORD_RESET_TOKEN_LIFETIME`
- `PATH_TRAVERSAL_PATTERNS`
- `PERMISSION_DENIED`
- `PORT_MAX_LENGTH`
- `PORT_PATTERN`
- `POSTGRES_HOST`
- `POSTGRES_PORT`
- `PROFILE_UPDATED`
- `QUERY_TIMEOUT`
- `REDIS_URL`
- `REMEMBER_ME_LIFETIME`
- `RESOURCE_NOT_FOUND`
- `RETRY_BASE_DELAY`
- `RETRY_MAX_DELAY`
- `ROLE_MAX_LENGTH`
- `SECRET_KEY`
- `SESSION_COOKIE_HTTPONLY`
- `SESSION_COOKIE_SAMESITE`
- `SESSION_COOKIE_SECURE`
- `SHORT_CACHE_TIMEOUT`
- `SLOW_API_THRESHOLD`
- `SLOW_QUERY_THRESHOLD`
- `SQL_INJECTION_PATTERNS`
- `STATUS_MAX_LENGTH`
- `SYNC_COMPLETED`
- `SYNC_DATA_ERROR`
- `TASK_CREATED`
- `TASK_EXECUTED`
- `TASK_EXECUTION_FAILED`
- `TASK_NAME_MAX_LENGTH`
- `TASK_PREFIX`
- `TASK_TYPE_MAX_LENGTH`
- `TESTING`
- `TIME_FORMAT`
- `TOKEN_EXPIRED`
- `TOKEN_INVALID`
- `USERNAME_MAX_LENGTH`
- `USERNAME_PATTERN`
- `VALIDATION_ERROR`
- `WTF_CSRF_ENABLED`
- `XSS_PATTERNS`

### 优化建议

1. **统一常量命名**: 确保常量命名规范一致
2. **添加常量注释**: 为每个常量添加详细注释
3. **优化常量组织**: 按功能模块重新组织常量
4. **清理未使用常量**: 删除未使用的常量定义
5. **添加常量验证**: 为常量值添加验证机制
