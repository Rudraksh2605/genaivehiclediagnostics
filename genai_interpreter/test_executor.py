"""
Test Executor for Generated Code.

Automatically runs generated test cases against generated source code:
  1. Writes code + tests to temporary files
  2. Executes tests via subprocess (pytest for Python)
  3. Parses results and returns pass/fail counts

Satisfies the TELIPORT requirement: "The test cases when executed on the
source code, should provide pass test results."
"""

import logging
import os
import subprocess
import sys
import tempfile
import shutil
import time
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class TestExecutor:
    """Executes generated test code and returns pass/fail results."""

    SUPPORTED_LANGUAGES = {"python"}  # Expandable

    def execute_tests(
        self,
        source_code: str,
        test_code: str,
        language: str = "python",
        timeout: int = 30,
    ) -> Dict[str, Any]:
        """
        Execute generated tests against generated source code.
        
        Args:
            source_code: The generated source code
            test_code: The generated test code
            language: Programming language (currently: python)
            timeout: Max execution time in seconds
            
        Returns:
            Dict with passed, failed, errors, output, execution_time_ms
        """
        if language not in self.SUPPORTED_LANGUAGES:
            return {
                "success": False,
                "language": language,
                "message": f"Auto-execution not supported for {language}. "
                           f"Supported: {', '.join(self.SUPPORTED_LANGUAGES)}",
                "passed": 0,
                "failed": 0,
                "errors": 0,
            }

        if language == "python":
            return self._execute_python_tests(source_code, test_code, timeout)

        return {"success": False, "message": "Unknown language"}

    def _execute_python_tests(
        self,
        source_code: str,
        test_code: str,
        timeout: int = 30,
    ) -> Dict[str, Any]:
        """Execute Python tests using pytest in a temporary directory."""

        tmpdir = tempfile.mkdtemp(prefix="vhd_test_")
        start_time = time.perf_counter()

        try:
            # Write source code
            source_path = os.path.join(tmpdir, "generated_module.py")
            with open(source_path, "w", encoding="utf-8") as f:
                f.write(source_code)

            # Prepare test code — fix imports to reference our temp module
            # Add import of generated module at the top  
            test_header = (
                "import sys, os\n"
                f"sys.path.insert(0, r'{tmpdir}')\n"
                "from generated_module import *\n\n"
            )

            # If test code already has imports, inject after them
            test_code_final = test_header + test_code

            test_path = os.path.join(tmpdir, "test_generated.py")
            with open(test_path, "w", encoding="utf-8") as f:
                f.write(test_code_final)

            # Run pytest
            result = subprocess.run(
                [sys.executable, "-m", "pytest", test_path, "-v", "--tb=short", "--no-header"],
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=tmpdir,
                env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
            )

            execution_time = (time.perf_counter() - start_time) * 1000
            output = result.stdout + result.stderr

            # Parse pytest output
            passed, failed, errors = self._parse_pytest_output(output)

            # Check for syntax errors in source
            syntax_ok = self._check_python_syntax(source_code)

            return {
                "success": result.returncode == 0,
                "language": "python",
                "passed": passed,
                "failed": failed,
                "errors": errors,
                "total_tests": passed + failed + errors,
                "pass_rate": round(passed / max(passed + failed + errors, 1) * 100, 1),
                "source_syntax_valid": syntax_ok,
                "execution_time_ms": round(execution_time, 1),
                "exit_code": result.returncode,
                "output": output[:3000],  # Truncate long output
            }

        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "language": "python",
                "message": f"Test execution timed out after {timeout}s",
                "passed": 0,
                "failed": 0,
                "errors": 1,
                "execution_time_ms": timeout * 1000,
            }
        except Exception as e:
            return {
                "success": False,
                "language": "python",
                "message": f"Execution error: {str(e)}",
                "passed": 0,
                "failed": 0,
                "errors": 1,
            }
        finally:
            # Clean up temp directory
            try:
                shutil.rmtree(tmpdir, ignore_errors=True)
            except Exception:
                pass

    def _parse_pytest_output(self, output: str) -> tuple:
        """Parse pytest output to extract pass/fail/error counts."""
        passed = 0
        failed = 0
        errors = 0

        for line in output.split("\n"):
            line_lower = line.lower().strip()
            # Look for summary line like "3 passed, 1 failed"
            if "passed" in line_lower or "failed" in line_lower or "error" in line_lower:
                import re
                p = re.search(r"(\d+)\s+passed", line_lower)
                f = re.search(r"(\d+)\s+failed", line_lower)
                e = re.search(r"(\d+)\s+error", line_lower)
                if p:
                    passed = int(p.group(1))
                if f:
                    failed = int(f.group(1))
                if e:
                    errors = int(e.group(1))

            # Also count individual PASSED/FAILED lines
            if line.strip().endswith("PASSED"):
                passed = max(passed, passed)  # Don't double count
            if line.strip().endswith("FAILED"):
                failed = max(failed, failed)

        return passed, failed, errors

    def _check_python_syntax(self, code: str) -> bool:
        """Check if Python source code has valid syntax."""
        try:
            compile(code, "<generated>", "exec")
            return True
        except SyntaxError:
            return False

    def validate_code_with_tests(
        self,
        requirement: str,
        language: str = "python",
    ) -> Dict[str, Any]:
        """
        Full validation pipeline: Generate code → Generate tests → Run tests.
        
        Args:
            requirement: Natural language requirement
            language: Target language
            
        Returns:
            Complete validation result with code, tests, and execution results
        """
        from genai_interpreter.code_generator import generate_code
        from genai_interpreter.test_generator import generate_tests
        from genai_interpreter.requirement_parser import parse_requirement

        total_start = time.perf_counter()

        # Step 1: Parse requirement
        blueprint = parse_requirement(requirement)

        # Step 2: Generate source code
        generated = generate_code(blueprint, language, use_llm=True)
        source_code = generated.code

        # Step 3: Generate test code
        test_result = generate_tests(blueprint, language, use_llm=True)
        test_code = test_result.code

        # Step 4: Execute tests
        exec_result = self.execute_tests(source_code, test_code, language)

        total_time = (time.perf_counter() - total_start) * 1000

        return {
            "requirement": requirement,
            "language": language,
            "source_code": {
                "code": source_code,
                "lines": generated.lines_of_code,
                "method": generated.generation_method,
            },
            "test_code": {
                "code": test_code,
                "lines": len(test_result.code.splitlines()),
                "method": test_result.generation_method,
            },
            "test_execution": exec_result,
            "total_pipeline_time_ms": round(total_time, 1),
        }


# Singleton
_executor = TestExecutor()

def get_executor() -> TestExecutor:
    return _executor
