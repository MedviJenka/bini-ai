import io
import base64
from pathlib import Path
from typing import Optional, Union, Type, List, Any
from dataclasses import dataclass
from PIL import Image
from crewai import LLM
from crewai.tools import BaseTool
from pydantic import BaseModel, Field, field_validator
from backend.utils.logger import Logger


log = Logger(name="BiniVisionTool")

MAX_IMAGE_RESOLUTION = 2048

LLMMessage = dict[str, Any]


# ------------------------------ #
#        Utility Functions       #
# ------------------------------ #

def resolve_path(path: str) -> str:
    """Resolve and validate file path."""
    resolved = Path(path).resolve()
    if not resolved.exists():
        log.fire.error(f"Image file does not exist: {resolved}")
        raise ValueError(f"Image file not found: {resolved}")
    return str(resolved)


def normalize_paths(value: Optional[Union[str, List[str]]]) -> Optional[List[str]]:
    """Normalize optional image paths to list."""
    if value is None:
        return None

    paths = [value] if isinstance(value, str) else value

    for p in paths:
        resolve_path(p)

    return paths


def resize_image(path: str) -> bytes:
    """Resize image safely for vision models."""
    try:
        img = Image.open(path)
    except Exception as e:
        raise ValueError(f"Cannot open image '{path}': {e}") from e

    try:
        # Convert RGBA / P / LA to RGB
        if img.mode in ("RGBA", "LA", "P"):
            img = img.convert("RGB")

        if max(img.size) > MAX_IMAGE_RESOLUTION:
            img.thumbnail((MAX_IMAGE_RESOLUTION, MAX_IMAGE_RESOLUTION), Image.LANCZOS)

        buffer = io.BytesIO()
        img.save(buffer, format="JPEG", quality=95, subsampling=0)
        return buffer.getvalue()
    except Exception as e:
        raise ValueError(f"Failed to process image '{path}': {e}") from e


def encode_image(path: str) -> str:
    """Encode image as base64 data URI. Always JPEG after resize_image()."""
    image_bytes = resize_image(path)
    encoded = base64.b64encode(image_bytes).decode("utf-8")
    return f"data:image/jpeg;base64,{encoded}"


# ------------------------------ #
#         Pydantic Schema        #
# ------------------------------ #

class ImagePromptSchema(BaseModel):

    image_path:        str                        = Field(...,          description="Primary image path")
    sample_image: Optional[Union[str, List[str]]] = Field(default=None, description="Optional comparison image path(s)")
    prompt:       str                             = Field(...,          description="Prompt describing what to analyze in the image")

    @classmethod
    @field_validator("image")
    def validate_image(cls, v: str) -> str:
        return resolve_path(v)

    @classmethod
    @field_validator("sample_image")
    def validate_sample_images(cls, v):
        return normalize_paths(v)

    def get_all_images(self) -> List[str]:
        """Return all image paths used in the request."""
        images = [self.image_path]

        if self.sample_image:
            images.extend(self.sample_image)

        log.fire.info(f"Vision images used: {images}")

        return images


# ------------------------------ #
#          Tool Runtime          #
# ------------------------------ #

@dataclass
class VisionMessageBuilder:
    """Build LLM vision messages."""

    schema: ImagePromptSchema

    def build(self) -> List[LLMMessage]:
        images = [
            {
                "type": "image_url",
                "image_url": {"url": encode_image(path)},
            }
            for path in self.schema.get_all_images()
        ]

        return [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": self.schema.prompt},
                    *images
                ],
            }
        ]


# ------------------------------ #
#        Vision Tool Class       #
# ------------------------------ #

class BiniVisionTool(BaseTool):

    name: str = "Bini Vision Tool"
    description: str = "Analyzes one or more images using a vision-capable LLM"
    args_schema: Type[BaseModel] = ImagePromptSchema

    def __init__(self, llm: LLM) -> None:
        super().__init__()

        if llm is None:
            raise ValueError("BiniVisionTool requires a valid LLM instance")

        self._llm = llm

    @staticmethod
    def _build_messages(schema: ImagePromptSchema) -> List[LLMMessage]:
        """Construct messages for the vision model."""
        builder = VisionMessageBuilder(schema=schema)
        return builder.build()

    def _run(self, **kwargs: Any) -> str:
        schema = ImagePromptSchema(**kwargs)
        messages = self._build_messages(schema)
        return self._llm.call(messages=messages)
