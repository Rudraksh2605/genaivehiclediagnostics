"""
Code Generation API Routes.

Provides endpoints for GenAI-powered code generation, design document
creation, test case generation, and LLM performance comparison.
"""

import logging
from typing import Optional, List
from pydantic import BaseModel, Field

from fastapi import APIRouter, HTTPException
from dataclasses import asdict

from genai_interpreter.requirement_parser import parse_requirement
from genai_interpreter.code_generator import (
    generate_code,
    generate_all_languages,
    get_supported_languages,
    get_generation_history,
    record_generation,
)
from genai_interpreter.design_generator import generate_design
from genai_interpreter.test_generator import generate_tests, generate_all_tests, SUPPORTED_TEST_LANGUAGES
from genai_interpreter.llm_comparison import compare_llms
from genai_interpreter.llm_provider import list_available_providers, get_metrics_history

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/codegen", tags=["Code Generation"])


# ── Request / Response Models ────────────────────────────────────────────────

class CodeGenRequest(BaseModel):
    requirement: str = Field(description="Natural-language vehicle diagnostics requirement")
    language: str = Field(default="python", description="Target language: python, cpp, kotlin, rust")
    use_llm: bool = Field(default=True, description="Attempt LLM generation (falls back to template)")
    provider: Optional[str] = Field(default=None, description="Specific LLM provider: gemini, openai, template")


class AllLanguagesRequest(BaseModel):
    requirement: str = Field(description="Natural-language requirement")
    use_llm: bool = Field(default=True)
    provider: Optional[str] = Field(default=None)


class DesignRequest(BaseModel):
    requirement: str = Field(description="Natural-language requirement")
    use_llm: bool = Field(default=True)
    provider: Optional[str] = Field(default=None)


class TestGenRequest(BaseModel):
    requirement: str = Field(description="Natural-language requirement")
    language: str = Field(default="python", description="Test language: python, cpp")
    use_llm: bool = Field(default=True)
    provider: Optional[str] = Field(default=None)


class CompareRequest(BaseModel):
    requirement: str = Field(description="Natural-language requirement")
    languages: Optional[List[str]] = Field(default=None, description="Languages to compare")


# ── Endpoints ────────────────────────────────────────────────────────────────

