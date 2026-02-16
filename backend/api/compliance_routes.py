"""
Compliance Checking API Routes.

Provides endpoints for MISRA/ASPICE compliance checking of generated C++ code.
"""

import logging
from pydantic import BaseModel, Field
from fastapi import APIRouter

from genai_interpreter.compliance_checker import check_compliance, get_supported_rules

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/compliance", tags=["Compliance"])


class ComplianceCheckRequest(BaseModel):
    code: str = Field(description="C++ source code to check")


@router.post("/check")
async def check_compliance_endpoint(req: ComplianceCheckRequest):
    """Check C++ code against MISRA C++:2008 rules."""
    report = check_compliance(req.code)
    return {
        "total_rules_checked": report.total_rules_checked,
        "rules_passed": report.rules_passed,
        "rules_failed": report.rules_failed,
        "compliance_percentage": report.compliance_percentage,
        "aspice_level": report.aspice_level,
        "violations": [
            {
                "rule_id": v.rule_id,
                "rule_description": v.rule_description,
                "severity": v.severity,
                "line_number": v.line_number,
                "line_content": v.line_content,
                "message": v.message,
            }
            for v in report.violations
        ],
        "timestamp": report.timestamp,
    }


@router.get("/rules")
async def get_rules():
    """List all supported MISRA rules."""
    rules = get_supported_rules()
    return {"count": len(rules), "rules": rules}
