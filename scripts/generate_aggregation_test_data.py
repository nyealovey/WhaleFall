#!/usr/bin/env python3
"""
聚合统计测试数据生成脚本
为 database_size_aggregations 表生成前七天的测试数据
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
        
        # 生成前7天的数据
        base_date = date.today() - timedelta(days=7)
        database_names = ['postgres', 'whalefall_dev', 'test_db', 'app_db']
        
        print('开始生成聚合统计数据...')
        
        for i in range(7):
            current_date = base_date + timedelta(days=i)
            print(f'生成 {current_date} 的数据...')
            
            for instance in instances:
                # 为每个实例生成2-3个数据库的聚合数据
                num_databases = random.randint(2, 3)
                selected_dbs = random.sample(database_names, min(num_databases, len(database_names)))
                
                for db_name in selected_dbs:
                    # 计算周期开始和结束日期（每周一为一周的开始）
                    period_start = current_date - timedelta(days=current_date.weekday())
                    period_end = period_start + timedelta(days=6)
                    
                    # 生成随机大小数据（MB）
                    base_size = random.randint(100, 3000)
                    avg_size = base_size + random.randint(-100, 100)
                    max_size = avg_size + random.randint(0, 300)
                    min_size = max(1, avg_size - random.randint(0, 200))
                    
                    # 生成变化数据
                    size_change = random.randint(-50, 100)
                    size_change_percent = round((size_change / avg_size) * 100, 2) if avg_size > 0 else 0
                    growth_rate = round(random.uniform(-3.0, 10.0), 2)
                    
                    # 使用SQL直接插入
                    sql = '''
                    INSERT INTO database_size_aggregations (
                        instance_id, database_name, period_type, period_start, period_end,
                        avg_size_mb, max_size_mb, min_size_mb, data_count,
                        avg_data_size_mb, max_data_size_mb, min_data_size_mb,
                        avg_log_size_mb, max_log_size_mb, min_log_size_mb,
                        size_change_mb, size_change_percent,
                        data_size_change_mb, data_size_change_percent,
                        log_size_change_mb, log_size_change_percent,
                        growth_rate, calculated_at, created_at
                    ) VALUES (
                        :instance_id, :database_name, 'weekly', :period_start, :period_end,
                        :avg_size, :max_size, :min_size, :data_count,
                        :avg_data_size, :max_data_size, :min_data_size,
                        :avg_log_size, :max_log_size, :min_log_size,
                        :size_change, :size_change_percent,
                        :data_size_change, :data_size_change_percent,
                        :log_size_change, :log_size_change_percent,
                        :growth_rate, :calculated_at, :created_at
                    )
                    '''
                    
                    params = {
                        'instance_id': instance[0],
                        'database_name': db_name,
                        'period_start': period_start,
                        'period_end': period_end,
                        'avg_size': avg_size,
                        'max_size': max_size,
                        'min_size': min_size,
                        'data_count': random.randint(5, 10),
                        'avg_data_size': avg_size - random.randint(0, 50),
                        'max_data_size': max_size - random.randint(0, 50),
                        'min_data_size': max(1, min_size - random.randint(0, 30)),
                        'avg_log_size': random.randint(10, 100),
                        'max_log_size': random.randint(20, 150),
                        'min_log_size': random.randint(5, 30),
                        'size_change': size_change,
                        'size_change_percent': size_change_percent,
                        'data_size_change': size_change - random.randint(0, 20),
                        'data_size_change_percent': round(size_change_percent * random.uniform(0.9, 1.1), 2),
                        'log_size_change': random.randint(-10, 20),
                        'log_size_change_percent': round(random.uniform(-5.0, 10.0), 2),
                        'growth_rate': growth_rate,
                        'calculated_at': datetime.now(),
                        'created_at': datetime.now()
                    }
                    
                    try:
                        db.session.execute(text(sql), params)
                        db.session.commit()
                    except Exception as e:
                        print(f'  插入失败: {e}')
                        db.session.rollback()
                        continue
        
        # 统计生成的数据
        result = db.session.execute(text('SELECT COUNT(*) FROM database_size_aggregations'))
        count = result.scalar()
        print(f'\\n总共生成了 {count} 条聚合记录')
        
        # 显示一些示例数据
        result = db.session.execute(text('''
            SELECT instance_id, database_name, period_type, avg_size_mb, period_start
            FROM database_size_aggregations 
            ORDER BY created_at DESC 
            LIMIT 5
        '''))
        
        samples = result.fetchall()
        print('\\n示例数据:')
        for sample in samples:
            print(f'  实例{sample[0]} - {sample[1]} - {sample[2]} - 平均大小: {sample[3]}MB - 周期: {sample[4]}')


if __name__ == '__main__':
    generate_test_data()
