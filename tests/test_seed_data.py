"""种子数据测试 - 验证 5 类种子数据的完整性、规模与审核状态"""
import json
from pathlib import Path

import pytest

EXPECTED_PROPRIETARY = ["photoshop", "notion", "figma", "slack", "zoom"]
EXPECTED_OPENSOURCE = ["gimp", "obsidian", "penpot", "element", "bigbluebutton"]
EXPECTED_COMPARISONS = [
    "photoshop-vs-gimp",
    "notion-vs-obsidian",
    "figma-vs-penpot",
    "slack-vs-element",
    "zoom-vs-bigbluebutton",
]
EXPECTED_LANGUAGES = ["en", "zh", "ja", "ko", "es"]
MAX_SEED_SCALE = 10  # 种子规模上限：每类 ≤ 10 条


def _load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


class TestSeedDataExistence:
    """5 类种子数据存在性测试"""

    def test_proprietary_data_exists(self, data_dir):
        """5 个商业软件数据存在"""
        proprietary_dir = data_dir / "proprietary"
        assert proprietary_dir.exists()
        for sw in EXPECTED_PROPRIETARY:
            assert (proprietary_dir / f"{sw}.json").exists(), (
                f"缺失商业软件数据: {sw}.json"
            )

    def test_opensource_data_exists(self, data_dir):
        """5 个开源软件数据存在"""
        opensource_dir = data_dir / "opensource"
        assert opensource_dir.exists()
        for sw in EXPECTED_OPENSOURCE:
            assert (opensource_dir / f"{sw}.json").exists(), (
                f"缺失开源软件数据: {sw}.json"
            )

    def test_comparison_data_exists(self, data_dir):
        """5 个对比内容数据存在"""
        comparison_dir = data_dir / "comparison"
        assert comparison_dir.exists()
        for c in EXPECTED_COMPARISONS:
            assert (comparison_dir / f"{c}.json").exists(), (
                f"缺失对比数据: {c}.json"
            )

    def test_translation_data_exists(self, data_dir):
        """25 个翻译数据存在（5 软件 × 5 语言）"""
        translation_dir = data_dir / "translation"
        assert translation_dir.exists()
        for sw in EXPECTED_PROPRIETARY:
            for lang in EXPECTED_LANGUAGES:
                assert (translation_dir / f"{sw}-{lang}.json").exists(), (
                    f"缺失翻译数据: {sw}-{lang}.json"
                )

    def test_image_meta_data_exists(self, data_dir):
        """5 个配图元数据存在"""
        image_meta_dir = data_dir / "image-meta"
        assert image_meta_dir.exists()
        for sw in EXPECTED_PROPRIETARY:
            assert (image_meta_dir / f"{sw}-screenshot.json").exists(), (
                f"缺失配图元数据: {sw}-screenshot.json"
            )


class TestSeedDataReviewStatus:
    """所有种子数据 reviewStatus = approved"""

    @pytest.mark.parametrize("sw", EXPECTED_PROPRIETARY)
    def test_proprietary_approved(self, data_dir, sw):
        data = _load_json(data_dir / "proprietary" / f"{sw}.json")
        assert data.get("reviewStatus") == "approved", (
            f"proprietary/{sw}.json reviewStatus 非 approved"
        )

    @pytest.mark.parametrize("sw", EXPECTED_OPENSOURCE)
    def test_opensource_approved(self, data_dir, sw):
        data = _load_json(data_dir / "opensource" / f"{sw}.json")
        assert data.get("reviewStatus") == "approved"

    @pytest.mark.parametrize("cid", EXPECTED_COMPARISONS)
    def test_comparison_approved(self, data_dir, cid):
        data = _load_json(data_dir / "comparison" / f"{cid}.json")
        assert data.get("reviewStatus") == "approved"

    @pytest.mark.parametrize("sw", EXPECTED_PROPRIETARY)
    @pytest.mark.parametrize("lang", EXPECTED_LANGUAGES)
    def test_translation_approved(self, data_dir, sw, lang):
        data = _load_json(data_dir / "translation" / f"{sw}-{lang}.json")
        assert data.get("reviewStatus") == "approved"

    @pytest.mark.parametrize("sw", EXPECTED_PROPRIETARY)
    def test_image_meta_approved(self, data_dir, sw):
        data = _load_json(data_dir / "image-meta" / f"{sw}-screenshot.json")
        assert data.get("reviewStatus") == "approved"


class TestSeedDataScale:
    """种子规模 ≤ 10（保证本地开发轻量）"""

    def test_proprietary_scale_le_10(self, data_dir):
        files = list((data_dir / "proprietary").glob("*.json"))
        assert len(files) <= MAX_SEED_SCALE

    def test_opensource_scale_le_10(self, data_dir):
        files = list((data_dir / "opensource").glob("*.json"))
        assert len(files) <= MAX_SEED_SCALE

    def test_comparison_scale_le_10(self, data_dir):
        files = list((data_dir / "comparison").glob("*.json"))
        assert len(files) <= MAX_SEED_SCALE

    def test_image_meta_scale_le_10(self, data_dir):
        files = list((data_dir / "image-meta").glob("*.json"))
        assert len(files) <= MAX_SEED_SCALE


class TestSeedManifest:
    """seed_manifest.json 与实际数据一致性"""

    def test_manifest_exists(self, data_dir):
        """seed_manifest.json 存在"""
        assert (data_dir / "seed_manifest.json").exists()

    def test_manifest_counts_match(self, data_dir):
        """manifest 中的数量与实际文件数一致"""
        manifest = _load_json(data_dir / "seed_manifest.json")
        assert manifest["proprietaryCount"] == 5
        assert manifest["opensourceCount"] == 5
        assert manifest["comparisonCount"] == 5
        assert manifest["translationCount"] == 25
        assert manifest["imageMetaCount"] == 5
        assert manifest["totalPages"] == 25

    def test_manifest_languages(self, data_dir):
        """manifest 中语言列表为 5 种"""
        manifest = _load_json(data_dir / "seed_manifest.json")
        assert set(manifest["languages"]) == set(EXPECTED_LANGUAGES)

    def test_manifest_mappings(self, data_dir):
        """manifest 中的商业→开源映射完整"""
        manifest = _load_json(data_dir / "seed_manifest.json")
        expected = dict(zip(EXPECTED_PROPRIETARY, EXPECTED_OPENSOURCE))
        assert manifest["mappings"] == expected
