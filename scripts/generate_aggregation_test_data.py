#!/usr/bin/env python3
"""
聚合统计测试数据生成脚本
为 database_size_aggregations 表生成前七天的测试数据
按照设计：每天每个实例每个数据库只有一条记录
"""

import os
import sys
import random
from datetime import datetime, date, timedelta

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app, db
from sqlalchemy import text


def generate_test_data():
    """生成聚合统计测试数据"""
    app = create_app()
    
    with app.app_context():
        # 清理现有数据
        print("清理现有数据...")
        db.session.execute(text('DELETE FROM database_size_aggregations'))
        db.session.commit()
        print("已清理现有数据")
        
        # 获取实例信息
        result = db.session.execute(text('SELECT id, name, db_type FROM instances'))
        instances = result.fetchall()
        print(f'找到 {len(instances)} 个实例')
        
        if not instances:
            print('没有找到实例，无法生成数据')
            return
        
        # 生成前7天的数据（每天一条记录）
        base_date = date.today() - timedelta(days=7)
        database_names = ['postgres', 'whalefall_dev', 'test_db', 'app_db']
        
        print('开始生成聚合统计数据...')
        
        for i in range(7):
            current_date = base_date + timedelta(days=i)
            print(f'生成 {current_date} 的数据...')
            
            for instance in instances:
                for db_name in database_names:
                    # 生成随机数据
                    base_size = random.randint(100, 3000)  # 基础大小 100-3000MB
                    data_size = int(base_size * 0.8)  # 数据大小占80%
                    log_size = int(base_size * 0.2)   # 日志大小占20%
                    
                    # 生成变化数据
                    size_change = random.randint(-50, 50)
                    size_change_percent = round((size_change / base_size) * 100, 2) if base_size > 0 else 0
                    data_size_change = random.randint(-30, 30)
                    data_size_change_percent = round((data_size_change / data_size) * 100, 2) if data_size > 0 else 0
                    log_size_change = random.randint(-20, 20)
                    log_size_change_percent = round((log_size_change / log_size) * 100, 2) if log_size > 0 else 0
                    growth_rate = round(random.uniform(-2, 2), 2)
                    
                    # 插入数据
                    sql = """
                    INSERT INTO database_size_aggregations (
                        instance_id, database_name, period_type, period_start, period_end,
                        data_count, avg_size_mb, max_size_mb, min_size_mb,
                        avg_data_size_mb, max_data_size_mb, min_data_size_mb,
                        avg_log_size_mb, max_log_size_mb, min_log_size_mb,
                        size_change_mb, size_change_percent,
                        data_size_change_mb, data_size_change_percent,
                        log_size_change_mb, log_size_change_percent,
                        growth_rate, calculated_at, created_at
                    ) VALUES (
                        :instance_id, :database_name, :period_type, :period_start, :period_end,
                        :data_count, :avg_size_mb, :max_size_mb, :min_size_mb,
                        :avg_data_size_mb, :max_data_size_mb, :min_data_size_mb,
                        :avg_log_size_mb, :max_log_size_mb, :min_log_size_mb,
                        :size_change_mb, :size_change_percent,
                        :data_size_change_mb, :data_size_change_percent,
                        :log_size_change_mb, :log_size_change_percent,
                        :growth_rate, :calculated_at, :created_at
                    )
                    """
                    
                    db.session.execute(text(sql), {
                        'instance_id': instance.id,
                        'database_name': db_name,
                        'period_type': 'daily',
                        'period_start': current_date,
                        'period_end': current_date,  # 同一天
                        'data_count': 1,  # 每天只有一条记录
                        'avg_size_mb': base_size,
                        'max_size_mb': base_size,
                        'min_size_mb': base_size,
                        'avg_data_size_mb': data_size,
                        'max_data_size_mb': data_size,
                        'min_data_size_mb': data_size,
                        'avg_log_size_mb': log_size,
                        'max_log_size_mb': log_size,
                        'min_log_size_mb': log_size,
                        'size_change_mb': size_change,
                        'size_change_percent': size_change_percent,
                        'data_size_change_mb': data_size_change,
                        'data_size_change_percent': data_size_change_percent,
                        'log_size_change_mb': log_size_change,
                        'log_size_change_percent': log_size_change_percent,
                        'growth_rate': growth_rate,
                        'calculated_at': datetime.now(),
                        'created_at': datetime.now()
                    })
            
            # 每生成一天的数据就提交一次
            db.session.commit()
            print(f'  {current_date} 数据生成完成')
        
        print('\n数据生成完成！')
        
        # 验证数据
        result = db.session.execute(text('SELECT COUNT(*) FROM database_size_aggregations'))
        count = result.scalar()
        print(f'总记录数: {count}')
        
        # 按日期查看
        result = db.session.execute(text('''
            SELECT period_start, COUNT(*) as count
            FROM database_size_aggregations 
            GROUP BY period_start 
            ORDER BY period_start
        '''))
        by_date = result.fetchall()
        
        print('\n按日期分组查看:')
        for row in by_date:
            print(f'{row.period_start}: {row.count} 条记录')
        
        # 按实例查看
        result = db.session.execute(text('''
            SELECT i.name as instance_name, COUNT(*) as count
            FROM database_size_aggregations a
            JOIN instances i ON a.instance_id = i.id
            GROUP BY i.name
            ORDER BY i.name
        '''))
        by_instance = result.fetchall()
        
        print('\n按实例分组查看:')
        for row in by_instance:
            print(f'{row.instance_name}: {row.count} 条记录')


if __name__ == '__main__':
    generate_test_data()