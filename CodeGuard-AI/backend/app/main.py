"""
CodeGuard AI - FastAPI Backend

Endpoints:
  POST /analyze                              upload ZIP, run static+security analysis (no API key needed)
  POST /analyze-project/{workspace_id}        run AI bug detection on top of static findings (needs API key)
  GET  /findings/{workspace_id}                list current findings
  POST /generate-fix/{workspace_id}/{finding_id}   AI generates a fix proposal (needs API key)
  POST /apply-fix/{workspace_id}/{finding_id}      user approves -> apply + sandbox test + verify
  GET  /report/{workspace_id}                  final dashboard/report (real data only, no fake stats)
  GET  /download/{workspace_id}                download ZIP of working dir with verified fixes merged in
  GET  /health                                  service + capability status
"""

import difflib
import shutil
import tempfile
import uuid
import zipfile
from pathlib import Path

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from . import ai_analysis, static_analysis, verifier
from .models import AnalyzeResponse, Finding, FixProposal, ApplyFixResult, ReportResponse
from .sandbox import docker_available
from .workspace import (
    Workspace, FixAttempt, create_workspace_from_zip, get_workspace,
    get_python_files, ZipSecurityError,
)

app = FastAPI(title="CodeGuard AI", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # demo/dev setting; restrict to known origins in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    return {
        "status": "ok",
        "ai_available": ai_analysis.ai_available(),
        "docker_available": docker_available(),
    }


@app.post("/analyze", response_model=AnalyzeResponse)
async def analyze(file: UploadFile = File(...)):
    """Upload a ZIP and run static + security analysis. No API key required."""
    if not file.filename.endswith(".zip"):
        raise HTTPException(400, "Only .zip files are accepted")

    with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as tmp:
        tmp.write(await file.read())
        tmp_path = Path(tmp.name)

    try:
        ws, file_count = create_workspace_from_zip(tmp_path)
    except ZipSecurityError as e:
        raise HTTPException(400, f"Rejected ZIP: {e}")
    except zipfile.BadZipFile:
        raise HTTPException(400, "Not a valid ZIP file")
    finally:
        tmp_path.unlink(missing_ok=True)

    py_files = get_python_files(ws.working_dir)
    raw_findings = static_analysis.analyze_project(py_files, ws.working_dir)

    for f in raw_findings:
        ws.findings[f["id"]] = f

    return AnalyzeResponse(
        workspace_id=ws.id,
        file_count=file_count,
        python_file_count=len(py_files),
        findings=[Finding(**f) for f in ws.findings.values()],
        ai_available=ai_analysis.ai_available(),
    )


@app.post("/analyze-project/{workspace_id}", response_model=AnalyzeResponse)
def analyze_project(workspace_id: str):
    """Run AI bug detection on top of existing static findings. Requires ANTHROPIC_API_KEY."""
    if not ai_analysis.ai_available():
        raise HTTPException(
            400,
            "AI analysis unavailable: ANTHROPIC_API_KEY is not set on the server. "
            "Static analysis results above are still valid and usable without it.",
        )

    try:
        ws = get_workspace(workspace_id)
    except KeyError:
        raise HTTPException(404, "workspace not found")

    py_files = get_python_files(ws.working_dir)
    existing = list(ws.findings.values())

    for filepath in py_files:
        rel_path = str(filepath.relative_to(ws.working_dir))
        try:
            source = filepath.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        ai_findings = ai_analysis.detect_bugs(source, rel_path, existing)
        for f in ai_findings:
            ws.findings[f["id"]] = f

    ws.ai_analyzed = True

    return AnalyzeResponse(
        workspace_id=ws.id,
        file_count=len(list(ws.working_dir.rglob("*"))),
        python_file_count=len(py_files),
        findings=[Finding(**f) for f in ws.findings.values()],
        ai_available=True,
    )


@app.get("/findings/{workspace_id}")
def list_findings(workspace_id: str):
    try:
        ws = get_workspace(workspace_id)
    except KeyError:
        raise HTTPException(404, "workspace not found")
    return {"workspace_id": workspace_id, "findings": list(ws.findings.values())}


