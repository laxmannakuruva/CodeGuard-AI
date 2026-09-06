"""
Workspace Management
Handles safe extraction of uploaded ZIP files into per-workspace temp
directories, and an in-memory store tracking each workspace's state
(findings, fix attempts, working directory).

Security notes:
- Extraction guards against zip-slip (path traversal via ../../ entries).
- Enforces a max file count and max total uncompressed size to avoid
  zip-bomb style resource exhaustion.
- Uploaded code is NEVER imported/executed by this process directly;
  only inspected via AST-based static tools or run inside the sandbox.
"""

import os
import shutil
import uuid
import zipfile
from dataclasses import dataclass, field
from pathlib import Path

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent / "workspaces"
WORKSPACE_ROOT.mkdir(exist_ok=True)

MAX_FILES = 2000
MAX_TOTAL_UNCOMPRESSED_BYTES = 200 * 1024 * 1024  # 200MB
IGNORE_DIRS = {".git", "venv", ".venv", "__pycache__", "node_modules", ".mypy_cache"}


class ZipSecurityError(Exception):
    pass


@dataclass
class FixAttempt:
    finding_id: str
    file: str
    original_code: str
    fixed_code: str
    diff: str
    explanation: str
    status: str = "proposed"  # proposed | fix_verified | fix_failed
    result: dict = field(default_factory=dict)


@dataclass
class Workspace:
    id: str
    original_dir: Path
    working_dir: Path
    findings: dict = field(default_factory=dict)   # finding_id -> Finding-like dict
    fixes: dict = field(default_factory=dict)        # finding_id -> FixAttempt
    baseline_tests: dict = field(default_factory=dict)  # cached baseline sandbox run
    ai_analyzed: bool = False


_WORKSPACES: dict[str, Workspace] = {}


def _safe_extract(zip_path: Path, dest_dir: Path) -> int:
    """Extract a zip file safely, guarding against zip-slip. Returns file count."""
    file_count = 0
    total_size = 0

    with zipfile.ZipFile(zip_path) as zf:
        members = zf.infolist()
        if len(members) > MAX_FILES:
            raise ZipSecurityError(f"ZIP contains too many files ({len(members)} > {MAX_FILES})")

        for member in members:
            total_size += member.file_size
            if total_size > MAX_TOTAL_UNCOMPRESSED_BYTES:
                raise ZipSecurityError("ZIP uncompressed size exceeds limit")

            member_path = Path(member.filename)
            if member_path.is_absolute() or ".." in member_path.parts:
                raise ZipSecurityError(f"Unsafe path in ZIP: {member.filename}")

            target_path = dest_dir / member_path
            resolved = target_path.resolve()
            if not str(resolved).startswith(str(dest_dir.resolve())):
                raise ZipSecurityError(f"Zip-slip attempt detected: {member.filename}")

        zf.extractall(dest_dir)
        file_count = sum(1 for m in members if not m.is_dir())

    return file_count


def create_workspace_from_zip(zip_path: Path) -> tuple[Workspace, int]:
    """Create a new workspace by safely extracting a ZIP into it."""
    workspace_id = uuid.uuid4().hex
    base_dir = WORKSPACE_ROOT / workspace_id
    original_dir = base_dir / "original"
    working_dir = base_dir / "working"
    original_dir.mkdir(parents=True)

    file_count = _safe_extract(zip_path, original_dir)

    # working_dir starts as a copy of original; verified fixes get merged here
    shutil.copytree(original_dir, working_dir)

    ws = Workspace(id=workspace_id, original_dir=original_dir, working_dir=working_dir)
    _WORKSPACES[workspace_id] = ws
    return ws, file_count


def get_workspace(workspace_id: str) -> Workspace:
    ws = _WORKSPACES.get(workspace_id)
    if ws is None:
        raise KeyError(f"workspace not found: {workspace_id}")
    return ws


def get_python_files(directory: Path) -> list[Path]:
    py_files = []
    for root, dirs, files in os.walk(directory):
        dirs[:] = [d for d in dirs if d not in IGNORE_DIRS]
        for f in files:
            if f.endswith(".py"):
                py_files.append(Path(root) / f)
    return py_files


def get_test_files(directory: Path) -> list[Path]:
    return [
        p for p in get_python_files(directory)
        if p.name.startswith("test_") or p.name.endswith("_test.py")
    ]
