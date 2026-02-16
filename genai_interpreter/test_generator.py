"""
Test Case Generator.

Generates test suites from requirement blueprints in multiple languages:
- Python (pytest)
- C++ (Google Test)

Uses LLM when available, falls back to Jinja2 templates.
"""

import os
import logging
import time
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from datetime import datetime

from jinja2 import Environment, FileSystemLoader, TemplateNotFound

from genai_interpreter.llm_provider import get_provider, record_metrics, LLMCallMetrics
from genai_interpreter.code_generator import DEFAULT_UNITS

logger = logging.getLogger(__name__)

SUPPORTED_TEST_LANGUAGES = {
    "python": {"name": "Python (pytest)", "ext": ".py", "template": "test_python.j2"},
    "cpp":    {"name": "C++ (Google Test)", "ext": ".cpp", "template": "test_cpp.j2"},
}


@dataclass
class GeneratedTest:
    """Result of test generation."""
    language: str
    language_name: str
    code: str
    filename: str
    test_count: int
    generation_method: str
    generation_time_ms: float
    llm_metrics: Optional[LLMCallMetrics] = None
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())


# ── Template engine ──────────────────────────────────────────────────────────

_template_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "templates")


def _get_jinja_env() -> Environment:
    return Environment(
        loader=FileSystemLoader(_template_dir),
        trim_blocks=True,
        lstrip_blocks=True,
    )


def _generate_test_from_template(blueprint: Dict[str, Any], language: str) -> str:
    lang_info = SUPPORTED_TEST_LANGUAGES.get(language)
    if not lang_info:
        raise ValueError(f"Unsupported test language: {language}")

    env = _get_jinja_env()
    try:
        template = env.get_template(lang_info["template"])
    except TemplateNotFound:
        raise ValueError(f"Test template not found: {lang_info['template']}")

    signals = blueprint.get("signals", ["speed", "battery_soc", "tire_pressure"])

    return template.render(
        service_name="vehicle_health",
        requirement=blueprint.get("raw_requirement", ""),
        signals=signals,
        units=DEFAULT_UNITS,
        namespace="vehicle",
    )


# ── LLM-based test generation ───────────────────────────────────────────────

_TEST_PROMPT = """You are an expert QA engineer for automotive software. Generate a comprehensive test suite in {language_name}.

REQUIREMENT: "{requirement}"

The service has these signals: {signals}
And these alert types: {alerts}

Generate test cases for:
1. Data model initialization and defaults
2. API endpoint responses (status codes, response structure)
3. Alert generation when signals exceed thresholds
4. Edge cases (empty data, boundary values)
5. Service lifecycle (start/stop simulation)

{extra_rules}

Generate ONLY the test code, no explanations."""


def _get_test_extra_rules(language: str) -> str:
    if language == "cpp":
        return "Use Google Test (gtest) framework. Include TEST and TEST_F macros."
    return "Use pytest framework. Include proper fixtures (@pytest.fixture). Use assert statements."


# ── Public API ───────────────────────────────────────────────────────────────

def generate_tests(
    blueprint: Dict[str, Any],
    language: str = "python",
    use_llm: bool = True,
    provider_name: Optional[str] = None,
) -> GeneratedTest:
    """
    Generate test cases for a given blueprint and language.
    """
    if language not in SUPPORTED_TEST_LANGUAGES:
        raise ValueError(
            f"Unsupported test language '{language}'. "
            f"Supported: {list(SUPPORTED_TEST_LANGUAGES.keys())}"
        )

    lang_info = SUPPORTED_TEST_LANGUAGES[language]
    start = time.perf_counter()
    method = "template"
    llm_metrics = None

    if use_llm:
        provider = get_provider(provider_name)
        if provider.name != "template":
            try:
                prompt = _TEST_PROMPT.format(
                    language_name=lang_info["name"],
                    requirement=blueprint.get("raw_requirement", ""),
                    signals=", ".join(blueprint.get("signals", [])),
                    alerts=", ".join(blueprint.get("alerts", [])),
                    extra_rules=_get_test_extra_rules(language),
                )
                response = provider.generate(prompt)
                record_metrics(response.metrics)

                code = response.text.strip()
                if code.startswith("```"):
                    lines = code.split("\n")
                    lines = lines[1:]
                    if lines and lines[-1].strip() == "```":
                        lines = lines[:-1]
                    code = "\n".join(lines)

                elapsed = (time.perf_counter() - start) * 1000
                test_count = code.count("def test_") + code.count("TEST(") + code.count("TEST_F(")

                return GeneratedTest(
                    language=language,
                    language_name=lang_info["name"],
                    code=code,
                    filename=f"test_vehicle_health_service{lang_info['ext']}",
                    test_count=test_count,
                    generation_method=f"llm:{provider.name}",
                    generation_time_ms=round(elapsed, 1),
                    llm_metrics=response.metrics,
                )
            except Exception as exc:
                logger.warning(f"LLM test generation failed, using template: {exc}")

    # Template fallback
    code = _generate_test_from_template(blueprint, language)
    elapsed = (time.perf_counter() - start) * 1000
    test_count = code.count("def test_") + code.count("TEST(") + code.count("TEST_F(")

    return GeneratedTest(
        language=language,
        language_name=lang_info["name"],
        code=code,
        filename=f"test_vehicle_health_service{lang_info['ext']}",
        test_count=test_count,
        generation_method=method,
        generation_time_ms=round(elapsed, 1),
    )


def generate_all_tests(
    blueprint: Dict[str, Any],
    use_llm: bool = True,
    provider_name: Optional[str] = None,
) -> List[GeneratedTest]:
    """Generate test suites in ALL supported test languages."""
    return [
        generate_tests(blueprint, lang, use_llm, provider_name)
        for lang in SUPPORTED_TEST_LANGUAGES
    ]
