import uvicorn
import base64
from settings import Config
from services.mcp_server import _run_vision
from utils.logger import Logger
from typing import Optional, AsyncGenerator
from contextlib import asynccontextmanager
from fastapi import FastAPI, File, Form, UploadFile, APIRouter


log = Logger(name='logfire-mcp')


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncGenerator:
    log.fire.info(f'{log.name} service started successfully')
    yield
    log.fire.info(f'{log.name} service finished successfully')


router = APIRouter(prefix=f"/api/{Config.API_VERSION}", lifespan=lifespan)


@router.post("/vision")
async def vision_http(
    prompt: str = Form(...),
    image: UploadFile = File(...),
    sample_image: Optional[list[UploadFile]] = None,
) -> dict:
    b64 = base64.b64encode(await image.read()).decode()
    b64_samples = [base64.b64encode(await s.read()).decode() for s in sample_image] if sample_image else None
    return _run_vision(prompt=prompt, image=b64, sample_image=b64_samples)


app = FastAPI(version=Config.API_VERSION, redoc_url='/redoc', docs_url='/docs')

app.include_router(router=router)


if __name__ == '__main__':
    uvicorn.run(app, host="0.0.0.0", port=6001)
