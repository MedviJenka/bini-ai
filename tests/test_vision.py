import pytest
from pathlib import Path
from ai.agents.vision_agent.crew import vision_agent


IMAGE_PATH = str(Path(__file__).resolve().parent.parent / "data" / "images" / "main.png")


class TestVisionPositive:

    def test_portfolio_distribution_is_displayed(self) -> None:
        result = vision_agent(prompt="is Portfolio Distribution displayed", image_path=IMAGE_PATH)
        assert result["final_decision"]["status"] == "Passed"
        assert result["final_decision"]["confidence_level"] >= 80

    def test_alerts_by_category_is_displayed(self) -> None:
        result = vision_agent(prompt="is Alerts by Category displayed", image_path=IMAGE_PATH)
        assert result["final_decision"]["status"] == "Passed"

    def test_properties_count_displayed(self) -> None:
        result = vision_agent(prompt="is the number 22 displayed next to Properties", image_path=IMAGE_PATH)
        assert result["final_decision"]["status"] == "Passed"

    def test_pending_count_displayed(self) -> None:
        result = vision_agent(prompt="is the number 96 displayed next to Pending", image_path=IMAGE_PATH)
        assert result["final_decision"]["status"] == "Passed"


class TestVisionNegative:

    def test_cat_is_not_displayed(self) -> None:
        result = vision_agent(prompt="is a cat displayed", image_path=IMAGE_PATH)
        assert result["final_decision"]["status"] == "Failed"

    def test_login_button_is_not_displayed(self) -> None:
        result = vision_agent(prompt="is a Login button displayed", image_path=IMAGE_PATH)
        assert result["final_decision"]["status"] == "Failed"

    def test_table_is_not_displayed(self) -> None:
        result = vision_agent(prompt="is a data table displayed", image_path=IMAGE_PATH)
        assert result["final_decision"]["status"] == "Failed"


class TestVisionSchema:

    @pytest.fixture(scope="class")
    def result(self) -> dict:
        return vision_agent(prompt="what elements are displayed", image_path=IMAGE_PATH)

    def test_main_image_attributes_not_empty(self, result: dict) -> None:
        assert len(result["main_image_attributes"]) > 0

    def test_each_attribute_has_element_and_type(self, result: dict) -> None:
        for attr in result["main_image_attributes"]:
            assert attr["element"], "element name must not be empty"
            assert attr["element_type"], "element_type must not be empty"

    def test_text_content_detected(self, result: dict) -> None:
        all_text = " ".join(attr["text_content"] for attr in result["main_image_attributes"])
        assert any(keyword in all_text for keyword in ["22", "96", "Properties", "Pending", "Portfolio"]), (
            f"Expected dashboard text in attributes, got: {all_text}"
        )

    def test_reference_comparison_none_without_samples(self, result: dict) -> None:
        assert result["reference_comparison"] is None

    def test_sample_image_attributes_none_without_samples(self, result: dict) -> None:
        assert result["sample_image_attributes"] is None

    def test_final_decision_has_reason(self, result: dict) -> None:
        assert result["final_decision"]["reason"], "reason must not be empty"

    def test_dimensions_not_empty(self, result: dict) -> None:
        assert result["dimensions"], "dimensions must not be empty"

    def test_raw_observations_not_empty(self, result: dict) -> None:
        assert result["raw_observations"], "raw_observations must not be empty"
