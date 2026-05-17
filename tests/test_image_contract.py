import json
import mimetypes
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from pydantic import BaseModel, Field

from backend.ai.agents.vision_agent import crew as vision_crew
from backend.api.v1.bini.logic import json_schema_to_pydantic
from backend.api.v1.bini import api as bini_api
from backend.paths import ImagePaths
from services.bini import app
from tests.data.schemas import OutputSchema, SummaryOutputSchema


class CrewResultStub:
    def __init__(self, raw=None, pydantic=None) -> None:
        self.raw = raw
        self.pydantic = pydantic


class CrewStub:
    def __init__(self, result: CrewResultStub) -> None:
        self.result = result
        self.inputs = None

    def kickoff(self, inputs: dict) -> CrewResultStub:
        self.inputs = inputs
        return self.result


@pytest.fixture
def api_client() -> TestClient:
    with TestClient(app) as client:
        yield client


def _post_image_request(client: TestClient, schema_model=None):
    data = {"prompt": "what is displayed in this image?"}
    if schema_model is not None:
        data["schema_output"] = json.dumps(schema_model.model_json_schema())

    image_path = Path(ImagePaths.MAIN_IMAGE)
    content_type = mimetypes.guess_type(image_path.name)[0] or "application/octet-stream"

    with image_path.open("rb") as image_file:
        return client.post(
            "/api/v1/bini/image",
            data=data,
            files={"image": (image_path.name, image_file, content_type)},
        )


def test_computer_vision_agent_returns_string_without_schema(monkeypatch) -> None:
    def fake_crew(self):
        return CrewStub(CrewResultStub(raw="Passed: terminal screenshot"))

    monkeypatch.setattr(vision_crew.ComputerVisionAgent, "crew", fake_crew)

    result = vision_crew.computer_vision_agent(
        prompt="what is displayed in this image?",
        image_path=ImagePaths.MAIN_IMAGE,
        schema_output=None,
    )

    assert isinstance(result, str)
    assert result == "Passed: terminal screenshot"


def test_computer_vision_agent_returns_schema_keys_only(monkeypatch) -> None:
    payload = {
        "summary": "A terminal screenshot is displayed.",
        "passed_or_failed": "Passed",
        "unexpected": "discard me",
    }
    stub = CrewStub(CrewResultStub(raw=json.dumps(payload)))

    def fake_crew(self):
        return stub

    monkeypatch.setattr(vision_crew.ComputerVisionAgent, "crew", fake_crew)

    result = vision_crew.computer_vision_agent(
        prompt="what is displayed in this image?",
        image_path=ImagePaths.MAIN_IMAGE,
        schema_output=SummaryOutputSchema,
    )

    assert isinstance(result, dict)
    assert set(result) == set(SummaryOutputSchema.model_fields)
    assert result == {
        "summary": "A terminal screenshot is displayed.",
        "passed_or_failed": "Passed",
    }
    assert "Return only a valid JSON object" in stub.inputs["prompt"]


def test_json_schema_to_pydantic_preserves_nullable_fields() -> None:
    class NullableSchema(BaseModel):
        response: str
        meta: str | None = Field(None, description="Optional metadata")

    model = json_schema_to_pydantic(NullableSchema.model_json_schema())
    result = model.model_validate({"response": "ok", "meta": None}).model_dump()

    assert result == {"response": "ok", "meta": None}


def test_image_api_returns_plain_text_without_schema(api_client: TestClient, monkeypatch) -> None:
    async def fake_bini_image(prompt: str, image: str, sample_image=None, schema_output=None) -> str:
        assert schema_output is None
        return "Passed: plain text output"

    monkeypatch.setattr(bini_api, "bini_image", fake_bini_image)

    response = _post_image_request(api_client)

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/plain")
    assert response.text == "Passed: plain text output"


@pytest.mark.parametrize(
    "schema_model, payload",
    [
        (
            SummaryOutputSchema,
            {
                "summary": "A terminal screenshot is displayed.",
                "passed_or_failed": "Passed",
            },
        ),
        (
            OutputSchema,
            {
                "first_image_analysis": "The first image shows a terminal.",
                "second_image_analysis": "The sample image is also a terminal.",
                "confidence_in_precent": 98.5,
                "final_result": "The sample matches the main image.",
                "passed_or_failed": "Passed",
            },
        ),
    ],
)
def test_image_api_returns_json_with_same_schema_keys(api_client: TestClient, monkeypatch, schema_model, payload) -> None:
    async def fake_bini_image(prompt: str, image: str, sample_image=None, schema_output=None) -> dict:
        assert schema_output is not None
        assert set(schema_output.model_fields) == set(schema_model.model_fields)
        return payload

    monkeypatch.setattr(bini_api, "bini_image", fake_bini_image)

    response = _post_image_request(api_client, schema_model=schema_model)

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/json")
    assert isinstance(response.json(), dict)
    assert set(response.json()) == set(schema_model.model_fields)
    assert response.json() == payload