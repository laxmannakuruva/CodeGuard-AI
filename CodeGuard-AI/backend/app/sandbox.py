"""
Sandbox Execution
Runs a project's test suite in isolation. Docker is the required,
supported isolation mechanism for production use:
  - no network access
  - memory limit
  - wall-clock timeout
  - non-root user inside the container
  - read-only bind mount of the code being tested

If Docker is not installed (e.g. some local dev machines / CI runners),
this module can optionally fall back to a resource-limited subprocess.
That fallback is NOT a real security boundary -- it still runs on the
host -- so it is OFF by default and only used when the operator
explicitly opts in via CODEGUARD_ALLOW_INSECURE_SANDBOX=1. Every result
returned to the API includes an "isolation_mode" field so the frontend
can display exactly which mode ran the code.
"""

import os
import resource
import shutil
import subprocess
from pathlib import Path

IMAGE_NAME = "codeguard-ai-sandbox"
DOCKERFILE_DIR = Path(__file__).resolve().parent.parent
INSECURE_FALLBACK_ENV = "CODEGUARD_ALLOW_INSECURE_SANDBOX"


def docker_available() -> bool:
    return shutil.which("docker") is not None


def _docker_image_exists() -> bool:
    result = subprocess.run(
        ["docker", "image", "inspect", IMAGE_NAME],
        capture_output=True, text=True,
    )
    return result.returncode == 0


def build_sandbox_image() -> dict:
    if not docker_available():
        return {"built": False, "error": "docker not installed"}
    result = subprocess.run(
        ["docker", "build", "-f", str(DOCKERFILE_DIR / "sandbox.Dockerfile"),
         "-t", IMAGE_NAME, str(DOCKERFILE_DIR)],
        capture_output=True, text=True, timeout=300,
    )
    if result.returncode != 0:
        return {"built": False, "error": result.stderr[-2000:]}
    return {"built": True, "error": None}


def _run_in_docker(target_dir: Path, timeout: int) -> dict:
    if not _docker_image_exists():
        build_result = build_sandbox_image()
        if not build_result["built"]:
            return {"exit_code": None, "logs": "", "error": f"sandbox image build failed: {build_result['error']}"}

    try:
        result = subprocess.run(
            [
                "docker", "run", "--rm",
                "--network", "none",
                "--memory", "256m",
                "--memory-swap", "256m",
                "--user", "1000:1000",
                "-v", f"{target_dir}:/app:ro",
                IMAGE_NAME,
            ],
            capture_output=True, text=True, timeout=timeout,
        )
        return {"exit_code": result.returncode, "logs": (result.stdout + result.stderr)[-5000:], "error": None}
    except subprocess.TimeoutExpired:
        return {"exit_code": None, "logs": "", "error": f"sandbox timed out after {timeout}s"}
    except Exception as e:
        return {"exit_code": None, "logs": "", "error": str(e)}


def _limit_resources():
    """Applied via preexec_fn in the insecure fallback -- caps CPU time and memory."""
    resource.setrlimit(resource.RLIMIT_CPU, (20, 20))
    resource.setrlimit(resource.RLIMIT_AS, (512 * 1024 * 1024, 512 * 1024 * 1024))


def _run_restricted_subprocess(target_dir: Path, timeout: int) -> dict:
    """
    INSECURE fallback: runs pytest directly on the host with CPU/memory
    limits, no network isolation, no filesystem isolation beyond the
    copied working directory. Only runs if explicitly opted into.
    """
    try:
        result = subprocess.run(
            ["python3", "-m", "pytest", "--tb=short", "-q", "."],
            cwd=str(target_dir),
            capture_output=True, text=True, timeout=timeout,
            preexec_fn=_limit_resources,
        )
        return {"exit_code": result.returncode, "logs": (result.stdout + result.stderr)[-5000:], "error": None}
    except subprocess.TimeoutExpired:
        return {"exit_code": None, "logs": "", "error": f"execution timed out after {timeout}s"}
    except Exception as e:
        return {"exit_code": None, "logs": "", "error": str(e)}


def run_tests(target_dir: Path, timeout: int = 30) -> dict:
    """
    Run the project's test suite against target_dir.
    Returns: {exit_code, logs, error, isolation_mode}
    """
    if docker_available():
        result = _run_in_docker(target_dir, timeout)
        result["isolation_mode"] = "docker"
        return result

    if os.environ.get(INSECURE_FALLBACK_ENV) == "1":
        result = _run_restricted_subprocess(target_dir, timeout)
        result["isolation_mode"] = "restricted-subprocess (INSECURE - install Docker for real isolation)"
        return result

    return {
        "exit_code": None,
        "logs": "",
        "error": "Docker is not installed and the insecure fallback is disabled. "
                 f"Install Docker, or set {INSECURE_FALLBACK_ENV}=1 for local dev only.",
        "isolation_mode": "none",
    }
