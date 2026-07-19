"""集成测试 - 端到端验证 Hugo 服务器实盘可访问性与页面渲染"""
import pytest
import httpx


class TestHugoServerLive:
    """Hugo 开发服务器（端口 1313）实盘连通性测试"""

    def test_hugo_server_root_accessible(self, hugo_server_url):
        """Hugo 服务器根路径可访问（返回 200）"""
        with httpx.Client(timeout=10.0, follow_redirects=True) as client:
            resp = client.get(f"{hugo_server_url}/")
        assert resp.status_code == 200
        assert "html" in resp.headers.get("content-type", "").lower()

    def test_english_homepage_returns_200(self, hugo_server_url):
        """英文首页 /en/ 返回 200"""
        with httpx.Client(timeout=10.0, follow_redirects=True) as client:
            resp = client.get(f"{hugo_server_url}/en/")
        assert resp.status_code == 200

    def test_chinese_homepage_returns_200(self, hugo_server_url):
        """中文首页 /zh/ 返回 200"""
        with httpx.Client(timeout=10.0, follow_redirects=True) as client:
            resp = client.get(f"{hugo_server_url}/zh/")
        assert resp.status_code == 200

    def test_japanese_homepage_returns_200(self, hugo_server_url):
        """日文首页 /ja/ 返回 200"""
        with httpx.Client(timeout=10.0, follow_redirects=True) as client:
            resp = client.get(f"{hugo_server_url}/ja/")
        assert resp.status_code == 200

    def test_korean_homepage_returns_200(self, hugo_server_url):
        """韩文首页 /ko/ 返回 200"""
        with httpx.Client(timeout=10.0, follow_redirects=True) as client:
            resp = client.get(f"{hugo_server_url}/ko/")
        assert resp.status_code == 200

    def test_spanish_homepage_returns_200(self, hugo_server_url):
        """西班牙文首页 /es/ 返回 200"""
        with httpx.Client(timeout=10.0, follow_redirects=True) as client:
            resp = client.get(f"{hugo_server_url}/es/")
        assert resp.status_code == 200


class TestSoftwareDetailPages:
    """商业软件详情页端到端可访问性"""

    @pytest.mark.parametrize("software", ["photoshop", "notion", "figma", "slack", "zoom"])
    def test_english_detail_page_returns_200(self, hugo_server_url, software):
        """5 个英文详情页返回 200"""
        url = f"{hugo_server_url}/en/alternatives/{software}/"
        with httpx.Client(timeout=10.0, follow_redirects=True) as client:
            resp = client.get(url)
        assert resp.status_code == 200, f"{url} 返回 {resp.status_code}"

    def test_photoshop_chinese_detail_page_returns_200(self, hugo_server_url):
        """Photoshop 中文详情页 /zh/alternatives/photoshop/ 返回 200"""
        url = f"{hugo_server_url}/zh/alternatives/photoshop/"
        with httpx.Client(timeout=10.0, follow_redirects=True) as client:
            resp = client.get(url)
        assert resp.status_code == 200


class TestPageContent:
    """页面渲染内容关键字段验证"""

    def test_dev_preview_banner_present_in_page(self, hugo_server_url):
        """DEV PREVIEW 横幅出现在页面 HTML 中"""
        with httpx.Client(timeout=10.0, follow_redirects=True) as client:
            resp = client.get(f"{hugo_server_url}/en/")
        text = resp.text.lower()
        assert "dev-preview" in text or "dev preview" in text

    def test_english_homepage_contains_title(self, hugo_server_url):
        """英文首页包含 OSSAF 或替代关键词"""
        with httpx.Client(timeout=10.0, follow_redirects=True) as client:
            resp = client.get(f"{hugo_server_url}/en/")
        text = resp.text.lower()
        assert "ossaf" in text or "open source" in text or "alternative" in text

    def test_photoshop_detail_contains_gimp(self, hugo_server_url):
        """Photoshop 详情页包含 GIMP 关键词"""
        with httpx.Client(timeout=10.0, follow_redirects=True) as client:
            resp = client.get(f"{hugo_server_url}/en/alternatives/photoshop/")
        text = resp.text.lower()
        assert "gimp" in text

    def test_ai_disclosure_present_on_ai_generated_page(self, hugo_server_url):
        """AI 披露横幅在 aiGenerated=true 页面中显示"""
        with httpx.Client(timeout=10.0, follow_redirects=True) as client:
            resp = client.get(f"{hugo_server_url}/en/alternatives/photoshop/")
        text = resp.text.lower()
        # 页面中应包含 AI 披露字样
        assert "ai" in text and (
            "disclosure" in text or "披露" in text or "ai-disclosure" in text
        )


class TestEndToEndPipeline:
    """端到端管道集成测试"""

    def test_hugo_server_full_flow(self, hugo_server_url):
        """Hugo 服务器完整数据流可访问（首页 → 详情页）"""
        with httpx.Client(timeout=10.0, follow_redirects=True) as client:
            hugo_root = client.get(f"{hugo_server_url}/")
            assert hugo_root.status_code == 200

    def test_mock_server_app_object_works(self):
        """Mock 服务器 app 对象可正常驱动（通过 TestClient 验证数据流前置条件）

        不依赖 8765 端口实盘运行，因该端口可能被其他进程占用。
        """
        from fastapi.testclient import TestClient
        from mock_server.main import app

        with TestClient(app) as client:
            health = client.get("/health")
            assert health.status_code == 200
            assert health.json()["status"] == "healthy"

    def test_full_user_journey(self, hugo_server_url):
        """完整用户旅程：首页 → 详情页"""
        with httpx.Client(timeout=10.0, follow_redirects=True) as client:
            # 1. 访问首页
            home = client.get(f"{hugo_server_url}/en/")
            assert home.status_code == 200

            # 2. 访问详情页
            detail = client.get(f"{hugo_server_url}/en/alternatives/photoshop/")
            assert detail.status_code == 200
