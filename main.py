from typing import Optional
from fastmcp import FastMCP
from backend.utils.logger import Logger
from backend.ai.agents.vision_agent.crew import vision_agent


log = Logger(name='logfire-mcp')

mcp = FastMCP(name="Bini Vision")


@mcp.tool(name='Vision')
def vision(prompt: str, image: str, sample_image: Optional[list[str]] = None) -> dict:
    """
    [Vision MCP]
    Analyze an image using the Bini vision agent.
    image_data: base64-encoded image bytes (any common format: PNG, JPEG, WebP, etc.)
    sample_images: optional list of base64-encoded comparison image bytes
    """
    image_uri = f"data:image/jpeg;base64,{image}"
    sample_uris = [f"data:image/jpeg;base64,{s}" for s in sample_image] if sample_image else None
    return vision_agent(prompt=prompt, image_path=image_uri, sample_image=sample_uris)


if __name__ == '__main__':
    mcp.run(transport='streamable-http', host='0.0.0.0', port=6000)
