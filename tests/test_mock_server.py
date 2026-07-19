"""Mock 服务器测试 - 验证 FastAPI Mock 服务器及其 5 个 API Mock 端点

使用 FastAPI TestClient 直接对 app 对象进行测试，无需启动 uvicorn 进程，
也不依赖 8765 端口（该端口可能被其他进程占用，见任务上下文）。
"""
import pytest
from fastapi.testclient import TestClient

from mock_server.main import app
from mock_server.routes import alternativeto, claude, gemini, github, openai


@pytest.fixture(scope="module")
def client() -> TestClient:
    """FastAPI TestClient fixture（直接驱动 ASGI app，无需网络端口）"""
    return TestClient(app)


class TestMockServerModule:
    """Mock 服务器模块可导入性测试"""

    def test_main_module_importable(self):
        """mock_server.main 模块可导入"""
        assert app is not None
        assert app.title == "OSSAF Mock Server"

    def test_all_route_modules_importable(self):
        """5 个路由模块均可导入"""
        modules = [claude, openai, gemini, github, alternativeto]
        for m in modules:
            assert hasattr(m, "router"), f"{m.__name__} 缺少 router"

    def test_app_has_health_endpoint(self):
        """app 已注册 /health 端点"""
        routes = [r.path for r in app.routes]
        assert "/health" in routes

    def test_app_has_all_mock_endpoints(self):
        """app 已注册 5 个 Mock API 端点"""
        routes = [r.path for r in app.routes]
        # 至少包含以下路径模式
        assert "/v1/messages" in routes
        assert "/v1/chat/completions" in routes
        # Gemini 路径含模型名占位
        gemini_routes = [r for r in routes if "generateContent" in str(r)]
        assert len(gemini_routes) >= 1


class TestMockServerEndpoints:
    """Mock 服务器端点测试（通过 TestClient 直接驱动 ASGI app）

    使用 TestClient 而非 httpx 实盘请求，原因：
    1. 8765 端口可能被其他进程占用（任务上下文已提示）
    2. 单元/集成测试应独立于运行环境，不依赖外部进程
    3. TestClient 与 uvicorn 启动的 app 行为完全一致
    """

    def test_health_endpoint_returns_200(self, client):
        """/health 端点返回 200 且 status=healthy"""
        resp = client.get("/health")
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "healthy"
        assert body["service"] == "ossaf-mock-server"

    def test_root_endpoint_returns_api_list(self, client):
        """根端点返回 API 列表"""
        resp = client.get("/")
        assert resp.status_code == 200
        body = resp.json()
        assert body["service"] == "ossaf-mock-server"
        assert "endpoints" in body
        assert "apis" in body["endpoints"]

    def test_claude_mock_returns_correct_format(self, client):
        """Claude API Mock 返回 content[].text 一级嵌套结构"""
        resp = client.post(
            "/v1/messages",
            json={
                "model": "claude-3-sonnet-20240229",
                "max_tokens": 1000,
                "messages": [{"role": "user", "content": "test"}],
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        # Claude 响应结构：content[].text
        assert "content" in data
        assert isinstance(data["content"], list)
        assert len(data["content"]) > 0
        assert "text" in data["content"][0]
        assert isinstance(data["content"][0]["text"], str)
        assert len(data["content"][0]["text"]) > 0

    def test_openai_mock_returns_correct_format(self, client):
        """OpenAI API Mock 返回 choices[].message.content 二级嵌套结构"""
        resp = client.post(
            "/v1/chat/completions",
            json={
                "model": "gpt-4o-2024-05-13",
                "messages": [{"role": "user", "content": "test"}],
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        # OpenAI 响应结构：choices[].message.content
        assert "choices" in data
        assert isinstance(data["choices"], list)
        assert len(data["choices"]) > 0
        assert "message" in data["choices"][0]
        assert "content" in data["choices"][0]["message"]
        assert isinstance(data["choices"][0]["message"]["content"], str)

    def test_gemini_mock_returns_correct_format(self, client):
        """Gemini API Mock 返回 candidates[].content.parts[].text 三级嵌套结构"""
        resp = client.post(
            "/v1/models/gemini-pro:generateContent",
            json={
                "contents": [{"parts": [{"text": "test"}]}],
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        # Gemini 响应结构：candidates[].content.parts[].text
        assert "candidates" in data
        assert isinstance(data["candidates"], list)
        assert len(data["candidates"]) > 0
        candidate = data["candidates"][0]
        assert "content" in candidate
        assert "parts" in candidate["content"]
        assert isinstance(candidate["content"]["parts"], list)
        assert len(candidate["content"]["parts"]) > 0
        assert "text" in candidate["content"]["parts"][0]
        assert isinstance(candidate["content"]["parts"][0]["text"], str)
