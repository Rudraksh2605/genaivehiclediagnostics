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
    get_provider, record_metrics, LLMCallMetrics, generate_with_fallback,
)

logger = logging.getLogger(__name__)

# ── Supported languages ─────────────────────────────────────────────────────

SUPPORTED_LANGUAGES = {
    "python":         {"name": "Python / FastAPI",     "ext": ".py",   "template": "service_python.j2"},
    "cpp":            {"name": "C++ (MISRA-Compliant)","ext": ".cpp",  "template": "service_cpp.j2"},
    "kotlin":         {"name": "Kotlin / Android",     "ext": ".kt",   "template": "service_kotlin.j2"},
    "rust":           {"name": "Rust",                 "ext": ".rs",   "template": "service_rust.j2"},
    "dockerfile":     {"name": "Dockerfile",           "ext": "",      "template": "service_dockerfile.j2"},
    "html_widget":    {"name": "HTML/JS Widget",       "ext": ".html", "template": "service_html_widget.j2"},
    "compose_widget": {"name": "Jetpack Compose",      "ext": ".kt",   "template": "service_compose_widget.j2"},
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


# ── Per-Language LLM Prompts ─────────────────────────────────────────────────

_LLM_PROMPTS = {
    "cpp": """You are an expert C++ developer. Implement the following functionality with STRICT adherence to these constraints:

FUNCTIONALITY: {requirement}

CONSTRAINTS:
1. OUTPUT ONLY C++ CODE. Do not output any markdown blocks, explanations, notes, or concluding remarks.
2. NO COMMENTS. Do not include any comments in the code whatsoever. No // lines, no /* */ blocks, no @brief tags.
3. FOLLOW MISRA C++:2008 RULES silently. Ensure compliance (initialized variables, explicit constructors, enum underlying types, single exit point) but do NOT annotate or list any rules.
4. THREAD SAFETY. Use std::mutex and std::lock_guard.
5. NO WHITE SPACE/FORMATTING FLUFF. Keep code concise.
6. Use <cstdint> for fixed-width types. No Boost.

START OUTPUT IMMEDIATELY WITH #include directives.""",

    "python": """You are an expert Python developer. Implement the following functionality with STRICT adherence to these constraints:

FUNCTIONALITY: {requirement}

CONSTRAINTS:
1. OUTPUT ONLY PYTHON CODE. Do not output any markdown blocks, explanations, notes, or concluding remarks.
2. NO COMMENTS. Do not include any comments or docstrings in the code whatsoever. No # lines, no triple-quote blocks.
3. USE TYPE HINTS on all function parameters and return types.
4. USE PYDANTIC MODELS for data structures.
5. USE FASTAPI for REST endpoints.
6. THREAD SAFETY. Use threading.Lock where needed.
7. DEFINE `def process_telemetry(telemetry_data: dict, store: object) -> None:` to hook into the 1Hz simulation loop. Extract data from `telemetry_data` and write to the global `_alerts` array if conditions met.
8. NO WHITE SPACE/FORMATTING FLUFF. Keep code concise.

START OUTPUT IMMEDIATELY WITH import statements.""",

    "kotlin": """You are an expert Kotlin/Android developer. Implement the following functionality with STRICT adherence to these constraints:

FUNCTIONALITY: {requirement}

CONSTRAINTS:
1. OUTPUT ONLY KOTLIN CODE. Do not output any markdown blocks, explanations, notes, or concluding remarks.
2. NO COMMENTS. Do not include any comments in the code whatsoever. No // lines, no /* */ blocks, no KDoc.
3. USE DATA CLASSES for models.
4. USE RETROFIT ANNOTATIONS for API endpoints.
5. FOLLOW ANDROID/KOTLIN CONVENTIONS.
6. THREAD SAFETY. Use synchronized blocks or Mutex where needed.
7. NO WHITE SPACE/FORMATTING FLUFF. Keep code concise.

START OUTPUT IMMEDIATELY WITH package or import statements.""",

    "rust": """You are an expert Rust developer. Implement the following functionality with STRICT adherence to these constraints:

FUNCTIONALITY: {requirement}

CONSTRAINTS:
1. OUTPUT ONLY RUST CODE. Do not output any markdown blocks, explanations, notes, or concluding remarks.
2. NO COMMENTS. Do not include any comments in the code whatsoever. No // lines, no /// doc comments.
3. USE SERDE for serialization/deserialization.
4. USE Arc<Mutex<>> for shared state and thread safety.
5. IMPLEMENT Default trait for data types.
6. NO WHITE SPACE/FORMATTING FLUFF. Keep code concise.

START OUTPUT IMMEDIATELY WITH use statements.""",

    "dockerfile": """You are a DevOps expert. Write a Dockerfile to containerize a Python SoA application that implements the following functionality:

FUNCTIONALITY: {requirement}

CONSTRAINTS:
1. OUTPUT ONLY DOCKERFILE CONTENT. Do not output any markdown blocks, explanations, or notes.
2. NO COMMENTS.
3. Use `python:3.10-slim` as the base image.
4. Install exactly these dependencies: `fastapi uvicorn pydantic scikit-learn numpy pandas`
5. Copy a file named `vehicle_health_service.py` to `/app`.
6. Expose port 8001.
7. Run `uvicorn vehicle_health_service:app --host 0.0.0.0 --port 8001` as the entrypoint.

START OUTPUT IMMEDIATELY WITH FROM.""",

    "html_widget": """You are a Frontend UI expert. Create an HTML/JS widget snippet (glassmorphism style) for a dashboard to visualize this feature:

FUNCTIONALITY: {requirement}

CONSTRAINTS:
1. OUTPUT ONLY HTML/CSS/JS. Do not output markdown blocks or explanations.
2. Start with an outer `<div class="p-4 rounded-xl backdrop-blur-md bg-white/5 border border-white/10 flex flex-col gap-3">`.
3. Give it a title with an `<h3>`.
4. Include a canvas or a value display block for visualizing the specific data points mentioned.
5. Use modern Tailwind classes for styling (we have Tailwind injected).
6. Provide a tiny `<script>` attached to it to randomly hook or simulate local data updates using `setInterval`.

START OUTPUT IMMEDIATELY WITH THE <div tag.""",

    "compose_widget": """You are an Android Native UI expert. Create a Jetpack Compose widget function to visualize this feature on mobile:

FUNCTIONALITY: {requirement}

CONSTRAINTS:
1. OUTPUT ONLY KOTLIN CODE. Do not output markdown blocks or explanations.
2. Create a single `@Composable fun FeatureWidget(...)`
3. Use standard Material 3 components: `Card`, `Column`, `Row`, `Text`, `CircularProgressIndicator`.
4. Style the generic card with a dark background and subtle outline.
5. Do not include excessive imports; just the composable function itself and immediate definitions (like Data classes specifically for the UI state).

START OUTPUT IMMEDIATELY WITH @Composable.""",
}


def _generate_with_llm(
    blueprint: Dict[str, Any],
    language: str,
    provider_name: Optional[str] = None,
) -> tuple[str, LLMCallMetrics]:
    """Generate code using an LLM provider."""
    lang_info = SUPPORTED_LANGUAGES[language]

    prompt_template = _LLM_PROMPTS.get(language, _LLM_PROMPTS["python"])
    requirement = blueprint.get("raw_requirement", "")
    prompt = prompt_template.format(requirement=requirement)

    response = generate_with_fallback(prompt)
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
                filename = f"vehicle_health_service{lang_info['ext']}"
                if language == "dockerfile":
                    filename = "Dockerfile"
                elif language == "html_widget":
                    filename = "widget.html"
                elif language == "compose_widget":
                    filename = "Widget.kt"

                return GeneratedCode(
                    language=language,
                    language_name=lang_info["name"],
                    code=code,
                    filename=filename,
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

    filename = f"vehicle_health_service{lang_info['ext']}"
    if language == "dockerfile":
        filename = "Dockerfile"
    elif language == "html_widget":
        filename = "widget.html"
    elif language == "compose_widget":
        filename = "Widget.kt"

    return GeneratedCode(
        language=language,
        language_name=lang_info["name"],
        code=code,
        filename=filename,
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
