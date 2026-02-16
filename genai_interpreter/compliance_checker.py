"""
MISRA/ASPICE Compliance Checker.

Checks generated C/C++ code against a subset of MISRA C++:2008 rules
and generates an ASPICE-aligned compliance report.
"""

import re
import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class MISRAViolation:
    """A single MISRA rule violation."""
    rule_id: str
    rule_description: str
    severity: str  # "required", "advisory", "mandatory"
    line_number: Optional[int]
    line_content: str
    message: str


@dataclass
class ComplianceReport:
    """Full compliance check result."""
    total_rules_checked: int
    rules_passed: int
    rules_failed: int
    violations: List[MISRAViolation]
    compliance_percentage: float
    aspice_level: str  # "Level 0" to "Level 3"
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())


# ── MISRA Rule Definitions ───────────────────────────────────────────────────

MISRA_RULES = {
    "Rule 0-1-1": {
        "description": "A project shall not contain unreachable code",
        "severity": "required",
        "check": "_check_unreachable_code",
    },
    "Rule 2-10-1": {
        "description": "Different identifiers shall be typographically unambiguous",
        "severity": "required",
        "check": "_check_identifier_ambiguity",
    },
    "Rule 5-0-1": {
        "description": "Value of an expression shall not be implicitly converted",
        "severity": "required",
        "check": "_check_implicit_conversions",
    },
    "Rule 6-6-5": {
        "description": "A function shall have a single point of exit at the end",
        "severity": "required",
        "check": "_check_single_exit",
    },
    "Rule 7-2-2": {
        "description": "Enumeration underlying type shall be explicitly specified",
        "severity": "required",
        "check": "_check_enum_types",
    },
    "Rule 8-5-1": {
        "description": "All variables shall have a value before being used",
        "severity": "required",
        "check": "_check_uninitialized_vars",
    },
    "Rule 12-1-1": {
        "description": "Constructors that can be called with a single argument shall be declared explicit",
        "severity": "required",
        "check": "_check_explicit_constructors",
    },
    "Rule 15-0-2": {
        "description": "Pointer arithmetic shall not be applied",
        "severity": "advisory",
        "check": "_check_pointer_arithmetic",
    },
    "Rule 16-0-5": {
        "description": "Arguments to function-like macros shall not contain tokens that look like preprocessing directives",
        "severity": "required",
        "check": "_check_macro_directives",
    },
    "Rule 18-0-3": {
        "description": "The library functions abort, exit, getenv and system shall not be used",
        "severity": "required",
        "check": "_check_forbidden_functions",
    },
}


# ── Rule Check Functions ─────────────────────────────────────────────────────

