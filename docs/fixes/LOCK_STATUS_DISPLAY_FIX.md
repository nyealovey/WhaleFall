# 修复锁定状态显示不一致问题

## 1. 问题背景

在旧版本中，不同数据库（如 Oracle, PostgreSQL, SQL Server）对账户“锁定”状态的定义和展示方式存在差异，导致在账户列表页面上，“锁定状态”的显示不统一，容易引起用户混淆。

- **Oracle**: 通过 `ACCOUNT_STATUS` 字段判断，`LOCKED` 或 `EXPIRED & LOCKED` 表示锁定。
- **PostgreSQL**: 没有内置的账户锁定状态，通常通过自定义逻辑实现。
- **SQL Server**: 通过 `is_disabled` 字段判断。

这种不一致性使得用户难以准确判断账户的真实状态。

## 2. 解决方案

为了解决此问题，我们引入了 `is_active` 字段作为统一的账户状态标识。

- **`is_active = True`**: 表示账户“正常”，可以正常登录和使用。
- **`is_active = False`**: 表示账户“非活跃”，等同于“锁定”或“禁用”，无法登录。

### 统一状态同步逻辑

在账户数据同步过程中，我们对不同数据库的原始状态进行了归一化处理：

```python
# Oracle 状态转换
if account_status in ['LOCKED', 'EXPIRED & LOCKED']:
    is_active = False
else:
    is_active = True

# SQL Server 状态转换
is_active = not is_disabled
```

通过这种方式，无论底层数据库如何定义锁定状态，最终都转换为统一的 `is_active` 状态。

### 更新UI显示

在前端模板中，我们调整了显示逻辑，统一使用 `is_active` 字段来判断和展示账户状态：

```html
{% if account.is_active %}
    <span class="badge bg-success">正常</span>
{% else %}
    <span class="badge bg-danger">非活跃</span>
{% endif %}
```

## 3. 修复效果

- **状态显示统一**: 所有数据库的账户状态都以“正常”和“非活跃”两种形式展示，清晰明了。
- **筛选逻辑简化**: “账户状态”筛选器现在基于 `is_active` 字段工作，逻辑更简单，结果更准确。
- **用户体验改善**: 避免了因状态定义不一致带来的混淆，提升了系统的易用性。