from crewai import Agent, Task
from dataclasses import dataclass
from functools import cached_property
from backend.settings import LLMFactory
from backend.utils.logger import Logger


log = Logger(name="agent-infra")


@dataclass
class AgentInfrastructure:

    """Base class for CrewAI agent infrastructure."""

    # CrewAI's @CrewBase expects these names (string paths are supported).
    agents_config: dict = "config/agents.yaml"
    tasks_config: dict = "config/tasks.yaml"

    def __post_init__(self) -> None:
        self.agents: list[Agent] = []
        self.tasks: list[Task] = []
        log.fire.debug("AgentInfrastructure initialized")

    @cached_property
    def llm(self):
        """Create a single LLM instance per class."""
        log.fire.debug("Initializing LLM through AzureLLMFactory")
        return LLMFactory().llm
