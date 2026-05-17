from pydantic import BaseModel, Field


class HealthResponseSchema(BaseModel):
    """Schema for the health check response."""
    status: int = Field(default=200, description="Health status of the service")
    health: str = Field(default="healthy", description="Health check status")
    api: str = Field(..., description="API version or identifier")
    env: str = Field(..., description="Environment (e.g., dev, prod, etc..)")
