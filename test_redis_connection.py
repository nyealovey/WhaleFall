#!/usr/bin/env python3
"""
测试Redis连接
"""

import redis
import os

# 测试不同的Redis URL格式
redis_urls = [
    "redis://:Taifish2024!@localhost:6379/0",
    "redis://:Taifish2024%21@localhost:6379/0",
    "redis://localhost:6379/0",
    "redis://:Taifish2024!@localhost:6379",
    "redis://:Taifish2024%21@localhost:6379"
]

for i, url in enumerate(redis_urls, 1):
    print(f"\n{i}. 测试Redis URL: {url}")
    try:
        r = redis.from_url(url)
        result = r.ping()
        print(f"   ✓ 连接成功: {result}")
        
        # 测试设置和获取值
        r.set("test_key", "test_value")
        value = r.get("test_key")
        print(f"   ✓ 读写测试成功: {value}")
        
        # 清理测试数据
        r.delete("test_key")
        print(f"   ✓ 清理完成")
        
    except Exception as e:
        print(f"   ✗ 连接失败: {e}")

print("\n" + "="*50)
print("测试完成")
