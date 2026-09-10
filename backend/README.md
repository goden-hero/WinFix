# WinFix Agent Backend

Run locally from this directory:

```bash
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

API docs are available at `http://localhost:8000/docs`. Sessions are stored in `backend/data/winfix.db` by default; set `WINFIX_DATABASE_PATH` to override it. The default agent runtime is Pi with `WINFIX_MODEL=qwen3:8b` and `OLLAMA_BASE_URL=http://127.0.0.1:11434`. Install the isolated Pi runtime once with `cd pi_runtime && npm install --ignore-scripts`. Set `WINFIX_AGENT_RUNTIME=direct_ollama` only to use the legacy one-shot adapter during troubleshooting.
