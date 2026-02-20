"""
LLM Provider Abstraction Layer.
Supports multiple LLM backends (Google Gemini, OpenAI, stub) with a unified
interface for code generation, design generation, and requirement parsing.

Tracks per-call metrics (latency, tokens, model) for LLM comparison.
"""

import os
import time
import logging
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List
from datetime import datetime

logger = logging.getLogger(__name__)


# ── Metrics ──────────────────────────────────────────────────────────────────

@dataclass
class LLMCallMetrics:
    """Metrics captured from a single LLM call."""
    model: str
    provider: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    latency_ms: float = 0.0
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    success: bool = True
    error: Optional[str] = None


@dataclass
class LLMResponse:
    """Standardised response from any LLM provider."""
    text: str
    metrics: LLMCallMetrics
    raw: Optional[Any] = None          # provider-specific raw response


# ── Base Provider ────────────────────────────────────────────────────────────

class BaseLLMProvider:
    """Abstract base for LLM providers."""

    name: str = "base"

    def generate(self, prompt: str, **kwargs) -> LLMResponse:
        raise NotImplementedError

    def is_available(self) -> bool:
        return False


# ── Google Gemini Provider ───────────────────────────────────────────────────

class GeminiProvider(BaseLLMProvider):
    """Google Gemini API provider."""

    name = "gemini"

    def __init__(self) -> None:
        self._api_key = os.getenv("GOOGLE_API_KEY", "")
        self._model_name = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
        self._client = None

    def is_available(self) -> bool:
        if not self._api_key:
            return False
        try:
            import google.generativeai  # noqa: F401
            return True
        except ImportError:
            return False

    def _get_client(self):
        if self._client is None:
            import google.generativeai as genai
            genai.configure(api_key=self._api_key)
            self._client = genai.GenerativeModel(self._model_name)
        return self._client

    def generate(self, prompt: str, **kwargs) -> LLMResponse:
        model = self._get_client()
        start = time.perf_counter()
        max_retries = 2
        retry_delay = 5  # seconds

        logger.info(f"[GEMINI] Starting generation, prompt length={len(prompt)} chars")

        for attempt in range(max_retries + 1):
            try:
                import google.generativeai as genai
                gen_config = genai.GenerationConfig(
                    max_output_tokens=65536,
                    temperature=0.2,
                )
                logger.info(f"[GEMINI] Calling generate_content (attempt {attempt+1}/{max_retries+1})...")
                response = model.generate_content(prompt, generation_config=gen_config)
                latency = (time.perf_counter() - start) * 1000

                # Debug: log raw response structure
                logger.info(f"[GEMINI] Response received in {latency:.0f}ms")
                logger.info(f"[GEMINI] Has candidates: {bool(response.candidates)}")
                if response.candidates:
                    c = response.candidates[0]
                    logger.info(f"[GEMINI] Candidate finish_reason: {c.finish_reason}")
                    logger.info(f"[GEMINI] Has content: {bool(c.content)}")
                    if c.content:
                        logger.info(f"[GEMINI] Content parts count: {len(c.content.parts)}")
                        if c.content.parts:
                            part_text = c.content.parts[0].text or ""
                            logger.info(f"[GEMINI] Part text length: {len(part_text)}")
                            logger.info(f"[GEMINI] Part text preview: {part_text[:200]!r}")

                # Check if response has valid text
                text = ""
                try:
                    text = response.text or ""
                    logger.info(f"[GEMINI] response.text length: {len(text)}")
                except (ValueError, AttributeError) as text_err:
                    logger.warning(f"[GEMINI] response.text failed: {text_err}")
                    # Safety filter or empty response
                    if hasattr(response, 'candidates') and response.candidates:
                        c = response.candidates[0]
                        if hasattr(c, 'content') and c.content and c.content.parts:
                            text = c.content.parts[0].text or ""

                if not text.strip():
                    logger.error("[GEMINI] Empty text after extraction, raising error")
                    raise RuntimeError("Gemini returned empty response — check quota or safety filters")

                print(f"DEBUG: Gemini Raw Response:\n{text[:500]}...\n[End of Preview]")
                logger.info(f"[GEMINI] SUCCESS: generated {len(text)} chars, {text.count(chr(10))+1} lines")

                usage = getattr(response, "usage_metadata", None)
                prompt_tok = getattr(usage, "prompt_token_count", 0) or 0
                comp_tok = getattr(usage, "candidates_token_count", 0) or 0

                metrics = LLMCallMetrics(
                    model=self._model_name,
                    provider=self.name,
                    prompt_tokens=prompt_tok,
                    completion_tokens=comp_tok,
                    total_tokens=prompt_tok + comp_tok,
                    latency_ms=round(latency, 1),
                )
                return LLMResponse(text=text, metrics=metrics, raw=response)

            except Exception as exc:
                error_str = str(exc).lower()
                # Only check for actual API rate-limit errors, not our own messages
                is_rate_limit = any(k in error_str for k in ["429", "quota", "resource_exhausted"])
                logger.error(f"[GEMINI] Exception (attempt {attempt+1}): {type(exc).__name__}: {exc}")
                logger.error(f"[GEMINI] Is rate limit: {is_rate_limit}")

                if is_rate_limit and attempt < max_retries:
                    logger.warning(f"[GEMINI] Rate-limited, retrying in {retry_delay}s...")
                    time.sleep(retry_delay)
                    continue

                latency = (time.perf_counter() - start) * 1000
                logger.error(f"[GEMINI] FINAL FAILURE after {attempt+1} attempts: {exc}")
                # Raise so generate_with_fallback can catch and try next provider
                raise RuntimeError(f"Gemini failed: {exc}")


