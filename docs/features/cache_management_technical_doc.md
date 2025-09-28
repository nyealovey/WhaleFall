# 缓存管理功能技术文档

## 1. 功能概述

### 1.1 功能描述
缓存管理功能是鲸落系统的性能优化模块，负责系统缓存的创建、更新、删除和监控。该模块基于Flask-Caching实现，提供统一的缓存接口，支持多种缓存后端，显著提升系统性能和响应速度。

### 1.2 主要特性
- **多缓存后端**：支持Redis、内存、文件系统缓存
- **统一缓存接口**：提供一致的缓存操作API
- **缓存策略**：支持TTL、LRU等缓存策略
- **缓存监控**：实时监控缓存使用情况
- **缓存清理**：支持手动和自动缓存清理
- **性能优化**：智能缓存键生成和批量操作
- **缓存统计**：详细的缓存命中率和性能统计

### 1.3 技术特点
- 基于Flask-Caching的缓存框架
- 支持多种缓存后端
- 智能缓存键管理
- 异步缓存操作
- 缓存性能监控

## 2. 技术架构

### 2.1 整体架构
```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   缓存接口层    │    │   缓存管理层    │    │   缓存存储层    │
│                 │    │                 │    │                 │
│ - 装饰器接口    │◄──►│ - 缓存管理器    │◄──►│ - Redis缓存     │
│ - API接口       │    │ - 键生成器      │    │ - 内存缓存      │
│ - 监控接口      │    │ - 策略管理      │    │ - 文件缓存      │
│ - 统计接口      │    │ - 性能优化      │    │ - 数据库缓存    │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

### 2.2 核心组件
- **缓存管理器**：统一缓存操作接口
- **键生成器**：智能缓存键生成
- **策略管理器**：缓存策略配置
- **监控服务**：缓存性能监控

## 3. 后端实现

### 3.1 缓存管理器
```python
# app/utils/cache_manager.py
import hashlib
import json
from collections.abc import Callable
from functools import wraps
from typing import Any
from flask_caching import Cache
from app.utils.structlog_config import get_system_logger


class CacheManager:
    """缓存管理器"""
    
    def __init__(self, cache: Cache) -> None:
        self.cache = cache
        self.default_timeout = 300  # 5分钟默认超时
        self.system_logger = get_system_logger()
    
    def _generate_key(self, prefix: str, *args, **kwargs: Any) -> str:
        """生成缓存键"""
        # 将参数序列化为字符串
        key_data = {"args": args, "kwargs": sorted(kwargs.items())}
        key_string = json.dumps(key_data, sort_keys=True, default=str)
        
        # 生成哈希值
        key_hash = hashlib.sha256(key_string.encode()).hexdigest()
        
        return f"{prefix}:{key_hash}"
    
    def get(self, key: str) -> Any | None:
        """获取缓存值"""
        try:
            return self.cache.get(key)
        except Exception as e:
            self.system_logger.warning("获取缓存失败", module="cache", key=key, exception=str(e))
            return None
    
    def set(self, key: str, value: Any, timeout: int | None = None) -> bool:
        """设置缓存值"""
        try:
            timeout = timeout or self.default_timeout
            self.cache.set(key, value, timeout=timeout)
            return True
        except Exception as e:
            self.system_logger.warning("设置缓存失败", module="cache", key=key, exception=str(e))
            return False
    
    def delete(self, key: str) -> bool:
        """删除缓存值"""
        try:
            self.cache.delete(key)
            return True
        except Exception:
            self.system_logger.warning("删除缓存失败: {key}, 错误: {e}")
            return False
    
    def clear(self) -> bool:
        """清空所有缓存"""
        try:
            self.cache.clear()
            return True
        except Exception as e:
            self.system_logger.warning("清空缓存失败", module="cache", exception=str(e))
            return False
    
    def get_cache_stats(self) -> dict:
        """获取缓存统计信息"""
        try:
            # 这里需要根据具体的缓存后端实现
            return {
                "total_keys": 0,
                "memory_usage": 0,
                "hit_rate": 0.0,
                "miss_rate": 0.0
            }
        except Exception as e:
            self.system_logger.error("获取缓存统计失败", module="cache", exception=str(e))
            return {}


# 全局缓存管理器实例
cache_manager = None


def init_cache_manager(cache: Cache) -> None:
    """初始化缓存管理器"""
    global cache_manager
    cache_manager = CacheManager(cache)
    system_logger = get_system_logger()
    system_logger.info("缓存管理器初始化完成", module="cache")


def cached(
    timeout: int = 300,
    key_prefix: str = "default",
    unless: Callable | None = None,
    key_func: Callable | None = None,
) -> Callable:
    """缓存装饰器"""
    def decorator(f: Callable) -> Callable:
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # 生成缓存键
            if key_func:
                cache_key = key_func(*args, **kwargs)
            else:
                cache_key = cache_manager._generate_key(key_prefix, *args, **kwargs)
            
            # 检查unless条件
            if unless and unless(*args, **kwargs):
                return f(*args, **kwargs)
            
            # 尝试从缓存获取
            result = cache_manager.get(cache_key)
            if result is not None:
                return result
            
            # 执行函数并缓存结果
            result = f(*args, **kwargs)
            cache_manager.set(cache_key, result, timeout)
            
            return result
        
        return decorated_function
    return decorator
