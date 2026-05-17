from datetime import datetime
from typing import Optional, Literal
from pydantic import BaseModel, field_validator, Field


class OutputSchema(BaseModel):
    first_image_analysis:  str                           = Field(..., description="Analysis of the first image provided.")
    second_image_analysis: str                           = Field(..., description="Analysis of the second image provided.")
    confidence_in_precent: float                         = Field(..., description="Confidence level of the analysis in percent.")
    final_result:          str                           = Field(..., description="Final result based on the analysis.")
    passed_or_failed:      Literal['Passed', 'Failed']   = Field(..., description="Indicates whether the analysis passed or failed.")


class ColorListSchema(BaseModel):
    colors:                list[str] = Field(..., description="List of colors identified in the image.")
    confidence_in_precent: float     = Field(..., description="Confidence level of the color identification in percent.")
    passed_or_failed:      str       = Field(..., description="Indicates whether the color identification passed or failed.")


class ChatOutputSchema(BaseModel):
    confidence_in_precent: float = Field(..., description="Confidence level of the analysis in percent.")
    final_result:          str   = Field(..., description="Final result based on the analysis.")
    passed_or_failed:      str   = Field(..., description="Indicates whether the analysis passed or failed.")


class EvaluationOutputSchema(BaseModel):
    evaluation_result_in_precent: float = Field(..., description="Result of the evaluation in precent format.")
    improvement_suggestions:      str   = Field(..., description="Suggestions for improvement based on the evaluation.")
    thoughts:                     str   = Field(..., description="Additional thoughts regarding the evaluation.")


class ConfidenceSchema(BaseModel):
    response:              str      = Field(..., description="Response from the analysis.")
    meta:         Optional[str]     = Field(..., description="Optional metadata related to the response.")
    analysis:              str      = Field(..., description="Detailed analysis of the response.")
    confidence_in_precent: float    = Field(..., description="Confidence level of the analysis in percent.")
    metadata:              str      = Field(..., description="Additional metadata information.")
    time:                  datetime = Field(..., description="Timestamp of the analysis.")


class ConfidenceSchema2(BaseModel):
    response: str
    confidence: float


class SummaryOutputSchema(BaseModel):

    summary: str
    passed_or_failed: str

    @field_validator("passed_or_failed", mode="before")
    def capitalize_first_letter(cls, value: str) -> str:
        return value.title()


class CatResponseSchema(BaseModel):
    is_cat_present:     bool  = Field(..., description="Indicates if a cat is present in the image.")
    confidence_score:   float = Field(..., description="Confidence score of the cat detection.")
    cat_color:          str   = Field(..., description="Color of the detected cat.")
    cat_count:          int   = Field(..., description="Number of cats detected in the image.")
    background_details: str   = Field(..., description="Details about the background of the image.")
    background_color:   str   = Field(..., description="Color of the background in the image.")
    passed_or_failed:   str   = Field(..., description="Indicates whether the detection passed or failed.")


class InteractionsRecordingOutputSchema(BaseModel):

    passed_or_failed:  Literal['Passed', 'Failed'] = Field(..., description='Indicates whether the test passed or failed')
    answer_time:       str                         = Field(..., description="ANSWER TIME row, Time when the answer was recorded, in HH:MM:SS format")
    participant_count: int                         = Field(..., description='Number of participants in the interaction')
    transfered_by:     str                         = Field(..., description="Name of the person who transferred the interaction")
    duration:          str                         = Field(..., description="Duration of the interaction in MM:SS format")
    items:             dict                        = Field(default_factory=dict, description='what is displayed in this image?')
