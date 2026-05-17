import pytest
from client.bini import BiniClient
from backend.paths import ImagePaths
from backend.utils.logger import Logfire
from tests.data.schemas import CatResponseSchema, OutputSchema, SummaryOutputSchema, InteractionsRecordingOutputSchema


log = Logfire("bini-image-8081-test")

REPEAT = 1


@pytest.fixture(scope="session")
def client() -> BiniClient:
    return BiniClient(host="10.8.2.35", port=8082)


class TestBiniImageService:

    @pytest.fixture(autouse=True)
    def setup(self, client: BiniClient) -> None:
        self.client = client

    # ------------------------------------------------------------------ #
    #  1. No schema — raw string, must contain "Passed"
    # ------------------------------------------------------------------ #
    @pytest.mark.repeat(REPEAT)
    @pytest.mark.parametrize("prompt, expected", [
        ("what is displayed in this image?", "Passed"),
        ("is this an cmd or powershell?",    "Passed"),
    ])
    def test_image_no_schema_returns_string_with_passed(self, prompt, expected) -> None:
        response = self.client.run_image(prompt=prompt, image=ImagePaths.MAIN_IMAGE)
        assert isinstance(response, str), f"Expected str, got {type(response)}"
        assert expected in response, f"Expected '{expected}' in response, got: {response}"

    # ------------------------------------------------------------------ #
    #  2. Schema provided — must return dict with correct keys
    # ------------------------------------------------------------------ #
    @pytest.mark.repeat(REPEAT)
    def test_image_with_schema_returns_dict(self) -> None:
        response = self.client.run_image(
            prompt="is sample image displayed in the main?",
            image=ImagePaths.MAIN_IMAGE,
            sample_image=[ImagePaths.SAMPLE_IMAGE],
            schema_output=OutputSchema,
        )
        assert isinstance(response, dict), f"Expected dict, got {type(response)}"
        assert "passed_or_failed" in response, f"Key 'passed_or_failed' missing: {response}"
        assert "Failed" in response["passed_or_failed"], f"Expected 'Failed', got: {response['passed_or_failed']}"

    # ------------------------------------------------------------------ #
    #  3. Cat image with schema — all fields present and valid
    # ------------------------------------------------------------------ #
    @pytest.mark.repeat(REPEAT)
    @pytest.mark.parametrize("prompt", [
        "Is there a cat in this image?",
        "what is displayed in this image?",
    ])
    def test_cat_image_with_schema(self, prompt) -> None:
        response = self.client.run_image(
            prompt=prompt,
            image=ImagePaths.CAT_IMAGE,
            schema_output=CatResponseSchema,
        )
        assert isinstance(response, dict), f"Expected dict, got {type(response)}"
        assert "Passed" in response.get("passed_or_failed", ""), f"Expected 'Passed', got: {response}"
        assert response.get("is_cat_present") is True, f"Expected is_cat_present=True, got: {response}"
        assert response.get("cat_count") == 1, f"Expected cat_count=1, got: {response}"
        assert response.get("confidence_score", 0) > 0.8, f"Expected confidence > 0.8, got: {response}"

    # ------------------------------------------------------------------ #
    #  4. Cat image without schema — raw string mentions "cat"
    # ------------------------------------------------------------------ #
    @pytest.mark.repeat(REPEAT)
    def test_cat_image_no_schema(self) -> None:
        response = self.client.run_image(
            prompt="what is displayed in this image?",
            image=ImagePaths.CAT_IMAGE,
        )
        assert isinstance(response, str), f"Expected str, got {type(response)}"
        assert "cat" in response.lower(), f"Expected 'cat' in response, got: {response}"
        assert "Passed" in response, f"Expected 'Passed' in response, got: {response}"

    # ------------------------------------------------------------------ #
    #  5. SummaryOutputSchema — pass / fail sanity
    # ------------------------------------------------------------------ #
    @pytest.mark.repeat(REPEAT)
    @pytest.mark.parametrize("prompt, expected", [
        ("is that a terminal displayed?", "Passed"),
        ("is a cat displayed?", "Failed"),
    ])
    def test_summary_schema_pass_fail(self, prompt, expected) -> None:
        response = self.client.run_image(
            prompt=prompt,
            image=ImagePaths.MAIN_IMAGE,
            schema_output=SummaryOutputSchema,
        )
        assert isinstance(response, dict), f"Expected dict, got {type(response)}"
        assert expected in response.get("passed_or_failed", ""), \
            f"Expected '{expected}', got: {response.get('passed_or_failed')}"

    # ------------------------------------------------------------------ #
    #  6. Sample image comparison — IR play button
    # ------------------------------------------------------------------ #
    @pytest.mark.repeat(REPEAT)
    def test_sample_image_comparison_passed(self) -> None:
        response = self.client.run_image(
            prompt="is the sample image displayed in the main image?",
            image=ImagePaths.IR_IMAGE,
            sample_image=ImagePaths.IR_PLAY_BUTTON_SAMPLE_IMAGE,
            schema_output=InteractionsRecordingOutputSchema,
        )
        assert isinstance(response, dict), f"Expected dict, got {type(response)}"
        assert "PASSED" in response.get("passed_or_failed", "").upper(), \
            f"Expected 'PASSED', got: {response.get('passed_or_failed')}"

    # ------------------------------------------------------------------ #
    #  7. IR metadata with schema — specific field values
    # ------------------------------------------------------------------ #
    @pytest.mark.repeat(REPEAT)
    def test_ir_metadata_schema_field_values(self) -> None:
        response = self.client.run_image(
            prompt="what is displayed in this screenshot?",
            image=ImagePaths.IR_METADATA,
            schema_output=InteractionsRecordingOutputSchema,
        )
        assert isinstance(response, dict), f"Expected dict, got {type(response)}"
        assert "10:58:32" in response.get("answer_time", ""), \
            f"Expected '10:58:32' in answer_time, got: {response.get('answer_time')}"
        assert response.get("participant_count") == 2, \
            f"Expected participant_count=2, got: {response.get('participant_count')}"

    # ------------------------------------------------------------------ #
    #  8. Negative — wrong object not present in image
    # ------------------------------------------------------------------ #
    @pytest.mark.repeat(REPEAT)
    @pytest.mark.parametrize("prompt, expected", [
        ("is a cat displayed?",     "Failed"),
        ("is a dragon displayed?",  "Failed"),
        ("is a pizza displayed?",   "Failed"),
    ])
    def test_negative_prompts_return_failed(self, prompt, expected) -> None:
        response = self.client.run_image(
            prompt=prompt,
            image=ImagePaths.MAIN_IMAGE,
            schema_output=SummaryOutputSchema,
        )
        assert isinstance(response, dict), f"Expected dict, got {type(response)}"
        assert expected in response.get("passed_or_failed", ""), \
            f"Expected '{expected}', got: {response.get('passed_or_failed')}"
