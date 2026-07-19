"""pytest 全局 fixture - OSSAF 测试套件共享配置"""
import os
import sys
from pathlib import Path

import pytest

# 将项目根目录加入 sys.path，便于直接 import adapters / pipeline / schemas / mock_server
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


@pytest.fixture(scope="session")
def mock_server_url() -> str:
    """Mock 服务器基础 URL（端口 8765）。"""
    return "http://127.0.0.1:8765"


@pytest.fixture(scope="session")
def hugo_server_url() -> str:
    """Hugo 开发服务器基础 URL（端口 1313）。"""
    return "http://127.0.0.1:1313"


@pytest.fixture(scope="session")
def data_dir() -> Path:
    """种子数据目录路径。"""
    return PROJECT_ROOT / "data"


@pytest.fixture(scope="session")
def schemas_dir() -> Path:
    """JSON Schema 目录路径。"""
    return PROJECT_ROOT / "schemas"


@pytest.fixture(scope="session")
def project_root() -> Path:
    """项目根目录路径。"""
    return PROJECT_ROOT


@pytest.fixture(scope="session")
def layouts_dir() -> Path:
    """Hugo layouts 目录路径。"""
    return PROJECT_ROOT / "layouts"


@pytest.fixture(scope="session")
def content_dir() -> Path:
    """Hugo content 目录路径。"""
    return PROJECT_ROOT / "content"
