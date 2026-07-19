"""AGNES_LLM API Mock - 模拟 AGNES_LLM /v1/chat/completions 端点

AGNES_LLM 兼容 OpenAI Chat Completions API 格式（国内可达，无需翻墙）。
响应结构特征（二级数组嵌套，同 OpenAI）:
    response.choices[].message.content

挂载前缀：/agnes（在 main.py 中通过 prefix="/agnes" 注册）
完整路径：/agnes/v1/chat/completions
"""
import logging
import time
import uuid
from typing import Any, Dict

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

logger = logging.getLogger("mock_server.agnes")

router = APIRouter()


@router.post("/v1/chat/completions")
async def create_chat_completion(request: Request) -> JSONResponse:
    """模拟 AGNES_LLM /v1/chat/completions 端点。

    接受任意请求体，返回符合 OpenAI Chat Completions API 格式的响应。
    Mock 响应内容为简单的翻译示例文本（默认 agnes-2.0-flash 模型）。
    """
    try:
        body = await request.json()
        logger.info(
            "AGNES mock received request, model=%s, messages=%d",
            body.get("model", "unknown"),
            len(body.get("messages", [])),
        )
    except Exception as exc:
        logger.warning("Failed to parse request body: %s", exc)

    # 生成符合 OpenAI Chat Completions API 格式的 Mock 响应
    response_data: Dict[str, Any] = {
        "id": f"chatcmpl-agnes-mock-{uuid.uuid4().hex[:8]}",
        "object": "chat.completion",
        "created": int(time.time()),
        "model": "agnes-2.0-flash",
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": (
                        "[AGNES Mock 翻译示例] Adobe Photoshop 是由 Adobe 公司开发的专业图像编辑软件，"
                        "广泛用于照片修饰、数字艺术和图形设计。"
                    ),
                },
                "finish_reason": "stop",
            }
        ],
        "usage": {
            "prompt_tokens": 32,
            "completion_tokens": 48,
            "total_tokens": 80,
        },
    }
    return JSONResponse(content=response_data)
