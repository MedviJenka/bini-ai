import uvicorn
import base64
from backend.settings import Config
from services.mcp import _run_vision
from backend.utils.logger import Logger
from typing import Optional, AsyncGenerator
from contextlib import asynccontextmanager
from fastapi import FastAPI, File, UploadFile


log = Logger(name='logfire-mcp')


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncGenerator:
    log.fire.info(f'{log.name} service started successfully')
    yield
    log.fire.info(f'{log.name} service finished successfully')


app = FastAPI(version=Config.API_VERSION, lifespan=lifespan, redoc_url='/redoc', docs_url='/docs')


@app.post(f"/api/{Config.API_VERSION}/upload")
async def vision_http(prompt: str, image: UploadFile = File(...), sample_image: Optional[list[UploadFile]] = File(...)) -> dict:
    b64 = base64.b64encode(await image.read()).decode()
    return _run_vision(prompt=prompt, image=b64, sample_image=sample_image)


if __name__ == '__main__':
    uvicorn.run(app, host="0.0.0.0", port=7000)