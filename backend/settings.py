from dataclasses import dataclass
from functools import cached_property
from crewai import LLM
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from backend.paths import ROOT_DIR


class Settings(BaseSettings):

    model_config = SettingsConfigDict(env_file="../.env", extra="ignore")

    API_VERSION:       str = Field(default="v1")
    ENV:               str = Field(default='dev')
    HOST:              str = Field(default='0.0.0.0')
    PORT:              int = Field(...)
    LOG_DIR:           str = Field(default=str(ROOT_DIR / "logs"))
    LOG_LEVEL:         str = Field(default='DEBUG')
    ANTHROPIC_API_KEY: str = Field(...)
    LOGFIRE_TOKEN:     str = Field(...)

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


TestConfig = TestSettings()
