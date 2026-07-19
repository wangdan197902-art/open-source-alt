"""GitHub API Mock - 模拟 GitHub /repos/{owner}/{repo}/contents/{path} 端点

返回 Awesome Lists 数据（5个商业软件的开源替代方案列表）。
响应符合 GitHub Contents API 格式。
"""
import json
import logging
from pathlib import Path
from typing import Any, Dict

from fastapi import APIRouter
from fastapi.responses import JSONResponse

logger = logging.getLogger("mock_server.github")

router = APIRouter()

_FIXTURES_DIR = Path(__file__).resolve().parent.parent / "fixtures"


def _load_fixture(name: str) -> Dict[str, Any]:
    """加载 fixture JSON 文件。"""
    fixture_path = _FIXTURES_DIR / name
    if not fixture_path.exists():
        logger.error("Fixture not found: %s", fixture_path)
        return {}
    with fixture_path.open("r", encoding="utf-8") as f:
        return json.load(f)


@router.get("/repos/{owner}/{repo}/contents/{path:path}")
async def get_repo_contents(owner: str, repo: str, path: str) -> JSONResponse:
    """模拟 GitHub /repos/{owner}/{repo}/contents/{path} 端点。

    返回 fixture 中预录制的 Awesome Lists 数据（base64 编码的 Markdown）。
    无论 owner/repo/path 为何值，均返回相同的 Awesome Lists 内容，
    以便 Mock 测试时简化调用方逻辑。
    """
    logger.info(
        "GitHub mock received request, owner=%s, repo=%s, path=%s",
        owner,
        repo,
        path,
    )

    response_data = _load_fixture("github_awesome_list.json")
    return JSONResponse(content=response_data)
