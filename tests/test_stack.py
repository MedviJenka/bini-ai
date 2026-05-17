from pydantic import BaseModel

from backend.paths import ImagePaths
from client.bini import BiniClient


bini = BiniClient(host='10.8.2.35')


class TextOutputSchema(BaseModel):
    analysis: str
    confidence_in_precent: float
    interesting_info: str
    city_area_in_sq_km: float


class ImageOutputSchema(BaseModel):
    analysis: str
    confidence_in_precent: float
    passed_or_failed: str


def test_1() -> None:
    assert bini.run_text(prompt=f'what is the capital of france?', schema_output=TextOutputSchema)


def test_2() -> None:
    response = bini.run_image(prompt=f'what is displayed in this image?', image=ImagePaths.CAT_IMAGE, schema_output=ImageOutputSchema)
    print(response)
    assert response


def test_3() -> None:
    assert bini.run_text(prompt=f'what is the capital of france?')


def test_4() -> None:
    assert bini.run_image(prompt=f'what is displayed in this image?', image=ImagePaths.CAT_IMAGE)
