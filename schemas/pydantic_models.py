"""OSSAF Pydantic Models - 与 JSON Schema 一一对应的运行时模型 (Pydantic v2)

本模块定义了 5 个核心实体模型，与同目录下的 5 份 JSON Schema 文件保持
字段级一致性，作为 Mock 数据生成器、Hugo 内容生成器和适配器之间的运行时
单一真相源 (SSOT)。

对应关系:
    Proprietary  ↔ proprietary.schema.json
    OpenSource   ↔ opensource.schema.json
    Comparison   ↔ comparison.schema.json
    Translation  ↔ translation.schema.json
    ImageMeta    ↔ image-meta.schema.json

注意:
    - 所有模型均禁止额外字段 (extra="forbid")，对应 JSON Schema 的
      additionalProperties: false
    - _meta 字段在 Python 端通过别名 `meta` 暴露，序列化时需使用
      by_alias=True 以保持与 JSON Schema 字段名一致
"""
from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


# =============================================================================
# 公共溯源块 _meta
# =============================================================================
class Meta(BaseModel):
    """溯源元数据块，记录数据的来源、Schema版本和置信度。

    对应 JSON Schema 中所有实体的 `_meta` 对象定义。
    """

    model_config = ConfigDict(extra="forbid")

    source: str = Field(
        ...,
        description="派生来源，如 'manual'、'ai-generated'、'official-api'",
    )
    schema_version: str = Field(
        ...,
        description="Schema版本号，遵循 semver，如 '1.0.0'",
    )
    unverified_fields: Optional[List[str]] = Field(
        default=None,
        description="尚未经人工核实的字段名列表",
    )
    confidence: Literal["high", "medium", "low"] = Field(
        ...,
        description="数据置信度",
    )


# =============================================================================
# 1. 商业软件 Proprietary  ↔  proprietary.schema.json
# =============================================================================
class Proprietary(BaseModel):
    """商业软件记录。对应 proprietary.schema.json。"""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    id: str = Field(
        ...,
        description="唯一标识符，使用 kebab-case，如 'photoshop'",
        pattern=r"^[a-z0-9]+(-[a-z0-9]+)*$",
        min_length=1,
        max_length=64,
    )
    name: str = Field(
        ...,
        description="软件官方名称，如 'Adobe Photoshop'",
        min_length=1,
        max_length=128,
    )
    vendor: str = Field(
        ...,
        description="软件厂商/提供商名称，如 'Adobe'",
        min_length=1,
        max_length=128,
    )
    category: str = Field(
        ...,
        description="分类标识符，使用 kebab-case，如 'image-editing'",
        pattern=r"^[a-z0-9]+(-[a-z0-9]+)*$",
        min_length=1,
        max_length=64,
    )
    officialUrl: str = Field(
        ...,
        description="软件官方网站URL",
        pattern=r"^https?://",
    )
    pricingModel: str = Field(
        ...,
        description="定价模型，如 'subscription'、'one-time'、'freemium'",
        min_length=1,
        max_length=64,
    )
    platforms: List[str] = Field(
        ...,
        description="支持的平台列表，如 ['windows', 'macos', 'linux']",
        min_length=1,
    )
    trademarkStatus: Literal["pending-review", "reviewed", "rejected"] = Field(
        ...,
        description="商标状态：待审核/已审核/已拒绝",
    )
    reviewStatus: Literal["pending", "approved", "rejected"] = Field(
        ...,
        description="审核状态：待审核/已通过/已拒绝",
    )
    aiGenerated: bool = Field(
        ...,
        description="是否由AI生成（标记数据来源，便于后续人工复核）",
    )
    metadata: Optional[Dict[str, Any]] = Field(
        default=None,
        description="可选的扩展元数据",
    )
    meta: Meta = Field(
        ...,
        alias="_meta",
        description="溯源元数据块",
    )


