import uvicorn
import base64
from typing import Optional
from fastapi import FastAPI, File, UploadFile
from backend.utils.logger import Logger
from services.mcp import _run_vision
from backend.settings import Config


log = Logger(name='logfire-mcp')

app = FastAPI()


@app.post(f"/api/{Config.API_VERSION}/upload")
async def vision_http(prompt: str, image: UploadFile = File(...), sample_image: Optional[list[str]] = None) -> dict:
    b64 = base64.b64encode(await image.read()).decode()
    return _run_vision(prompt, b64, sample_image)


if __name__ == '__main__':
    uvicorn.run(app, host="0.0.0.0", port=7000)