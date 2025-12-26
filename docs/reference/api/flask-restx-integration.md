# Flask-RESTX（`marshal/fields`）使用说明

> 状态：Active  
> 负责人：WhaleFall Team  
> 创建：2025-12-25  
> 更新：2025-12-26  
> 范围：`app/routes/**` 的输出序列化（Response payload 白名单）  
> 关联：`../../standards/backend/api-response-envelope.md`；`../../standards/backend/sensitive-data-handling.md`

## 字段/参数表

WhaleFall 当前使用 `flask-restx` 的方式为：**仅使用 `fields` + `marshal` 定义/应用“输出字段白名单”**。

| 组件 | 位置（示例） | 用途 |
| --- | --- | --- |
| `flask_restx.fields` | `app/routes/*_restx_models.py` | 声明响应字段结构（白名单） |
| `flask_restx.marshal` | `app/routes/**/*.py` | 将 dict/list 按字段定义进行序列化/裁剪 |
| RestX 模型文件 | `app/routes/accounts/restx_models.py` 等 | 以“域”为单位集中维护字段定义 |

当前仓库内的 RestX 模型文件（以实际代码为准）：

- `app/routes/accounts/restx_models.py`
- `app/routes/capacity/restx_models.py`
- `app/routes/common_restx_models.py`
- `app/routes/credentials_restx_models.py`
- `app/routes/dashboard_restx_models.py`
- `app/routes/databases/restx_models.py`
- `app/routes/history/restx_models.py`
- `app/routes/instances/restx_models.py`
- `app/routes/partition_restx_models.py`
- `app/routes/scheduler_restx_models.py`
- `app/routes/tags/restx_models.py`
- `app/routes/users_restx_models.py`

## 默认值/约束

- 当前项目**未启用** `Api/Namespace/Swagger UI/OpenAPI`：仓库内不存在 `/api/docs`、`/api/swagger.json` 等 RestX 自动文档端点（如需启用，应另行设计并补充运维/回滚说明）。
- `marshal(...)` 仅负责生成“字段白名单后的 payload”，不负责 JSON 封套；对外 API 仍必须通过 `app/utils/response_utils.py` 的 `jsonify_unified_success(...)` 返回统一封套（见 `../../standards/backend/api-response-envelope.md`）。
- 字段定义应遵循敏感数据处理标准：禁止在 payload 中输出密钥/口令/可逆密文等（见 `../../standards/backend/sensitive-data-handling.md`）。

## 示例

在路由中使用 `marshal + jsonify_unified_success` 的最小示例：

```python
from flask_restx import marshal

from app.routes.users_restx_models import USER_LIST_ITEM_FIELDS
from app.utils.response_utils import jsonify_unified_success

payload = marshal(user.to_dict(), USER_LIST_ITEM_FIELDS)
return jsonify_unified_success(data=payload)
```

## 版本/兼容性说明

- 字段演进建议优先“新增字段”保持向前兼容，避免直接重命名/挪字段导致调用方写兼容分支。
- 如必须兼容历史字段结构，只允许在边界层做一次规范化（canonicalization），避免将兼容逻辑扩散到服务层/路由层/前端多处（参见 `../../standards/backend/error-message-schema-unification.md`）。

## 常见错误

- `marshal` 输出为空或字段缺失：通常是字段定义未覆盖、或输入 payload 的 key/类型与字段定义不匹配。
- 输出意外包含敏感信息：字段白名单未收敛；应回到 `*_restx_models.py` 移除/替换敏感字段，并补充脱敏逻辑。
