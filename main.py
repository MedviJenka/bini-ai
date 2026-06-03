import base64
import os
import tempfile
from typing import Optional
from fastmcp import FastMCP
from backend.utils.logger import Logger
from backend.ai.agents.vision_agent.crew import vision_agent


log = Logger(name='logfire-mcp')

mcp = FastMCP(name="Bini Vision")


def _b64_to_tempfile(b64: str, suffix: str = ".jpg") -> str:
    data = base64.b64decode(b64)
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as f:
        f.write(data)
        return f.name


@mcp.tool(name='Vision')
def vision(prompt: str, image: str, sample_images: Optional[list[str]] = None) -> dict:

    """Analyze an image using the Bini vision agent.[Vision MCP]"""

    temp_files: list[str] = []

    try:
        image_path = _b64_to_tempfile(image)
        temp_files.append(image_path)
        sample_paths: list[str] | None = None

        if sample_images:
            sample_paths = [_b64_to_tempfile(s) for s in sample_images]
            temp_files.extend(sample_paths)

        return vision_agent(prompt=prompt, image_path=image_path, sample_image=sample_paths)

    finally:
        for p in temp_files:
            try:
                os.unlink(p)
            except OSError:
                pass

if __name__ == '__main__':
    import asyncio
    mcp.run_async(transport='sse')
