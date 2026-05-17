import pytest
import asyncio
import uvicorn
import threading
from time import sleep
from typing import Generator
from pydantic import BaseModel, Field
from backend.paths import ImagePaths
from services.bini import app
from client.bini import BiniClient
from backend.utils.logger import Logfire
from backend.ai.agents.vision_agent.flow import bini_image
from tests.data.schemas import OutputSchema, CatResponseSchema, SummaryOutputSchema, InteractionsRecordingOutputSchema, ColorListSchema

log = Logfire('bini-image-local-server-test')

REPEAT = 10


@pytest.fixture(scope="session", autouse=True)
def client() -> Generator:
    """to run parallel: pytest -n auto --dist=loadscope --disable-warnings"""
    config = uvicorn.Config(app=app, workers=4, host="0.0.0.0", port=9999, log_level="critical", lifespan="on")
    uvicorn_server = uvicorn.Server(config)
    thread = threading.Thread(target=uvicorn_server.run, daemon=True)
    thread.start()
    sleep(10)
    bini_client = BiniClient(host="localhost", port=9999)
    yield bini_client
    uvicorn_server.should_exit = True
    thread.join(timeout=5)


class TestImageServiceAPI:

    @pytest.fixture(autouse=True)
    def setup(self, client: BiniClient) -> None:
        self.client = client

    @pytest.mark.repeat(REPEAT)
    @pytest.mark.parametrize('prompt, expected, expected_type', [
        ('what is displayed in this image?', 'Passed', str),
        ('is this an cmd or powershell?', 'Passed', str)
    ])
    def test_bini_image_response_without_schema(self, prompt, expected, expected_type) -> None:
        """No schema/samples: crew answers the prompt directly and ends with Passed."""
        response = self.client.run_image(prompt=prompt, image=ImagePaths.MAIN_IMAGE)
        assert expected in response, log.fire.error(f"Expected '{expected}' in response")
        assert isinstance(response, expected_type), log.fire.error(f"Expected type: '{expected_type}' in response {type(response)}")

    @pytest.mark.repeat(REPEAT)
    @pytest.mark.parametrize('prompt, schema, expected, expected_type', [
        ('is sample image displayed in the main?', OutputSchema, 'Failed', dict)
    ])
    def test_bini_image_response_with_schema(self, prompt, schema, expected, expected_type) -> None:
        response = self.client.run_image(prompt=prompt,
                                         image=ImagePaths.MAIN_IMAGE,
                                         sample_image=[ImagePaths.SAMPLE_IMAGE],
                                         schema_output=schema)

        print(response)
        assert expected in response.get('passed_or_failed'), log.fire.error(f"Expected '{expected}' in response, got: {response.get('passed_or_failed')}")
        assert isinstance(response, expected_type), log.fire.error(f"Expected type: '{expected}' in response {type(response)}")

    @pytest.mark.repeat(REPEAT)
    @pytest.mark.parametrize("prompt, schema, expected", [
        ("Is there a cat in this image?", CatResponseSchema, "Passed"),
        ("what is displayed in this image?", CatResponseSchema, "Passed")
    ])
    def test_cat_image_with_complex_questions(self, prompt, schema, expected) -> None:
        """Test cat image analysis with schema."""
        response = self.client.run_image(prompt=prompt, image=ImagePaths.CAT_IMAGE, schema_output=schema)
        assert expected in response.get("passed_or_failed"), log.fire.error(f"Expected '{expected}' in response, got: {response.get('final_result')}")
        assert response.get('cat_count') == 1, log.fire.error(f"Expected cat_count to be 1, got: {response.get('cat_count')}")
        assert response.get('is_cat_present') is True, log.fire.error(f"Expected is_cat_present to be True, got: {response.get('is_cat_present')}")
        assert response.get('confidence_score') > 0.8, log.fire.error(f"Expected confidence_score > 0.8, got: {response.get('confidence_score')}")
        assert 'brown' or 'tabby' or 'gray' in response.get('cat_color').lower(), log.fire.error(f"Expected cat_color to be 'tabby', got: {response.get('cat_color')}")

    @pytest.mark.repeat(REPEAT)
    @pytest.mark.parametrize("prompt, expected", [("what is displayed in this image?", "Passed")])
    def test_cat_image_with_complex_questions_no_schema(self, client, prompt, expected) -> None:
        """Test cat image analysis without a schema."""
        response = self.client.run_image(prompt=prompt, image=ImagePaths.CAT_IMAGE)
        assert expected in response, log.fire.error(f"Expected '{expected}' in response, got: {response}")
        assert 'cat' in response, log.fire.error(f"Expected '{expected}' in response, got: {response}")

    @pytest.mark.repeat(REPEAT)
    @pytest.mark.parametrize("prompt, schema, expected, sample_image", [
        ('what is displayed in this screenshot?', InteractionsRecordingOutputSchema, 'Passed', None),
    ])
    def test_interactions_recording_list_view_with_schema(self, prompt, schema, expected, sample_image) -> None:
        """Test interactions recording analysis with and without schema."""
        response = self.client.run_image(prompt=prompt, image=ImagePaths.IR_METADATA, schema_output=schema, sample_image=sample_image)
        assert '10:58:32' in response.get('answer_time'), log.fire.error(f"Expected '10:58:32' in answer_time, got: {response.get('answer_time')}")
        assert response.get('participant_count') == 2, log.fire.error(f"Expected participant_count to be 5, got: {response.get('participant_count')}")
        assert response.get('transfered_by') == 'STAUTO01_st_load_1', log.fire.error(f"Expected transfered_by to be 'STAUTO01_st_load_1', got: {response.get('transfered_by')}")


