import os
import base64
import tempfile
from typing import Optional
from fastmcp import FastMCP
from utils.logger import Logger
from ai.agents.vision_agent.crew import vision_agent
from fastmcp.apps.file_upload import FileUpload


log = Logger(name='logfire-mcp')

mcp = FastMCP(name="Bini Vision")

file = FileUpload(max_file_size=3000)

mcp.add_provider(file)


def _b64_to_temp_file(b64: str) -> str:
    """Decode a base64 image to a temp file and return its path."""
    raw = base64.b64decode(b64)
    fd, path = tempfile.mkstemp(suffix=".jpg")
    os.write(fd, raw)
    os.close(fd)
    return path

def _run_vision(prompt: str, image: str, sample_image: Optional[list[str]] = None) -> dict:
    tmp = _b64_to_temp_file(image)
    tmp_samples = [_b64_to_temp_file(b64=each_sample) for each_sample in sample_image] if sample_image else None
    try:
        log.fire.info(f'running vision: prompt: {prompt}, images provided: {len(image)}')
        return vision_agent(prompt=prompt, image_path=tmp, sample_image=tmp_samples)
    finally:
        os.unlink(tmp)
        for s in (tmp_samples or []):
            os.unlink(s)


@mcp.tool(name='bini-vision')
def vision_mcp(prompt: str, image: str, sample_image: Optional[list[str]] = None) -> dict:
    """
    Analyze an image using the Bini vision agent.
    image: base64-encoded image bytes (any common format: PNG, JPEG, WebP, etc.)
    sample_image: optional list of base64-encoded comparison image bytes

    # ----------------------------------------------------------------------------------- #
    #       claude mcp add bini-vision --transport http http://localhost:6000/mcp         #
    # ----------------------------------------------------------------------------------- #
    """
    return _run_vision(prompt=prompt, image=image, sample_image=sample_image)


if __name__ == '__main__':
    mcp.run_async(transport='streamable-http', host='0.0.0.0', port=6000)