# =============================================================================
# 2. 开源软件 OpenSource  ↔  opensource.schema.json
# =============================================================================
class OpenSource(BaseModel):
    """开源软件记录。对应 opensource.schema.json。"""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    id: str = Field(
        ...,
        description="唯一标识符，使用 kebab-case，如 'gimp'",
        pattern=r"^[a-z0-9]+(-[a-z0-9]+)*$",
        min_length=1,
        max_length=64,
    )
    name: str = Field(
        ...,
        description="开源软件官方名称，如 'GIMP'",
        min_length=1,
        max_length=128,
    )
    license: Literal[
        "MIT",
        "Apache-2.0",
        "GPL-2.0",
        "GPL-3.0",
        "BSD-2-Clause",
        "BSD-3-Clause",
        "LGPL-2.1",
        "LGPL-3.0",
        "MPL-2.0",
        "AGPL-3.0",
        "CDDL-1.0",
        "EPL-2.0",
    ] = Field(
        ...,
        description="OSI 认证的开源协议 SPDX 标识符",
    )
    repository: str = Field(
        ...,
        description="代码仓库URL",
        pattern=r"^https?://",
    )
    category: str = Field(
        ...,
        description="分类标识符，使用 kebab-case",
        pattern=r"^[a-z0-9]+(-[a-z0-9]+)*$",
        min_length=1,
        max_length=64,
    )
    platforms: List[str] = Field(
        ...,
        description="支持的平台列表",
        min_length=1,
    )
    maturityLevel: Literal["experimental", "beta", "stable", "mature"] = Field(
        ...,
        description="项目成熟度等级",
    )
    communitySize: Literal["small", "medium", "large", "huge"] = Field(
        ...,
        description="社区规模",
    )
    reviewStatus: Literal["pending", "approved", "rejected"] = Field(
        ...,
        description="审核状态",
    )
    aiGenerated: bool = Field(
        ...,
        description="是否由AI生成",
    )
    metadata: Optional[Dict[str, Any]] = Field(
        default=None,
        description="可选的扩展元数据",
    )
    meta: Meta = Field(
        ...,
        alias="_meta",
        description="溯源元数据块",
    )


# =============================================================================
# 3. 对比内容 Comparison  ↔  comparison.schema.json
# =============================================================================
class FeatureComparisonItem(BaseModel):
    """功能对比的单个条目。"""

    model_config = ConfigDict(extra="forbid")

    feature: str = Field(
        ...,
        description="功能名称，如 '图层编辑'",
        min_length=1,
        max_length=128,
    )
    proprietarySupport: Literal["yes", "partial", "no"] = Field(
        ...,
        description="商业软件对该功能的支持程度",
    )
    openSourceSupport: Literal["yes", "partial", "no"] = Field(
        ...,
        description="开源软件对该功能的支持程度",
    )
    notes: Optional[str] = Field(
        default=None,
        description="可选的功能差异备注",
        max_length=512,
    )


class AIGeneratedDetails(BaseModel):
    """AI 生成详情。"""

    model_config = ConfigDict(extra="forbid")

    model: Optional[str] = Field(
        default=None,
        description="生成内容所用的AI模型标识",
        max_length=64,
    )
    generatedAt: Optional[str] = Field(
        default=None,
        description="生成时间，ISO 8601 格式",
    )
    promptHash: Optional[str] = Field(
        default=None,
        description="所用提示词的哈希值",
        max_length=128,
    )
    tokensUsed: Optional[int] = Field(
        default=None,
        description="本次生成消耗的 token 数量",
        ge=0,
    )


class Comparison(BaseModel):
    """商业软件与开源软件对比内容。对应 comparison.schema.json。"""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    id: str = Field(
        ...,
        description="唯一标识符，使用 kebab-case，如 'photoshop-vs-gimp'",
        pattern=r"^[a-z0-9]+(-[a-z0-9]+)*$",
        min_length=1,
        max_length=128,
    )
    proprietaryId: str = Field(
        ...,
        description="关联的商业软件ID",
        pattern=r"^[a-z0-9]+(-[a-z0-9]+)*$",
        min_length=1,
        max_length=64,
    )
    openSourceId: str = Field(
        ...,
        description="关联的开源软件ID",
        pattern=r"^[a-z0-9]+(-[a-z0-9]+)*$",
        min_length=1,
        max_length=64,
    )
    featureComparison: List[FeatureComparisonItem] = Field(
        ...,
        description="功能逐项对比列表",
        min_length=1,
    )
    pros: List[str] = Field(
        default_factory=list,
        description="开源软件相对于商业软件的优势列表",
    )
    cons: List[str] = Field(
        default_factory=list,
        description="开源软件相对于商业软件的劣势列表",
    )
    migrationDifficulty: Literal["easy", "medium", "hard"] = Field(
        ...,
        description="迁移难度等级",
    )
    useCases: List[str] = Field(
        ...,
        description="适用场景列表",
        min_length=1,
    )
    aiGenerated: bool = Field(
        ...,
        description="是否由AI生成",
    )
    aiGeneratedDetails: Optional[AIGeneratedDetails] = Field(
        default=None,
        description="AI生成的详情",
    )
    reviewStatus: Literal["pending", "approved", "rejected"] = Field(
        ...,
        description="审核状态",
    )
    metadata: Optional[Dict[str, Any]] = Field(
        default=None,
        description="可选的扩展元数据",
    )
    meta: Meta = Field(
        ...,
        alias="_meta",
        description="溯源元数据块",
    )


