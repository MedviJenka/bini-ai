from typing import Literal, List
from pydantic import BaseModel, Field


Elements = Literal["ID", "NAME", "CSS", "XPATH"]


class PageBaseCSVElementSchema(BaseModel):
    element_name:      str       = Field(..., description="Human-readable name of the UI element (visible text or aria-label).")
    element_type:      Elements  = Field(..., description="Type of intrinsic element identifier. Priority order: ID > NAME > then the others.")
    element_attribute: str       = Field(..., description="Raw attribute value of the element. Must not contain CSS selectors, XPATHs, or hrefs.")


class PageBaseCSVSchema(BaseModel):
    elements:  List[PageBaseCSVElementSchema] = Field(..., description="List of UI elements extracted from the page.")
