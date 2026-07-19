"""AIClient - 统一的AI API适配器

支持Claude/GPT-4o/Gemini三种API，通过OSSAF_API_BASE_URL环境变量切换Mock/Real。
解决三级嵌套响应结构差异：
- Claude: content[].text（一级嵌套）
- OpenAI: choices[].message.content（二级嵌套）
- Gemini: candidates[].content.parts[].text（三级嵌套）
"""
import os
from typing import Optional, Literal
from pydantic import BaseModel
from httpx import AsyncClient
from tenacity import retry, stop_after_attempt, wait_fixed, retry_if_exception_type


class UnifiedResponse(BaseModel):
    """统一的AI响应模型"""
    text: str
    model: str
    usage: dict
    raw_response: dict


class QuotaExceededError(Exception):
    """API配额耗尽"""
    pass


class AIClient:
    """AI API统一客户端"""

    def __init__(
        self,
        provider: Literal["claude", "openai", "gemini", "agnes"],
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
    ):
        self.provider = provider
        self.api_key = api_key or self._get_api_key(provider)
        # AGNES Provider 使用独立的 base_url（国内可达的 agnes-ai.com）
        if provider == "agnes":
            default_base = "https://apihub.agnes-ai.com/v1"
            self.base_url = base_url or os.getenv("AGNES_BASE_URL", default_base)
            self.model = "agnes-2.0-flash"
        else:
            self.base_url = base_url or os.getenv("OSSAF_API_BASE_URL", "http://127.0.0.1:8765")

    def _get_api_key(self, provider: str) -> str:
        """三层凭证降级：构造函数参数 → 环境变量 → Mock占位符"""
        env_var = {
            "claude": "ANTHROPIC_API_KEY",
            "openai": "OPENAI_API_KEY",
            "gemini": "GOOGLE_API_KEY",
            "agnes": "AGNES_API_KEY",
        }
        key = os.getenv(env_var[provider])
        if key and not key.startswith("SK-PLACEHOLDER"):
            return key
        # 降级到Mock占位符
        return f"SK-MOCK-{provider.upper()}-DEV-001"

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_fixed(10),
        retry=retry_if_exception_type(Exception),
    )
    async def generate(self, prompt: str, max_tokens: int = 1000) -> UnifiedResponse:
        """生成文本"""
        async with AsyncClient() as client:
            if self.provider == "claude":
                response = await self._call_claude(client, prompt, max_tokens)
            elif self.provider == "openai":
                response = await self._call_openai(client, prompt, max_tokens)
            elif self.provider == "gemini":
                response = await self._call_gemini(client, prompt, max_tokens)
            elif self.provider == "agnes":
                response = await self._call_agnes(client, prompt, max_tokens)
            else:
                raise ValueError(f"不支持的provider: {self.provider}")

            # 检查配额
            if response.status_code == 429:
                raise QuotaExceededError(f"{self.provider} API配额耗尽")

            response.raise_for_status()
            data = response.json()
            return self._normalize_response(data)

    async def _call_claude(self, client, prompt, max_tokens):
        """调用Claude API"""
        return await client.post(
            f"{self.base_url}/v1/messages",
            headers={
                "x-api-key": self.api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={
                "model": "claude-3-sonnet-20240229",
                "max_tokens": max_tokens,
                "messages": [{"role": "user", "content": prompt}],
            },
        )

    async def _call_openai(self, client, prompt, max_tokens):
        """调用OpenAI API"""
        return await client.post(
            f"{self.base_url}/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "content-type": "application/json",
            },
            json={
                "model": "gpt-4o-2024-05-13",
                "max_tokens": max_tokens,
                "messages": [{"role": "user", "content": prompt}],
            },
        )

    async def _call_gemini(self, client, prompt, max_tokens):
        """调用Gemini API"""
        return await client.post(
            f"{self.base_url}/v1/models/gemini-pro:generateContent",
            headers={"content-type": "application/json"},
            params={"key": self.api_key},
            json={
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {"maxOutputTokens": max_tokens},
            },
        )

    async def _call_agnes(self, client, prompt, max_tokens):
        """调用AGNES_LLM API（OpenAI SDK 兼容方式，国内可达）"""
        return await client.post(
            f"{self.base_url}/chat/completions",
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "content-type": "application/json",
            },
            json={
                "model": self.model,
                "max_tokens": max_tokens,
                "messages": [{"role": "user", "content": prompt}],
            },
        )

    def _normalize_response(self, data: dict) -> UnifiedResponse:
        """归一化响应（解决三级嵌套差异）"""
        if self.provider == "claude":
            # Claude: content[].text（一级嵌套）
            text = data["content"][0]["text"]
            model = data["model"]
            usage = data.get("usage", {})
        elif self.provider == "openai":
            # OpenAI: choices[].message.content（二级嵌套）
            text = data["choices"][0]["message"]["content"]
            model = data["model"]
            usage = data.get("usage", {})
        elif self.provider == "gemini":
            # Gemini: candidates[].content.parts[].text（三级嵌套）
            text = data["candidates"][0]["content"]["parts"][0]["text"]
            model = "gemini-pro"
            usage = data.get("usageMetadata", {})
        elif self.provider == "agnes":
            # AGNES: 兼容 OpenAI 格式 choices[].message.content（二级嵌套）
            text = data["choices"][0]["message"]["content"]
            model = data["model"]
            usage = data.get("usage", {})
        else:
            raise ValueError(f"不支持的provider: {self.provider}")

        return UnifiedResponse(
            text=text,
            model=model,
            usage=usage,
            raw_response=data,
        )
