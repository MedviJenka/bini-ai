from typing import Literal
from pydantic import BaseModel, Field


__all__ = [
    "VisualAttribute",
    "ComparisonFinding",
    "QAObservation",
    "VisionSchema"
]


class VisualAttribute(BaseModel):
    element:            str       = Field(..., description="The name of the UI element or object (e.g., 'Submit Button')")
    color_names:        list[str] = Field(..., description="List of color names associated with the element")
    text_content:       str       = Field(..., description="Any text identified within the element")
    dates:              list[str] = Field(default_factory=list, description="List of dates found within the element")


class ComparisonFinding(BaseModel):
    is_sample_image_provided: bool = Field(default=False, description="Whether or not the image was provided")
    attribute:          str                                     = Field(..., description="The property being compared (e.g., 'Font Size')")
    match:              bool                                    = Field(..., description="True if it matches the sample image")
    severity:           Literal["critical", "major", "minor"]   = Field(default="minor", description="Impact severity: critical blocks testing, major affects functionality, minor is cosmetic")
    difference_details: str                                     = Field(default="", description="Description of the discrepancy; empty when match is True")


class QAObservation(BaseModel):
    original_prompt:  str                         = Field(..., description="The original user prompt")
    status:           Literal["Passed", "Failed"] = Field(..., description="QA status relative to the original prompt")
    confidence_level: int                         = Field(..., description="Confidence level of the decision (0-100)", ge=0, le=100)
    reason:           str                         = Field(default="", description="Explanation of why the status was assigned — used as assertion message in generated tests")


class VisionSchema(BaseModel):
    main_image_attributes:   list[VisualAttribute]                 = Field(..., description="List of all detected visual elements and their properties for the main image")
    sample_image_attributes: list[list[VisualAttribute]] | None    = Field(default=None, description="Per-sample lists of detected visual elements and their properties")
    reference_comparison:    list[ComparisonFinding] | None        = Field(default=None, description="Comparison results if a sample image was provided; null when no samples given")
    dimensions:              str                                   = Field(..., description="Estimated or detected aspect ratio/resolution")
    raw_observations:        str                                   = Field(..., description="A brief factual summary of the overall scene")
    final_decision:          QAObservation                         = Field(..., description="QA verdict for the overall prompt — aggregates all observations into a single pass/fail with confidence")