class TestFlowOutputAndTypes:

    @pytest.mark.repeat(REPEAT)
    @pytest.mark.parametrize("schema, expected_type", [(OutputSchema, dict), (None, str)])
    def test_bini_image_output_types(self, schema, expected_type):
        result = asyncio.run(bini_image(
            prompt="what is displayed in the sample image?",
            image=ImagePaths.MAIN_IMAGE,
            sample_image=ImagePaths.SAMPLE_IMAGE,
            schema_output=schema)
        )
        log.fire.info(f'{result}')
        assert type(result) is expected_type, log.fire.error(f'output type error, expected: {expected_type} got: {type(result)}')

    @pytest.mark.repeat(REPEAT)
    @pytest.mark.parametrize("prompt, expected", [
        ('is this a shell or an IDE?', 'Passed'),
        ('is a cat displayed?', 'Failed'),
        ('is a dragon displayed?', 'Failed'),
        ('is a pizza displayed?', 'Failed'),
        ('is a white background displayed?', 'Failed'),
        ('is microsoft text displayed?', 'Passed')
    ])
    def test_sanity_images(self, prompt, expected) -> None:
        response = asyncio.run(bini_image(prompt=prompt, image=ImagePaths.MAIN_IMAGE))
        assert expected in response, log.fire.error(f"Test failed with response: {response}")

    @pytest.mark.repeat(REPEAT)
    @pytest.mark.parametrize("prompt, expected", [
        ('is that a terminal displayed?', 'Passed'),
        ('is a cat displayed?', 'Failed')
    ])
    def test_sanity_image_with_schema(self, prompt, expected) -> None:
        response = asyncio.run(bini_image(prompt=prompt, image=ImagePaths.MAIN_IMAGE, schema_output=SummaryOutputSchema))
        assert expected in response.get('passed_or_failed'), log.fire.error(f"Test failed with response: {response}")

    @pytest.mark.repeat(REPEAT)
    @pytest.mark.parametrize("prompt, expected, sample_image", [
        ('is sample image displayed in the main image?', 'Passed', ImagePaths.IR_PLAY_BUTTON_SAMPLE_IMAGE),
        ('is a volume icon displayed in this image? take example from sample image', 'Passed', ImagePaths.VOLUME_ICON_SAMPLE_IMAGE),
        ('is the sample image displayed in the main image?', 'Passed', ImagePaths.IR_PLAY_BUTTON_SAMPLE_IMAGE),
        ('is the sample image displayed in the main screenshot?', 'Passed', ImagePaths.TAG_ICON_SAMPLE_IMAGE),
    ])
    def test_interactions_recording_list_view(self, prompt, expected, sample_image) -> None:
        """Test interactions recording analysis without schema."""
        response = asyncio.run(bini_image(prompt=prompt, image=ImagePaths.IR_IMAGE, sample_image=sample_image, schema_output=InteractionsRecordingOutputSchema))
        assert expected in response.get('passed_or_failed'), log.fire.error(f"Expected '{expected}' in response")

    @pytest.mark.repeat(REPEAT)
    @pytest.mark.parametrize("prompt, expected_color", [
        ('what is the background color of the "Sign In" section?', 'Blue'),
        ('what is the "Sign In" text color?', 'White'),
        ('what is the text color of interactions insights text?', 'Gray')
    ])
    def test_interactions_recording_welcome_page(self, prompt, expected_color) -> None:
        """Test interactions recording analysis without schema."""
        response = asyncio.run(bini_image(prompt=prompt, image=ImagePaths.WELCOME_IMAGE, schema_output=ColorListSchema))
        assert expected_color in response.get('colors'), log.fire.error(f"Expected '{expected_color}' in response")

    @pytest.mark.repeat(REPEAT)
    @pytest.mark.parametrize("prompt, expected", [('does the sample image present in the main image?', 'Failed')])
    def test_interactions_recording_list_view_with_wrong_sample_image(self, prompt, expected) -> None:
        """Test interactions recording analysis without schema."""
        response = asyncio.run(bini_image(prompt=prompt, image=ImagePaths.IR_IMAGE, sample_image=ImagePaths.SAMPLE_IMAGE))
        assert expected in response, log.fire.error(f"Expected '{expected}' in response")


