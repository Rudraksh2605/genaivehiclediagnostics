"""
Multi-Language Code Generator.

Generates service source code from a parsed requirement blueprint in multiple
target languages: Python/FastAPI, C++ (MISRA), Kotlin/Android, Rust.

Uses LLM when available, falls back to Jinja2 templates otherwise.
"""

import os
import logging
import time
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from datetime import datetime

from jinja2 import Environment, FileSystemLoader, TemplateNotFound

from genai_interpreter.llm_provider import (
    get_provider,
    record_metrics,
    LLMCallMetrics,
)

logger = logging.getLogger(__name__)

# ── Supported languages ─────────────────────────────────────────────────────

SUPPORTED_LANGUAGES = {
    "python":  {"name": "Python / FastAPI",     "ext": ".py",  "template": "service_python.j2"},
    "cpp":     {"name": "C++ (MISRA-Compliant)","ext": ".cpp", "template": "service_cpp.j2"},
    "kotlin":  {"name": "Kotlin / Android",     "ext": ".kt",  "template": "service_kotlin.j2"},
    "rust":    {"name": "Rust",                 "ext": ".rs",  "template": "service_rust.j2"},
}

# Default units for common vehicle signals
DEFAULT_UNITS: Dict[str, str] = {
    "speed": "km/h",
    "battery_soc": "%",
    "tire_pressure": "PSI",
    "throttle_position": "%",
    "brake_position": "%",
    "gear_position": "gear",
    "ev_range": "km",
    "steering_angle": "°",
    "engine_temp": "°C",
    "fuel_level": "%",
    "acceleration": "m/s²",
    "gps_location": "lat/lon",
}


@dataclass
class GeneratedCode:
    """Result of code generation."""
    language: str
    language_name: str
    code: str
    filename: str
    lines_of_code: int
    generation_method: str  # "template" or "llm"
    generation_time_ms: float
    llm_metrics: Optional[LLMCallMetrics] = None
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())


@dataclass
class CodeGenerationResult:
    """Full result of a code generation request."""
    requirement: str
    blueprint: Dict[str, Any]
    generated_files: List[GeneratedCode]
    total_lines: int = 0
    total_time_ms: float = 0.0
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())


# ── Template-based generation ────────────────────────────────────────────────

_template_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "templates")
_jinja_env: Optional[Environment] = None


def _get_jinja_env() -> Environment:
    global _jinja_env
    if _jinja_env is None:
        _jinja_env = Environment(
            loader=FileSystemLoader(_template_dir),
            trim_blocks=True,
            lstrip_blocks=True,
        )
    return _jinja_env


def _generate_from_template(
    blueprint: Dict[str, Any],
    language: str,
) -> str:
    """Render code using Jinja2 templates."""
    lang_info = SUPPORTED_LANGUAGES.get(language)
    if not lang_info:
        raise ValueError(f"Unsupported language: {language}")

    env = _get_jinja_env()
    try:
        template = env.get_template(lang_info["template"])
    except TemplateNotFound:
        raise ValueError(f"Template not found for {language}: {lang_info['template']}")

    service_name = "vehicle_health"
    signals = blueprint.get("signals", ["speed", "battery_soc", "tire_pressure"])

    return template.render(
        service_name=service_name,
        requirement=blueprint.get("raw_requirement", ""),
        signals=signals,
        units=DEFAULT_UNITS,
        namespace="vehicle",
    )


# ── LLM-based generation ────────────────────────────────────────────────────

_LLM_CODE_PROMPT = """You are an expert automotive software engineer. Generate production-ready {language_name} source code for a Service-Oriented Architecture (SoA) vehicle diagnostics service.

REQUIREMENT: "{requirement}"

EXTRACTED BLUEPRINT:
- Signals: {signals}
- Services: {services}
- UI Components: {ui_components}
- Alerts: {alerts}

LANGUAGE: {language_name}

RULES:
1. Generate a complete, compilable/runnable source file
2. Include proper data models for each signal
3. Include a service interface with get/set methods
4. Include thread safety (mutex/locks)
5. Include proper documentation/comments
{extra_rules}

Generate ONLY the source code, no explanations. Start with the appropriate file header/imports."""


def _get_extra_rules(language: str) -> str:
    if language == "cpp":
        return """6. Follow MISRA C++:2008 rules:
   - All variables must be initialized (Rule 8-5-1)
   - Use explicit constructors (Rule 12-1-1)
   - Specify enum underlying types (Rule 7-2-2)
   - No implicit type conversions (Rule 5-0-1)
   - Single exit point per function (Rule 6-6-5)
7. Use standard C++ (no Boost)
8. Include <cstdint> for fixed-width types"""
    elif language == "kotlin":
        return """6. Use Kotlin data classes for models
7. Use Retrofit annotations for API endpoints
8. Follow Android/Kotlin conventions"""
    elif language == "rust":
        return """6. Use serde for serialization
7. Use Arc<Mutex<>> for shared state
8. Implement Default trait for data types"""
    return "6. Use type hints and Pydantic models\n7. Use FastAPI for REST endpoints"


