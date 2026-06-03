import asyncio
import base64
from pathlib import Path
from typing import Optional, Union
from fastmcp import Client


def encode_image(image_path: Union[str, Path]) -> str:
    image_path = Path(image_path)

    with image_path.open("rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


async def call_vision_mcp(
    prompt: str,
    image_path: Union[str, Path],
    sample_image: Optional[Union[str, list]] = None,
) -> None:
    image_b64 = encode_image(image_path)

    async with Client("http://localhost:6000/mcp") as client:
        result = await client.call_tool(
            "Vision",
            {
                "prompt": prompt,
                "image": image_b64,
                "sample_image": sample_image,
            },
        )

        print(f"Result type: {type(result)}")
        print(result)


if __name__ == "__main__":
    asyncio.run(
        call_vision_mcp(
            prompt="Is Playwright displayed?",
            image_path=r"C:\Users\medvi\OneDrive\Desktop\bini-ai\data\images\main.png",
        )
    )