"""
LLM Performance Comparison Engine.

Runs the same requirement through multiple LLM providers and compares
their outputs on defined KPIs:
- Code correctness (syntax validity)
- Generation time (latency)
- Token usage (cost proxy)
- Lines of code generated
- Code complexity (basic metrics)
"""

import ast
import logging
import time
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from datetime import datetime

from genai_interpreter.llm_provider import list_available_providers, get_provider, LLMCallMetrics
from genai_interpreter.code_generator import generate_code, SUPPORTED_LANGUAGES

logger = logging.getLogger(__name__)


@dataclass
class LLMCodeResult:
    """Result from a single LLM for one language."""
    provider: str
    language: str
    code: str
    lines_of_code: int
    latency_ms: float
    tokens_used: int
    syntax_valid: bool
    error: Optional[str] = None


@dataclass
class LLMComparisonEntry:
    """Comparison of one language across providers."""
    language: str
    results: List[LLMCodeResult]


@dataclass
class LLMComparisonReport:
    """Full comparison report across providers and languages."""
    requirement: str
    providers_compared: List[str]
    languages_tested: List[str]
    comparisons: List[LLMComparisonEntry]
    summary: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())


def _check_python_syntax(code: str) -> tuple[bool, Optional[str]]:
    """Check if Python code is syntactically valid."""
    try:
        ast.parse(code)
        return True, None
    except SyntaxError as e:
        return False, f"Line {e.lineno}: {e.msg}"


def _check_syntax(code: str, language: str) -> tuple[bool, Optional[str]]:
    """Basic syntax check. Only Python has a built-in checker."""
    if language == "python":
        return _check_python_syntax(code)
    # For other languages, do a basic heuristic check
    if not code.strip():
        return False, "Empty code"
    # Check for matched braces in C++/Kotlin/Rust
    if language in ("cpp", "kotlin", "rust"):
        opens = code.count("{")
        closes = code.count("}")
        if opens != closes:
            return False, f"Mismatched braces: {opens} open, {closes} close"
    return True, None


def compare_llms(
    blueprint: Dict[str, Any],
    languages: Optional[List[str]] = None,
    providers: Optional[List[str]] = None,
) -> LLMComparisonReport:
    """
    Compare available LLM providers on code generation from the same blueprint.

    Args:
        blueprint: Parsed requirement blueprint.
        languages: Languages to test (default: all supported).
        providers: Specific providers to compare (default: all available).

    Returns:
        LLMComparisonReport with per-provider, per-language results.
    """
    if languages is None:
        languages = list(SUPPORTED_LANGUAGES.keys())
    if providers is None:
        providers = list_available_providers()

    # Always include template as baseline
    if "template" not in providers:
        providers.append("template")

    comparisons: List[LLMComparisonEntry] = []

    for lang in languages:
        lang_results: List[LLMCodeResult] = []

        for prov in providers:
            try:
                gen = generate_code(
                    blueprint,
                    language=lang,
                    use_llm=True,
                    provider_name=prov,
                )
                syntax_ok, syntax_err = _check_syntax(gen.code, lang)

                lang_results.append(LLMCodeResult(
                    provider=prov,
                    language=lang,
                    code=gen.code,
                    lines_of_code=gen.lines_of_code,
                    latency_ms=gen.generation_time_ms,
                    tokens_used=(
                        gen.llm_metrics.total_tokens
                        if gen.llm_metrics else 0
                    ),
                    syntax_valid=syntax_ok,
                    error=syntax_err,
                ))
            except Exception as exc:
                lang_results.append(LLMCodeResult(
                    provider=prov,
                    language=lang,
                    code="",
                    lines_of_code=0,
                    latency_ms=0,
                    tokens_used=0,
                    syntax_valid=False,
                    error=str(exc),
                ))

        comparisons.append(LLMComparisonEntry(language=lang, results=lang_results))

    # Build summary
    summary: Dict[str, Any] = {}
    for prov in providers:
        prov_results = [
            r
            for comp in comparisons
            for r in comp.results
            if r.provider == prov
        ]
        total_lines = sum(r.lines_of_code for r in prov_results)
        total_tokens = sum(r.tokens_used for r in prov_results)
        avg_latency = (
            sum(r.latency_ms for r in prov_results) / len(prov_results)
            if prov_results
            else 0
        )
        syntax_pass = sum(1 for r in prov_results if r.syntax_valid)

        summary[prov] = {
            "total_lines_generated": total_lines,
            "total_tokens_used": total_tokens,
            "average_latency_ms": round(avg_latency, 1),
            "syntax_pass_rate": f"{syntax_pass}/{len(prov_results)}",
            "languages_tested": len(prov_results),
        }

    return LLMComparisonReport(
        requirement=blueprint.get("raw_requirement", ""),
        providers_compared=providers,
        languages_tested=languages,
        comparisons=comparisons,
        summary=summary,
    )
