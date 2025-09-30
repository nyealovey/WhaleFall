#!/usr/bin/env python3
"""
聚合统计测试数据生成脚本
为 database_size_aggregations 表生成测试数据
按照设计：每个实例的每个数据库，每个周期只能有一条记录
- 日统计：每天一条记录
- 周统计：每周一条记录
- 月统计：每月一条记录
- 季统计：每季一条记录
"""

import os
import sys
import random
from datetime import datetime, date, timedelta
from app.utils.time_utils import time_utils

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
        
        database_names = ['postgres', 'whalefall_dev', 'test_db', 'app_db']
        base_date = date.today() - timedelta(days=7)
        
        # 生成日统计数据（前7天）
        print('\n=== 生成日统计数据 ===')
        for i in range(7):
            current_date = base_date + timedelta(days=i)
            print(f'生成 {current_date} 的日统计数据...')
            
            for instance in instances:
                for db_name in database_names:
                    base_size = random.randint(100, 3000)
                    data_size = int(base_size * 0.8)
                    log_size = int(base_size * 0.2)
                    
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
                        'period_end': current_date,
                        'data_count': 1,
                        'avg_size_mb': base_size,
                        'max_size_mb': base_size,
                        'min_size_mb': base_size,
                        'avg_data_size_mb': data_size,
                        'max_data_size_mb': data_size,
                        'min_data_size_mb': data_size,
                        'avg_log_size_mb': log_size,
                        'max_log_size_mb': log_size,
                        'min_log_size_mb': log_size,
                        'size_change_mb': random.randint(-50, 50),
                        'size_change_percent': random.uniform(-5, 5),
                        'data_size_change_mb': random.randint(-30, 30),
                        'data_size_change_percent': random.uniform(-3, 3),
                        'log_size_change_mb': random.randint(-20, 20),
                        'log_size_change_percent': random.uniform(-2, 2),
                        'growth_rate': random.uniform(-2, 2),
                        'calculated_at': time_utils.now(),
                        'created_at': time_utils.now()
                    })
            db.session.commit()
        
        # 生成周统计数据（前4周）
        print('\n=== 生成周统计数据 ===')
        for week in range(4):
            week_start = base_date - timedelta(days=base_date.weekday()) - timedelta(weeks=week)
            week_end = week_start + timedelta(days=6)
            print(f'生成 {week_start} 到 {week_end} 的周统计数据...')
            
            for instance in instances:
                for db_name in database_names:
                    base_size = random.randint(100, 3000)
                    data_size = int(base_size * 0.8)
                    log_size = int(base_size * 0.2)
                    
                    db.session.execute(text(sql), {
                        'instance_id': instance.id,
                        'database_name': db_name,
                        'period_type': 'weekly',
                        'period_start': week_start,
                        'period_end': week_end,
                        'data_count': 7,
                        'avg_size_mb': base_size,
                        'max_size_mb': base_size + random.randint(0, 200),
                        'min_size_mb': base_size - random.randint(0, 100),
                        'avg_data_size_mb': data_size,
                        'max_data_size_mb': data_size + random.randint(0, 150),
                        'min_data_size_mb': data_size - random.randint(0, 80),
                        'avg_log_size_mb': log_size,
                        'max_log_size_mb': log_size + random.randint(0, 50),
                        'min_log_size_mb': log_size - random.randint(0, 20),
                        'size_change_mb': random.randint(-100, 200),
                        'size_change_percent': random.uniform(-10, 10),
                        'data_size_change_mb': random.randint(-80, 160),
                        'data_size_change_percent': random.uniform(-8, 8),
                        'log_size_change_mb': random.randint(-20, 40),
                        'log_size_change_percent': random.uniform(-5, 5),
                        'growth_rate': random.uniform(-5, 5),
                        'calculated_at': time_utils.now(),
                        'created_at': time_utils.now()
                    })
            db.session.commit()
        
        # 生成月统计数据（前3个月）
        print('\n=== 生成月统计数据 ===')
        for month in range(3):
            month_start = date(base_date.year, base_date.month, 1) - timedelta(days=30 * month)
            if month_start.month == 12:
                month_end = date(month_start.year + 1, 1, 1) - timedelta(days=1)
            else:
                month_end = date(month_start.year, month_start.month + 1, 1) - timedelta(days=1)
            
            print(f'生成 {month_start} 到 {month_end} 的月统计数据...')
            
            for instance in instances:
                for db_name in database_names:
                    base_size = random.randint(100, 3000)
                    data_size = int(base_size * 0.8)
                    log_size = int(base_size * 0.2)
                    
                    db.session.execute(text(sql), {
                        'instance_id': instance.id,
                        'database_name': db_name,
                        'period_type': 'monthly',
                        'period_start': month_start,
                        'period_end': month_end,
                        'data_count': 30,
                        'avg_size_mb': base_size,
                        'max_size_mb': base_size + random.randint(0, 500),
                        'min_size_mb': base_size - random.randint(0, 200),
                        'avg_data_size_mb': data_size,
                        'max_data_size_mb': data_size + random.randint(0, 400),
                        'min_data_size_mb': data_size - random.randint(0, 160),
                        'avg_log_size_mb': log_size,
                        'max_log_size_mb': log_size + random.randint(0, 100),
                        'min_log_size_mb': log_size - random.randint(0, 40),
                        'size_change_mb': random.randint(-200, 500),
                        'size_change_percent': random.uniform(-20, 20),
                        'data_size_change_mb': random.randint(-160, 400),
                        'data_size_change_percent': random.uniform(-16, 16),
                        'log_size_change_mb': random.randint(-40, 100),
                        'log_size_change_percent': random.uniform(-10, 10),
                        'growth_rate': random.uniform(-10, 10),
                        'calculated_at': time_utils.now(),
                        'created_at': time_utils.now()
                    })
            db.session.commit()
        
        print('\n数据生成完成！')
        
        # 验证数据
        result = db.session.execute(text('SELECT COUNT(*) FROM database_size_aggregations'))
        count = result.scalar()
        print(f'总记录数: {count}')
        
        # 按周期类型查看
        result = db.session.execute(text('''
            SELECT period_type, COUNT(*) as count
            FROM database_size_aggregations 
            GROUP BY period_type
            ORDER BY period_type
        '''))
        by_period = result.fetchall()
        
        print('\n按周期类型分组查看:')
        for row in by_period:
            print(f'{row.period_type}: {row.count} 条记录')
        
        # 按日期查看
        result = db.session.execute(text('''
            SELECT period_type, period_start, COUNT(*) as count
            FROM database_size_aggregations 
            GROUP BY period_type, period_start 
            ORDER BY period_type, period_start
        '''))
        by_date = result.fetchall()
        
        print('\n按周期类型和日期分组查看:')
        current_type = None
        for row in by_date:
            if current_type != row.period_type:
                print(f'\n{row.period_type.upper()}:')
                current_type = row.period_type
            print(f'  {row.period_start}: {row.count} 条记录')


if __name__ == '__main__':
    generate_test_data()