from fastapi import FastAPI, HTTPException, Depends, Security
from fastapi.security.api_key import APIKeyHeader
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import uvicorn

import loads, carriers, calls
from config import settings

API_KEY_HEADER = APIKeyHeader(name="X-API-Key", auto_error=True)


def verify_api_key(api_key: str = Security(API_KEY_HEADER)):
    if api_key != settings.API_KEY:
        raise HTTPException(status_code=403, detail="Invalid API key")
    return api_key


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Starting Carrier Sales API...")
    yield
    print("Shutting down...")


app = FastAPI(
    title="Carrier Sales API",
    description="Inbound carrier load sales automation API for HappyRobot integration",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(
    loads.router,
    prefix="/loads",
    tags=["Loads"],
    dependencies=[Depends(verify_api_key)],
)
app.include_router(
    carriers.router,
    prefix="/carriers",
    tags=["Carriers"],
    dependencies=[Depends(verify_api_key)],
)
app.include_router(
    calls.router,
    prefix="/calls",
    tags=["Calls"],
    dependencies=[Depends(verify_api_key)],
)


@app.get("/health", tags=["Health"])
def health_check():
    return {"status": "ok", "version": "1.0.0"}


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
