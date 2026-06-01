from pydantic import BaseModel, Field
from typing import List, Optional


class VisualAttribute(BaseModel):
    element:      str       = Field(..., description="The name of the UI element or object (e.g., 'Submit Button')")
    color_names:  List[str] = Field(..., description="List of color names associated with the element")
    text_content: str       = Field(..., description="Any text identified within the element")
    dates:        List[str] = Field(..., description="List of dates found within the element")


class ComparisonFinding(BaseModel):
    attribute:                   str  = Field(..., description="The property being compared (e.g., 'Font Size')")
    match:                       bool = Field(..., description="True if it matches the sample image")
    difference_details:          str  = Field(..., description="Description of the discrepancy found")


class VisionSchema(BaseModel):
    main_image_attributes:   List[VisualAttribute]                 = Field(..., description="List of all detected visual elements and their properties for the main image")
    sample_image_attributes: Optional[List[List[VisualAttribute]]] = Field(default=None, description="Per-sample lists of detected visual elements and their properties")
    reference_comparison:    List[ComparisonFinding]               = Field(..., description="Comparison results if a sample image was provided")
    dimensions:              str                                   = Field(..., description="Estimated or detected aspect ratio/resolution")
    raw_observations:        str                                   = Field(..., description="A brief factual summary of the overall scene")
