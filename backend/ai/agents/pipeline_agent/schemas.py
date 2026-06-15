from pydantic import BaseModel, Field


class PipelineInput(BaseModel):
    name:           str = Field(..., description="Name used for agent.md and skill.md files")
    purpose:        str = Field(..., description="What this agent/skill does")
    trigger:        str = Field("",  description="Slash command or phrase that invokes the skill")
    tools:          str = Field("",  description="Comma-separated tools the agent uses")
    context:        str = Field("",  description="Extra constraints or domain context")
    related_agents: str = Field("",  description="Comma-separated agent names this agent coordinates with")
    related_skills: str = Field("",  description="Comma-separated skill names this agent uses")
    workflow:       str = Field("",  description="Free-text description of the agent's execution steps")


class PipelineFlowInput(BaseModel):
    items:            list[PipelineInput] = Field(..., description="Agent/skill pairs to generate")
    command_name:     str                 = Field(..., description="Name for the generated command file")
    command_purpose:  str                 = Field(..., description="What the command orchestrates")
    command_trigger:  str                 = Field("",  description="Slash command that invokes it")
    command_workflow: str                 = Field("",  description="High-level orchestration workflow description")
    command_context:  str                 = Field("",  description="Extra context for the command author")


class ItemOutput(BaseModel):
    name:     str = Field(..., description="Name of the generated agent/skill pair")
    agent_md: str = Field(..., description="Generated agent markdown content")
    skill_md: str = Field(..., description="Generated skill markdown content")


class PipelineFlowOutput(BaseModel):
    items:      list[ItemOutput] = Field(..., description="Generated agent/skill outputs per item")
    command_md: str              = Field(..., description="Generated command markdown that orchestrates all agents")


# Legacy single-item output kept for backward compatibility
class PipelineOutput(BaseModel):
    agent_md:    str = Field(..., description="Generated agent markdown content")
    skill_md:    str = Field(..., description="Generated skill markdown content")
    commands_md: str = Field(..., description="Generated command markdown content")
