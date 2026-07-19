"""Hugo 站点测试 - 验证 Hugo 配置、模板与内容结构完整性"""
from pathlib import Path

import pytest


PROJECT_ROOT = Path(__file__).resolve().parent.parent


class TestHugoConfig:
    """Hugo 配置文件测试"""

    def test_hugo_toml_exists(self):
        """hugo.toml 配置文件存在"""
        assert (PROJECT_ROOT / "hugo.toml").exists()

    def test_hugo_toml_has_required_keys(self):
        """hugo.toml 包含必需配置项"""
        content = (PROJECT_ROOT / "hugo.toml").read_text(encoding="utf-8")
        assert 'baseURL' in content
        assert 'languageCode' in content
        assert 'defaultContentLanguage' in content
        assert 'defaultContentLanguageInSubdir' in content

    def test_hugo_toml_has_five_languages(self):
        """hugo.toml 配置了 5 种语言"""
        content = (PROJECT_ROOT / "hugo.toml").read_text(encoding="utf-8")
        # [languages.en] [languages.zh] [languages.ja] [languages.ko] [languages.es]
        for lang in ["en", "zh", "ja", "ko", "es"]:
            assert f"[languages.{lang}]" in content, f"hugo.toml 缺少语言配置: {lang}"

    def test_hugo_toml_dev_preview_enabled(self):
        """hugo.toml 中 devPreview 已启用"""
        content = (PROJECT_ROOT / "hugo.toml").read_text(encoding="utf-8")
        assert "devPreview" in content
        assert "true" in content.lower()

    def test_hugo_toml_ai_disclosure_enabled(self):
        """hugo.toml 中 aiDisclosure 已启用"""
        content = (PROJECT_ROOT / "hugo.toml").read_text(encoding="utf-8")
        assert "aiDisclosure" in content


class TestHugoLayouts:
    """Hugo layouts 目录结构完整性"""

    REQUIRED_PARTIALS = [
        "ai-disclosure.html",
        "alternative-card.html",
        "dev-preview-banner.html",
        "footer.html",
        "head.html",
        "header.html",
    ]
    REQUIRED_DEFAULT_TEMPLATES = ["list.html", "single.html", "pagination.html"]

    def test_layouts_dir_exists(self, layouts_dir):
        """layouts 目录存在"""
        assert layouts_dir.exists()

    def test_index_html_exists(self, layouts_dir):
        """layouts/index.html 首页模板存在"""
        assert (layouts_dir / "index.html").exists()

    @pytest.mark.parametrize("partial", REQUIRED_PARTIALS)
    def test_partial_template_exists(self, layouts_dir, partial):
        """必需的 partial 模板存在"""
        path = layouts_dir / "partials" / partial
        assert path.exists(), f"partials/{partial} 缺失"

    @pytest.mark.parametrize("tmpl", REQUIRED_DEFAULT_TEMPLATES)
    def test_default_template_exists(self, layouts_dir, tmpl):
        """必需的 _default 模板存在"""
        path = layouts_dir / "_default" / tmpl
        assert path.exists(), f"_default/{tmpl} 缺失"

    def test_dev_preview_banner_template_has_dev_preview_text(self, layouts_dir):
        """DEV PREVIEW 横幅模板含 DEV PREVIEW 字样"""
        content = (layouts_dir / "partials" / "dev-preview-banner.html").read_text(encoding="utf-8")
        assert "DEV PREVIEW" in content or "dev-preview" in content

    def test_ai_disclosure_template_has_disclosure_text(self, layouts_dir):
        """AI 披露横幅模板含披露字样"""
        content = (layouts_dir / "partials" / "ai-disclosure.html").read_text(encoding="utf-8")
        assert "ai_disclosure" in content or "AI" in content or "披露" in content


class TestHugoContent:
    """Hugo 内容目录结构测试"""

    REQUIRED_LANGS = ["en", "zh", "ja", "ko", "es"]
    REQUIRED_SOFTWARE = ["photoshop", "notion", "figma", "slack", "zoom"]

    def test_content_dir_exists(self, content_dir):
        """content 目录存在"""
        assert content_dir.exists()

    @pytest.mark.parametrize("lang", REQUIRED_LANGS)
    def test_language_index_md_exists(self, content_dir, lang):
        """5 语种 _index.md 存在"""
        path = content_dir / lang / "_index.md"
        assert path.exists(), f"{lang}/_index.md 缺失"

    def test_root_index_md_exists(self, content_dir):
        """根 _index.md 存在"""
        assert (content_dir / "_index.md").exists()

    @pytest.mark.parametrize("lang", REQUIRED_LANGS)
    @pytest.mark.parametrize("software", REQUIRED_SOFTWARE)
    def test_alternative_page_exists(self, content_dir, lang, software):
        """5 语种 × 5 软件 = 25 个详情页存在"""
        path = content_dir / lang / "alternatives" / f"{software}.md"
        assert path.exists(), f"{lang}/alternatives/{software}.md 缺失"

    def test_total_content_files_at_least_25(self, content_dir):
        """content/ 目录下至少 25 个 .md 文件"""
        md_files = list(content_dir.rglob("*.md"))
        assert len(md_files) >= 25, (
            f"内容文件不足 25 个，实际 {len(md_files)}"
        )

    def test_photoshop_detail_page_has_ai_generated_flag(self, content_dir):
        """photoshop 详情页 front matter 中 aiGenerated 标记存在"""
        path = content_dir / "en" / "alternatives" / "photoshop.md"
        content = path.read_text(encoding="utf-8")
        assert "aiGenerated" in content

    def test_photoshop_detail_page_has_approved_status(self, content_dir):
        """photoshop 详情页 reviewStatus=approved"""
        path = content_dir / "en" / "alternatives" / "photoshop.md"
        content = path.read_text(encoding="utf-8")
        assert "approved" in content


class TestHugoStaticAssets:
    """Hugo 静态资源测试"""

    def test_static_css_exists(self):
        """static/css/style.css 存在"""
        path = PROJECT_ROOT / "static" / "css" / "style.css"
        assert path.exists()

    def test_static_css_non_empty(self):
        """style.css 文件非空"""
        path = PROJECT_ROOT / "static" / "css" / "style.css"
        content = path.read_text(encoding="utf-8")
        assert len(content) > 0
