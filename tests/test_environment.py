"""环境测试 - 验证开发环境前置条件已满足"""
import sys
import shutil
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent


class TestPythonEnvironment:
    """Python 运行时环境测试"""

    def test_python_version_meets_minimum(self):
        """Python 版本 >= 3.11"""
        major, minor = sys.version_info[:2]
        assert (major, minor) >= (3, 11), (
            f"Python {major}.{minor} 不满足最低要求 3.11"
        )

    def test_python_version_3_14_or_above_supported(self):
        """Python 3.14 及以上版本运行时信息可读取"""
        assert sys.version_info.major == 3
        assert isinstance(sys.executable, str) and len(sys.executable) > 0


class TestHugoInstalled:
    """Hugo 静态站点生成器可用性测试"""

    def test_hugo_binary_in_path(self):
        """hugo 可执行文件可在 PATH 中找到"""
        hugo_path = shutil.which("hugo")
        assert hugo_path is not None, "hugo 未安装或不在 PATH 中"

    def test_hugo_version_command_runs(self):
        """hugo version 命令可执行（通过 exit code 验证）"""
        import subprocess
        result = subprocess.run(
            ["hugo", "version"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        assert result.returncode == 0
        assert "hugo" in result.stdout.lower()


class TestPythonDependencies:
    """requirements.txt 中的核心依赖已安装"""

    REQUIRED_PACKAGES = [
        "fastapi",
        "uvicorn",
        "pydantic",
        "httpx",
        "requests",
        "jsonschema",
        "pytest",
        "tenacity",
        "dotenv",
    ]

    @pytest.mark.parametrize("package", REQUIRED_PACKAGES)
    def test_package_importable(self, package):
        """核心依赖包可正常导入"""
        try:
            __import__(package)
        except ImportError as exc:
            pytest.fail(f"依赖包 {package} 未安装: {exc}")


class TestProjectFiles:
    """项目关键文件存在性测试"""

    def test_env_mock_exists(self):
        """.env.mock 文件存在"""
        env_mock = PROJECT_ROOT / ".env.mock"
        assert env_mock.exists(), ".env.mock 文件缺失"

    def test_env_mock_has_required_keys(self):
        """.env.mock 包含核心配置项"""
        env_mock = PROJECT_ROOT / ".env.mock"
        content = env_mock.read_text(encoding="utf-8")
        required_keys = [
            "OSSAF_API_BASE_URL",
            "OSSAF_AI_BACKEND",
            "ANTHROPIC_API_KEY",
            "OPENAI_API_KEY",
            "GOOGLE_API_KEY",
        ]
        for key in required_keys:
            assert key in content, f".env.mock 缺少 {key}"

    def test_makefile_exists(self):
        """Makefile 存在"""
        makefile = PROJECT_ROOT / "Makefile"
        assert makefile.exists(), "Makefile 缺失"

    def test_makefile_executable_target_help(self):
        """make help 命令可执行"""
        import subprocess
        result = subprocess.run(
            ["make", "help"],
            cwd=str(PROJECT_ROOT),
            capture_output=True,
            text=True,
            timeout=10,
        )
        assert result.returncode == 0
        assert "OSSAF" in result.stdout or "命令" in result.stdout

    def test_requirements_txt_exists(self):
        """requirements.txt 存在"""
        req = PROJECT_ROOT / "requirements.txt"
        assert req.exists(), "requirements.txt 缺失"

    def test_hugo_toml_exists(self):
        """hugo.toml 存在"""
        hugo_toml = PROJECT_ROOT / "hugo.toml"
        assert hugo_toml.exists(), "hugo.toml 缺失"


class TestProjectStructure:
    """项目目录结构完整性"""

    REQUIRED_DIRS = [
        "adapters",
        "pipeline",
        "mock_server",
        "schemas",
        "data",
        "content",
        "layouts",
        "static",
    ]

    @pytest.mark.parametrize("dir_name", REQUIRED_DIRS)
    def test_required_directory_exists(self, dir_name):
        """必需的子目录均存在"""
        dir_path = PROJECT_ROOT / dir_name
        assert dir_path.exists() and dir_path.is_dir(), (
            f"目录 {dir_name} 缺失"
        )
