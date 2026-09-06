# CodeGuard AI

Upload a Python project as a ZIP. CodeGuard AI runs static and security
analysis immediately (no API key needed), optionally layers on AI-powered
bug detection and fix generation (requires an Anthropic API key), and
verifies every proposed fix inside an isolated sandbox before it's
accepted.

## Architecture

```
React frontend  ⇄  FastAPI backend  ⇄  pylint / bandit (always available)
                                     ⇄  Claude (optional, needs API key)
                                     ⇄  Docker sandbox (test execution)
```

## User flow

```
Upload ZIP
   → Analyze Project (static + security, instant, no API key)
   → Show findings
   → Select a finding
   → Generate AI fix (needs API key)
   → Show original vs fixed code (diff)
   → User approves
   → Apply patch in an isolated temp workspace
   → Run tests in Docker sandbox
   → Verify fix (compile check + tests + static re-check)
   → Show Fixed / Failed
   → Final dashboard/report
```

## Setup

### Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Optional: enables AI bug detection + AI fix generation
export ANTHROPIC_API_KEY=your_key_here

uvicorn app.main:app --reload --port 8000
```

Without `ANTHROPIC_API_KEY` set, the app still fully works for static +
security analysis — the AI-only endpoints return a clear 400 explaining
why, instead of failing unpredictably.

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Open the printed local URL (defaults to `http://localhost:5173`). The
frontend talks to the backend at `http://localhost:8000` by default
(see `frontend/.env`, `VITE_API_URL`).

### Docker (required for real sandbox isolation)

```bash
# Docker must be installed and running for the sandbox to isolate test execution.
docker --version
```

If Docker isn't installed, `/apply-fix` will refuse to run tests by
default rather than silently executing uploaded code on the host. For
local development *only*, you can opt into a resource-limited (but NOT
fully isolated) fallback:

```bash
export CODEGUARD_ALLOW_INSECURE_SANDBOX=1
```

Every API response includes an `isolation_mode` field so you always
know exactly how test code was executed. **Never enable the insecure
fallback in production.**

## API endpoints

| Method | Path | Requires API key | Description |
|---|---|---|---|
| GET | `/health` | no | Service status + AI/Docker availability |
| POST | `/analyze` | no | Upload ZIP → static + security analysis |
| POST | `/analyze-project/{workspace_id}` | yes | AI bug detection on top of static findings |
| GET | `/findings/{workspace_id}` | no | List current findings |
| POST | `/generate-fix/{workspace_id}/{finding_id}` | yes | AI proposes a fix (original vs fixed) |
| POST | `/apply-fix/{workspace_id}/{finding_id}` | no | Apply approved fix, run sandbox, verify |
| GET | `/report/{workspace_id}` | no | Aggregate dashboard data (all real, no fake stats) |
| GET | `/download/{workspace_id}` | no | Download ZIP with verified fixes merged in |

## Safety

- Uploaded code is **never executed directly** by the backend process.
  Static analysis (pylint, bandit) is AST-based and doesn't run your code.
- Only `pytest` execution touches actual code, and that only happens
  inside the Docker sandbox: no network, memory-capped, non-root user,
  read-only mount, wall-clock timeout.
- ZIP extraction is guarded against zip-slip (path traversal) and has
  file-count / size limits.
- Fixes are applied to a disposable candidate directory first; they're
  only merged into the downloadable working copy after verification
  passes.

## What's real vs. simulated

- All dashboard numbers in `/report` are computed directly from stored
  findings and fix attempts for that workspace — nothing is hardcoded
  or randomly generated.
- Static/security analysis (pylint, bandit) always runs for real.
- AI analysis and AI fix generation call the real Anthropic API and
  require a real `ANTHROPIC_API_KEY` — there is no mocked/demo mode in
  the shipped code (mocking was only used in this project's own test
  suite, to validate the pipeline without burning API calls).

## Project structure

```
CodeGuard-AI/
├── backend/
│   ├── app/
│   │   ├── main.py            FastAPI app, all endpoints
│   │   ├── workspace.py        Safe ZIP extraction, workspace store
│   │   ├── static_analysis.py  pylint + bandit (no API key needed)
│   │   ├── ai_analysis.py      Claude bug detection + fix generation
│   │   ├── sandbox.py           Docker sandbox (+ labeled dev fallback)
│   │   ├── verifier.py          Multi-signal fix verification
│   │   └── models.py            Pydantic schemas
│   ├── sandbox.Dockerfile
│   ├── sandbox_entrypoint.sh
│   └── requirements.txt
└── frontend/
    ├── src/
    │   ├── App.jsx               Orchestrates the full flow
    │   ├── api.js                 Backend API client
    │   └── components/
    │       ├── Stepper.jsx        Pipeline progress indicator
    │       ├── UploadZone.jsx     ZIP upload (drag/drop)
    │       ├── FindingsList.jsx   Findings summary + list
    │       ├── FixPanel.jsx        Generate/approve fix, diff, result
    │       ├── DiffView.jsx        Unified diff renderer
    │       ├── Report.jsx          Final dashboard
    │       └── Badge.jsx           Severity/source/status tags
    └── .env                        VITE_API_URL
```
