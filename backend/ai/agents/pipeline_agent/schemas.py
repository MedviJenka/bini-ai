from pydantic import BaseModel, Field
from typing import Optional


class PipelineInput(BaseModel):
    name:    str = Field(..., description="Name of the agent or skill being documented")
    purpose: str = Field(..., description="What the agent/skill does")
    trigger: str = Field(default="", description="Slash command or phrase that triggers the skill")
    tools:   str = Field(default="", description="Comma-separated list of tools the agent uses")
    context: str = Field(default="", description="Any extra context or constraints")


class PipelineOutput(BaseModel):
    agent_md:    str = Field(..., description="Generated CLAUDE.md content for the agent")
    skill_md:    str = Field(..., description="Generated SKILL.md content for the skill")
    commands_md: str = Field(..., description="Generated COMMANDS.md content")
