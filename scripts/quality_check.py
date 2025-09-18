from app.utils.structlog_config import get_system_logger

logger = get_system_logger()

#!/usr/bin/env python3
"""
泰摸鱼吧 - 代码质量检查脚本
整合所有代码质量工具，提供统一的检查接口
"""

import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any


class QualityChecker:
    """代码质量检查器"""

    def __init__(self):
        self.project_root = Path(__file__).parent.parent
        self.results = {
            "timestamp": datetime.now().isoformat(),
            "checks": {},
            "summary": {"total_checks": 0, "passed_checks": 0, "failed_checks": 0, "warnings": 0},
        }

    def run_command(self, cmd: list[str], cwd: Path = None) -> tuple[int, str, str]:
        """运行命令并返回结果"""
        try:
            result = subprocess.run(
                cmd,
                cwd=cwd or self.project_root,
                capture_output=True,
                text=True,
                timeout=300,  # 5分钟超时
            )
            return result.returncode, result.stdout, result.stderr
        except subprocess.TimeoutExpired:
            return -1, "", "命令执行超时"
        except Exception as e:
            return -1, "", str(e)

    def check_ruff(self) -> dict[str, Any]:
        """运行Ruff代码检查"""
        logger.info("🔍 运行Ruff代码检查...")
        cmd = ["uv", "run", "ruff", "check", ".", "--output-format=json"]
        returncode, stdout, stderr = self.run_command(cmd)

        issues = []
        if returncode == 0:
            logger.info("✅ Ruff检查通过")
        else:
            try:
                issues = json.loads(stdout) if stdout else []
            except json.JSONDecodeError:
                issues = [{"message": stderr or "Ruff检查失败"}]
            logger.info("❌ Ruff检查发现 {len(issues)} 个问题")

        return {"tool": "ruff", "returncode": returncode, "issues": issues, "output": stdout, "error": stderr}

    def check_black(self) -> dict[str, Any]:
        """运行Black代码格式化检查"""
        logger.info("🎨 运行Black格式化检查...")
        cmd = ["uv", "run", "black", "--check", "--diff", "."]
        returncode, stdout, stderr = self.run_command(cmd)

        if returncode == 0:
            logger.info("✅ Black格式化检查通过")
        else:
            logger.info("❌ Black格式化检查失败，需要格式化")

        return {"tool": "black", "returncode": returncode, "output": stdout, "error": stderr}

    def check_isort(self) -> dict[str, Any]:
        """运行isort导入排序检查"""
        logger.info("📦 运行isort导入排序检查...")
        cmd = ["uv", "run", "isort", "--check-only", "--diff", "."]
        returncode, stdout, stderr = self.run_command(cmd)

        if returncode == 0:
            logger.info("✅ isort导入排序检查通过")
        else:
            logger.info("❌ isort导入排序检查失败，需要重新排序")

        return {"tool": "isort", "returncode": returncode, "output": stdout, "error": stderr}

    def check_mypy(self) -> dict[str, Any]:
        """运行MyPy类型检查"""
        logger.info("🔬 运行MyPy类型检查...")
        cmd = ["uv", "run", "mypy", "app/", "--show-error-codes", "--show-column-numbers"]
        returncode, stdout, stderr = self.run_command(cmd)

        if returncode == 0:
            logger.info("✅ MyPy类型检查通过")
        else:
            logger.info("❌ MyPy类型检查发现类型问题")

        return {"tool": "mypy", "returncode": returncode, "output": stdout, "error": stderr}

    def check_bandit(self) -> dict[str, Any]:
        """运行Bandit安全扫描"""
        logger.info("🔒 运行Bandit安全扫描...")
        cmd = ["uv", "run", "bandit", "-r", "app/", "-f", "json"]
        returncode, stdout, stderr = self.run_command(cmd)

        issues = []
        if returncode == 0:
            logger.info("✅ Bandit安全扫描通过")
        else:
            try:
                result = json.loads(stdout) if stdout else {}
                issues = result.get("results", [])
            except json.JSONDecodeError:
                issues = [{"issue": {"text": stderr or "Bandit扫描失败"}}]
            logger.info("❌ Bandit安全扫描发现 {len(issues)} 个安全问题")

        return {"tool": "bandit", "returncode": returncode, "issues": issues, "output": stdout, "error": stderr}

    def check_pytest(self) -> dict[str, Any]:
        """运行pytest测试"""
        logger.info("🧪 运行pytest测试...")
        cmd = [
            "uv",
            "run",
            "pytest",
            "tests/",
            "-v",
            "--tb=short",
            "--json-report",
            "--json-report-file=test-report.json",
        ]
        returncode, stdout, stderr = self.run_command(cmd)

        # 读取测试报告
        test_report = {}
        report_file = self.project_root / "test-report.json"
        if report_file.exists():
            try:
                with open(report_file, encoding="utf-8") as f:
                    test_report = json.load(f)
            except (json.JSONDecodeError, FileNotFoundError):
                pass

        if returncode == 0:
            logger.info("✅ 所有测试通过")
        else:
            logger.info("❌ 部分测试失败")

        return {"tool": "pytest", "returncode": returncode, "output": stdout, "error": stderr, "report": test_report}

    def check_imports(self) -> dict[str, Any]:
        """检查未使用的导入"""
        logger.info("📋 检查未使用的导入...")
        cmd = ["uv", "run", "ruff", "check", ".", "--select", "F401", "--output-format=json"]
        returncode, stdout, stderr = self.run_command(cmd)

        unused_imports = []
        if returncode != 0:
            try:
                unused_imports = json.loads(stdout) if stdout else []
            except json.JSONDecodeError:
                pass

        if not unused_imports:
            logger.info("✅ 没有发现未使用的导入")
        else:
            logger.info("❌ 发现 {len(unused_imports)} 个未使用的导入")

        return {
            "tool": "unused_imports",
            "returncode": returncode,
            "unused_imports": unused_imports,
            "output": stdout,
            "error": stderr,
        }

    def check_complexity(self) -> dict[str, Any]:
        """检查代码复杂度"""
        logger.info("📊 检查代码复杂度...")
        cmd = ["uv", "run", "ruff", "check", ".", "--select", "C901", "--output-format=json"]
        returncode, stdout, stderr = self.run_command(cmd)

        complexity_issues = []
        if returncode != 0:
            try:
                complexity_issues = json.loads(stdout) if stdout else []
            except json.JSONDecodeError:
                pass

        if not complexity_issues:
            logger.info("✅ 代码复杂度检查通过")
        else:
            logger.info("❌ 发现 {len(complexity_issues)} 个复杂度问题")

        return {
            "tool": "complexity",
            "returncode": returncode,
            "complexity_issues": complexity_issues,
            "output": stdout,
            "error": stderr,
        }

    def run_all_checks(self) -> None:
        """运行所有检查"""
        logger.info("🚀 开始代码质量检查...")
        print("=" * 60)

        checks = [
            ("ruff", self.check_ruff),
            ("black", self.check_black),
            ("isort", self.check_isort),
            ("mypy", self.check_mypy),
            ("bandit", self.check_bandit),
            ("pytest", self.check_pytest),
            ("imports", self.check_imports),
            ("complexity", self.check_complexity),
        ]

        for check_name, check_func in checks:
            try:
                result = check_func()
                self.results["checks"][check_name] = result
                self.results["summary"]["total_checks"] += 1

                if result["returncode"] == 0:
                    self.results["summary"]["passed_checks"] += 1
                else:
                    self.results["summary"]["failed_checks"] += 1

            except Exception as e:
                logger.info("❌ {check_name} 检查出错: {e}")
                self.results["checks"][check_name] = {"tool": check_name, "returncode": -1, "error": str(e)}
                self.results["summary"]["total_checks"] += 1
                self.results["summary"]["failed_checks"] += 1

            print()

        self.print_summary()
        self.save_report()

    def print_summary(self) -> None:
        """打印检查摘要"""
        print("=" * 60)
        logger.info("📋 检查摘要")
        print("=" * 60)

        summary = self.results["summary"]
        logger.info("总检查项: {summary['total_checks']}")
        logger.info("通过: {summary['passed_checks']} ✅")
        logger.info("失败: {summary['failed_checks']} ❌")

        if summary["failed_checks"] > 0:
            logger.info("\n❌ 失败的检查:")
            for check_name, result in self.results["checks"].items():
                if result.get("returncode", 0) != 0:
                    logger.info("  - {check_name}: {result.get('error', '检查失败')}")

        print("\n" + "=" * 60)

        if summary["failed_checks"] == 0:
            logger.info("🎉 所有检查通过！代码质量良好！")
            sys.exit(0)
        else:
            logger.info("⚠️  发现代码质量问题，请修复后重新检查")
            sys.exit(1)

    def save_report(self) -> None:
        """保存检查报告"""
        report_file = self.project_root / "userdata" / "logs" / "quality_check_report.json"
        report_file.parent.mkdir(parents=True, exist_ok=True)

        with open(report_file, "w", encoding="utf-8") as f:
            json.dump(self.results, f, indent=2, ensure_ascii=False)

        logger.info("📄 详细报告已保存到: {report_file}")


def main():
    """主函数"""
    logger.info("泰摸鱼吧 - 代码质量检查工具")
    print("=" * 60)

    # 检查是否在项目根目录
    if not (Path.cwd() / "pyproject.toml").exists():
        logger.info("❌ 请在项目根目录运行此脚本")
        sys.exit(1)

    # 检查uv是否可用
    try:
        subprocess.run(["uv", "--version"], capture_output=True, check=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        logger.info("❌ 未找到uv命令，请先安装uv")
        sys.exit(1)

    checker = QualityChecker()
    checker.run_all_checks()


if __name__ == "__main__":
    main()
