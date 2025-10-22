"""
标准API接口实现模板

这些模板展示了统一验证规范的标准实现方式，可以作为开发新接口或重构旧接口的参考。
"""

from flask import Blueprint, request
from app import db
from app.utils.decorators import validate_json, create_required, update_required, delete_required, view_required
from app.utils.data_validator import DataValidator
from app.utils.response_utils import jsonify_unified_success
from app.errors import ValidationError, NotFoundError

# 创建示例蓝图
blueprint = Blueprint("resource", __name__)


# ============================================================================
# 模板1: JSON写接口（POST）
# ============================================================================

@blueprint.route("/api/resources", methods=["POST"])
@validate_json(required_fields=["name", "host", "port"])
@create_required
def create_resource():
    """
    创建资源接口模板
    
    装饰器顺序：
    1. @validate_json - 验证JSON格式和必填字段
    2. @create_required - 验证创建权限
    """
    # 1. 获取数据（已经过 @validate_json 验证）
    data = request.get_json()
    
    # 2. 清理输入
    data = DataValidator.sanitize_input(data)
    
    # 3. 领域数据验证
    is_valid, error_msg = DataValidator.validate_instance_data(data)
    if not is_valid:
        raise ValidationError(error_msg)
    
    # 4. 业务逻辑
    # resource = Resource(**data)
    # db.session.add(resource)
    # db.session.commit()
    
    # 5. 返回成功响应
    return jsonify_unified_success(
        data={"id": 1, "name": data["name"]},
        message="创建成功"
    )


# ============================================================================
# 模板2: 查询接口（GET）
# ============================================================================

@blueprint.route("/api/resources")
@view_required
def list_resources():
    """
    查询资源列表接口模板
    
    特点：
    - 使用 type 参数安全转换类型
    - 参数验证使用异常抛出
    - 统一的分页响应格式
    """
    # 1. 获取参数（使用 type 参数安全转换）
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 20, type=int)
    search = request.args.get("search", "").strip()
    status = request.args.get("status", "").strip()
    
    # 2. 参数验证
    if page < 1:
        raise ValidationError("页码必须大于0")
    if per_page < 1 or per_page > 100:
        raise ValidationError("每页数量必须在1-100之间")
    
    # 3. 构建查询
    # query = Resource.query
    # 
    # if search:
    #     query = query.filter(Resource.name.contains(search))
    # 
    # if status:
    #     query = query.filter(Resource.status == status)
    
    # 4. 分页
    # pagination = query.paginate(
    #     page=page,
    #     per_page=per_page,
    #     error_out=False
    # )
    
    # 5. 返回响应
    return jsonify_unified_success(
        data={
            "items": [],  # [item.to_dict() for item in pagination.items]
            "pagination": {
                "page": page,
                "per_page": per_page,
                "total": 0,
                "pages": 0,
                "has_next": False,
                "has_prev": False
            }
        }
    )


# ============================================================================
# 模板3: 更新接口（PUT/PATCH）
# ============================================================================

@blueprint.route("/api/resources/<int:resource_id>", methods=["PUT"])
@validate_json(required_fields=["name"])
@update_required
def update_resource(resource_id: int):
    """
    更新资源接口模板
    
    特点：
    - 先检查资源是否存在
    - 验证数据后再更新
    - 使用 NotFoundError 处理资源不存在
    """
    # 1. 查找资源
    # resource = Resource.query.get(resource_id)
    # if not resource:
    #     raise NotFoundError("资源不存在")
    
    # 2. 获取并清理数据
    data = request.get_json()
    data = DataValidator.sanitize_input(data)
    
    # 3. 验证数据
    is_valid, error_msg = DataValidator.validate_instance_data(data)
    if not is_valid:
        raise ValidationError(error_msg)
    
    # 4. 更新资源
    # for key, value in data.items():
    #     if hasattr(resource, key):
    #         setattr(resource, key, value)
    # 
    # db.session.commit()
    
    # 5. 返回成功响应
    return jsonify_unified_success(
        data={"id": resource_id, "name": data["name"]},
        message="更新成功"
    )


# ============================================================================
# 模板4: 删除接口（DELETE）
# ============================================================================

@blueprint.route("/api/resources/<int:resource_id>", methods=["DELETE"])
@delete_required
def delete_resource(resource_id: int):
    """
    删除资源接口模板
    
    特点：
    - 简洁的删除逻辑
    - 使用 NotFoundError 处理资源不存在
    - 返回简单的成功消息
    """
    # 1. 查找资源
    # resource = Resource.query.get(resource_id)
    # if not resource:
    #     raise NotFoundError("资源不存在")
    
    # 2. 删除资源
    # db.session.delete(resource)
    # db.session.commit()
    
    # 3. 返回成功响应
    return jsonify_unified_success(message="删除成功")


# ============================================================================
# 模板5: 批量操作接口（POST）
# ============================================================================

@blueprint.route("/api/resources/batch", methods=["POST"])
@validate_json(required_fields=["ids", "action"])
@update_required
def batch_operation():
    """
    批量操作接口模板
    
    特点：
    - 验证批量数据
    - 统计操作结果
    - 返回详细的操作统计
    """
    # 1. 获取数据
    data = request.get_json()
    ids = data.get("ids", [])
    action = data.get("action")
    
    # 2. 验证参数
    if not isinstance(ids, list) or not ids:
        raise ValidationError("ids 必须是非空数组")
    
    if action not in ["enable", "disable", "delete"]:
        raise ValidationError("不支持的操作类型")
    
    # 3. 执行批量操作
    success_count = 0
    failed_count = 0
    
    # for resource_id in ids:
    #     try:
    #         resource = Resource.query.get(resource_id)
    #         if resource:
    #             if action == "enable":
    #                 resource.is_active = True
    #             elif action == "disable":
    #                 resource.is_active = False
    #             elif action == "delete":
    #                 db.session.delete(resource)
    #             success_count += 1
    #         else:
    #             failed_count += 1
    #     except Exception:
    #         failed_count += 1
    # 
    # db.session.commit()
    
    # 4. 返回操作结果
    return jsonify_unified_success(
        data={
            "total": len(ids),
            "success": success_count,
            "failed": failed_count
        },
        message=f"批量操作完成，成功 {success_count} 个，失败 {failed_count} 个"
    )


# ============================================================================
# 反面示例：不要这样写
# ============================================================================

def bad_example_create():
    """
    ❌ 错误示例：不要这样写
    
    问题：
    1. 缺少装饰器验证
    2. 使用内联错误返回
    3. 不安全的类型转换
    4. 没有数据清理
    """
    # ❌ 缺少 @validate_json 装饰器
    data = request.get_json()
    
    # ❌ 内联错误返回
    if not data:
        return {"error": "数据不能为空"}, 400
    
    # ❌ 没有验证必填字段
    if not data.get("name"):
        return {"error": "名称不能为空"}, 400
    
    # ❌ 没有数据清理
    # resource = Resource(**data)
    
    return {"success": True, "data": {}}, 200


def bad_example_list():
    """
    ❌ 错误示例：不要这样写
    
    问题：
    1. 不安全的类型转换
    2. 没有参数验证
    3. 响应格式不统一
    """
    # ❌ 不安全的类型转换（可能抛出 ValueError）
    page = int(request.args.get("page", 1))
    per_page = int(request.args.get("per_page", 20))
    
    # ❌ 没有参数验证
    # query = Resource.query.paginate(page=page, per_page=per_page)
    
    # ❌ 响应格式不统一
    return {
        "code": 200,
        "data": [],
        "msg": "success"
    }
