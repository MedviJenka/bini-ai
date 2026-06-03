import base64
import asyncio
from pathlib import Path
from typing import Optional, Union
from fastmcp import Client


def _encode_image(image_path: str) -> str:
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode()


async def call_vision_mcp(prompt: str, image: str, sample_image: Optional[Union[str, list]] = None):

    async with Client("http://localhost:6000/mcp") as client:
        result = await client.call_tool("Vision", {'prompt': prompt, 'image': Path(image), 'sample_image': sample_image})
        print(result)


if __name__ == '__main__':
    asyncio.run(call_vision_mcp(prompt="is playwright displayed", image=r"C:\Users\medvi\OneDrive\Desktop\bini-ai\data\images\main.png"))
