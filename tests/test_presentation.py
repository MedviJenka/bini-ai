import pytest
import uvicorn
import threading
from time import sleep
from typing import Generator
from pydantic import BaseModel, Field

from backend.paths import ImagePaths
from services.bini import app
from client.bini import BiniClient
from backend.utils.logger import Logfire


log = Logfire('bini-image-local-server-test')


@pytest.fixture(scope="session", autouse=True)
def client() -> Generator:
    """to run parallel: pytest -n auto --dist=loadscope --disable-warnings"""
    config = uvicorn.Config(app=app, workers=16, host="0.0.0.0", port=8081, log_level="critical", lifespan="on")
    uvicorn_server = uvicorn.Server(config)
    thread = threading.Thread(target=uvicorn_server.run, daemon=True)
    thread.start()
    sleep(10)
    bini_client = BiniClient(host="localhost", port=8081)
    yield bini_client
    uvicorn_server.should_exit = True
    thread.join(timeout=5)


class ColorListSchema(BaseModel):
    conclusion:            str       = Field(..., description="Summary conclusion about the colors in the image")
    colors:                list[str] = Field(..., description="List of colors identified in the image.")
    confidence_in_precent: float     = Field(..., description="Confidence level of the color identification in percent.")


class Test:

    @pytest.fixture(autouse=True)
    def setup(self, client: BiniClient) -> None:
        self.client = client

    @pytest.mark.parametrize('prompt, colors, confidence', [('list the colors you see in this page', 2, 90)])
    def test_colors_schema(self, prompt: str, colors: int, confidence: float) -> None:
        response = self.client.run_image(image=ImagePaths.PAUSE_RESUME_MAIN_IMAGE, prompt=prompt, schema_output=ColorListSchema)
        assert len(response.get('colors')) > colors, log.fire.error(f"Expected more than '{colors}' colors in response, got: {response.get('colors')}")
        assert response.get('confidence_in_precent') >= confidence, log.fire.error(f"Expected confidence >= '{confidence}' in response, got: {response.get('confidence_in_precent')}")
        print(response)
        print(type(response))

    @pytest.mark.parametrize('prompt', ['is a blue play button visible on the image?'])
    def test_colors_without_schema(self, prompt: str) -> None:
        response = self.client.run_image(image=ImagePaths.IR_PLAYER, prompt=prompt)
        assert 'Passed' in response
        print(response)
        print(type(response))
