#!/usr/bin/env python3
"""
添加版本字段到instances表
"""

from app import create_app, db

def add_version_fields():
    """添加主版本和详细版本字段到instances表"""
    app = create_app()
    with app.app_context():
        try:
            # 添加新字段
            print("添加版本字段到instances表...")
            
            # 检查字段是否已存在
            result = db.session.execute("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'instances' 
                AND column_name IN ('main_version', 'detailed_version')
            """)
            existing_columns = [row[0] for row in result.fetchall()]
            
            if 'main_version' not in existing_columns:
                db.session.execute("""
                    ALTER TABLE instances 
                    ADD COLUMN main_version VARCHAR(20)
                """)
                print("✅ 添加main_version字段")
            else:
                print("ℹ️  main_version字段已存在")
            
            if 'detailed_version' not in existing_columns:
                db.session.execute("""
                    ALTER TABLE instances 
                    ADD COLUMN detailed_version VARCHAR(50)
                """)
                print("✅ 添加detailed_version字段")
            else:
                print("ℹ️  detailed_version字段已存在")
            
            db.session.commit()
            print("✅ 版本字段添加完成")
            
            # 更新现有实例的版本信息
            print("\n更新现有实例的版本信息...")
            from app.models.instance import Instance
            from app.utils.version_parser import DatabaseVersionParser
            
            instances = Instance.query.filter(Instance.database_version.isnot(None)).all()
            updated_count = 0
            
            for instance in instances:
                if instance.database_version:
                    parsed = DatabaseVersionParser.parse_version(
                        instance.db_type.lower(), 
                        instance.database_version
                    )
                    
                    instance.main_version = parsed['main_version']
                    instance.detailed_version = parsed['detailed_version']
                    updated_count += 1
                    
                    print(f"  更新 {instance.name}: {parsed['main_version']} ({parsed['detailed_version']})")
            
            db.session.commit()
            print(f"✅ 更新了 {updated_count} 个实例的版本信息")
            
        except Exception as e:
            print(f"❌ 错误: {e}")
            db.session.rollback()
            raise

if __name__ == "__main__":
    add_version_fields()
