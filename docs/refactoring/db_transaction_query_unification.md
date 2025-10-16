# 数据库事务与查询模式统一方案

目标
- 写操作统一使用事务封装，确保提交/回滚一致与日志一致。
- 列表查询统一分页，避免 `all()` 全量返回。

事务统一
- 使用 `app/utils/db_context.py`（如有）或统一封装的事务管理器。
- 写操作异常统一走 `enhanced_error_handler` 并记录结构化日志。

查询统一
- 分页：`query.paginate(page=page, per_page=per_page, error_out=False)`。
- 过滤：统一参数 `q`, `sort_by`, `order`；避免在路由分散拼接。

示例
```python
def write_something():
    try:
        db.session.add(model)
        db.session.commit()
        return APIResponse.success_response(message="保存成功")
    except Exception as e:
        db.session.rollback()
        return APIResponse.error_response(message=str(e), code="SYSTEM_ERROR", status_code=500)
```

迁移步骤
1) 写操作补齐提交/回滚；异常统一映射错误码。
2) 列表统一分页与排序；为大数据场景提供筛选参数。

## 涉及代码位置
- `app/utils/db_context.py`
- `app/routes/*.py`
- `app/services/*.py`
- `app/models/*.py`（查询模型与分页字段）

---

## 事务细则
- 封装统一事务接口（示例）：
  - `db_context.transaction()` 或 `atomic()` 提供 `begin/commit/rollback` 语义；
  - 在异常时统一映射错误码与日志；
  - 禁止在业务层散落 `commit/rollback`，通过上下文集中管理。
- 幂等与重试：
  - 对外部依赖（网络/存储）建议在事务外进行重试；避免长事务持锁。
  - 在需要时采用乐观锁（版本号）或悲观锁（`SELECT ... FOR UPDATE`）策略，依据模型与负载评估。

## 查询与分页细则
- 标准分页：`paginate(page=page, per_page=per_page, error_out=False)`，返回 `items/total/pages`。
- 排序字段白名单：仅允许模型定义的字段；默认 `created_at desc`。
- 过滤：统一使用参数 `q/sort_by/order` 与必要字段过滤；避免拼接原始 SQL。
- 大页保护：`per_page` 最大 100；若前端需要导出大数据，走异步任务与文件下载。

## 示例：统一事务与查询
```python
from app.utils.api_response import APIResponse
from app.utils import db_context

def create_model(payload):
    try:
        with db_context.transaction() as session:
            m = Model(**payload)
            session.add(m)
        return APIResponse.success_response(message="保存成功")
    except Exception as e:
        return APIResponse.error_response(code="SYSTEM_ERROR", message=str(e), status_code=500)

def list_models(page=1, per_page=20, q=None, sort_by="created_at", order="desc"):
    query = Model.query
    if q:
        query = query.filter(Model.name.ilike(f"%{q}%"))
    # 排序与分页（字段白名单校验在调用前完成）
    if order == "desc":
        query = query.order_by(getattr(Model, sort_by).desc())
    else:
        query = query.order_by(getattr(Model, sort_by).asc())
    page_obj = query.paginate(page=page, per_page=per_page, error_out=False)
    return APIResponse.success_response(data={
        "items": [i.to_dict() for i in page_obj.items],
        "total": page_obj.total,
        "pages": page_obj.pages,
    })
```

## 迁移清单
1) 写操作统一迁移到事务封装；移除散落的 `commit/rollback`。
2) 列表接口统一分页与排序；增加字段白名单校验，避免越权或 SQL 注入风险。
3) 对需要强一致性的更新操作评估锁策略；避免长事务导致性能抖动。

## 验收标准
- 随机抽取 5 个写接口：异常时均能统一错误结构与日志；成功路径不留未提交风险。
- 随机抽取 5 个列表接口：分页/排序一致；`per_page` 上限生效，`error_out=False` 无异常抛出。
- 有锁场景评估通过（无长事务报警），并在日志中能观察到锁等待与耗时。

## 风险与回退
- 风险：统一事务可能影响现有提交时序；需灰度上线并监控锁等待与吞吐。
- 回退：对有问题的接口恢复原事务策略，并收敛到统一封装的兼容模式，逐步合并。