# ── OpenAI Provider ──────────────────────────────────────────────────────────

class OpenAIProvider(BaseLLMProvider):
    """OpenAI GPT API provider."""

    name = "openai"

    def __init__(self) -> None:
        self._api_key = os.getenv("OPENAI_API_KEY", "")
        self._model_name = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

    def is_available(self) -> bool:
        if not self._api_key:
            return False
        try:
            import openai  # noqa: F401
            return True
        except ImportError:
            return False

    def generate(self, prompt: str, **kwargs) -> LLMResponse:
        import openai
        client = openai.OpenAI(api_key=self._api_key)
        start = time.perf_counter()
        try:
            response = client.chat.completions.create(
                model=self._model_name,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
            )
            latency = (time.perf_counter() - start) * 1000
            choice = response.choices[0].message.content or ""
            usage = response.usage
            metrics = LLMCallMetrics(
                model=self._model_name,
                provider=self.name,
                prompt_tokens=usage.prompt_tokens if usage else 0,
                completion_tokens=usage.completion_tokens if usage else 0,
                total_tokens=usage.total_tokens if usage else 0,
                latency_ms=round(latency, 1),
            )
            return LLMResponse(text=choice, metrics=metrics, raw=response)
        except Exception as exc:
            latency = (time.perf_counter() - start) * 1000
            logger.error(f"OpenAI generation failed: {exc}")
            raise RuntimeError(f"OpenAI failed: {exc}")


# ── Local GGUF Provider (llama.cpp) ──────────────────────────────────────────

class LocalLlamacppProvider(BaseLLMProvider):
    """Local GGUF model provider using llama-cpp-python."""

    name = "localllama"

    def __init__(self) -> None:
        self._model_path = os.getenv("LOCAL_MODEL_PATH", "")
        self._llm = None
        self._n_ctx = int(os.getenv("LOCAL_MODEL_CTX", "4096"))

    def is_available(self) -> bool:
        if not self._model_path:
            logger.debug("[LOCALLAMA] Not available: LOCAL_MODEL_PATH env var is empty")
            return False
        if not os.path.exists(self._model_path):
            logger.warning(f"[LOCALLAMA] Not available: file not found at {self._model_path!r}")
            return False
        try:
            import llama_cpp  # noqa: F401
            return True
        except ImportError:
            logger.warning("[LOCALLAMA] Not available: llama-cpp-python not installed")
            return False

    def _get_llm(self):
        if self._llm is None:
            from llama_cpp import Llama
            logger.info(f"[LOCALLAMA] Loading model from {self._model_path}...")
            self._llm = Llama(
                model_path=self._model_path,
                n_ctx=self._n_ctx,
                n_gpu_layers=-1,  # Offload all to GPU if available
                verbose=False,
            )
            logger.info("[LOCALLAMA] Model loaded successfully")
        return self._llm

    def generate(self, prompt: str, **kwargs) -> LLMResponse:
        llm = self._get_llm()
        start = time.perf_counter()
        try:
            # Simple completion or chat? DeepSeek Coder is instruct-tuned.
            # We'll use create_chat_completion for better instruction following.
            response = llm.create_chat_completion(
                messages=[{"role": "user", "content": prompt}],
                max_tokens=2048,
                temperature=0.2,
            )
            latency = (time.perf_counter() - start) * 1000
            
            choice = response["choices"][0]["message"]["content"] or ""
            usage = response.get("usage", {})
            
            metrics = LLMCallMetrics(
                model=os.path.basename(self._model_path),
                provider=self.name,
                prompt_tokens=usage.get("prompt_tokens", 0),
                completion_tokens=usage.get("completion_tokens", 0),
                total_tokens=usage.get("total_tokens", 0),
                latency_ms=round(latency, 1),
            )
            return LLMResponse(text=choice, metrics=metrics, raw=response)

        except Exception as exc:
            latency = (time.perf_counter() - start) * 1000
            logger.error(f"Local LLM generation failed: {exc}")
            raise RuntimeError(f"Local LLM failed: {exc}")


