import uvicorn
from fastapi import FastAPI, Request
from backend.api.v1.bini import api
from backend.utils.logger import Logfire
from fastapi.middleware.cors import CORSMiddleware
from backend.api.health_schema import HealthResponseSchema
from fastapi.responses import RedirectResponse
from backend.settings import Config
from fastapi.responses import JSONResponse


log = Logfire(name="bini_api_client")

METADATA = {
    "title": f"Bini {Config.ENV} Environment",
    "description": "Computer Vision Agent API for image analysis",
    "version": Config.API_VERSION,
    "lifespan": api.lifespan,
}

app = FastAPI(**METADATA)

app.include_router(api.router)

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=False, allow_methods=["*"], allow_headers=["*"])


@app.exception_handler(Exception)
async def catch_all(_: Request, exc: Exception) -> JSONResponse:
    log.fire.error(f"Unhandled exception: {type(exc).__name__}: {exc}")
    return JSONResponse(status_code=500, content={"detail": "Internal Server Error"})


@app.get("/")
def root() -> RedirectResponse:
    return RedirectResponse("/docs")


@app.get("/health")
def health() -> HealthResponseSchema:
    log.fire.info("Health check endpoint called")
    return HealthResponseSchema(api=Config.API_VERSION, env=Config.ENV)


if __name__ == "__main__":
    uvicorn.run(app='bini:app', host="0.0.0.0", use_colors=True, port=8081, log_level="info", reload=True, workers=4)