class TestInteractionsRecording:

    @pytest.fixture(autouse=True)
    def setup(self, client: BiniClient) -> None:
        self.client = client

    @pytest.mark.repeat(REPEAT)
    @pytest.mark.parametrize("prompt, schema, expected, sample_image", [
        ('is the sample image displayed in the main screenshot?', None, 'Passed', ImagePaths.IR_PLAY_BUTTON_SAMPLE_IMAGE),
    ])
    def test_interactions_recording_list_view_without_schema(self, prompt, schema, expected, sample_image) -> None:
        """Test interactions recording analysis with and without schema."""
        response = self.client.run_image(prompt=prompt, image=ImagePaths.IR_IMAGE, schema_output=schema, sample_image=sample_image)
        assert expected in response, log.fire.error(f"Expected '{expected}' in response, got: {response}")

    @pytest.mark.repeat(REPEAT)
    @pytest.mark.parametrize("prompt, expected", [
        ("is the sample image visually displayed in the main image?", "Passed")
    ])
    def test_bini_image_consistency(self, prompt, expected) -> None:
        """len response asserts that the response has sufficient content"""
        response = self.client.run_image(
            prompt=prompt,
            image=ImagePaths.PAUSE_RESUME_MAIN_IMAGE,
            sample_image=[ImagePaths.PAUSE_RESUME_SAMPLE_IMAGE]
        )
        assert expected in response, log.fire.error(f"Expected '{expected}' in response")

    @pytest.mark.repeat(REPEAT)
    @pytest.mark.parametrize("prompt, expected", [
        ("is the sample image visually displayed in the main image?", 'Passed'),
    ])
    def test_bini_image_consistency_and_full_response_content(self, prompt, expected) -> None:
        response = self.client.run_image(
            prompt=prompt,
            image=ImagePaths.PAUSE_RESUME_MAIN_IMAGE,
            sample_image=[ImagePaths.PAUSE_RESUME_SAMPLE_IMAGE],
            schema_output=OutputSchema
        )
        assert expected in response.get('passed_or_failed'), log.fire.error(f"Expected '{expected}' in response")

    @pytest.mark.repeat(REPEAT)
    @pytest.mark.parametrize('prompt, expected', [
        ('is the play button displayed in this image?', 'Passed'),
        ('what user names are displayed in this image?', 'STSQUAD01_st_user4-1'),
        ('is "insert new note" placeholder displayed?', 'Passed'),
    ])
    def test_ir_player(self, prompt: str, expected: str) -> None:
        response = self.client.run_image(prompt=prompt, image=ImagePaths.IR_PLAYER)
        assert len(response.split()) > 1, log.fire.error(f"Expected response is thin")
        assert expected in response, log.fire.error(f"Expected '{expected}' in response")

    @pytest.mark.parametrize('prompt, expected', [
        ('Are these two images identical?', 'Passed'),
        ('Are these two timeline bars identical in colors and segment lengths?', 'Passed'),
    ])
    def test_identical_images(self, prompt: str, expected: str) -> None:
        response = self.client.run_image(prompt=prompt, image=ImagePaths.IDENTICAL_IMAGE_1, sample_image=[ImagePaths.IDENTICAL_IMAGE_2, ImagePaths.IDENTICAL_IMAGE_2])
        assert expected in response, log.fire.error(f"Expected '{expected}' in response")

    @pytest.mark.repeat(REPEAT)
    @pytest.mark.parametrize('prompt, expected', [
        ('is the sample image visually displayed in the main image?', 'Passed')
    ])
    def test_similar_images_2(self, prompt: str, expected: str) -> None:
        assert expected in self.client.run_image(image=ImagePaths.PAUSE_RESUME_MAIN_IMAGE, sample_image=ImagePaths.PAUSE_RESUME_SAMPLE_IMAGE, prompt=prompt)

    @pytest.mark.repeat(REPEAT)
    @pytest.mark.parametrize('prompt, expected', [('is a user icon displayed under the NAME column?', 'Passed')])
    def test_legal_hold(self, prompt: str, expected: str) -> None:
        """validate bini finds the username under name and not under legal hold column"""
        assert expected in self.client.run_image(image=ImagePaths.LEGAL_HOLD, prompt=prompt)


