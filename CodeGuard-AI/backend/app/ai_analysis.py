"""
AI Analysis & Fix Generation
Wraps the Anthropic API for two jobs:
  1. Detecting additional likely bugs beyond what static tools catch.
  2. Generating a full corrected version of a file for a specific finding.

Both functions require ANTHROPIC_API_KEY to be set. Callers must check
`ai_available()` first and degrade gracefully (static analysis alone
still works with zero API key).
"""

import json
import os
import uuid

MODEL = "claude-sonnet-4-5"

_client = None


def ai_available() -> bool:
    return bool(os.environ.get("ANTHROPIC_API_KEY"))


def _get_client():
    global _client
    if _client is None:
        from anthropic import Anthropic
        _client = Anthropic()
    return _client


BUG_DETECTION_SYSTEM_PROMPT = """You are a meticulous code reviewer specializing in finding real,
reproducible bugs (not style nits -- those are already covered by static tools).
You will be given a Python file's source code and existing static analysis findings.

Respond with ONLY valid JSON (no markdown fences, no preamble): a list of objects,
each with keys: "line" (int), "description" (string), "severity" ("low"|"medium"|"high"),
"confidence" (float 0-1). Do not repeat issues already listed in the static findings.
If you find no additional likely bugs, return an empty list: []
"""


def detect_bugs(file_source: str, rel_path: str, existing_findings: list[dict]) -> list[dict]:
    """Ask Claude for additional bugs beyond what static tools found. Returns Finding-shaped dicts."""
    client = _get_client()

    existing_summary = [
        {"line": f.get("line"), "description": f.get("description"), "tool": f.get("tool")}
        for f in existing_findings if f.get("file") == rel_path
    ]

    prompt = f"""File: {rel_path}

Existing static findings for this file (do not repeat these):
{json.dumps(existing_summary, indent=2)[:2000]}

Source code:
{file_source[:6000]}
"""
    response = client.messages.create(
        model=MODEL,
        max_tokens=1200,
        system=BUG_DETECTION_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}],
    )
    text = response.content[0].text.strip()
    text = text.removeprefix("```json").removeprefix("```").removesuffix("```").strip()

    try:
        raw_bugs = json.loads(text)
    except json.JSONDecodeError:
        return []

    findings = []
    for bug in raw_bugs:
        if not isinstance(bug, dict) or "description" not in bug:
            continue
        findings.append({
            "id": uuid.uuid4().hex,
            "file": rel_path,
            "line": bug.get("line"),
            "description": bug.get("description"),
            "severity": bug.get("severity", "medium"),
            "source": "ai",
            "tool": "claude",
            "code": None,
            "confidence": bug.get("confidence"),
            "status": "open",
        })
    return findings


FIX_SYSTEM_PROMPT = """You are a senior engineer fixing one specific, well-defined bug in a
Python file. You will be given the full current source of the file and a description of
the bug to fix (with a line number).

Respond with ONLY valid JSON (no markdown fences, no preamble) with exactly these keys:
{
  "fixed_code": "<the ENTIRE corrected file content, as a single string>",
  "explanation": "<1-3 sentences explaining what was wrong and what you changed>"
}

Rules:
- Make the MINIMAL change needed to fix this specific issue. Do not refactor unrelated code.
- Preserve all other existing behavior, formatting, comments, and unrelated code exactly.
- "fixed_code" must be the complete file, not a diff or snippet.
"""


def generate_fix(file_source: str, rel_path: str, finding: dict) -> dict:
    """Generate a full corrected file for one finding. Returns {"fixed_code", "explanation"}."""
    client = _get_client()

    prompt = f"""File: {rel_path}

Current source:
{file_source[:8000]}

Bug to fix:
- Line: {finding.get('line')}
- Description: {finding.get('description')}
- Severity: {finding.get('severity')}
- Detected by: {finding.get('tool')}
"""
    response = client.messages.create(
        model=MODEL,
        max_tokens=4000,
        system=FIX_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}],
    )
    text = response.content[0].text.strip()
    text = text.removeprefix("```json").removeprefix("```").removesuffix("```").strip()

    try:
        result = json.loads(text)
    except json.JSONDecodeError:
        raise ValueError("AI did not return valid JSON for fix generation")

    if "fixed_code" not in result:
        raise ValueError("AI response missing 'fixed_code'")

    return {
        "fixed_code": result["fixed_code"],
        "explanation": result.get("explanation", ""),
    }
