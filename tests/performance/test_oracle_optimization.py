"""
Oracle查询性能优化测试
测试批量查询优化前后的性能差异
"""

import time
import sys
import os
from typing import Any

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app.services.sync_adapters.oracle_sync_adapter import OracleSyncAdapter
from app.models import Instance


class MockOracleConnection:
    """模拟Oracle连接用于性能测试"""
    
    def __init__(self, user_count: int = 100):
        self.user_count = user_count
        self.query_count = 0
        self.query_times = []
    
    def execute_query(self, query: str, params: dict = None) -> list[tuple]:
        """模拟查询执行，记录查询次数和时间"""
        start_time = time.perf_counter()
        
        # 模拟查询延迟
        time.sleep(0.01)  # 10ms延迟模拟网络+数据库处理时间
        
        end_time = time.perf_counter()
        query_time = end_time - start_time
        
        self.query_count += 1
        self.query_times.append(query_time)
        
        # 根据查询类型返回模拟数据
        if "dba_users" in query.lower():
            return self._mock_users_data()
        elif "dba_role_privs" in query.lower():
            return self._mock_roles_data()
        elif "dba_sys_privs" in query.lower():
            return self._mock_system_privs_data()
        elif "dba_ts_quotas" in query.lower():
            return self._mock_tablespace_data()
        elif "dba_tables" in query.lower() and "count" in query.lower():
            return [(1,)]  # 表存在检查
        elif "dba_tables" in query.lower() or "dba_indexes" in query.lower():
            return self._mock_object_perms_data()
        else:
            return []
    
    def _mock_users_data(self) -> list[tuple]:
        """模拟用户数据"""
        users = []
        for i in range(self.user_count):
            users.append((
                f"USER_{i:03d}",
                i + 1,  # user_id
                "OPEN",  # account_status
                None,  # created
                None,  # expiry_date
                "USERS",  # default_tablespace
                "TEMP",  # temporary_tablespace
                "DEFAULT"  # profile
            ))
        return users
    
    def _mock_roles_data(self) -> list[tuple]:
        """模拟角色数据"""
        roles = []
        for i in range(self.user_count):
            # 每个用户1-3个角色
            role_count = (i % 3) + 1
            for j in range(role_count):
                roles.append((f"USER_{i:03d}", f"ROLE_{j}"))
        return roles
    
    def _mock_system_privs_data(self) -> list[tuple]:
        """模拟系统权限数据"""
        privs = []
        for i in range(self.user_count):
            # 每个用户2-5个系统权限
            priv_count = (i % 4) + 2
            for j in range(priv_count):
                privs.append((f"USER_{i:03d}", f"PRIVILEGE_{j}"))
        return privs
    
    def _mock_tablespace_data(self) -> list[tuple]:
        """模拟表空间数据"""
        ts_data = []
        for i in range(self.user_count):
            # 每个用户1-2个表空间
            ts_count = (i % 2) + 1
            for j in range(ts_count):
                ts_data.append((f"USER_{i:03d}", f"TABLESPACE_{j}", "QUOTA"))
        return ts_data
    
    def _mock_object_perms_data(self) -> list[tuple]:
        """模拟对象权限数据"""
        obj_data = []
        for i in range(self.user_count):
            # 每个用户0-1个对象权限
            if i % 3 == 0:  # 只有1/3的用户有对象权限
                obj_data.append((f"USER_{i:03d}", "USERS", "OWNER"))
        return obj_data


def test_oracle_optimization_performance():
    """测试Oracle查询优化性能"""
    print("🚀 Oracle查询性能优化测试")
    print("=" * 50)
    
    # 测试不同用户数量的性能
    user_counts = [10, 50, 100, 200]
    
    for user_count in user_counts:
        print(f"\n📊 测试用户数量: {user_count}")
        print("-" * 30)
        
        # 创建模拟连接
        connection = MockOracleConnection(user_count)
        
        # 创建Oracle同步适配器
        adapter = OracleSyncAdapter()
        
        # 创建模拟实例
        instance = Instance()
        instance.name = "TEST_ORACLE"
        
        # 测试优化后的批量查询
        start_time = time.perf_counter()
        
        try:
            accounts = adapter.get_database_accounts(instance, connection)
            
            end_time = time.perf_counter()
            total_time = end_time - start_time
            
            print(f"✅ 优化后性能:")
            print(f"   - 总查询次数: {connection.query_count}")
            print(f"   - 总耗时: {total_time:.3f}秒")
            print(f"   - 平均查询时间: {sum(connection.query_times)/len(connection.query_times):.3f}秒")
            print(f"   - 获取账户数: {len(accounts)}")
            
            # 计算性能提升估算
            # 原方法：每个用户4-5次查询 = user_count * 4.5
            original_queries = user_count * 4.5
            optimized_queries = connection.query_count
            improvement = (original_queries - optimized_queries) / original_queries * 100
            
            print(f"   - 查询次数减少: {improvement:.1f}%")
            print(f"   - 性能提升估算: {improvement:.1f}%")
            
        except Exception as e:
            print(f"❌ 测试失败: {e}")


def test_query_complexity():
    """测试查询复杂度分析"""
    print("\n🔍 查询复杂度分析")
    print("=" * 50)
    
    print("原方法 (N+1查询问题):")
    print("  - 1次查询所有用户基本信息")
    print("  - N次查询每个用户的角色权限") 
    print("  - N次查询每个用户的系统权限")
    print("  - N次查询每个用户的表空间权限")
    print("  - N次查询每个用户的类型特定信息")
    print("  - 总计: 1 + N*4 = O(N) 查询")
    
    print("\n优化后方法 (批量查询):")
    print("  - 1次查询所有用户基本信息")
    print("  - 1次批量查询所有用户角色权限")
    print("  - 1次批量查询所有用户系统权限") 
    print("  - 1次批量查询所有用户表空间权限")
    print("  - 1次批量查询所有用户对象权限")
    print("  - 总计: 5次查询 = O(1) 查询")
    
    print("\n性能提升预期:")
    print("  - 查询次数: 从O(N)降到O(1)")
    print("  - 网络往返: 减少80%以上")
    print("  - 数据库负载: 显著降低")
    print("  - 响应时间: 预计提升80%以上")


if __name__ == "__main__":
    test_query_complexity()
    test_oracle_optimization_performance()
    
    print("\n🎉 性能测试完成!")
    print("\n💡 优化建议:")
    print("  1. 在生产环境中监控实际性能")
    print("  2. 根据用户数量调整批量查询大小")
    print("  3. 考虑添加查询缓存机制")
    print("  4. 定期更新Oracle统计信息")
