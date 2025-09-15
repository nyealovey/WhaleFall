#!/usr/bin/env python3
"""
PostgreSQL日志查看脚本
"""

import subprocess
import sys
from datetime import datetime, timedelta

def view_recent_logs(lines=100):
    """查看最近的日志"""
    try:
        # 获取容器日志
        result = subprocess.run([
            'docker', 'logs', '--tail', str(lines), 'taifish_postgres_dev'
        ], capture_output=True, text=True)
        
        if result.returncode == 0:
            print("=== PostgreSQL 容器日志 ===")
            print(result.stdout)
        else:
            print(f"获取容器日志失败: {result.stderr}")
            return False
        
        return True
    except Exception as e:
        print(f"查看日志失败: {e}")
        return False

def view_slow_query_logs():
    """查看慢查询日志"""
    try:
        # 进入容器查看慢查询日志
        result = subprocess.run([
            'docker', 'exec', 'taifish_postgres_dev', 
            'find', '/var/lib/postgresql/data/log', '-name', '*.log', '-type', 'f'
        ], capture_output=True, text=True)
        
        if result.returncode == 0:
            log_files = result.stdout.strip().split('\n')
            if log_files and log_files[0]:
                print("=== 慢查询日志文件 ===")
                for log_file in log_files:
                    print(f"文件: {log_file}")
                    
                    # 查看包含慢查询的行
                    grep_result = subprocess.run([
                        'docker', 'exec', 'taifish_postgres_dev',
                        'grep', '-i', 'duration:', log_file
                    ], capture_output=True, text=True)
                    
                    if grep_result.returncode == 0 and grep_result.stdout:
                        print("慢查询记录:")
                        print(grep_result.stdout)
                    else:
                        print("  没有找到慢查询记录")
                    print("-" * 50)
            else:
                print("没有找到日志文件")
        else:
            print(f"查找日志文件失败: {result.stderr}")
            return False
        
        return True
    except Exception as e:
        print(f"查看慢查询日志失败: {e}")
        return False

def view_error_logs():
    """查看错误日志"""
    try:
        # 查看包含ERROR的日志
        result = subprocess.run([
            'docker', 'exec', 'taifish_postgres_dev',
            'grep', '-i', 'error', '/var/lib/postgresql/data/log/postgresql-*.log'
        ], capture_output=True, text=True)
        
        if result.returncode == 0 and result.stdout:
            print("=== 错误日志 ===")
            print(result.stdout)
        else:
            print("没有找到错误日志")
        
        return True
    except Exception as e:
        print(f"查看错误日志失败: {e}")
        return False

def view_connection_logs():
    """查看连接日志"""
    try:
        # 查看连接相关的日志
        result = subprocess.run([
            'docker', 'exec', 'taifish_postgres_dev',
            'grep', '-i', 'connection', '/var/lib/postgresql/data/log/postgresql-*.log'
        ], capture_output=True, text=True)
        
        if result.returncode == 0 and result.stdout:
            print("=== 连接日志 ===")
            print(result.stdout)
        else:
            print("没有找到连接日志")
        
        return True
    except Exception as e:
        print(f"查看连接日志失败: {e}")
        return False

def follow_logs():
    """实时跟踪日志"""
    try:
        print("实时跟踪PostgreSQL日志...")
        print("按 Ctrl+C 停止跟踪")
        
        # 使用docker logs -f 实时跟踪
        subprocess.run([
            'docker', 'logs', '-f', 'taifish_postgres_dev'
        ])
        
        return True
    except KeyboardInterrupt:
        print("\n停止跟踪日志")
        return True
    except Exception as e:
        print(f"跟踪日志失败: {e}")
        return False

def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='PostgreSQL日志查看工具')
    parser.add_argument('--recent', '-r', type=int, default=100, help='查看最近N行日志')
    parser.add_argument('--slow', '-s', action='store_true', help='查看慢查询日志')
    parser.add_argument('--error', '-e', action='store_true', help='查看错误日志')
    parser.add_argument('--connection', '-c', action='store_true', help='查看连接日志')
    parser.add_argument('--follow', '-f', action='store_true', help='实时跟踪日志')
    
    args = parser.parse_args()
    
    if args.follow:
        follow_logs()
    else:
        print("PostgreSQL日志查看工具")
        print("=" * 40)
        
        if args.slow:
            view_slow_query_logs()
        elif args.error:
            view_error_logs()
        elif args.connection:
            view_connection_logs()
        else:
            view_recent_logs(args.recent)

if __name__ == "__main__":
    main()
