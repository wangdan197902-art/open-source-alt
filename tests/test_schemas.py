"""Schema 测试 - 验证 5 份 JSON Schema 与 Pydantic 模型一致性"""
import json
from pathlib import Path

import pytest
from jsonschema import Draft7Validator

from schemas.pydantic_models import (
    Comparison,
    ImageMeta,
    OpenSource,
    Proprietary,
    Translation,
)


SCHEMA_FILES = [
    "proprietary.schema.json",
    "opensource.schema.json",
    "comparison.schema.json",
    "translation.schema.json",
    "image-meta.schema.json",
]


class TestSchemaFiles:
    """JSON Schema 文件存在性与合法性"""

    @pytest.mark.parametrize("schema_file", SCHEMA_FILES)
    def test_schema_file_exists(self, schemas_dir, schema_file):
        """5 份 Schema 文件均存在"""
        path = schemas_dir / schema_file
        assert path.exists(), f"Schema 文件缺失: {schema_file}"

    @pytest.mark.parametrize("schema_file", SCHEMA_FILES)
    def test_schema_passes_draft7(self, schemas_dir, schema_file):
        """Schema 自身通过 Draft-07 元 Schema 校验"""
        path = schemas_dir / schema_file
        with path.open("r", encoding="utf-8") as f:
            schema = json.load(f)
        # 不会抛出异常即视为通过
        Draft7Validator.check_schema(schema)

    def test_schema_count_is_five(self, schemas_dir):
        """Schema 文件总数为 5"""
        files = list(schemas_dir.glob("*.schema.json"))
        assert len(files) == 5, f"期望 5 份 Schema，实际 {len(files)}"


class TestSchemaFields:
    """Schema 关键字段约束测试"""

    def _load_schema(self, schemas_dir, name):
        with (schemas_dir / name).open("r", encoding="utf-8") as f:
            return json.load(f)

    def test_proprietary_reviewStatus_is_enum(self, schemas_dir):
        """proprietary.reviewStatus 为枚举"""
        schema = self._load_schema(schemas_dir, "proprietary.schema.json")
        rs = schema["properties"]["reviewStatus"]
        assert rs["type"] == "string"
        assert "enum" in rs
        assert set(rs["enum"]) == {"pending", "approved", "rejected"}

    def test_proprietary_aiGenerated_is_boolean(self, schemas_dir):
        """proprietary.aiGenerated 为 boolean"""
        schema = self._load_schema(schemas_dir, "proprietary.schema.json")
        ag = schema["properties"]["aiGenerated"]
        assert ag["type"] == "boolean"

    def test_opensource_reviewStatus_is_enum(self, schemas_dir):
        """opensource.reviewStatus 为枚举"""
        schema = self._load_schema(schemas_dir, "opensource.schema.json")
        rs = schema["properties"]["reviewStatus"]
        assert "enum" in rs
        assert "approved" in rs["enum"]

    def test_opensource_aiGenerated_is_boolean(self, schemas_dir):
        """opensource.aiGenerated 为 boolean"""
        schema = self._load_schema(schemas_dir, "opensource.schema.json")
        ag = schema["properties"]["aiGenerated"]
        assert ag["type"] == "boolean"

    def test_comparison_reviewStatus_is_enum(self, schemas_dir):
        """comparison.reviewStatus 为枚举"""
        schema = self._load_schema(schemas_dir, "comparison.schema.json")
        rs = schema["properties"]["reviewStatus"]
        assert "enum" in rs

    def test_comparison_aiGenerated_is_boolean(self, schemas_dir):
        """comparison.aiGenerated 为 boolean"""
        schema = self._load_schema(schemas_dir, "comparison.schema.json")
        ag = schema["properties"]["aiGenerated"]
        assert ag["type"] == "boolean"

    def test_translation_reviewStatus_is_enum(self, schemas_dir):
        """translation.reviewStatus 为枚举"""
        schema = self._load_schema(schemas_dir, "translation.schema.json")
        rs = schema["properties"]["reviewStatus"]
        assert "enum" in rs

    def test_image_meta_reviewStatus_is_enum(self, schemas_dir):
        """image-meta.reviewStatus 为枚举"""
        schema = self._load_schema(schemas_dir, "image-meta.schema.json")
        rs = schema["properties"]["reviewStatus"]
        assert "enum" in rs

    def test_all_schemas_have_meta_block(self, schemas_dir):
        """所有 Schema 都包含 _meta 溯源块"""
        for name in SCHEMA_FILES:
            schema = self._load_schema(schemas_dir, name)
            assert "_meta" in schema["properties"], f"{name} 缺少 _meta 块"
            assert "_meta" in schema["required"], f"{name} 未要求 _meta 字段"


class TestPydanticModels:
    """Pydantic 模型可正常导入与字段约束"""

    def test_proprietary_model_importable(self):
        """Proprietary 模型可导入"""
        assert Proprietary.__name__ == "Proprietary"

    def test_opensource_model_importable(self):
        """OpenSource 模型可导入"""
        assert OpenSource.__name__ == "OpenSource"

    def test_comparison_model_importable(self):
        """Comparison 模型可导入"""
        assert Comparison.__name__ == "Comparison"

    def test_translation_model_importable(self):
        """Translation 模型可导入"""
        assert Translation.__name__ == "Translation"

    def test_image_meta_model_importable(self):
        """ImageMeta 模型可导入"""
        assert ImageMeta.__name__ == "ImageMeta"

    def test_proprietary_reviewStatus_field_is_literal(self):
        """Proprietary.reviewStatus 字段类型为 Literal（枚举语义）"""
        field_info = Proprietary.model_fields["reviewStatus"]
        # Literal 类型注解会以 typing.Literal 形式存在
        assert "pending" in str(field_info.annotation)
        assert "approved" in str(field_info.annotation)
        assert "rejected" in str(field_info.annotation)

    def test_proprietary_aiGenerated_field_is_bool(self):
        """Proprietary.aiGenerated 字段类型为 bool"""
        field_info = Proprietary.model_fields["aiGenerated"]
        assert field_info.annotation is bool
