import base64
import os
import tempfile
from typing import Optional
from fastmcp import FastMCP
from backend.ai.agents.vision_agent.crew import vision_agent
from backend.utils.logger import Logger


log = Logger(name='logfire-mcp')

mcp = FastMCP(name="Bini Vision")


def _b64_to_tempfile(b64: str, suffix: str = ".jpg") -> str:
    data = base64.b64decode(b64)
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as f:
        f.write(data)
        return f.name


@mcp.tool()
def analyze_image(
    prompt: str,
    image_base64: str,
    sample_images_base64: Optional[list[str]] = None,
) -> dict:
    """Analyze an image using the Bini vision agent.

    Args:
        prompt: What to analyze or validate in the image.
        image_base64: Base64-encoded primary image (JPEG/PNG).
        sample_images_base64: Optional base64-encoded reference images for comparison.

    Returns:
        Structured analysis with detected elements, comparison findings, and observations.
    """
    temp_files: list[str] = []
    try:
        image_path = _b64_to_tempfile(image_base64)
        temp_files.append(image_path)

        sample_paths: list[str] | None = None
        if sample_images_base64:
            sample_paths = [_b64_to_tempfile(s) for s in sample_images_base64]
            temp_files.extend(sample_paths)

        return vision_agent(prompt=prompt, image_path=image_path, sample_image=sample_paths)
    finally:
        for p in temp_files:
            try:
                os.unlink(p)
            except OSError:
                pass