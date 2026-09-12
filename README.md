# WinFix Agent

Safe, local-first Windows diagnostics and remediation planning for a hackathon MVP.

See [architecture](docs/ARCHITECTURE.md), [API contract](docs/API_CONTRACT.md), and [safety model](docs/SAFETY_MODEL.md). The first working slice is performance diagnosis: create a session, run a read-only performance investigation, review structured evidence and a plan, then stop for approval.

## Local development

Backend:

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate  # Windows PowerShell: .venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload --port 9000
```

Frontend:

```bash
cd frontend
npm install
npm run dev
```

Configure `WINFIX_MODEL=qwen3:8b` (or `qwen3:4b`) and `OLLAMA_BASE_URL` when Ollama is available. Install the Pi sidecar once with `cd backend/pi_runtime && npm install --ignore-scripts`; it exposes only WinFix diagnostic tools, never Pi's coding or shell tools. Without Ollama, the backend uses its deterministic structured fallback for reliable development.
