"""
Pydantic models shared across the CodeGuard AI backend.
"""

from typing import Optional
from pydantic import BaseModel


class Finding(BaseModel):
    id: str
    file: str
    line: Optional[int] = None
    description: str
    severity: str  # "low" | "medium" | "high"
    source: str    # "static" | "security" | "ai"
    tool: str       # "pylint" | "bandit" | "claude"
    code: Optional[str] = None       # tool-specific rule code, e.g. "C0103"
    confidence: Optional[float] = None
    status: str = "open"  # "open" | "fix_proposed" | "fix_verified" | "fix_failed"


class AnalyzeResponse(BaseModel):
    workspace_id: str
    file_count: int
    python_file_count: int
    findings: list[Finding]
    ai_available: bool


class FixProposal(BaseModel):
    finding_id: str
    file: str
    original_code: str
    fixed_code: str
    diff: str
    explanation: str


class ApplyFixResult(BaseModel):
    finding_id: str
    status: str  # "fix_verified" | "fix_failed"
    compile_check: bool
    tests_result: str  # "passed" | "failed" | "no_tests_found"
    static_recheck: str  # "resolved" | "still_present" | "not_checked"
    isolation_mode: str  # "docker" | "restricted-subprocess"
    logs: str


class ReportResponse(BaseModel):
    workspace_id: str
    total_findings: int
    by_severity: dict
    by_status: dict
    by_source: dict
    files_analyzed: int
    fixes_verified: int
    fixes_failed: int
    findings: list[Finding]
