import asyncio
from fastmcp import Client
from typing import Optional, Union


async def call_vision_mcp(prompt: str, image_path: str, sample_images: Optional[Union[str, list]] = None):
    async with Client("http://localhost:6000/mcp") as client:
        result = await client.call_tool("Vision", {'prompt': prompt, 'image_path': image_path, 'sample_images': sample_images})
        print(result)


if __name__ == '__main__':
    asyncio.run(call_vision_mcp(prompt="is playwright displayed", image_path=r"C:\Users\medvi\OneDrive\Desktop\bini-ai\data\images\main.png"))
