from dataclasses import dataclass
from pydantic_settings import BaseSettings, SettingsConfigDict
from backend.paths import ROOT_DIR
from crewai import Agent, LLM
from functools import cached_property
from typing import Generic, TypeVar, Optional, Type
from pydantic import BaseModel, Field
from utils.infrastructure import AgentInfrastructure


T = TypeVar("T", bound=BaseModel)


class Settings(BaseSettings):

    model_config = SettingsConfigDict(env_file=(".env"), extra="ignore")

    API_VERSION:          str = Field(default="v1")
    ENV:                  str = Field(default='dev')
    ANTHROPIC_API_KEY:    str = Field(...)
    LOGFIRE_TOKEN:        str = Field(...)
    MCP_PROXY_AUTH_TOKEN: str = Field(...)
    CLAUDE_MODEL:         str = Field(...)
    VERBOSE:              str = Field(...)

    class Paths:
        LOGS = str(ROOT_DIR / "logs")


class TestSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    TOTAL_REQUESTS:  int = Field(default=5000, validation_alias="LOAD_TEST_REQUESTS")
    MAX_CONCURRENCY: int = Field(default=200, validation_alias="LOAD_TEST_CONCURRENCY")


Config = Settings()


# --------------------------------------------------------- #
#          LLM factory for different AI models              #
# --------------------------------------------------------- #
@dataclass
class LLMFactory:

    temperature: int = 0

    @cached_property
    def llm(self) -> LLM:
        return LLM(model="anthropic/claude-sonnet-4-6", api_key=Config.ANTHROPIC_API_KEY)


_infra = AgentInfrastructure()


class AgentConfigSchema(BaseModel):
    role:        str   = Field(...,  description='agent role title')
    goal:        str   = Field(...,  description='what the agent is trying to achieve')
    backstory:   str   = Field(...,  description='agent persona and background context')
    temperature: float = Field(0.0,  description='LLM sampling temperature; 0.0 = deterministic')
    verbose:     bool  = Field(True, description='enable CrewAI step-by-step logging')


class SingleAgent(Generic[T]):

    def __init__(self, config: AgentConfigSchema, llm: Optional[LLM] = None) -> None:
        self.config = config
        self.llm = llm or _infra.llm

    @cached_property
    def agent(self) -> Agent:
        return Agent(**self.config.model_dump(), llm=self.llm)

    def run(self, prompt: str, output_model: Optional[Type[T]] = None) -> str | dict:
        if output_model:
            return self.agent.kickoff(messages=prompt, response_format=output_model).pydantic.model_dump()
        return self.agent.kickoff(messages=prompt).raw


TestConfig = TestSettings()
