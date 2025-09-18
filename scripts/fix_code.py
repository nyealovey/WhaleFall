from app.utils.structlog_config import get_system_logger

logger = get_system_logger()

#!/usr/bin/env python3
"""
泰摸鱼吧 - 代码自动修复脚本
自动修复常见的代码质量问题
"""

import subprocess
import sys
from pathlib import Path


def run_command(cmd: list, cwd: Path = None) -> tuple[int, str, str]:
    """运行命令并返回结果"""
    try:
        result = subprocess.run(
            cmd, cwd=cwd or Path(__file__).parent.parent, capture_output=True, text=True, timeout=120
        )
        return result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return -1, "", "命令执行超时"
    except Exception as e:
        return -1, "", str(e)


def main():
    """主函数"""
    logger.info("🔧 泰摸鱼吧 - 代码自动修复工具")
    print("=" * 50)

    project_root = Path(__file__).parent.parent

    # 检查是否在项目根目录
    if not (project_root / "pyproject.toml").exists():
        logger.info("❌ 请在项目根目录运行此脚本")
        sys.exit(1)

    fixes = [
        ("Black代码格式化", ["uv", "run", "black", "."]),
        ("isort导入排序", ["uv", "run", "isort", "."]),
        ("Ruff自动修复", ["uv", "run", "ruff", "check", "--fix", "."]),
        ("Ruff格式化", ["uv", "run", "ruff", "format", "."]),
    ]

    for name, cmd in fixes:
        logger.info("\n🔧 {name}...")
        returncode, stdout, stderr = run_command(cmd, project_root)

        if returncode == 0:
            logger.info("✅ {name} 完成")
        else:
            logger.info("❌ {name} 失败")
            if stderr:
                logger.info("错误: {stderr[:200]}...")

    print("\n" + "=" * 50)
    logger.info("🎉 代码修复完成！")
    logger.info("\n💡 建议运行 'uv run python scripts/quick_check.py' 验证修复结果")


if __name__ == "__main__":
    main()