class TestVoca:

    @pytest.fixture(autouse=True)
    def setup(self, client: BiniClient) -> None:
        self.client = client

    @pytest.mark.parametrize("prompt", ['is manage participant button text exactly container "Manage Participant"'])
    def test_1(self, prompt) -> None:
        """Test interactions recording analysis with and without schema."""
        response = self.client.run_image(prompt=prompt, image=ImagePaths.VOCA, sample_image=ImagePaths.VOCA_SAMPLE_IMAGE)
        assert 'Passed' in response, log.fire.error(f"Expected 'Passed' in response, got: {response}")

    @pytest.mark.parametrize("prompt", ['is add participants button displayed in this screen?'])
    def test_2(self, prompt) -> None:
        """Test interactions recording analysis with and without schema."""
        response = self.client.run_image(prompt=prompt, image=ImagePaths.VOCA)
        assert 'Failed' in response, log.fire.error(f"Expected 'Failed' in response, got: {response}")

    @pytest.mark.parametrize("prompt", ['disregard the recap section and validate the participant colors displayed on the meeting speakers bar'])
    def test_3(self, prompt) -> None:
        """Test interactions recording analysis with and without schema."""
        response = self.client.run_image(prompt=prompt, image=ImagePaths.VOCA)
        assert 'Failed' in response, log.fire.error(f"Expected 'Failed' in response, got: {response}")


class Schema(BaseModel):
    final_question:   str = Field(..., description="The final question generated by Bini AI.")
    passed_or_failed: str = Field(..., description="Indicates whether the validation passed or failed.")
    analysis:         str = Field(..., description="Detailed analysis provided by Bini AI.")
    error_message:    str = Field(..., description="An error occurred while processing your request. Please try again later.")
