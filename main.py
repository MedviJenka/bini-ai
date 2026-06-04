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


@mcp.tool(name='Vision')
def vision(prompt: str, image: str, sample_image: Optional[list[str]] = None) -> dict:
    """
    [Vision MCP]
    Analyze an image using the Bini vision agent.
    image: base64-encoded image bytes (any common format: PNG, JPEG, WebP, etc.)
    sample_image: optional list of base64-encoded comparison image bytes
    """
    tmp = _b64_to_tempfile(image)
    tmp_samples = [_b64_to_tempfile(s) for s in sample_image] if sample_image else None
    try:
        return vision_agent(prompt=prompt, image_path=tmp, sample_image=tmp_samples)
    finally:
        os.unlink(tmp)
        for s in (tmp_samples or []):
            os.unlink(s)
