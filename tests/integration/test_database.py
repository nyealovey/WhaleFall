#!/usr/bin/env python3

"""
泰摸鱼吧 - 数据库连接测试脚本
"""

import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))


def test_database_connection():
    """测试数据库连接"""
    print("🔧 测试数据库连接...")

    try:
        from app import create_app, db

        # 创建Flask应用
        app = create_app()

        with app.app_context():
            # 测试数据库连接
            db.engine.connect()
            print("✅ 数据库连接成功")

            # 创建所有表
            db.create_all()
            print("✅ 数据库表创建成功")

            # 检查表是否创建
            inspector = db.inspect(db.engine)
            tables = inspector.get_table_names()
            print(f"📊 已创建的表: {tables}")

            return True

    except Exception as e:
        print(f"❌ 数据库连接失败: {e}")
        return False


def test_redis_connection():
    """测试Redis连接"""
    print("\n🔴 测试Redis连接...")

    try:
        import redis

        r = redis.Redis(host="localhost", port=6379, db=0, password="Taifish2024!", decode_responses=True)
        r.ping()
        print("✅ Redis连接成功")
        return True
    except Exception as e:
        print(f"❌ Redis连接失败: {e}")
        return False


def main():
    """主函数"""
    print("=" * 50)
    print("🐟 泰摸鱼吧 - 数据库连接测试")
    print("=" * 50)

    # 测试数据库
    db_success = test_database_connection()

    # 测试Redis
    redis_success = test_redis_connection()

    print("\n" + "=" * 50)
    print("📊 测试结果:")
    print(f"   数据库: {'✅ 成功' if db_success else '❌ 失败'}")
    print(f"   Redis: {'✅ 成功' if redis_success else '❌ 失败'}")
    print("=" * 50)

    if db_success and redis_success:
        print("🎉 所有服务连接正常，可以开始开发！")
        return True
    print("⚠️  部分服务连接失败，请检查配置")
    return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
