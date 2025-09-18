from app.utils.structlog_config import get_system_logger

logger = get_system_logger()

#!/usr/bin/env python3
"""
泰摸鱼吧 - 快速代码质量检查脚本
只运行基本的代码检查，不运行测试，生成详细报告
"""

import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path


def run_command(cmd: list, cwd: Path = None) -> tuple[int, str, str]:
    """运行命令并返回结果"""
    try:
        result = subprocess.run(
            cmd, cwd=cwd or Path(__file__).parent.parent, capture_output=True, text=True, timeout=60
        )
        return result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return -1, "", "命令执行超时"
    except Exception as e:
        return -1, "", str(e)


def check_ruff_detailed(project_root: Path) -> dict:
    """详细的Ruff检查"""
    logger.info("🔍 运行Ruff代码检查...")

    # 获取统计信息
    stats_cmd = ["uv", "run", "ruff", "check", ".", "--statistics"]
    stats_returncode, stats_stdout, stats_stderr = run_command(stats_cmd, project_root)

    # 获取详细问题列表
    details_cmd = ["uv", "run", "ruff", "check", ".", "--output-format=json"]
    details_returncode, details_stdout, details_stderr = run_command(details_cmd, project_root)

    issues = []
    if details_returncode != 0:
        try:
            issues = json.loads(details_stdout) if details_stdout else []
        except json.JSONDecodeError:
            issues = [{"message": details_stderr or "Ruff检查失败"}]

    if stats_returncode == 0:
        logger.info("✅ Ruff检查通过")
    else:
        logger.info("❌ Ruff检查发现 {len(issues)} 个问题")
        logger.info("统计信息: {stats_stdout.strip()}")

    return {
        "tool": "ruff",
        "returncode": stats_returncode,
        "issues": issues,
        "statistics": stats_stdout,
        "output": details_stdout,
        "error": details_stderr,
    }


def check_black_detailed(project_root: Path) -> dict:
    """详细的Black检查"""
    logger.info("🎨 运行Black格式化检查...")

    # 检查格式
    check_cmd = ["uv", "run", "black", "--check", "--diff", "."]
    check_returncode, check_stdout, check_stderr = run_command(check_cmd, project_root)

    files_to_format = []
    if check_returncode == 0:
        logger.info("✅ Black格式化检查通过")
    else:
        logger.info("❌ Black格式化检查失败，需要格式化")
        # 解析需要格式化的文件
        for line in check_stdout.split("\n"):
            if line.startswith("would reformat "):
                file_path = line.replace("would reformat ", "").strip()
                files_to_format.append(file_path)

        logger.info("需要格式化的文件: {len(files_to_format)} 个")
        for file_path in files_to_format[:10]:  # 只显示前10个
            logger.info("  - {file_path}")
        if len(files_to_format) > 10:
            logger.info("  ... 还有 {len(files_to_format) - 10} 个文件")

    return {
        "tool": "black",
        "returncode": check_returncode,
        "output": check_stdout,
        "error": check_stderr,
        "files_to_format": files_to_format,
    }


def check_isort_detailed(project_root: Path) -> dict:
    """详细的isort检查"""
    logger.info("📦 运行isort导入排序检查...")

    # 检查导入排序
    check_cmd = ["uv", "run", "isort", "--check-only", "--diff", "."]
    check_returncode, check_stdout, check_stderr = run_command(check_cmd, project_root)

    files_to_sort = []
    if check_returncode == 0:
        logger.info("✅ isort导入排序检查通过")
    else:
        logger.info("❌ isort导入排序检查失败，需要重新排序")
        # 解析需要排序的文件
        for line in check_stderr.split("\n"):
            if "ERROR:" in line and "Imports are incorrectly sorted" in line:
                file_path = line.split("ERROR: ")[1].split(" Imports are incorrectly sorted")[0].strip()
                files_to_sort.append(file_path)

        logger.info("需要排序的文件: {len(files_to_sort)} 个")
        for file_path in files_to_sort[:10]:  # 只显示前10个
            logger.info("  - {file_path}")
        if len(files_to_sort) > 10:
            logger.info("  ... 还有 {len(files_to_sort) - 10} 个文件")

    return {
        "tool": "isort",
        "returncode": check_returncode,
        "output": check_stdout,
        "error": check_stderr,
        "files_to_sort": files_to_sort,
    }


