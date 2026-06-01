from typing import Optional
from fastmcp import FastMCP
from backend.ai.agents.vision_agent.crew import vision_agent


mcp = FastMCP('vision-mcp')


@mcp.tool()
def vision_mcp(prompt: str, image: str, sample_image: Optional[str] = None) -> dict:
    return vision_agent(prompt=prompt, image=image, sample_image=sample_image)
