"""Claude API Mock - 模拟 Anthropic Claude /v1/messages 端点

响应结构特征（一级数组嵌套）:
    response.content[].text
"""
import json
import logging
from pathlib import Path
from typing import Any, Dict

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

logger = logging.getLogger("mock_server.claude")

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


@router.post("/v1/messages")
async def create_message(request: Request) -> JSONResponse:
    """模拟 Anthropic Claude /v1/messages 端点。

    接受任意请求体，返回 fixture 中预录制的 Claude 响应。
    响应格式为 content[].text 一级数组嵌套结构。
    """
    try:
        body = await request.json()
        logger.info(
            "Claude mock received request, model=%s, messages=%d",
            body.get("model", "unknown"),
            len(body.get("messages", [])),
        )
    except Exception as exc:
        logger.warning("Failed to parse request body: %s", exc)

    response_data = _load_fixture("claude_comparison.json")
    return JSONResponse(content=response_data)
