# Oracle 账户同步重复问题修复

## 1. 问题背景

在 Oracle 数据库的账户同步过程中，发现存在重复同步的问题。当 `DBA_USERS` 和 `ALL_USERS` 视图中存在相同的用户名时，系统会将同一个账户同步两次，导致数据冗余和不一致。

**问题原因**: 同步逻辑分别查询了 `DBA_USERS` 和 `ALL_USERS`，并且没有进行有效的去重处理。

## 2. 解决方案

为了解决该问题，我们优化了 Oracle 账户的同步查询逻辑，通过 `UNION` 操作对两个视图的结果进行合并和去重。

### 优化后的查询

```sql
SELECT username FROM DBA_USERS
UNION
SELECT username FROM ALL_USERS
```

通过 `UNION` 操作，数据库会自动去除重复的用户名，确保每个账户只会被同步一次。

### 同步逻辑调整

在同步适配器 `OracleSyncAdapter` 中，我们更新了获取账户列表的方法，采用了上述的 `UNION` 查询。

```python
# app/services/sync_adapters/oracle.py

class OracleSyncAdapter:
    def get_accounts(self):
        # ...
        query = "SELECT username FROM DBA_USERS UNION SELECT username FROM ALL_USERS"
        # ...
```

## 3. 修复效果

- **数据不再重复**: 同步过程中，每个 Oracle 账户只会被创建或更新一次，消除了数据冗余。
- **同步效率提升**: 减少了不必要的数据处理，略微提升了同步性能。
- **数据一致性增强**: 保证了账户列表的准确性和一致性。