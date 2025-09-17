"""
泰摸鱼吧 - 缓存管理器
提供统一的缓存接口，支持Redis缓存操作
"""

import json
import hashlib
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime, timedelta

import redis
from app.config import Config
from app.utils.structlog_config import get_logger

logger = get_logger("cache_manager")


class CacheManager:
    """缓存管理器"""
    
    def __init__(self):
        self.redis_client = redis.from_url(Config.CACHE_REDIS_URL)
        self.default_ttl = 7 * 24 * 3600  # 7天，按用户要求
        
    def _generate_cache_key(self, prefix: str, instance_id: int, username: str, db_name: str = None) -> str:
        """生成缓存键"""
        if db_name:
            key_data = f"{prefix}:{instance_id}:{username}:{db_name}"
        else:
            key_data = f"{prefix}:{instance_id}:{username}"
        
        # 使用MD5哈希确保键名长度合理
        key_hash = hashlib.md5(key_data.encode()).hexdigest()
        return f"taifish:{key_hash}"
    
    def get_database_permissions_cache(self, instance_id: int, username: str, db_name: str) -> Optional[Tuple[List[str], List[str]]]:
        """获取数据库权限缓存"""
        try:
            cache_key = self._generate_cache_key("db_perms", instance_id, username, db_name)
            cached_data = self.redis_client.get(cache_key)
            
            if cached_data:
                data = json.loads(cached_data)
                roles = data.get('roles', [])
                permissions = data.get('permissions', [])
                logger.debug(f"缓存命中: {username}@{db_name}", cache_key=cache_key)
                return roles, permissions
            
            return None
            
        except Exception as e:
            logger.warning(f"获取缓存失败: {username}@{db_name}", error=str(e))
            return None
    
    def set_database_permissions_cache(self, instance_id: int, username: str, db_name: str, 
                                    roles: List[str], permissions: List[str], ttl: int = None) -> bool:
        """设置数据库权限缓存"""
        try:
            cache_key = self._generate_cache_key("db_perms", instance_id, username, db_name)
            cache_data = {
                'roles': roles,
                'permissions': permissions,
                'cached_at': datetime.now().isoformat(),
                'instance_id': instance_id,
                'username': username,
                'db_name': db_name
            }
            
            ttl = ttl or self.default_ttl
            self.redis_client.setex(cache_key, ttl, json.dumps(cache_data, ensure_ascii=False))
            logger.debug(f"缓存已设置: {username}@{db_name}", cache_key=cache_key, ttl=ttl)
            return True
            
        except Exception as e:
            logger.warning(f"设置缓存失败: {username}@{db_name}", error=str(e))
            return False
    
    def get_all_database_permissions_cache(self, instance_id: int, username: str) -> Optional[Dict[str, Tuple[List[str], List[str]]]]:
        """获取用户所有数据库权限缓存"""
        try:
            pattern = f"taifish:db_perms:*:{instance_id}:{username}:*"
            keys = self.redis_client.keys(pattern)
            
            if not keys:
                return None
            
            cached_permissions = {}
            for key in keys:
                try:
                    cached_data = self.redis_client.get(key)
                    if cached_data:
                        data = json.loads(cached_data)
                        db_name = data.get('db_name')
                        if db_name:
                            roles = data.get('roles', [])
                            permissions = data.get('permissions', [])
                            cached_permissions[db_name] = (roles, permissions)
                except Exception as e:
                    logger.warning(f"解析缓存数据失败: {key}", error=str(e))
                    continue
            
            if cached_permissions:
                logger.debug(f"批量缓存命中: {username}", count=len(cached_permissions))
            
            return cached_permissions if cached_permissions else None
            
        except Exception as e:
            logger.warning(f"获取批量缓存失败: {username}", error=str(e))
            return None
    
    def invalidate_user_cache(self, instance_id: int, username: str) -> bool:
        """清除用户的所有缓存"""
        try:
            pattern = f"taifish:*:{instance_id}:{username}:*"
            keys = self.redis_client.keys(pattern)
            
            if keys:
                self.redis_client.delete(*keys)
                logger.info(f"已清除用户缓存: {username}", count=len(keys))
                return True
            
            return False
            
        except Exception as e:
            logger.warning(f"清除用户缓存失败: {username}", error=str(e))
            return False
    
    def invalidate_instance_cache(self, instance_id: int) -> bool:
        """清除实例的所有缓存"""
        try:
            pattern = f"taifish:*:{instance_id}:*"
            keys = self.redis_client.keys(pattern)
            
            if keys:
                self.redis_client.delete(*keys)
                logger.info(f"已清除实例缓存: {instance_id}", count=len(keys))
                return True
            
            return False
            
        except Exception as e:
            logger.warning(f"清除实例缓存失败: {instance_id}", error=str(e))
            return False
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """获取缓存统计信息"""
        try:
            pattern = "taifish:*"
            keys = self.redis_client.keys(pattern)
            
            stats = {
                'total_keys': len(keys),
                'memory_usage': 0,
                'key_types': {}
            }
            
            for key in keys:
                try:
                    key_type = key.decode().split(':')[1] if ':' in key.decode() else 'unknown'
                    stats['key_types'][key_type] = stats['key_types'].get(key_type, 0) + 1
                except:
                    continue
            
            return stats
            
        except Exception as e:
            logger.warning(f"获取缓存统计失败", error=str(e))
            return {'error': str(e)}
    
    def health_check(self) -> bool:
        """缓存健康检查"""
        try:
            self.redis_client.ping()
            return True
        except Exception as e:
            logger.error(f"缓存健康检查失败", error=str(e))
            return False


# 全局缓存管理器实例
cache_manager = CacheManager()
