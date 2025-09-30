#!/usr/bin/env python3
"""
时区模块迁移脚本
将 app.utils.timezone 的导入替换为 app.utils.time_utils
"""

import os
import re
from pathlib import Path

def migrate_file(file_path: Path) -> bool:
    """迁移单个文件"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        
        # 替换导入语句
        content = re.sub(
            r'from app\.utils\.timezone import ([^\\n]+)',
            r'from app.utils.time_utils import \1',
            content
        )
        
        # 如果文件被修改了，写回文件
        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"✅ 已迁移: {file_path}")
            return True
        else:
            print(f"⏭️  无需迁移: {file_path}")
            return False
            
    except Exception as e:
        print(f"❌ 迁移失败: {file_path} - {e}")
        return False

def main():
    """主函数"""
    print("🚀 开始迁移时区模块...")
    
    # 获取项目根目录
    project_root = Path(__file__).parent.parent
    
    # 需要迁移的文件模式
    patterns = [
        "app/**/*.py",
        "tests/**/*.py",
        "scripts/**/*.py"
    ]
    
    migrated_count = 0
    total_count = 0
    
    for pattern in patterns:
        for file_path in project_root.glob(pattern):
            if file_path.is_file() and file_path.suffix == '.py':
                total_count += 1
                if migrate_file(file_path):
                    migrated_count += 1
    
    print(f"\n📊 迁移完成:")
    print(f"   总文件数: {total_count}")
    print(f"   已迁移: {migrated_count}")
    print(f"   无需迁移: {total_count - migrated_count}")

if __name__ == "__main__":
    main()
