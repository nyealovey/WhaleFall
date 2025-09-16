#!/usr/bin/env python3
"""
测试 sys.user$ 表的 PTIME 字段
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from app.models.instance import Instance
from app.services.connection_factory import ConnectionFactory

def test_sys_user_table():
    """测试 sys.user$ 表的 PTIME 字段"""
    app = create_app()
    with app.app_context():
        # 获取Oracle实例
        oracle_instance = Instance.query.filter_by(db_type='oracle').first()
        if oracle_instance:
            print(f'Oracle实例: {oracle_instance.name} ({oracle_instance.host}:{oracle_instance.port})')
            
            # 创建连接
            conn = ConnectionFactory.create_connection(oracle_instance)
            if not conn:
                print('无法创建Oracle连接')
                return
            
            if not conn.connect():
                print('Oracle连接失败')
                return
            
            print('Oracle连接成功')
            
            try:
                # 测试查询 sys.user$ 表的 PTIME 字段
                print('\n测试查询 sys.user$ 表的 PTIME 字段:')
                result = conn.execute_query("SELECT name, ctime, ptime FROM sys.user$ WHERE ROWNUM <= 3")
                if result:
                    print('PTIME字段可用!')
                    for row in result:
                        print(f'  用户: {row[0]}, 创建时间: {row[1]}, 密码修改时间: {row[2]}')
                else:
                    print('PTIME字段查询结果为空')
                    
            except Exception as e:
                print(f'查询失败: {e}')
            finally:
                if hasattr(conn, 'disconnect'):
                    conn.disconnect()
                elif hasattr(conn, 'close'):
                    conn.close()
        else:
            print('未找到Oracle实例')

if __name__ == '__main__':
    test_sys_user_table()
