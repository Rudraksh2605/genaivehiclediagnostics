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

    def validate_with_retry(
        self,
        requirement: str,
        language: str = "python",
        max_retries: int = 3,
    ) -> Dict[str, Any]:
        """
        Iterative Build Loop: Generate → Test → Fix → Re-test.

        On test failure, feeds the error output back to the LLM to generate
        corrected code. Repeats up to max_retries times, demonstrating the
        self-healing iterative build mechanism.

        Args:
            requirement: Natural language requirement
            language: Target language
            max_retries: Maximum number of fix iterations (default: 3)

        Returns:
            Dict with all iterations, final result, and improvement metrics
        """
        from genai_interpreter.code_generator import generate_code
        from genai_interpreter.test_generator import generate_tests
        from genai_interpreter.requirement_parser import parse_requirement
        from genai_interpreter.llm_provider import get_provider

        total_start = time.perf_counter()
        iterations = []

        # Step 1: Parse requirement
        blueprint = parse_requirement(requirement)

        # Step 2: Initial code generation
        generated = generate_code(blueprint, language, use_llm=True)
        source_code = generated.code

        # Step 3: Generate test code (once — tests stay constant)
        test_result = generate_tests(blueprint, language, use_llm=True)
        test_code = test_result.code

        # Step 4: Execute tests
        exec_result = self.execute_tests(source_code, test_code, language)

        iterations.append({
            "iteration": 1,
            "action": "initial_generation",
            "source_code": source_code,
            "lines_of_code": generated.lines_of_code,
            "generation_method": generated.generation_method,
            "test_result": exec_result,
        })

        # Step 5: Iterative fix loop
        current_code = source_code
        attempt = 1

        while not exec_result.get("success", False) and attempt <= max_retries:
            attempt += 1
            logger.info(f"Iterative fix — attempt {attempt}/{max_retries + 1}")

            # Build a minimal fix prompt to save tokens
            error_output = exec_result.get("output", "Tests failed")
            fix_prompt = (
                f"FIX this {language} code. Output ONLY corrected code, nothing else.\n"
                f"Requirement: \"{requirement}\"\n"
                f"Code:\n{current_code}\n"
                f"Errors:\n{error_output[:500]}\n"
                f"Output the complete fixed source file now:"
            )

            try:
                from genai_interpreter.llm_provider import generate_with_fallback
                response = generate_with_fallback(fix_prompt)
                
                # We still want to try to run the tests even if no LLM is available,
                # maybe they pass anyway (though unlikely if we are here in the fix loop).
                # But more importantly, the logic below was appending 'skip_no_llm' and breaking
                # without running the test, leading to the UI showing "Skipped (no LLM)".
                if response.metrics.provider == "template":
                    logger.info("Only template provider available, stopping retries")
                    iterations.append({
                        "iteration": attempt,
                        "action": "skip_no_llm",
                        "message": "No LLM available for iterative fixing (template-only mode)",
                        "test_result": exec_result, # Use previous exec_result
                    })
                    break
                
                fixed_code = response.text.strip()
                # Strip markdown code blocks if present
                if fixed_code.startswith("```"):
                    lines = fixed_code.split("\n")
                    lines = lines[1:]  # remove opening ```lang
                    if lines and lines[-1].strip() == "```":
                        lines = lines[:-1]
                    fixed_code = "\n".join(lines)
                current_code = fixed_code
                
                # Re-run tests with fixed code
                exec_result = self.execute_tests(current_code, test_code, language)

                iterations.append({
                    "iteration": attempt,
                    "action": "iterative_fix",
                    "source_code": current_code,
                    "lines_of_code": len(current_code.splitlines()),
                    "generation_method": "llm:iterative_fix",
                    "test_result": exec_result,
                })

            except Exception as e:
                logger.warning(f"LLM fix attempt {attempt} failed: {e}")
                iterations.append({
                    "iteration": attempt,
                    "action": "fix_failed",
                    "error": str(e),
                    "test_result": exec_result,
                })
                break



        total_time = (time.perf_counter() - total_start) * 1000

        # Compute improvement metrics
        first_pass_rate = iterations[0]["test_result"].get("pass_rate", 0)
        final_pass_rate = iterations[-1]["test_result"].get("pass_rate", 0)

        return {
            "requirement": requirement,
            "language": language,
            "iterative_build": True,
            "total_iterations": len(iterations),
            "max_retries_allowed": max_retries,
            "final_success": exec_result.get("success", False),
            "improvement": {
                "initial_pass_rate": first_pass_rate,
                "final_pass_rate": final_pass_rate,
                "improved": final_pass_rate > first_pass_rate,
            },
            "source_code": {
                "code": current_code,
                "lines": len(current_code.splitlines()),
            },
            "test_code": {
                "code": test_code,
                "lines": len(test_code.splitlines()),
                "method": test_result.generation_method,
            },
            "iterations": iterations,
            "total_pipeline_time_ms": round(total_time, 1),
        }


# Singleton
_executor = TestExecutor()

def get_executor() -> TestExecutor:
    return _executor
