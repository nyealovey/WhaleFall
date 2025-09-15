#!/usr/bin/env python3
"""
PostgreSQL性能监控脚本
"""

import psycopg
import time
import json
from datetime import datetime

# 数据库配置
POSTGRES_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "dbname": "taifish_dev",
    "user": "taifish_user",
    "password": "Taifish2024!"
}

def get_database_stats():
    """获取数据库统计信息"""
    try:
        conn = psycopg.connect(**POSTGRES_CONFIG)
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM get_database_stats()")
        stats = cursor.fetchall()
        
        print("=== 数据库统计信息 ===")
        for metric, value in stats:
            print(f"{metric}: {value}")
        
        conn.close()
        return True
    except Exception as e:
        print(f"获取数据库统计失败: {e}")
        return False

def get_slow_queries(threshold_ms=1000):
    """获取慢查询"""
    try:
        conn = psycopg.connect(**POSTGRES_CONFIG)
        cursor = conn.cursor()
        
        cursor.execute(f"SELECT * FROM get_slow_queries({threshold_ms})")
        queries = cursor.fetchall()
        
        if queries:
            print(f"\n=== 慢查询 (>={threshold_ms}ms) ===")
            for i, query in enumerate(queries, 1):
                query_text, calls, total_time, mean_time, max_time, min_time, stddev_time = query
                print(f"\n{i}. 查询: {query_text[:100]}...")
                print(f"   调用次数: {calls}")
                print(f"   总时间: {total_time:.2f}ms")
                print(f"   平均时间: {mean_time:.2f}ms")
                print(f"   最大时间: {max_time:.2f}ms")
                print(f"   最小时间: {min_time:.2f}ms")
                print(f"   标准差: {stddev_time:.2f}ms")
        else:
            print(f"\n=== 没有发现慢查询 (>={threshold_ms}ms) ===")
        
        conn.close()
        return True
    except Exception as e:
        print(f"获取慢查询失败: {e}")
        return False

def get_table_performance():
    """获取表性能统计"""
    try:
        conn = psycopg.connect(**POSTGRES_CONFIG)
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM get_table_performance()")
        tables = cursor.fetchall()
        
        if tables:
            print(f"\n=== 表性能统计 ===")
            print(f"{'表名':<30} {'大小':<10} {'行数':<10} {'索引数':<8} {'最后清理':<20} {'最后分析':<20}")
            print("-" * 100)
            for table in tables:
                schemaname, tablename, size, row_count, index_count, last_vacuum, last_analyze = table
                last_vacuum_str = last_vacuum.strftime('%Y-%m-%d %H:%M:%S') if last_vacuum else 'Never'
                last_analyze_str = last_analyze.strftime('%Y-%m-%d %H:%M:%S') if last_analyze else 'Never'
                print(f"{tablename:<30} {size:<10} {row_count:<10} {index_count:<8} {last_vacuum_str:<20} {last_analyze_str:<20}")
        
        conn.close()
        return True
    except Exception as e:
        print(f"获取表性能统计失败: {e}")
        return False

def get_active_connections():
    """获取活动连接"""
    conn = None
    try:
        conn = psycopg.connect(**POSTGRES_CONFIG)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT 
                pid,
                usename,
                application_name,
                client_addr,
                state,
                query_start,
                state_change,
                query
            FROM pg_stat_activity 
            WHERE state != 'idle' 
            ORDER BY query_start DESC
        """)
        connections = cursor.fetchall()
        
        if connections:
            print(f"\n=== 活动连接 ({len(connections)} 个) ===")
            print(f"{'PID':<8} {'用户':<15} {'应用':<20} {'客户端':<15} {'状态':<10} {'查询开始':<20} {'查询'}")
            print("-" * 120)
            for conn_data in connections:
                pid, user, app, client, state, start, change, query = conn_data
                start_str = start.strftime('%H:%M:%S') if start else 'N/A'
                query_short = query[:50] + '...' if query and len(query) > 50 else query or 'N/A'
                client_str = str(client) if client else 'N/A'
                print(f"{pid:<8} {user:<15} {app:<20} {client_str:<15} {state:<10} {start_str:<20} {query_short}")
        else:
            print("\n=== 没有活动连接 ===")
        
        return True
    except Exception as e:
        print(f"获取活动连接失败: {e}")
        return False
    finally:
        if conn:
            conn.close()

def get_lock_info():
    """获取锁信息"""
    try:
        conn = psycopg.connect(**POSTGRES_CONFIG)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT 
                l.locktype,
                l.database,
                l.relation,
                l.page,
                l.tuple,
                l.virtualxid,
                l.transactionid,
                l.classid,
                l.objid,
                l.objsubid,
                l.virtualtransaction,
                l.pid,
                l.mode,
                l.granted,
                a.usename,
                a.query,
                a.query_start,
                a.state
            FROM pg_locks l
            LEFT JOIN pg_stat_activity a ON l.pid = a.pid
            WHERE NOT l.granted
            ORDER BY l.pid
        """)
        locks = cursor.fetchall()
        
        if locks:
            print(f"\n=== 等待锁 ({len(locks)} 个) ===")
            for lock in locks:
                locktype, database, relation, page, tuple, virtualxid, transactionid, classid, objid, objsubid, virtualtransaction, pid, mode, granted, usename, query, query_start, state = lock
                print(f"PID {pid} ({usename}): {locktype} {mode} on {relation or 'N/A'}")
                if query:
                    print(f"  查询: {query[:100]}...")
        else:
            print("\n=== 没有等待锁 ===")
        
        conn.close()
        return True
    except Exception as e:
        print(f"获取锁信息失败: {e}")
        return False

def monitor_continuously(interval=30):
    """持续监控"""
    print(f"开始持续监控，间隔 {interval} 秒...")
    print("按 Ctrl+C 停止监控")
    
    try:
        while True:
            print(f"\n{'='*60}")
            print(f"监控时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"{'='*60}")
            
            get_database_stats()
            get_slow_queries()
            get_table_performance()
            get_active_connections()
            get_lock_info()
            
            time.sleep(interval)
    except KeyboardInterrupt:
        print("\n监控已停止")

def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='PostgreSQL性能监控工具')
    parser.add_argument('--continuous', '-c', action='store_true', help='持续监控模式')
    parser.add_argument('--interval', '-i', type=int, default=30, help='监控间隔（秒）')
    parser.add_argument('--slow-threshold', '-s', type=int, default=1000, help='慢查询阈值（毫秒）')
    
    args = parser.parse_args()
    
    if args.continuous:
        monitor_continuously(args.interval)
    else:
        print("PostgreSQL性能监控报告")
        print("=" * 40)
        
        get_database_stats()
        get_slow_queries(args.slow_threshold)
        get_table_performance()
        get_active_connections()
        get_lock_info()

if __name__ == "__main__":
    main()
