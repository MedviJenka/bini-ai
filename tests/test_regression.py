import pytest
from typing import Generator
from client.bini import BiniClient
from backend.utils.logger import Logfire
from playwright.sync_api import sync_playwright


log = Logfire('bini-image-regression-server-test')

REPEAT = 10  # repeat n times for testing consistency


@pytest.fixture(scope="session", autouse=True)
def client() -> Generator:
    bini_client = BiniClient(host="localhost", port=8081)
    yield bini_client
    log.fire.info("Test session completed.")


class TestSampleImageTakenFromUI:

    @pytest.fixture(autouse=True)
    def setup(self, client: BiniClient) -> None:
        self.client = client

    @pytest.mark.repeat(REPEAT)
    @pytest.mark.parametrize('prompt, expected', [('are both images the same?', 'Passed')])
    def test_sample_image_taken_after_navigating_back_and_forward(self, prompt, expected) -> None:
        MAIN_IMAGE_PATH = "data/images/main.png"
        SAMPLE_IMAGE_PATH = "data/images/sample.png"
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page()
            page.goto("https://playwright.dev")
            page.screenshot(path=MAIN_IMAGE_PATH)
            page.goto("https://google.com")
            page.goto("https://playwright.dev")
            page.screenshot(path=SAMPLE_IMAGE_PATH)
            browser.close()

        response = self.client.run_image(prompt=prompt, image=MAIN_IMAGE_PATH, sample_image=SAMPLE_IMAGE_PATH)
        assert expected in response, log.fire.error(f"Expected '{expected}' in response")
