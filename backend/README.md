# WinFix Agent Backend

Run locally from this directory:

```bash
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload --port 9000
```

API docs are available at `http://localhost:9000/docs`. Sessions are stored in `backend/data/winfix.db` by default; set `WINFIX_DATABASE_PATH` to override it. The default agent runtime is Pi with `WINFIX_MODEL=qwen3:8b` and `OLLAMA_BASE_URL=http://127.0.0.1:11434`. Install the isolated Pi runtime once with `cd pi_runtime && npm install --ignore-scripts`. Set `WINFIX_AGENT_RUNTIME=direct_ollama` only to use the legacy one-shot adapter during troubleshooting.

## Battery Optimization (Stage 1: Read-Only Battery Diagnostics)

- **Scope**: Stage 1 provides strictly read-only battery & power diagnostics. It collects battery presence, charge %, charging status, power source (AC vs Battery), estimated remaining minutes, battery health estimate (`full_charge_capacity / design_capacity * 100`), power plan, battery saver state, warnings, and limitations.
- **Safety & Platform Abstraction**: Queries live systems via `ctypes.windll.kernel32.GetSystemPowerStatus`, `psutil.sensors_battery()`, and safe WMI read-only queries behind a `BatteryInfoProvider` protocol. Automatically uses `NonWindowsBatteryProvider` on Linux/macOS. No power plans, registry keys, CPU states, or system settings are modified. Stage 1 generates zero mutating actions.

