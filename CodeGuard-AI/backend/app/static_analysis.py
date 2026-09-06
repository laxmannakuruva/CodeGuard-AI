"""
Static & Security Analysis
Runs pylint (general problems) and bandit (security issues) against
Python files. This is pure AST-based static analysis -- no code from
the uploaded project is ever executed here. Works with NO API key.
"""

import json
import subprocess
import uuid
from pathlib import Path

# pylint message-type prefixes we surface as findings (skip pure convention/refactor
# noise like C/R codes by default to keep signal high; still counted but lower severity)
SEVERITY_BY_PYLINT_TYPE = {
    "error": "high",
    "warning": "medium",
    "convention": "low",
    "refactor": "low",
}

BANDIT_SEVERITY_MAP = {"HIGH": "high", "MEDIUM": "medium", "LOW": "low"}


def run_pylint(filepath: Path) -> list[dict]:
    try:
        result = subprocess.run(
            ["pylint", str(filepath), "--output-format=json", "--disable=all",
             "--enable=E,W,C0103,C0301,W0612,W0611"],
            capture_output=True, text=True, timeout=30,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError) as e:
        return [{"_tool_error": str(e)}]

    try:
        return json.loads(result.stdout) if result.stdout.strip() else []
    except json.JSONDecodeError:
        return []


def run_bandit(filepath: Path) -> dict:
    try:
        result = subprocess.run(
            ["bandit", "-f", "json", str(filepath)],
            capture_output=True, text=True, timeout=30,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError) as e:
        return {"_tool_error": str(e)}

    try:
        return json.loads(result.stdout) if result.stdout.strip() else {}
    except json.JSONDecodeError:
        return {}


def analyze_file(filepath: Path, rel_path: str) -> list[dict]:
    """
    Run pylint + bandit on a single file, return a list of normalized
    Finding-shaped dicts (matching app.models.Finding fields).
    """
    findings = []

    pylint_results = run_pylint(filepath)
    for item in pylint_results:
        if "_tool_error" in item:
            continue
        findings.append({
            "id": uuid.uuid4().hex,
            "file": rel_path,
            "line": item.get("line"),
            "description": item.get("message", "pylint issue"),
            "severity": SEVERITY_BY_PYLINT_TYPE.get(item.get("type"), "low"),
            "source": "static",
            "tool": "pylint",
            "code": item.get("symbol") or item.get("message-id"),
            "confidence": None,
            "status": "open",
        })

    bandit_results = run_bandit(filepath)
    for item in bandit_results.get("results", []):
        findings.append({
            "id": uuid.uuid4().hex,
            "file": rel_path,
            "line": item.get("line_number"),
            "description": item.get("issue_text", "security issue"),
            "severity": BANDIT_SEVERITY_MAP.get(item.get("issue_severity"), "medium"),
            "source": "security",
            "tool": "bandit",
            "code": item.get("test_id"),
            "confidence": None,
            "status": "open",
        })

    return findings


def analyze_project(python_files: list[Path], base_dir: Path) -> list[dict]:
    """Run static + security analysis across every Python file in the project."""
    all_findings = []
    for filepath in python_files:
        rel_path = str(filepath.relative_to(base_dir))
        all_findings.extend(analyze_file(filepath, rel_path))
    return all_findings