@router.post("/generate")
async def generate_code_endpoint(req: CodeGenRequest):
    """
    Generate source code from a natural-language requirement.

    Pipeline: Requirement → NLP Parse → Blueprint → Code Generation
    """
    try:
        # Step 1: Parse requirement into blueprint
        blueprint = parse_requirement(req.requirement)

        # Step 2: Generate code
        result = generate_code(
            blueprint,
            language=req.language,
            use_llm=req.use_llm,
            provider_name=req.provider,
        )

        return {
            "requirement": req.requirement,
            "blueprint": blueprint,
            "generated_code": {
                "language": result.language,
                "language_name": result.language_name,
                "filename": result.filename,
                "code": result.code,
                "lines_of_code": result.lines_of_code,
                "generation_method": result.generation_method,
                "generation_time_ms": result.generation_time_ms,
            },
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Code generation failed: {e}")
        raise HTTPException(status_code=500, detail=f"Generation failed: {str(e)}")


@router.post("/generate-all")
async def generate_all_endpoint(req: AllLanguagesRequest):
    """Generate code in ALL supported languages from a single requirement."""
    try:
        blueprint = parse_requirement(req.requirement)
        result = generate_all_languages(blueprint, req.use_llm, req.provider)
        record_generation(result)

        return {
            "requirement": req.requirement,
            "blueprint": blueprint,
            "total_lines": result.total_lines,
            "total_time_ms": result.total_time_ms,
            "generated_files": [
                {
                    "language": g.language,
                    "language_name": g.language_name,
                    "filename": g.filename,
                    "code": g.code,
                    "lines_of_code": g.lines_of_code,
                    "generation_method": g.generation_method,
                    "generation_time_ms": g.generation_time_ms,
                }
                for g in result.generated_files
            ],
        }
    except Exception as e:
        logger.error(f"Multi-language generation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/design")
async def generate_design_endpoint(req: DesignRequest):
    """Generate a service interface design document."""
    try:
        blueprint = parse_requirement(req.requirement)
        doc = generate_design(blueprint, req.use_llm, req.provider)

        return {
            "requirement": req.requirement,
            "blueprint": blueprint,
            "design_document": {
                "title": doc.title,
                "content": doc.content,
                "format": doc.format,
                "generation_method": doc.generation_method,
                "generation_time_ms": doc.generation_time_ms,
            },
        }
    except Exception as e:
        logger.error(f"Design generation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/test")
async def generate_test_endpoint(req: TestGenRequest):
    """Generate test cases for a requirement."""
    try:
        blueprint = parse_requirement(req.requirement)
        test = generate_tests(blueprint, req.language, req.use_llm, req.provider)

        return {
            "requirement": req.requirement,
            "blueprint": blueprint,
            "generated_test": {
                "language": test.language,
                "language_name": test.language_name,
                "filename": test.filename,
                "code": test.code,
                "test_count": test.test_count,
                "generation_method": test.generation_method,
                "generation_time_ms": test.generation_time_ms,
            },
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Test generation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/compare-llms")
async def compare_llms_endpoint(req: CompareRequest):
    """Compare multiple LLM providers on the same requirement."""
    try:
        blueprint = parse_requirement(req.requirement)
        report = compare_llms(blueprint, languages=req.languages)

        return {
            "requirement": req.requirement,
            "providers_compared": report.providers_compared,
            "languages_tested": report.languages_tested,
            "summary": report.summary,
            "comparisons": [
                {
                    "language": c.language,
                    "results": [
                        {
                            "provider": r.provider,
                            "lines_of_code": r.lines_of_code,
                            "latency_ms": r.latency_ms,
                            "tokens_used": r.tokens_used,
                            "syntax_valid": r.syntax_valid,
                            "error": r.error,
                        }
                        for r in c.results
                    ],
                }
                for c in report.comparisons
            ],
            "timestamp": report.timestamp,
        }
    except Exception as e:
        logger.error(f"LLM comparison failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/languages")
async def get_languages():
    """List supported code generation languages."""
    return {
        "code_languages": get_supported_languages(),
        "test_languages": {k: v["name"] for k, v in SUPPORTED_TEST_LANGUAGES.items()},
    }


@router.get("/providers")
async def get_providers():
    """List available LLM providers."""
    return {"available_providers": list_available_providers()}


@router.get("/history")
async def get_history():
    """Get recent code generation history."""
    return {"history": get_generation_history()}


@router.get("/metrics")
async def get_llm_metrics():
    """Get LLM call metrics history."""
    history = get_metrics_history()
    return {
        "count": len(history),
        "metrics": [
            {
                "model": m.model,
                "provider": m.provider,
                "prompt_tokens": m.prompt_tokens,
                "completion_tokens": m.completion_tokens,
                "total_tokens": m.total_tokens,
                "latency_ms": m.latency_ms,
                "success": m.success,
                "timestamp": m.timestamp,
            }
            for m in history
        ],
    }


# ── Test Execution (Auto-Validate) ──────────────────────────────────────────

class ValidateRequest(BaseModel):
    requirement: str = Field(..., description="Natural language requirement")
    language: str = Field(default="python", description="Language (currently python)")
    max_retries: int = Field(default=3, ge=0, le=5, description="Max iterative fix attempts (0 = no retry)")


@router.post("/validate")
async def validate_generated_code(req: ValidateRequest):
    """
    Full validation pipeline: Requirement → Code → Tests → Execute.

    Generates source code and test cases from a natural-language requirement,
    then automatically executes the tests and returns pass/fail results.

    With max_retries > 0, implements an **iterative build loop**:
    on test failure, feeds errors back to the LLM for auto-correction.
    """
    from genai_interpreter.test_executor import get_executor

    try:
        if req.max_retries > 0:
            result = get_executor().validate_with_retry(
                requirement=req.requirement,
                language=req.language,
                max_retries=req.max_retries,
            )
        else:
            result = get_executor().validate_code_with_tests(
                requirement=req.requirement,
                language=req.language,
            )
        return result
    except Exception as e:
        logger.error(f"Validation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ── Build Pipeline (Syntax / Compile Check) ─────────────────────────────────

class BuildRequest(BaseModel):
    code: str = Field(..., description="Source code to validate")
    language: str = Field(default="python", description="Language")


@router.post("/build")
async def build_check(req: BuildRequest):
    """
    Iterative build mechanism: validate generated code can compile/run.

    - Python: syntax check + import validation
    - C++: syntax pattern check (full compilation requires g++)
    - Kotlin/Rust: syntax pattern check
    """
    from genai_interpreter.build_pipeline import get_pipeline

    try:
        result = get_pipeline().validate(req.code, req.language)
        return result
    except Exception as e:
        logger.error(f"Build check failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/demo-compare")
async def demo_compare():
    """
    Demo LLM comparison — no API key required.

    Runs a sample vehicle telemetry requirement through the template provider
    across all supported languages, demonstrating the comparison engine.
    Returns per-language results with quality KPIs.
    """
    try:
        sample_requirement = (
            "Create a vehicle speed monitor service that reads CAN bus speed data, "
            "checks against configurable speed thresholds, and triggers alerts when "
            "the vehicle exceeds the limit for more than 5 consecutive readings."
        )
        blueprint = parse_requirement(sample_requirement)
        report = compare_llms(
            blueprint,
            languages=["python", "cpp", "kotlin", "rust"],
            providers=["template"],
        )
        return {
            "demo": True,
            "note": "Using template provider (no API key needed). Add GOOGLE_API_KEY or OPENAI_API_KEY for real LLM comparison.",
            "requirement": report.requirement,
            "providers_compared": report.providers_compared,
            "languages_tested": report.languages_tested,
            "summary": report.summary,
            "comparisons": [
                {
                    "language": comp.language,
                    "results": [
                        {
                            "provider": r.provider,
                            "lines_of_code": r.lines_of_code,
                            "latency_ms": r.latency_ms,
                            "tokens_used": r.tokens_used,
                            "syntax_valid": r.syntax_valid,
                            "code_preview": r.code[:200] + "..." if len(r.code) > 200 else r.code,
                        }
                        for r in comp.results
                    ],
                }
                for comp in report.comparisons
            ],
        }
    except Exception as e:
        logger.error(f"Demo compare failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

