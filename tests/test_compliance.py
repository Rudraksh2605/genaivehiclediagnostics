"""
Tests for MISRA + AUTOSAR Compliance Checker.
Validates rule detection, report structure, and ASPICE level assessment.
"""

import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from genai_interpreter.compliance_checker import (
    check_compliance,
    get_supported_rules,
    MISRAChecker,
    MISRA_RULES,
    AUTOSAR_RULES,
)


# ── Sample C++ Code Snippets ────────────────────────────────────────────────

CLEAN_CODE = """
#include <iostream>
#include <memory>
#include <cstdint>

enum class Color : uint8_t { Red, Green, Blue };

class Sensor {
public:
    explicit Sensor(int id) : id_(id), value_(0.0) {}
    double getValue() const { return value_; }
private:
    int id_;
    double value_ = 0.0;
};

int main() {
    auto sensor = std::make_unique<Sensor>(1);
    std::cout << sensor->getValue() << std::endl;
    return 0;
}
"""

CODE_WITH_UNREACHABLE = """
int foo() {
    return 42;
    int x = 10;
}
"""

CODE_WITH_FORBIDDEN = """
#include <cstdlib>
int main() {
    exit(0);
    system("ls");
    return 0;
}
"""

CODE_WITH_MAGIC_NUMBERS = """
int check(int val) {
    if (val > 42) {
        return 1;
    }
    return 0;
}
"""

CODE_WITH_RAW_NEW = """
class Widget {};
int main() {
    Widget* w = new Widget();
    delete w;
    return 0;
}
"""

CODE_WITH_MALLOC = """
#include <cstdlib>
int main() {
    int* arr = (int*)malloc(10 * sizeof(int));
    free(arr);
    return 0;
}
"""

CODE_WITH_UNINIT_VARS = """
int main() {
    int x;
    float y;
    x = 5;
    return 0;
}
"""

CODE_WITH_MULTI_RETURN = """
int classify(int x) {
    if (x > 100) {
        return 3;
    }
    if (x > 50) {
        return 2;
    }
    if (x > 0) {
        return 1;
    }
    return 0;
}
"""


# ── Test Classes ─────────────────────────────────────────────────────────────

class TestRuleRegistry:
    """Tests for rule registration."""

    def test_misra_rules_count(self):
        assert len(MISRA_RULES) == 10

    def test_autosar_rules_count(self):
        assert len(AUTOSAR_RULES) == 5

    def test_total_supported_rules(self):
        rules = get_supported_rules()
        assert len(rules) == 15

    def test_rule_structure(self):
        rules = get_supported_rules()
        for rule in rules:
            assert "rule_id" in rule
            assert "description" in rule
            assert "severity" in rule
            assert "standard" in rule

    def test_standards_present(self):
        rules = get_supported_rules()
        standards = set(r["standard"] for r in rules)
        assert "MISRA C++:2008" in standards
        assert "AUTOSAR" in standards


class TestMISRAChecks:
    """Tests for MISRA rule detection."""

    def test_clean_code_minimal_violations(self):
        report = check_compliance(CLEAN_CODE)
        assert report.compliance_percentage >= 80

    def test_unreachable_code_detected(self):
        report = check_compliance(CODE_WITH_UNREACHABLE)
        rule_ids = [v.rule_id for v in report.violations]
        assert "Rule 0-1-1" in rule_ids

    def test_forbidden_functions_detected(self):
        report = check_compliance(CODE_WITH_FORBIDDEN)
        rule_ids = [v.rule_id for v in report.violations]
        assert "Rule 18-0-3" in rule_ids

    def test_uninitialized_vars_detected(self):
        report = check_compliance(CODE_WITH_UNINIT_VARS)
        rule_ids = [v.rule_id for v in report.violations]
        assert "Rule 8-5-1" in rule_ids


class TestAUTOSARChecks:
    """Tests for AUTOSAR rule detection."""

    def test_magic_numbers_detected(self):
        report = check_compliance(CODE_WITH_MAGIC_NUMBERS)
        rule_ids = [v.rule_id for v in report.violations]
        assert "A5-1-1" in rule_ids

    def test_raii_violation_detected(self):
        report = check_compliance(CODE_WITH_RAW_NEW)
        rule_ids = [v.rule_id for v in report.violations]
        assert "A12-0-1" in rule_ids

    def test_malloc_detected(self):
        report = check_compliance(CODE_WITH_MALLOC)
        rule_ids = [v.rule_id for v in report.violations]
        assert "A18-5-1" in rule_ids


class TestComplianceReport:
    """Tests for compliance report structure."""

    def test_report_fields(self):
        report = check_compliance(CLEAN_CODE)
        assert hasattr(report, "total_rules_checked")
        assert hasattr(report, "rules_passed")
        assert hasattr(report, "rules_failed")
        assert hasattr(report, "violations")
        assert hasattr(report, "compliance_percentage")
        assert hasattr(report, "aspice_level")
        assert hasattr(report, "timestamp")

    def test_total_rules_is_15(self):
        report = check_compliance(CLEAN_CODE)
        assert report.total_rules_checked == 15

    def test_percentage_bounds(self):
        report = check_compliance(CLEAN_CODE)
        assert 0 <= report.compliance_percentage <= 100

    def test_aspice_level_format(self):
        report = check_compliance(CLEAN_CODE)
        assert "Level" in report.aspice_level

    def test_high_compliance_gets_high_aspice(self):
        report = check_compliance(CLEAN_CODE)
        # Clean code should get at least Level 2
        level_num = int(report.aspice_level.split(" ")[1])
        assert level_num >= 2

    def test_violation_structure(self):
        report = check_compliance(CODE_WITH_FORBIDDEN)
        assert len(report.violations) > 0
        v = report.violations[0]
        assert v.rule_id
        assert v.rule_description
        assert v.severity
        assert v.message


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
