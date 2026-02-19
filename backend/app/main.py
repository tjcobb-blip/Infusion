import pathlib

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles

from app.api import auth, cases, documents, tasks, schedule, financial, pharmacy, organizations

app = FastAPI(
    title="Infusion Referral Orchestration Platform",
    version="1.0.0",
    description="Unified referral orchestration platform for infusion therapy",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    return {"status": "ok"}


app.include_router(auth.router)
app.include_router(cases.router)
app.include_router(documents.router)
app.include_router(tasks.router)
app.include_router(schedule.router)
app.include_router(financial.router)
app.include_router(pharmacy.router)
app.include_router(organizations.router)

# --- Serve frontend static files ---
FRONTEND_DIST = pathlib.Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"

if FRONTEND_DIST.exists():
    app.mount("/assets", StaticFiles(directory=FRONTEND_DIST / "assets"), name="static")

    @app.get("/{full_path:path}")
    async def serve_frontend(request: Request, full_path: str):
        """Serve the React SPA for any non-API route."""
        file_path = FRONTEND_DIST / full_path
        if file_path.is_file():
            return FileResponse(file_path)
        return FileResponse(FRONTEND_DIST / "index.html")
