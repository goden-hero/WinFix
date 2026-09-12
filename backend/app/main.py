from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes_actions import router as actions_router
from app.api.routes_diagnosis import router as diagnosis_router
from app.api.routes_sessions import router as sessions_router

app = FastAPI(title="WinFix Agent API", version="0.1.0", description="Safe, structured Windows diagnostics and remediation planning.")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(sessions_router, prefix="/api/v1")
app.include_router(actions_router, prefix="/api/v1")
app.include_router(diagnosis_router, prefix="/api/v1")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "winfix-agent"}