def _generate_with_llm(
    blueprint: Dict[str, Any],
    language: str,
    provider_name: Optional[str] = None,
) -> tuple[str, LLMCallMetrics]:
    """Generate code using an LLM provider."""
    lang_info = SUPPORTED_LANGUAGES[language]
    prompt = _LLM_CODE_PROMPT.format(
        language_name=lang_info["name"],
        requirement=blueprint.get("raw_requirement", ""),
        signals=", ".join(blueprint.get("signals", [])),
        services=", ".join(blueprint.get("services", [])),
        ui_components=", ".join(blueprint.get("ui_components", [])),
        alerts=", ".join(blueprint.get("alerts", [])),
        extra_rules=_get_extra_rules(language),
    )

    provider = get_provider(provider_name)
    response = provider.generate(prompt)
    record_metrics(response.metrics)

    # Clean markdown code fences if present
    code = response.text.strip()
    if code.startswith("```"):
        lines = code.split("\n")
        lines = lines[1:]  # remove opening fence
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        code = "\n".join(lines)

    return code, response.metrics


# ── Public API ───────────────────────────────────────────────────────────────

def generate_code(
    blueprint: Dict[str, Any],
    language: str = "python",
    use_llm: bool = True,
    provider_name: Optional[str] = None,
) -> GeneratedCode:
    """
    Generate service source code for a given language.

    Args:
        blueprint: Parsed requirement blueprint dict.
        language: Target language key (python, cpp, kotlin, rust).
        use_llm: Whether to attempt LLM generation first.
        provider_name: Specific LLM provider to use (optional).

    Returns:
        GeneratedCode with the generated source and metrics.
    """
    if language not in SUPPORTED_LANGUAGES:
        raise ValueError(
            f"Unsupported language '{language}'. "
            f"Supported: {list(SUPPORTED_LANGUAGES.keys())}"
        )

    lang_info = SUPPORTED_LANGUAGES[language]
    start = time.perf_counter()
    method = "template"
    llm_metrics = None

    if use_llm:
        provider = get_provider(provider_name)
        if provider.name != "template":
            try:
                code, llm_metrics = _generate_with_llm(
                    blueprint, language, provider_name
                )
                method = f"llm:{provider.name}"
                elapsed = (time.perf_counter() - start) * 1000
                return GeneratedCode(
                    language=language,
                    language_name=lang_info["name"],
                    code=code,
                    filename=f"vehicle_health_service{lang_info['ext']}",
                    lines_of_code=code.count("\n") + 1,
                    generation_method=method,
                    generation_time_ms=round(elapsed, 1),
                    llm_metrics=llm_metrics,
                )
            except Exception as exc:
                logger.warning(f"LLM generation failed, falling back to template: {exc}")

    # Template-based fallback
    code = _generate_from_template(blueprint, language)
    elapsed = (time.perf_counter() - start) * 1000

    return GeneratedCode(
        language=language,
        language_name=lang_info["name"],
        code=code,
        filename=f"vehicle_health_service{lang_info['ext']}",
        lines_of_code=code.count("\n") + 1,
        generation_method=method,
        generation_time_ms=round(elapsed, 1),
    )


def generate_all_languages(
    blueprint: Dict[str, Any],
    use_llm: bool = True,
    provider_name: Optional[str] = None,
) -> CodeGenerationResult:
    """Generate code for ALL supported languages."""
    results: List[GeneratedCode] = []
    total_start = time.perf_counter()

    languages = list(SUPPORTED_LANGUAGES.keys())
    for i, lang in enumerate(languages):
        gen = generate_code(blueprint, lang, use_llm, provider_name)
        results.append(gen)
        # Delay between LLM calls to avoid rate-limiting (free tier: 5 RPM)
        if use_llm and i < len(languages) - 1:
            logger.info(f"Rate-limit delay: waiting 15s before next language ({languages[i+1]})...")
            time.sleep(15)

    total_time = (time.perf_counter() - total_start) * 1000

    return CodeGenerationResult(
        requirement=blueprint.get("raw_requirement", ""),
        blueprint=blueprint,
        generated_files=results,
        total_lines=sum(g.lines_of_code for g in results),
        total_time_ms=round(total_time, 1),
    )


def get_supported_languages() -> Dict[str, str]:
    """Return dict of language_key → display_name."""
    return {k: v["name"] for k, v in SUPPORTED_LANGUAGES.items()}


# ── Generation History ───────────────────────────────────────────────────────

_generation_history: List[Dict[str, Any]] = []


def record_generation(result: CodeGenerationResult) -> None:
    entry = {
        "requirement": result.requirement,
        "languages": [g.language for g in result.generated_files],
        "total_lines": result.total_lines,
        "total_time_ms": result.total_time_ms,
        "methods": [g.generation_method for g in result.generated_files],
        "timestamp": result.timestamp,
    }
    _generation_history.append(entry)
    if len(_generation_history) > 100:
        _generation_history.pop(0)


def get_generation_history() -> List[Dict[str, Any]]:
    return list(_generation_history)