# ── Template Stub Provider (no API key needed) ──────────────────────────────

class TemplateProvider(BaseLLMProvider):
    """Fallback provider using Jinja2 templates — always available."""

    name = "template"

    def is_available(self) -> bool:
        return True

    def generate(self, prompt: str, **kwargs) -> LLMResponse:
        """Return a placeholder acknowledging template-based generation."""
        start = time.perf_counter()
        text = (
            "# [Template-based generation]\n"
            "# This output was generated using built-in templates.\n"
            "# Configure GOOGLE_API_KEY, OPENAI_API_KEY, or LOCAL_MODEL_PATH for AI generation.\n"
        )
        latency = (time.perf_counter() - start) * 1000
        metrics = LLMCallMetrics(
            model="template-v1",
            provider=self.name,
            latency_ms=round(latency, 1),
        )
        return LLMResponse(text=text, metrics=metrics)


# ── Provider Registry ────────────────────────────────────────────────────────

_PROVIDERS: Dict[str, BaseLLMProvider] = {}


def _init_providers() -> None:
    global _PROVIDERS
    _PROVIDERS = {
        "gemini": GeminiProvider(),
        "openai": OpenAIProvider(),
        "localllama": LocalLlamacppProvider(),
        "template": TemplateProvider(),
    }
    # Log availability on first init
    for pname, prov in _PROVIDERS.items():
        avail = prov.is_available()
        logger.info(f"[PROVIDERS] {pname}: {'✅ available' if avail else '❌ not available'}")
    local = _PROVIDERS["localllama"]
    logger.info(f"[PROVIDERS] localllama model_path = {local._model_path!r}")
    logger.info(f"[PROVIDERS] localllama path exists = {os.path.exists(local._model_path) if local._model_path else 'N/A'}")


def get_provider(name: Optional[str] = None) -> BaseLLMProvider:
    """
    Return a provider by name, or the best available one.

    Priority: gemini → openai → localllama → template (always available).
    """
    if not _PROVIDERS:
        _init_providers()

    if name and name in _PROVIDERS:
        p = _PROVIDERS[name]
        if p.is_available():
            return p
        logger.warning(f"Provider '{name}' not available, falling back")

    for pname in ("gemini", "openai", "localllama", "template"):
        if _PROVIDERS[pname].is_available():
            logger.info(f"Using LLM provider: {pname}")
            return _PROVIDERS[pname]

    return _PROVIDERS["template"]


def list_available_providers() -> List[str]:
    """Return names of providers that are currently usable."""
    if not _PROVIDERS:
        _init_providers()
    return [n for n, p in _PROVIDERS.items() if p.is_available()]


# ── Metrics History ──────────────────────────────────────────────────────────

_metrics_history: List[LLMCallMetrics] = []


def record_metrics(m: LLMCallMetrics) -> None:
    _metrics_history.append(m)
    if len(_metrics_history) > 500:
        _metrics_history.pop(0)


def get_metrics_history() -> List[LLMCallMetrics]:
    return list(_metrics_history)


# ── Fallback Generation ─────────────────────────────────────────────────────

def generate_with_fallback(prompt: str, **kwargs) -> LLMResponse:
    """
    Try all available providers in priority order (gemini → openai → template).
    
    If Gemini hits rate limit or fails, automatically falls back to OpenAI,
    then to the template provider. Logs each fallback attempt clearly.
    """
    if not _PROVIDERS:
        _init_providers()

    fallback_chain = ["gemini", "openai", "localllama", "template"]
    last_error = None

    for pname in fallback_chain:
        provider = _PROVIDERS.get(pname)
        if not provider or not provider.is_available():
            logger.info(f"[FALLBACK] Skipping {pname}: not available")
            continue

        try:
            logger.info(f"[FALLBACK] Trying provider: {pname}")
            response = provider.generate(prompt, **kwargs)

            # Check for empty response (safety filter, etc.)
            if not response.text.strip():
                logger.warning(f"[FALLBACK] {pname} returned empty response, trying next...")
                continue

            logger.info(f"[FALLBACK] ✅ Success with provider: {pname} ({len(response.text)} chars)")
            return response

        except Exception as exc:
            last_error = exc
            logger.warning(f"[FALLBACK] ❌ {pname} failed: {exc}, trying next provider...")
            continue

    # All real providers failed — return template as last resort
    logger.error(f"[FALLBACK] All providers exhausted. Last error: {last_error}")
    return _PROVIDERS["template"].generate(prompt, **kwargs)
