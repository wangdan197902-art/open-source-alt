"""Gemini API Mock - 模拟 Google Gemini /v1/models/{model}:generateContent 端点

响应结构特征（三级数组嵌套）:
    response.candidates[].content.parts[].text
"""
import json
import logging
from pathlib import Path
from typing import Any, Dict

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

logger = logging.getLogger("mock_server.gemini")

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


@router.post("/v1/models/{model}:generateContent")
async def generate_content(model: str, request: Request) -> JSONResponse:
    """模拟 Google Gemini /v1/models/{model}:generateContent 端点。

    接受任意请求体，返回 fixture 中预录制的 Gemini 响应。
    响应格式为 candidates[].content.parts[].text 三级数组嵌套结构。
    """
    try:
        body = await request.json()
        logger.info(
            "Gemini mock received request, model=%s, contents=%d",
            model,
            len(body.get("contents", [])),
        )
    except Exception as exc:
        logger.warning("Failed to parse request body: %s", exc)

    response_data = _load_fixture("gemini_comparison.json")
    return JSONResponse(content=response_data)
