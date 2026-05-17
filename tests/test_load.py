import json
import os
import aiohttp
import pytest
import asyncio
from pathlib import Path
from typing import Any, Dict
from backend.paths import ImagePaths
from backend.settings import Config, TestConfig


DEFAULT_BASE_URL = f"http://10.8.2.35:{Config.PORT}/api/{Config.API_VERSION}/bini"
TARGET_URL = os.getenv("LOAD_TEST_URL", f"{DEFAULT_BASE_URL}/text")
PROMPT = os.getenv("LOAD_TEST_PROMPT", "Load test request")
SCHEMA_OUTPUT = os.getenv("LOAD_TEST_SCHEMA_OUTPUT")
IMAGE_PATH = os.getenv("LOAD_TEST_IMAGE_PATH", ImagePaths.MAIN_IMAGE)
SAMPLE_IMAGE_PATH = os.getenv("LOAD_TEST_SAMPLE_IMAGE_PATH", ImagePaths.SAMPLE_IMAGE)


def parse_schema(raw_value: str | None) -> Any:
    if not raw_value:
        return None

    try:
        return json.loads(raw_value)
    except json.JSONDecodeError:
        return raw_value


IS_IMAGE_ENDPOINT = TARGET_URL.rstrip("/").endswith("/image")
TEXT_PAYLOAD: Dict[str, Any] = {
    "prompt": PROMPT,
    "schema_output": parse_schema(SCHEMA_OUTPUT),
}

MAIN_IMAGE_BYTES = (
    Path(IMAGE_PATH).read_bytes() if IS_IMAGE_ENDPOINT and IMAGE_PATH else None
)
SAMPLE_IMAGE_BYTES = (
    Path(SAMPLE_IMAGE_PATH).read_bytes()
    if IS_IMAGE_ENDPOINT and SAMPLE_IMAGE_PATH
    else None
)


def build_image_form_data() -> aiohttp.FormData:
    if MAIN_IMAGE_BYTES is None:
        raise RuntimeError("Image endpoint selected but no image bytes loaded.")

    form = aiohttp.FormData()
    form.add_field("prompt", PROMPT)
    form.add_field("image", MAIN_IMAGE_BYTES, filename=os.path.basename(IMAGE_PATH))

    if SAMPLE_IMAGE_BYTES:
        form.add_field(
            "sample_images",
            SAMPLE_IMAGE_BYTES,
            filename=os.path.basename(SAMPLE_IMAGE_PATH),
        )

    if SCHEMA_OUTPUT:
        form.add_field("schema_output", SCHEMA_OUTPUT)

    return form


async def call_api(session: aiohttp.ClientSession) -> str:
    request_kwargs: Dict[str, Any]
    if IS_IMAGE_ENDPOINT:
        request_kwargs = {"data": build_image_form_data()}
    else:
        request_kwargs = {"json": TEXT_PAYLOAD}

    async with session.post(TARGET_URL, **request_kwargs) as resp:
        resp.raise_for_status()
        return await resp.text()


async def run_request(session: aiohttp.ClientSession, semaphore: asyncio.Semaphore):
    async with semaphore:
        return await call_api(session)


@pytest.mark.asyncio
async def test_api_load() -> None:

    concurrency = min(TestConfig.MAX_CONCURRENCY, TestConfig.TOTAL_REQUESTS)
    semaphore = asyncio.Semaphore(concurrency)

    async with aiohttp.ClientSession() as session:
        tasks = [
            asyncio.create_task(run_request(session, semaphore))
            for _ in range(TestConfig.TOTAL_REQUESTS)
        ]
        responses = await asyncio.gather(*tasks)
        print(responses)

    assert len(responses) == TestConfig.TOTAL_REQUESTS
    assert all(responses)
