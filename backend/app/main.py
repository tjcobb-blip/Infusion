from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import auth, cases, documents, tasks, schedule, financial, pharmacy

app = FastAPI(
    title="Infusion Referral Orchestration Platform",
    version="1.0.0",
    description="Unified referral orchestration platform for infusion therapy",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
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