# =============================================================================
# 4. 翻译内容 Translation  ↔  translation.schema.json
# =============================================================================
class Translation(BaseModel):
    """翻译内容记录。对应 translation.schema.json。"""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    id: str = Field(
        ...,
        description="唯一标识符，使用 kebab-case",
        pattern=r"^[a-z0-9]+(-[a-z0-9]+)*$",
        min_length=1,
        max_length=128,
    )
    sourceTextHash: str = Field(
        ...,
        description="源文本的哈希值（推荐 SHA-256），用于缓存命中与去重判定",
        pattern=r"^[a-fA-F0-9]{32,128}$",
        min_length=32,
        max_length=128,
    )
    targetLang: Literal[
        "en",
        "zh",
        "zh-tw",
        "ja",
        "ko",
        "es",
        "fr",
        "de",
        "pt",
        "it",
        "ru",
        "ar",
        "nl",
        "pl",
        "tr",
        "id",
        "vi",
        "th",
        "hi",
        "bn",
        "ms",
        "uk",
    ] = Field(
        ...,
        description="目标语言代码（BCP 47 子集）",
    )
    translatedText: str = Field(
        ...,
        description="翻译后的文本内容",
        min_length=1,
    )
    translatorModel: str = Field(
        ...,
        description="执行翻译的模型标识",
        min_length=1,
        max_length=64,
    )
    confidenceScore: float = Field(
        ...,
        description="翻译置信度评分，范围 [0, 1]",
        ge=0,
        le=1,
    )
    reviewStatus: Literal["pending", "approved", "rejected"] = Field(
        ...,
        description="审核状态",
    )
    metadata: Optional[Dict[str, Any]] = Field(
        default=None,
        description="可选的扩展元数据",
    )
    meta: Meta = Field(
        ...,
        alias="_meta",
        description="溯源元数据块",
    )


# =============================================================================
# 5. 配图元数据 ImageMeta  ↔  image-meta.schema.json
# =============================================================================
class ImageMeta(BaseModel):
    """配图元数据。对应 image-meta.schema.json。"""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    id: str = Field(
        ...,
        description="唯一标识符，使用 kebab-case",
        pattern=r"^[a-z0-9]+(-[a-z0-9]+)*$",
        min_length=1,
        max_length=128,
    )
    type: Literal[
        "screenshot",
        "logo",
        "diagram",
        "comparison-chart",
        "icon",
        "illustration",
    ] = Field(
        ...,
        description="图片类型：截图/Logo/示意图/对比图/图标/插画",
    )
    prompt: str = Field(
        ...,
        description="图片生成提示词",
        min_length=1,
        max_length=2048,
    )
    modelUsed: str = Field(
        ...,
        description="用于生成图片的模型标识",
        min_length=1,
        max_length=64,
    )
    url: str = Field(
        ...,
        description="图片访问URL（可为本地相对路径或CDN URL）",
        min_length=1,
        max_length=1024,
    )
    altText: str = Field(
        ...,
        description="图片替代文本（用于无障碍访问和SEO）",
        min_length=1,
        max_length=256,
    )
    licenseInfo: str = Field(
        ...,
        description="图片许可证信息",
        min_length=1,
        max_length=128,
    )
    reviewStatus: Literal["pending", "approved", "rejected"] = Field(
        ...,
        description="审核状态",
    )
    metadata: Optional[Dict[str, Any]] = Field(
        default=None,
        description="可选的扩展元数据",
    )
    meta: Meta = Field(
        ...,
        alias="_meta",
        description="溯源元数据块",
    )


__all__ = [
    "Meta",
    "Proprietary",
    "OpenSource",
    "FeatureComparisonItem",
    "AIGeneratedDetails",
    "Comparison",
    "Translation",
    "ImageMeta",
]
