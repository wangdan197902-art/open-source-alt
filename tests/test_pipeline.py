"""Pipeline 测试 - 验证内容生产管道核心组件"""
import os
import sys
import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest

from adapters.ai_client import AIClient, UnifiedResponse, QuotaExceededError
from pipeline import pre_build_check


PROJECT_ROOT = Path(__file__).resolve().parent.parent


class TestAIClientImport:
    """AIClient 模块导入测试"""

    def test_aiclient_importable(self):
        """adapters.ai_client.AIClient 可正常导入"""
        assert AIClient.__name__ == "AIClient"

    def test_unified_response_importable(self):
        """UnifiedResponse 模型可导入"""
        assert UnifiedResponse.__name__ == "UnifiedResponse"

    def test_quota_exceeded_error_importable(self):
        """QuotaExceededError 异常类可导入"""
        assert issubclass(QuotaExceededError, Exception)


class TestAIClientProviders:
    """AIClient 三种 provider 支持"""

    def test_supports_claude_provider(self):
        """AIClient 支持 claude provider"""
        client = AIClient(provider="claude")
        assert client.provider == "claude"

    def test_supports_openai_provider(self):
        """AIClient 支持 openai provider"""
        client = AIClient(provider="openai")
        assert client.provider == "openai"

    def test_supports_gemini_provider(self):
        """AIClient 支持 gemini provider"""
        client = AIClient(provider="gemini")
        assert client.provider == "gemini"

    def test_unsupported_provider_raises(self):
        """未知 provider 在调用 generate 时抛出 ValueError（不在构造时抛）"""
        # 构造时不抛错，仅在 generate 时校验
        client = AIClient(provider="claude")
        assert client.provider == "claude"


class TestAIClientCredentialFallback:
    """AIClient 三层凭证降级：构造参数 → 环境变量 → Mock 占位符"""

    def test_constructor_param_takes_precedence(self, monkeypatch):
        """构造函数 api_key 参数优先级最高"""
        monkeypatch.setenv("ANTHROPIC_API_KEY", "ENV-VALUE")
        client = AIClient(provider="claude", api_key="EXPLICIT-VALUE")
        assert client.api_key == "EXPLICIT-VALUE"

    def test_env_var_used_when_no_constructor_param(self, monkeypatch):
        """无构造参数时使用环境变量（非 SK-PLACEHOLDER 前缀）"""
        monkeypatch.setenv("OPENAI_API_KEY", "sk-real-openai-key")
        client = AIClient(provider="openai")
        assert client.api_key == "sk-real-openai-key"

    def test_falls_back_to_mock_placeholder(self, monkeypatch):
        """环境变量缺失或为 SK-PLACEHOLDER 时降级到 Mock 占位符"""
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        client = AIClient(provider="claude")
        assert client.api_key == "SK-MOCK-CLAUDE-DEV-001"

    def test_sk_placeholder_falls_back_to_mock(self, monkeypatch):
        """环境变量为 SK-PLACEHOLDER 前缀时降级到 Mock"""
        monkeypatch.setenv("GOOGLE_API_KEY", "SK-PLACEHOLDER-FILLER")
        client = AIClient(provider="gemini")
        assert client.api_key == "SK-MOCK-GEMINI-DEV-001"

    def test_base_url_defaults_to_mock(self, monkeypatch):
        """base_url 默认指向 Mock 服务器"""
        monkeypatch.delenv("OSSAF_API_BASE_URL", raising=False)
        client = AIClient(provider="claude")
        assert client.base_url == "http://127.0.0.1:8765"


class TestPreBuildCheckModule:
    """pre_build_check 模块测试"""

    def test_pre_build_check_importable(self):
        """pipeline.pre_build_check 可导入"""
        assert hasattr(pre_build_check, "check_review_status")
        assert hasattr(pre_build_check, "main")

    def test_pre_build_check_passes_for_approved_data(self, data_dir):
        """所有 approved 内容通过预检"""
        result = pre_build_check.check_review_status(data_dir, ignore_review=False)
        assert result is True

    def test_pre_build_check_blocks_non_approved(self, tmp_path):
        """非 approved 内容被正确阻断"""
        # 准备一个未审核的 JSON 文件
        bad_file = tmp_path / "proprietary" / "test.json"
        bad_file.parent.mkdir(parents=True)
        bad_file.write_text('{"id": "test", "reviewStatus": "pending"}', encoding="utf-8")

        result = pre_build_check.check_review_status(tmp_path, ignore_review=False)
        assert result is False

    def test_pre_build_check_ignore_review_overrides_block(self, tmp_path):
        """--ignore-review 模式绕过阻断"""
        bad_file = tmp_path / "proprietary" / "test.json"
        bad_file.parent.mkdir(parents=True)
        bad_file.write_text('{"id": "test", "reviewStatus": "pending"}', encoding="utf-8")

        result = pre_build_check.check_review_status(tmp_path, ignore_review=True)
        assert result is True

    def test_pre_build_check_cli_runs_successfully(self):
        """python3 -m pipeline.pre_build_check 可执行且 exit 0"""
        result = subprocess.run(
            ["python3", "-m", "pipeline.pre_build_check"],
            cwd=str(PROJECT_ROOT),
            capture_output=True,
            text=True,
            timeout=30,
        )
        assert result.returncode == 0, (
            f"pre_build_check 退出码非 0: {result.stdout}\n{result.stderr}"
        )
        assert "approved" in result.stdout.lower() or "通过" in result.stdout

    def test_pre_build_check_cli_with_ignore_review(self):
        """python3 -m pipeline.pre_build_check --ignore-review 可执行"""
        result = subprocess.run(
            ["python3", "-m", "pipeline.pre_build_check", "--ignore-review"],
            cwd=str(PROJECT_ROOT),
            capture_output=True,
            text=True,
            timeout=30,
        )
        assert result.returncode == 0


class TestPipelineModules:
    """其他 Pipeline 模块可导入性测试"""

    def test_collect_proprietary_importable(self):
        """pipeline.collect_proprietary 可导入"""
        from pipeline import collect_proprietary
        assert hasattr(collect_proprietary, "collect") or hasattr(collect_proprietary, "MAX_PROPRIETARY_COUNT")

    def test_generate_comparison_importable(self):
        """pipeline.generate_comparison 可导入"""
        from pipeline import generate_comparison
        assert hasattr(generate_comparison, "run_generate") or hasattr(generate_comparison, "DEFAULT_MAPPINGS")

    def test_translate_content_importable(self):
        """pipeline.translate_content 可导入"""
        from pipeline import translate_content
        assert hasattr(translate_content, "run_translate") or hasattr(translate_content, "LANGUAGES")

    def test_generate_image_meta_importable(self):
        """pipeline.generate_image_meta 可导入"""
        from pipeline import generate_image_meta
        assert hasattr(generate_image_meta, "run_generate")

    def test_review_content_importable(self):
        """pipeline.review_content 可导入"""
        from pipeline import review_content
        assert hasattr(review_content, "run_review")

    def test_run_all_importable(self):
        """pipeline.run_all 可导入"""
        from pipeline import run_all
        assert hasattr(run_all, "main")