def generate_report(results: dict, project_root: Path) -> None:
    """生成详细报告"""
    report_file = project_root / "userdata" / "logs" / "quick_quality_report.json"
    report_file.parent.mkdir(parents=True, exist_ok=True)

    # 添加时间戳和摘要
    results["timestamp"] = datetime.now().isoformat()
    results["summary"] = {
        "total_checks": len(results["checks"]),
        "passed_checks": sum(1 for r in results["checks"].values() if r["returncode"] == 0),
        "failed_checks": sum(1 for r in results["checks"].values() if r["returncode"] != 0),
    }

    with open(report_file, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    logger.info("\n📄 详细报告已保存到: {report_file}")

    # 生成修复建议文件
    generate_fix_suggestions(results, project_root)


def generate_fix_suggestions(results: dict, project_root: Path) -> None:
    """生成修复建议文件"""
    suggestions_file = project_root / "userdata" / "logs" / "fix_suggestions.md"

    with open(suggestions_file, "w", encoding="utf-8") as f:
        f.write("# 代码质量修复建议\n\n")
        f.write(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")

        # Ruff问题
        ruff_result = results["checks"].get("ruff", {})
        if ruff_result.get("returncode") != 0:
            f.write("## 🔍 Ruff 代码检查问题\n\n")
            f.write(f"发现 {len(ruff_result.get('issues', []))} 个问题\n\n")

            # 按文件分组问题
            issues_by_file = {}
            for issue in ruff_result.get("issues", []):
                file_path = issue.get("filename", "unknown")
                if file_path not in issues_by_file:
                    issues_by_file[file_path] = []
                issues_by_file[file_path].append(issue)

            for file_path, file_issues in list(issues_by_file.items())[:10]:  # 只显示前10个文件
                f.write(f"### {file_path}\n\n")
                for issue in file_issues[:5]:  # 每个文件只显示前5个问题
                    f.write(f"- **行 {issue.get('location', {}).get('row', '?')}**: {issue.get('message', '')}\n")
                    f.write(f"  - 规则: {issue.get('code', '')}\n")
                    f.write(f"  - 严重程度: {issue.get('severity', '')}\n\n")
                if len(file_issues) > 5:
                    f.write(f"... 还有 {len(file_issues) - 5} 个问题\n\n")

            f.write("**修复命令**:\n```bash\nuv run ruff check --fix .\n```\n\n")

        # Black问题
        black_result = results["checks"].get("black", {})
        if black_result.get("returncode") != 0:
            f.write("## 🎨 Black 格式化问题\n\n")
            files_to_format = black_result.get("files_to_format", [])
            f.write(f"需要格式化的文件: {len(files_to_format)} 个\n\n")

            f.write("**需要格式化的文件列表**:\n")
            for file_path in files_to_format:
                f.write(f"- {file_path}\n")

            f.write("\n**修复命令**:\n```bash\nuv run black .\n```\n\n")

        # isort问题
        isort_result = results["checks"].get("isort", {})
        if isort_result.get("returncode") != 0:
            f.write("## 📦 isort 导入排序问题\n\n")
            files_to_sort = isort_result.get("files_to_sort", [])
            f.write(f"需要排序的文件: {len(files_to_sort)} 个\n\n")

            f.write("**需要排序的文件列表**:\n")
            for file_path in files_to_sort:
                f.write(f"- {file_path}\n")

            f.write("\n**修复命令**:\n```bash\nuv run isort .\n```\n\n")

        # 综合修复建议
        f.write("## 🚀 一键修复所有问题\n\n")
        f.write("```bash\n")
        f.write("# 1. 自动修复Ruff问题\n")
        f.write("uv run ruff check --fix .\n\n")
        f.write("# 2. 格式化代码\n")
        f.write("uv run black .\n\n")
        f.write("# 3. 排序导入\n")
        f.write("uv run isort .\n\n")
        f.write("# 4. 验证修复结果\n")
        f.write("make quality\n")
        f.write("```\n\n")

        f.write("## 📊 检查结果摘要\n\n")
        summary = results.get("summary", {})
        f.write(f"- 总检查项: {summary.get('total_checks', 0)}\n")
        f.write(f"- 通过: {summary.get('passed_checks', 0)} ✅\n")
        f.write(f"- 失败: {summary.get('failed_checks', 0)} ❌\n")

    logger.info("📋 修复建议已保存到: {suggestions_file}")


def main():
    """主函数"""
    logger.info("🚀 泰摸鱼吧 - 快速代码质量检查")
    print("=" * 50)

    project_root = Path(__file__).parent.parent

    # 检查是否在项目根目录
    if not (project_root / "pyproject.toml").exists():
        logger.info("❌ 请在项目根目录运行此脚本")
        sys.exit(1)

    # 运行详细检查
    results = {"checks": {}}

    # Ruff检查
    ruff_result = check_ruff_detailed(project_root)
    results["checks"]["ruff"] = ruff_result

    # Black检查
    black_result = check_black_detailed(project_root)
    results["checks"]["black"] = black_result

    # isort检查
    isort_result = check_isort_detailed(project_root)
    results["checks"]["isort"] = isort_result

    # 生成报告
    generate_report(results, project_root)

    # 打印摘要
    print("\n" + "=" * 50)
    summary = results.get("summary", {})
    logger.info("📊 检查结果: {summary.get('passed_checks', 0)}/{summary.get('total_checks', 0)} 通过")

    if summary.get("failed_checks", 0) == 0:
        logger.info("🎉 所有检查通过！")
        sys.exit(0)
    else:
        logger.info("⚠️  发现代码质量问题，请查看详细报告")
        logger.info("\n💡 快速修复:")
        logger.info("  - 查看修复建议: cat userdata/logs/fix_suggestions.md")
        logger.info("  - 一键修复: make fix-code")
        logger.info("  - 验证结果: make quality")
        sys.exit(1)


if __name__ == "__main__":
    main()
