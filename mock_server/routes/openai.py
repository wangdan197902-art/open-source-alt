"""OpenAI API Mock - 模拟 OpenAI /v1/chat/completions 端点

响应结构特征（二级数组嵌套）:
    response.choices[].message.content
"""
import json
import logging
from pathlib import Path
from typing import Any, Dict

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

logger = logging.getLogger("mock_server.openai")

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


@router.post("/v1/chat/completions")
async def create_chat_completion(request: Request) -> JSONResponse:
    """模拟 OpenAI /v1/chat/completions 端点。

    接受任意请求体，返回 fixture 中预录制的 OpenAI 响应。
    响应格式为 choices[].message.content 二级数组嵌套结构。
    """
    try:
        body = await request.json()
        logger.info(
            "OpenAI mock received request, model=%s, messages=%d",
            body.get("model", "unknown"),
            len(body.get("messages", [])),
        )
    except Exception as exc:
        logger.warning("Failed to parse request body: %s", exc)

    response_data = _load_fixture("openai_comparison.json")
    return JSONResponse(content=response_data)