@app.post("/generate-fix/{workspace_id}/{finding_id}", response_model=FixProposal)
def generate_fix(workspace_id: str, finding_id: str):
    """Ask Claude to propose a fix for one specific finding. Requires ANTHROPIC_API_KEY."""
    if not ai_analysis.ai_available():
        raise HTTPException(400, "AI fix generation unavailable: ANTHROPIC_API_KEY is not set on the server.")

    try:
        ws = get_workspace(workspace_id)
    except KeyError:
        raise HTTPException(404, "workspace not found")

    finding = ws.findings.get(finding_id)
    if finding is None:
        raise HTTPException(404, "finding not found")

    file_path = ws.working_dir / finding["file"]
    if not file_path.exists():
        raise HTTPException(404, f"file not found in workspace: {finding['file']}")

    original_code = file_path.read_text(encoding="utf-8")

    try:
        result = ai_analysis.generate_fix(original_code, finding["file"], finding)
    except ValueError as e:
        raise HTTPException(502, f"AI fix generation failed: {e}")

    fixed_code = result["fixed_code"]
    diff = "\n".join(difflib.unified_diff(
        original_code.splitlines(), fixed_code.splitlines(),
        fromfile=f"a/{finding['file']}", tofile=f"b/{finding['file']}",
        lineterm="",
    ))

    fix_attempt = FixAttempt(
        finding_id=finding_id, file=finding["file"],
        original_code=original_code, fixed_code=fixed_code,
        diff=diff, explanation=result["explanation"], status="proposed",
    )
    ws.fixes[finding_id] = fix_attempt
    finding["status"] = "fix_proposed"

    return FixProposal(
        finding_id=finding_id, file=finding["file"],
        original_code=original_code, fixed_code=fixed_code,
        diff=diff, explanation=result["explanation"],
    )


@app.post("/apply-fix/{workspace_id}/{finding_id}", response_model=ApplyFixResult)
def apply_fix(workspace_id: str, finding_id: str):
    """
    User has approved the proposed fix. Applies it in an isolated
    candidate directory (never the original upload), runs the test
    suite in the Docker sandbox, and verifies the result. Only on
    verification success is the fix merged into the workspace's
    working directory (available via /download).
    """
    try:
        ws = get_workspace(workspace_id)
    except KeyError:
        raise HTTPException(404, "workspace not found")

    fix = ws.fixes.get(finding_id)
    if fix is None:
        raise HTTPException(400, "no fix has been generated for this finding yet")

    finding = ws.findings.get(finding_id)

    # Build an isolated candidate directory: full copy of current working dir + this one fix
    candidate_dir = ws.working_dir.parent / f"candidate_{finding_id}"
    if candidate_dir.exists():
        shutil.rmtree(candidate_dir)
    shutil.copytree(ws.working_dir, candidate_dir)

    target_file = candidate_dir / fix.file
    target_file.write_text(fix.fixed_code, encoding="utf-8")

    verification = verifier.verify_fix(candidate_dir, fix.file, finding)

    fix.status = verification["status"]
    fix.result = verification
    finding["status"] = verification["status"]

    if verification["status"] == "fix_verified":
        # merge the fix permanently into the workspace's working directory
        (ws.working_dir / fix.file).write_text(fix.fixed_code, encoding="utf-8")

    shutil.rmtree(candidate_dir, ignore_errors=True)

    return ApplyFixResult(
        finding_id=finding_id,
        status=verification["status"],
        compile_check=verification["compile_check"],
        tests_result=verification["tests_result"],
        static_recheck=verification["static_recheck"],
        isolation_mode=verification["isolation_mode"],
        logs=verification["logs"],
    )


@app.get("/report/{workspace_id}", response_model=ReportResponse)
def report(workspace_id: str):
    """Aggregate real, computed statistics for the workspace. No fabricated numbers."""
    try:
        ws = get_workspace(workspace_id)
    except KeyError:
        raise HTTPException(404, "workspace not found")

    findings = list(ws.findings.values())
    by_severity: dict = {}
    by_status: dict = {}
    by_source: dict = {}

    for f in findings:
        by_severity[f["severity"]] = by_severity.get(f["severity"], 0) + 1
        by_status[f["status"]] = by_status.get(f["status"], 0) + 1
        by_source[f["source"]] = by_source.get(f["source"], 0) + 1

    fixes_verified = sum(1 for fx in ws.fixes.values() if fx.status == "fix_verified")
    fixes_failed = sum(1 for fx in ws.fixes.values() if fx.status == "fix_failed")

    return ReportResponse(
        workspace_id=workspace_id,
        total_findings=len(findings),
        by_severity=by_severity,
        by_status=by_status,
        by_source=by_source,
        files_analyzed=len(get_python_files(ws.working_dir)),
        fixes_verified=fixes_verified,
        fixes_failed=fixes_failed,
        findings=[Finding(**f) for f in findings],
    )


@app.get("/download/{workspace_id}")
def download(workspace_id: str):
    """Download a ZIP of the working directory (original code + any verified fixes merged in)."""
    try:
        ws = get_workspace(workspace_id)
    except KeyError:
        raise HTTPException(404, "workspace not found")

    zip_base = ws.working_dir.parent / f"codeguard_fixed_{workspace_id}"
    zip_path = shutil.make_archive(str(zip_base), "zip", ws.working_dir)
    return FileResponse(zip_path, filename=f"codeguard_fixed_{workspace_id[:8]}.zip",
                         media_type="application/zip")
