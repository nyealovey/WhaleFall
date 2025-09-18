from app.utils.structlog_config import get_system_logger

logger = get_system_logger()

#!/usr/bin/env python3
"""
泰摸鱼吧 - 修复行尾空白问题
批量修复代码中的行尾空白字符
"""

from pathlib import Path


def fix_trailing_whitespace(file_path: Path) -> bool:
    """修复文件中的行尾空白问题"""
    try:
        with open(file_path, encoding="utf-8") as f:
            lines = f.readlines()

        modified = False
        for i, line in enumerate(lines):
            if line.rstrip() != line.rstrip(" \t"):
                lines[i] = line.rstrip() + "\n"
                modified = True

        if modified:
            with open(file_path, "w", encoding="utf-8") as f:
                f.writelines(lines)
            return True
        return False
    except Exception:
        logger.info("修复 {file_path} 时出错: {e}")
        return False


def main():
    """主函数"""
    logger.info("🔧 泰摸鱼吧 - 修复行尾空白问题")
    print("=" * 50)

    project_root = Path(__file__).parent.parent

    # 获取所有Python文件
    python_files = list(project_root.rglob("*.py"))
    # 排除一些目录
    excluded_dirs = {"migrations", "userdata", "venv", ".venv", "__pycache__", ".git"}
    python_files = [f for f in python_files if not any(d in f.parts for d in excluded_dirs)]

    logger.info("📁 找到 {len(python_files)} 个Python文件")

    fixed_files = 0
    for file_path in python_files:
        if fix_trailing_whitespace(file_path):
            logger.info("✅ 修复了: {file_path.relative_to(project_root)}")
            fixed_files += 1

    logger.info("\n🎉 总共修复了 {fixed_files} 个文件")
    logger.info("💡 建议运行 'make quality' 验证修复结果")


if __name__ == "__main__":
    main()
