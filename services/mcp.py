import base64
import os
import tempfile
from typing import Optional
from fastmcp import FastMCP
from backend.utils.logger import Logger
from backend.ai.agents.vision_agent.crew import vision_agent
from fastmcp.apps.file_upload import FileUpload


log = Logger(name='logfire-mcp')

mcp = FastMCP(name="Bini Vision")

file = FileUpload(max_file_size=3000)

mcp.add_provider(file)


def _b64_to_tempfile(b64: str) -> str:
    """Decode a base64 image to a temp file and return its path."""
    raw = base64.b64decode(b64)
    fd, path = tempfile.mkstemp(suffix=".jpg")
    os.write(fd, raw)
    os.close(fd)
    return path

def _run_vision(prompt: str, image_b64: str, sample_image: Optional[list[str]] = None) -> dict:
    tmp = _b64_to_tempfile(image_b64)
    tmp_samples = [_b64_to_tempfile(s) for s in sample_image] if sample_image else None
    try:
        return vision_agent(prompt=prompt, image_path=tmp, sample_image=tmp_samples)
    finally:
        os.unlink(tmp)
        for s in (tmp_samples or []):
            os.unlink(s)


@mcp.tool(name='Vision')
def vision_mcp(prompt: str, image: str, sample_image: Optional[list[str]] = None) -> dict:
    """
    Analyze an image using the Bini vision agent.
    image: base64-encoded image bytes (any common format: PNG, JPEG, WebP, etc.)
    sample_image: optional list of base64-encoded comparison image bytes
    """
    return _run_vision(prompt, image, sample_image)


if __name__ == '__main__':
    mcp.run_async(transport='http', host='0.0.0.0', port=6000)
