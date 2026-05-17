from typing import Literal

from pydantic import BaseModel, Field
from client.bini import BiniClient


bini = BiniClient(host='10.8.2.35', port=8082)


class TextOutputSchema(BaseModel):
    analysis:              str   = Field(..., description="Detailed analysis of the text prompt")
    answer:                str   = Field(..., description="Answer to the text prompt")
    confidence_in_precent: float = Field(..., description="Confidence level of the analysis in percent")
    interesting_info:      str   = Field(..., description="Additional interesting information related to the text")
    city_area_in_sq_km:    float = Field(..., description="City area in square kilometers")


class ImageOutputSchema(BaseModel):
    analysis:              str                         = Field(..., description="Detailed analysis of the image content")
    confidence_in_precent: float                       = Field(..., description="Confidence level of the analysis in percent")
    passed_or_failed:      Literal['Passed', 'Failed'] = Field(..., description="Indicates whether the image passed or failed the analysis")
    list_of_colors:        list[str]                   = Field(..., description="List of prominent colors in the image")
    number_of_cats:        int                         = Field(..., description="Number of cats detected in the image")


def text_example() -> dict | str:
    return bini.run_text(prompt=f'what is the capital of france?', schema_output=TextOutputSchema)


def image_example() -> dict | str:
    return bini.run_image(prompt=f'what is displayed in this image?',
                          image=r"C:\Users\evgenyp\OneDrive - AudioCodes Ltd\Desktop\cat.jpg",
                          schema_output=ImageOutputSchema)


def text_example_without_schema() -> dict | str:
    return bini.run_text(prompt=f'what is the capital of france?')


def image_example_without_schema() -> dict | str:
    return bini.run_image(prompt=f'what is displayed in this image?', image=r"C:\Users\evgenyp\OneDrive - AudioCodes Ltd\Desktop\cat.jpg")


if __name__ == '__main__':
    # print(text_example())
    print(image_example())
    print(image_example_without_schema())
    # for _ in range(15):
    #     print(image_example_without_schema())
