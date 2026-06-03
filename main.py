from typing import Optional
from fastmcp import FastMCP
from backend.utils.logger import Logger
from backend.ai.agents.vision_agent.crew import vision_agent


log = Logger(name='logfire-mcp')

mcp = FastMCP(name="Bini Vision")


@mcp.tool(name='Vision')
def vision(prompt: str, image_path: str, sample_images: Optional[list[str]] = None) -> dict:
    """
    [Vision MCP]
    Analyze an image using the Bini vision agent, this mcp returns detailed information about the image with the correct
    context from the prompt
    """
    return vision_agent(prompt=prompt, image_path=image_path, sample_image=sample_images)

if __name__ == '__main__':
    mcp.run(transport='streamable-http', host='0.0.0.0', port=6000)
