"""
Tests for Multi-Language Code Generation.
"""

import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from genai_interpreter.code_generator import (
    generate_code,
    generate_all_languages,
    get_supported_languages,
    GeneratedCode,
)
from genai_interpreter.requirement_parser import parse_requirement

SAMPLE_BLUEPRINT = parse_requirement("Monitor battery voltage and trigger alert if below 300V")


class TestCodeGenerator:
    """Tests for code_generator module functions."""

    def test_supported_languages(self):
        langs = get_supported_languages()
        assert "python" in langs
        assert "cpp" in langs
        assert "kotlin" in langs
        assert "rust" in langs

    def test_generate_python_template(self):
        # use_llm=False to force template
        result = generate_code(SAMPLE_BLUEPRINT, language="python", use_llm=False)
        assert isinstance(result, GeneratedCode)
        assert result.language == "python"
        assert len(result.code) > 0
        assert "class BatteryMonitor" in result.code or "def monitor_battery" in result.code or "FastAPI" in result.code
        assert result.generation_method == "template"

    def test_generate_cpp_template(self):
        result = generate_code(SAMPLE_BLUEPRINT, language="cpp", use_llm=False)
        assert result.language == "cpp"
        assert "#include" in result.code

    def test_generate_kotlin_template(self):
        result = generate_code(SAMPLE_BLUEPRINT, language="kotlin", use_llm=False)
        assert result.language == "kotlin"
        assert "Kotlin" in result.code or "data class" in result.code or "fun " in result.code

    def test_generate_rust_template(self):
        result = generate_code(SAMPLE_BLUEPRINT, language="rust", use_llm=False)
        assert result.language == "rust"
        assert "fn main" in result.code or "struct" in result.code

    def test_generate_all_languages(self):
        results = generate_all_languages(SAMPLE_BLUEPRINT, use_llm=False)
        assert results.total_lines > 0
        assert len(results.generated_files) >= 4
        assert any(f.language == "python" for f in results.generated_files)
        assert any(f.language == "cpp" for f in results.generated_files)

    def test_invalid_language_raises_error(self):
        with pytest.raises(ValueError):
            generate_code(SAMPLE_BLUEPRINT, language="brainfuck")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