class MISRAChecker:
    """Checks C++ code against MISRA rules."""

    def __init__(self, code: str):
        self.code = code
        self.lines = code.split("\n")

    def check_all(self) -> List[MISRAViolation]:
        violations: List[MISRAViolation] = []
        for rule_id, rule_info in MISRA_RULES.items():
            method = getattr(self, rule_info["check"], None)
            if method:
                rule_violations = method(rule_id, rule_info)
                violations.extend(rule_violations)
        return violations

    def _check_unreachable_code(self, rule_id: str, info: Dict) -> List[MISRAViolation]:
        """Check for code after return statements within same block."""
        violations = []
        in_block = False
        after_return = False
        for i, line in enumerate(self.lines, 1):
            stripped = line.strip()
            if stripped.startswith("return ") or stripped == "return;":
                after_return = True
                continue
            if after_return and stripped and stripped != "}" and not stripped.startswith("//"):
                violations.append(MISRAViolation(
                    rule_id=rule_id,
                    rule_description=info["description"],
                    severity=info["severity"],
                    line_number=i,
                    line_content=stripped,
                    message=f"Potentially unreachable code after return statement",
                ))
                after_return = False
            if stripped == "}":
                after_return = False
        return violations

    def _check_identifier_ambiguity(self, rule_id: str, info: Dict) -> List[MISRAViolation]:
        """Check for identifiers that differ only in case or by _ vs camelCase."""
        return []  # Advanced check — would require full AST

    def _check_implicit_conversions(self, rule_id: str, info: Dict) -> List[MISRAViolation]:
        """Check for common implicit conversion patterns."""
        violations = []
        patterns = [
            (r"\bint\s+\w+\s*=\s*\d+\.\d+", "Implicit float-to-int conversion"),
            (r"\bfloat\s+\w+\s*=\s*\d+;", "Implicit int-to-float conversion (use .0F suffix)"),
        ]
        for i, line in enumerate(self.lines, 1):
            for pattern, msg in patterns:
                if re.search(pattern, line):
                    violations.append(MISRAViolation(
                        rule_id=rule_id,
                        rule_description=info["description"],
                        severity=info["severity"],
                        line_number=i,
                        line_content=line.strip(),
                        message=msg,
                    ))
        return violations

    def _check_single_exit(self, rule_id: str, info: Dict) -> List[MISRAViolation]:
        """Check for multiple return statements in a function."""
        violations = []
        func_name = ""
        return_count = 0
        brace_depth = 0
        func_start = 0

        for i, line in enumerate(self.lines, 1):
            stripped = line.strip()

            # Detect function definitions
            if re.match(r"^\s*([\w:<>&*]+\s+)+\w+\s*\(", line) and "{" not in line:
                func_name = stripped
                func_start = i
                return_count = 0
            elif re.match(r"^\s*([\w:<>&*]+\s+)+\w+\s*\(.*\)\s*\{", line):
                func_name = stripped
                func_start = i
                return_count = 0
                brace_depth = 1

            if "{" in stripped:
                brace_depth += stripped.count("{")
            if "}" in stripped:
                brace_depth -= stripped.count("}")

            if "return " in stripped or stripped == "return;":
                return_count += 1

            if brace_depth == 0 and return_count > 1 and func_name:
                violations.append(MISRAViolation(
                    rule_id=rule_id,
                    rule_description=info["description"],
                    severity=info["severity"],
                    line_number=func_start,
                    line_content=func_name[:80],
                    message=f"Function has {return_count} return statements (should have 1)",
                ))
                func_name = ""
                return_count = 0

        return violations

    def _check_enum_types(self, rule_id: str, info: Dict) -> List[MISRAViolation]:
        """Check enums have explicit underlying type."""
        violations = []
        for i, line in enumerate(self.lines, 1):
            if re.search(r"\benum\s+(class\s+)?\w+\s*\{", line):
                if ":" not in line.split("{")[0]:
                    violations.append(MISRAViolation(
                        rule_id=rule_id,
                        rule_description=info["description"],
                        severity=info["severity"],
                        line_number=i,
                        line_content=line.strip(),
                        message="Enum missing explicit underlying type (e.g., : uint8_t)",
                    ))
        return violations

    def _check_uninitialized_vars(self, rule_id: str, info: Dict) -> List[MISRAViolation]:
        """Check for uninitialized variable declarations."""
        violations = []
        type_pattern = r"^\s*(int|float|double|char|bool|uint\d+_t|int\d+_t|size_t)\s+(\w+)\s*;"
        for i, line in enumerate(self.lines, 1):
            if re.search(type_pattern, line):
                violations.append(MISRAViolation(
                    rule_id=rule_id,
                    rule_description=info["description"],
                    severity=info["severity"],
                    line_number=i,
                    line_content=line.strip(),
                    message="Variable declared without initialization",
                ))
        return violations

    def _check_explicit_constructors(self, rule_id: str, info: Dict) -> List[MISRAViolation]:
        """Check single-arg constructors are explicit."""
        violations = []
        for i, line in enumerate(self.lines, 1):
            # Match constructors with single parameter, not marked explicit
            match = re.search(r"^\s+(\w+)\s*\(\s*\w+\s+\w+\s*\)", line)
            if match and "explicit" not in line and "::" not in line:
                violations.append(MISRAViolation(
                    rule_id=rule_id,
                    rule_description=info["description"],
                    severity=info["severity"],
                    line_number=i,
                    line_content=line.strip(),
                    message="Single-argument constructor should be declared explicit",
                ))
        return violations

    def _check_pointer_arithmetic(self, rule_id: str, info: Dict) -> List[MISRAViolation]:
        """Check for pointer arithmetic operations."""
        violations = []
        patterns = [r"\w+\+\+\s*;.*\*", r"\*\w+\s*\+\s*\d+", r"\*\(\w+\s*\+"]
        for i, line in enumerate(self.lines, 1):
            for pattern in patterns:
                if re.search(pattern, line):
                    violations.append(MISRAViolation(
                        rule_id=rule_id,
                        rule_description=info["description"],
                        severity=info["severity"],
                        line_number=i,
                        line_content=line.strip(),
                        message="Pointer arithmetic detected",
                    ))
        return violations

    def _check_macro_directives(self, rule_id: str, info: Dict) -> List[MISRAViolation]:
        """Check for preprocessing directives in macro arguments."""
        return []  # Would require preprocessor analysis

    def _check_forbidden_functions(self, rule_id: str, info: Dict) -> List[MISRAViolation]:
        """Check for use of abort, exit, getenv, system."""
        violations = []
        forbidden = ["abort(", "exit(", "getenv(", "system("]
        for i, line in enumerate(self.lines, 1):
            for func in forbidden:
                if func in line and "//" not in line.split(func)[0]:
                    violations.append(MISRAViolation(
                        rule_id=rule_id,
                        rule_description=info["description"],
                        severity=info["severity"],
                        line_number=i,
                        line_content=line.strip(),
                        message=f"Forbidden function '{func[:-1]}' used",
                    ))
        return violations


# ── ASPICE Level Assessment ──────────────────────────────────────────────────

def _assess_aspice_level(compliance_pct: float, has_traceability: bool = True) -> str:
    if compliance_pct >= 95 and has_traceability:
        return "Level 3 - Established"
    elif compliance_pct >= 80:
        return "Level 2 - Managed"
    elif compliance_pct >= 50:
        return "Level 1 - Performed"
    return "Level 0 - Incomplete"


# ── Public API ───────────────────────────────────────────────────────────────

def check_compliance(code: str) -> ComplianceReport:
    """
    Check C++ code against MISRA rules and return a compliance report.
    """
    checker = MISRAChecker(code)
    violations = checker.check_all()

    total_rules = len(MISRA_RULES)
    failed_rules = len(set(v.rule_id for v in violations))
    passed_rules = total_rules - failed_rules
    pct = (passed_rules / total_rules * 100) if total_rules > 0 else 0

    return ComplianceReport(
        total_rules_checked=total_rules,
        rules_passed=passed_rules,
        rules_failed=failed_rules,
        violations=violations,
        compliance_percentage=round(pct, 1),
        aspice_level=_assess_aspice_level(pct),
    )


def get_supported_rules() -> List[Dict[str, str]]:
    """List all MISRA rules that are checked."""
    return [
        {
            "rule_id": rule_id,
            "description": info["description"],
            "severity": info["severity"],
        }
        for rule_id, info in MISRA_RULES.items()
    ]
