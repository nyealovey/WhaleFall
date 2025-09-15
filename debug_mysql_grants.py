#!/usr/bin/env python3
"""
调试MySQL权限获取过程
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from app.services.database_connection_factory import DatabaseConnectionFactory

def debug_mysql_grants():
    """调试MySQL权限获取"""
    app = create_app()
    
    with app.app_context():
        # 获取MySQL实例
        from app.models.instance import Instance
        mysql_instance = Instance.query.filter_by(db_type='mysql').first()
        
        if not mysql_instance:
            print("未找到MySQL实例")
            return
            
        print(f"MySQL实例: {mysql_instance.name}")
        
        # 创建数据库连接
        conn_factory = DatabaseConnectionFactory()
        conn = conn_factory.create_connection(mysql_instance)
        
        if not conn:
            print("无法连接到MySQL实例")
            return
            
        try:
            # 获取backup@localhost的权限
            grants = conn.execute_query("SHOW GRANTS FOR %s@%s", ("backup", "localhost"))
            print(f"\nSHOW GRANTS FOR backup@localhost:")
            for i, grant in enumerate(grants, 1):
                print(f"  {i}. {grant[0]}")
            
            # 解析权限
            global_privileges = []
            database_privileges = {}
            
            for grant in grants:
                grant_str = grant[0]
                print(f"\n处理权限: {grant_str}")
                
                if "GRANT ALL PRIVILEGES" in grant_str.upper():
                    global_privileges.append("ALL PRIVILEGES")
                    print("  -> 添加 ALL PRIVILEGES")
                elif "ON *.*" in grant_str:
                    # 全局权限
                    privs_string = grant_str.split("ON *.*")[0].replace("GRANT ", "").strip()
                    print(f"  -> 全局权限字符串: '{privs_string}'")
                    privs_list = [p.strip() for p in privs_string.split(",") if p.strip()]
                    print(f"  -> 分割后的权限: {privs_list}")
                    for priv in privs_list:
                        if priv not in global_privileges:
                            global_privileges.append(priv)
                            print(f"    -> 添加权限: {priv}")
                elif "ON `" in grant_str and "`.*" in grant_str:
                    # 数据库权限
                    db_name = grant_str.split("ON `")[1].split("`.*")[0]
                    privs_string = grant_str.split("ON `")[0].replace("GRANT ", "").strip()
                    print(f"  -> 数据库权限: {db_name} = {privs_string}")
                    privs_list = [p.strip() for p in privs_string.split(",") if p.strip()]
                    if db_name not in database_privileges:
                        database_privileges[db_name] = []
                    database_privileges[db_name].extend(privs_list)
                    print(f"    -> 添加数据库权限: {db_name} = {privs_list}")
            
            print(f"\n最终解析结果:")
            print(f"全局权限: {global_privileges}")
            print(f"数据库权限: {database_privileges}")
            
        except Exception as e:
            print(f"获取权限失败: {e}")
        finally:
            conn.close()

if __name__ == "__main__":
    debug_mysql_grants()
