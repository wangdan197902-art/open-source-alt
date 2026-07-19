"""Schema校验脚本 - 验证JSON Schema文件本身的合法性"""
import json
from pathlib import Path
from jsonschema import Draft7Validator

SCHEMAS_DIR = Path(__file__).parent

def validate_all_schemas():
    schemas = [
        "proprietary.schema.json",
        "opensource.schema.json",
        "comparison.schema.json",
        "translation.schema.json",
        "image-meta.schema.json",
    ]
    for schema_file in schemas:
        path = SCHEMAS_DIR / schema_file
        with open(path) as f:
            schema = json.load(f)
        Draft7Validator.check_schema(schema)
        print(f"✅ {schema_file} - valid")

if __name__ == "__main__":
    validate_all_schemas()