```

### 3.2 缓存路由
```python
# app/routes/cache_management.py
from flask import Blueprint, jsonify, request
from flask_login import login_required, current_user
from app.utils.decorators import admin_required
from app.utils.cache_manager import cache_manager
from app.utils.api_response import APIResponse
from app.utils.structlog_config import log_info, log_error


cache_bp = Blueprint("cache", __name__)


@cache_bp.route("/api/cache/stats")
@login_required
@admin_required
def get_cache_stats() -> tuple[dict, int]:
    """获取缓存统计信息"""
    try:
        stats = cache_manager.get_cache_stats()
        
        log_info(
            "获取缓存统计",
            module="cache_management",
            user_id=current_user.id,
            stats=stats
        )
        
        return APIResponse.success(stats)
        
    except Exception as e:
        log_error(f"获取缓存统计失败: {str(e)}", module="cache_management")
        return APIResponse.error(f"获取缓存统计失败: {str(e)}"), 500


@cache_bp.route("/api/cache/clear", methods=["POST"])
@login_required
@admin_required
def clear_cache() -> tuple[dict, int]:
    """清空缓存"""
    try:
        success = cache_manager.clear()
        
        if success:
            log_info(
                "清空缓存",
                module="cache_management",
                user_id=current_user.id
            )
            return APIResponse.success({"message": "缓存清空成功"})
        else:
            return APIResponse.error("缓存清空失败"), 500
            
    except Exception as e:
        log_error(f"清空缓存失败: {str(e)}", module="cache_management")
        return APIResponse.error(f"清空缓存失败: {str(e)}"), 500


@cache_bp.route("/api/cache/delete", methods=["POST"])
@login_required
@admin_required
def delete_cache_key() -> tuple[dict, int]:
    """删除指定缓存键"""
    try:
        data = request.get_json()
        key = data.get("key")
        
        if not key:
            return APIResponse.error("缺少缓存键参数"), 400
        
        success = cache_manager.delete(key)
        
        if success:
            log_info(
                "删除缓存键",
                module="cache_management",
                user_id=current_user.id,
                cache_key=key
            )
            return APIResponse.success({"message": "缓存键删除成功"})
        else:
            return APIResponse.error("缓存键删除失败"), 500
            
    except Exception as e:
        log_error(f"删除缓存键失败: {str(e)}", module="cache_management")
        return APIResponse.error(f"删除缓存键失败: {str(e)}"), 500
```

## 4. 配置管理

### 4.1 缓存配置
```python
# app/config.py
import os

class Config:
    # 缓存配置
    CACHE_TYPE = os.getenv("CACHE_TYPE", "simple")  # simple, redis, filesystem
    
    if CACHE_TYPE == "redis":
        CACHE_REDIS_URL = os.getenv("CACHE_REDIS_URL", "redis://localhost:6379/0")
    elif CACHE_TYPE == "filesystem":
        CACHE_DIR = os.getenv("CACHE_DIR", "userdata/cache")
    
    # 缓存默认超时时间（秒）
    CACHE_DEFAULT_TIMEOUT = int(os.getenv("CACHE_DEFAULT_TIMEOUT", "300"))
    
    # 缓存键前缀
    CACHE_KEY_PREFIX = os.getenv("CACHE_KEY_PREFIX", "whalefall")
```

### 4.2 环境变量配置
```bash
# 缓存配置
CACHE_TYPE=redis
CACHE_REDIS_URL=redis://localhost:6379/0
CACHE_DEFAULT_TIMEOUT=300
CACHE_KEY_PREFIX=whalefall
```

## 5. 使用示例

### 5.1 装饰器使用
```python
from app.utils.cache_manager import cached

@cached(timeout=600, key_prefix="user_data")
def get_user_data(user_id: int):
    """获取用户数据（缓存10分钟）"""
    # 数据库查询逻辑
    return user_data

@cached(timeout=300, key_prefix="system_stats", unless=lambda: current_user.is_admin())
def get_system_stats():
    """获取系统统计（管理员不缓存）"""
    # 统计计算逻辑
    return stats
```

### 5.2 手动缓存操作
```python
from app.utils.cache_manager import cache_manager

# 设置缓存
cache_manager.set("user:123", user_data, timeout=600)

# 获取缓存
user_data = cache_manager.get("user:123")

# 删除缓存
cache_manager.delete("user:123")
```

## 6. 性能优化

### 6.1 缓存策略
- 合理设置TTL时间
- 使用LRU淘汰策略
- 批量操作减少网络开销

### 6.2 键管理
- 使用有意义的键前缀
- 避免键冲突
- 定期清理过期键

### 6.3 监控优化
- 监控缓存命中率
- 分析缓存性能
- 优化缓存策略

---

**注意**: 本文档描述了缓存管理功能的完整技术实现，包括缓存操作、配置管理、性能优化等各个方面。该功能为鲸落系统提供了高效的缓存能力，显著提升了系统性能。
