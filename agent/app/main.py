from fastapi import FastAPI
from app.routers.internal import internal_router

app = FastAPI(title="CDM Agent Middleware")
app.include_router(internal_router)

@app.get("/health")
def health_check():
    return {"status": "ok"}
