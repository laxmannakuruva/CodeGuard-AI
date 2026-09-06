"""
Fix Verification
After a proposed fix is written into a candidate working directory,
this module decides whether the fix is actually verified. Uploaded
projects vary widely -- some have real pytest suites, many (small demo
repos) don't -- so verification combines three independent signals
rather than relying on tests alone:

  1. compile_check   -- the fixed file is syntactically valid Python
  2. tests_result     -- "passed" / "failed" / "no_tests_found"
  3. static_recheck   -- re-running the SAME tool/rule that flagged the
                          original finding, to confirm that specific
                          issue is gone (best-effort; not all findings
                          map to a single re-checkable rule)

A fix is "fix_verified" only if compile_check passes AND tests_result
is not "failed" AND static_recheck is not "still_present".
"""

import ast
from pathlib import Path

from . import sandbox
from .workspace import get_test_files
from .static_analysis import run_pylint, run_bandit


def check_compiles(file_path: Path) -> bool:
    try:
        source = file_path.read_text(encoding="utf-8")
        ast.parse(source)
        return True
    except (SyntaxError, UnicodeDecodeError, OSError):
        return False


def recheck_static_finding(file_path: Path, finding: dict) -> str:
    """Re-run the originating tool and check if the same issue (code+line-ish) still appears."""
    tool = finding.get("tool")
    code = finding.get("code")

    if tool == "pylint":
        results = run_pylint(file_path)
        still_present = any(
            item.get("symbol") == code or item.get("message-id") == code
            for item in results if "_tool_error" not in item
        )
        return "still_present" if still_present else "resolved"

    if tool == "bandit":
        results = run_bandit(file_path)
        still_present = any(
            item.get("test_id") == code for item in results.get("results", [])
        )
        return "still_present" if still_present else "resolved"

    # AI-detected findings don't map to a single re-checkable rule
    return "not_checked"


def verify_fix(candidate_dir: Path, fixed_file_rel: str, finding: dict) -> dict:
    """
    Run all verification signals against a candidate working directory
    (a full copy of the project with the proposed fix already written in).
    """
    fixed_file_path = candidate_dir / fixed_file_rel

    compile_ok = check_compiles(fixed_file_path)

    static_status = recheck_static_finding(fixed_file_path, finding) if compile_ok else "not_checked"

    test_files = get_test_files(candidate_dir)
    if not test_files:
        tests_status = "no_tests_found"
        sandbox_result = {"logs": "", "isolation_mode": "n/a (no tests to run)", "error": None}
    else:
        sandbox_result = sandbox.run_tests(candidate_dir)
        if sandbox_result.get("error"):
            tests_status = "failed"
        elif sandbox_result.get("exit_code") == 0:
            tests_status = "passed"
        else:
            tests_status = "failed"

    verified = compile_ok and tests_status != "failed" and static_status != "still_present"

    return {
        "status": "fix_verified" if verified else "fix_failed",
        "compile_check": compile_ok,
        "tests_result": tests_status,
        "static_recheck": static_status,
        "isolation_mode": sandbox_result.get("isolation_mode", "n/a"),
        "logs": sandbox_result.get("logs") or sandbox_result.get("error") or "",
    }
