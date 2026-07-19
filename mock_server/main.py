"""OSSAF Mock Server - FastAPI 应用入口

模拟 6 个外部 API:
    1. Anthropic Claude  - /v1/messages
    2. OpenAI GPT-4o     - /v1/chat/completions
    3. Google Gemini     - /v1/models/{model}:generateContent
    4. AGNES_LLM         - /agnes/v1/chat/completions（国内可达，OpenAI 兼容格式）
    5. GitHub            - /repos/{owner}/{repo}/contents/{path}
    6. AlternativeTo     - /api/v1/software/{id}/alternatives

启动命令:
    uvicorn mock_server.main:app --host 127.0.0.1 --port 8765
    或
    python3 -m mock_server

绑定地址: 127.0.0.1:8765
CORS: 仅允许 http://localhost:1313 (Hugo 开发服务器)
"""
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routes import agnes, alternativeto, claude, gemini, github, openai

# =============================================================================
# 日志配置
# =============================================================================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("mock_server.main")

# =============================================================================
# FastAPI 应用
# =============================================================================
app = FastAPI(
    title="OSSAF Mock Server",
    description="OSSAF 项目的本地 Mock 服务器，模拟 6 个外部 API（Claude/GPT-4o/Gemini/AGNES_LLM/GitHub/AlternativeTo）",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# =============================================================================
# CORS 配置（仅允许 Hugo 开发服务器）
# =============================================================================
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:1313",
        "http://127.0.0.1:1313",
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["*"],
)

# =============================================================================
# 注册路由模块
# =============================================================================
app.include_router(claude.router, tags=["Claude API"])
app.include_router(openai.router, tags=["OpenAI API"])
app.include_router(gemini.router, tags=["Gemini API"])
app.include_router(agnes.router, prefix="/agnes", tags=["AGNES_LLM API"])
app.include_router(github.router, tags=["GitHub API"])
app.include_router(alternativeto.router, tags=["AlternativeTo API"])


# =============================================================================
# 健康检查与根端点
# =============================================================================
@app.get("/health", tags=["Health"])
async def health_check() -> dict:
    """健康检查端点。"""
    return {"status": "healthy", "service": "ossaf-mock-server"}


@app.get("/", tags=["Root"])
async def root() -> dict:
    """根端点 - 返回 API 列表。"""
    return {
        "service": "ossaf-mock-server",
        "version": "0.1.0",
        "description": "OSSAF 本地 Mock 服务器，模拟 6 个外部 API",
        "endpoints": {
            "health": "GET /health",
            "docs": "GET /docs",
            "apis": [
                {
                    "name": "Claude (Anthropic)",
                    "method": "POST",
                    "path": "/v1/messages",
                    "response_structure": "content[].text (一级数组嵌套)",
                },
                {
                    "name": "OpenAI GPT-4o",
                    "method": "POST",
                    "path": "/v1/chat/completions",
                    "response_structure": "choices[].message.content (二级数组嵌套)",
                },
                {
                    "name": "Google Gemini",
                    "method": "POST",
                    "path": "/v1/models/{model}:generateContent",
                    "response_structure": "candidates[].content.parts[].text (三级数组嵌套)",
                },
                {
                    "name": "AGNES_LLM (国内可达，OpenAI 兼容)",
                    "method": "POST",
                    "path": "/agnes/v1/chat/completions",
                    "response_structure": "choices[].message.content (二级数组嵌套，同 OpenAI)",
                    "default_model": "agnes-2.0-flash",
                },
                {
                    "name": "GitHub",
                    "method": "GET",
                    "path": "/repos/{owner}/{repo}/contents/{path}",
                    "response_structure": "GitHub Contents API 格式 (base64 编码)",
                },
                {
                    "name": "AlternativeTo",
                    "method": "GET",
                    "path": "/api/v1/software/{software_id}/alternatives",
                    "response_structure": "alternatives[] 数组",
                    "supported_ids": [
                        "photoshop",
                        "notion",
                        "figma",
                        "slack",
                        "zoom",
                    ],
                },
            ],
        },
    }


logger.info("OSSAF Mock Server application initialized")
