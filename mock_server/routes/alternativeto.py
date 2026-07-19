"""AlternativeTo API Mock - 模拟 /api/v1/software/{id}/alternatives 端点

根据商业软件 ID 返回对应的开源替代方案列表。
支持 5 个商业软件: photoshop, notion, figma, slack, zoom
"""
import json
import logging
from pathlib import Path
from typing import Any, Dict

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse

logger = logging.getLogger("mock_server.alternativeto")

router = APIRouter()

_FIXTURES_DIR = Path(__file__).resolve().parent.parent / "fixtures"

# 商业软件 ID 到 fixture 文件的映射
_SOFTWARE_FIXTURE_MAP: Dict[str, str] = {
    "photoshop": "alternativeto_photoshop.json",
    "adobe-photoshop": "alternativeto_photoshop.json",
    "notion": "alternativeto_notion.json",
    "figma": "alternativeto_figma.json",
    "slack": "alternativeto_slack.json",
    "zoom": "alternativeto_zoom.json",
    "zoom-meetings": "alternativeto_zoom.json",
}


def _load_fixture(name: str) -> Dict[str, Any]:
    """加载 fixture JSON 文件。"""
    fixture_path = _FIXTURES_DIR / name
    if not fixture_path.exists():
        logger.error("Fixture not found: %s", fixture_path)
        return {"alternatives": []}
    with fixture_path.open("r", encoding="utf-8") as f:
        return json.load(f)


@router.get("/api/v1/software/{software_id}/alternatives")
async def get_alternatives(software_id: str) -> JSONResponse:
    """模拟 AlternativeTo /api/v1/software/{id}/alternatives 端点。

    根据商业软件 ID 返回对应的开源替代方案列表。
    若 ID 不在支持列表中，则返回 404 错误。
    """
    logger.info("AlternativeTo mock received request, software_id=%s", software_id)

    fixture_name = _SOFTWARE_FIXTURE_MAP.get(software_id.lower())
    if fixture_name is None:
        logger.warning("Unknown software_id: %s", software_id)
        raise HTTPException(
            status_code=404,
            detail={
                "error": "software_not_found",
                "message": f"Software '{software_id}' is not supported by mock server",
                "supported_ids": list(_SOFTWARE_FIXTURE_MAP.keys()),
            },
        )

    response_data = _load_fixture(fixture_name)
    return JSONResponse(content=response_data)
