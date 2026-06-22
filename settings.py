from dataclasses import dataclass
from functools import cached_property
from crewai import LLM
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from utils.paths import ROOT_DIR
from typing import Literal


class Settings(BaseSettings):

    model_config = SettingsConfigDict(extra="ignore")

    API_VERSION:                    str = Field(default="v1")
    ENV:                            str = Field(default='dev')
    LOGFIRE_TOKEN:                  str = Field(...)
    MCP_PROXY_AUTH_TOKEN:           str = Field(...)
    CLAUDE_PROXY_URL:               str = Field(default="http://127.0.0.1:8787/v1")
    VERBOSE:                        str = Field(...)
    LLM_PROVIDER:                   str = Field(default="anthropic", description='anthropic, openai, etc... it will be used in LLMFactory class for classification')
    LLM_MODEL:                      str = Field(default='claude-sonnet-4-6', description='llm model, for example: claude-sonnet-4-6, gpt=5.4, etc...')
    CLAUDE_PROXY_MAX_CONCURRENCY:   int = Field(default=4)
    CLAUDE_PROXY_TIMEOUT:           int = Field(default=300)
    CLAUDE_PROXY_MODEL_ALLOWLIST:   str = Field(default="claude-sonnet-4-6,claude-opus-4-6,claude-haiku-4-6")
    LLM_API_KEY:                    str = Field(default="claude-sonnet-4-6,claude-opus-4-6,claude-haiku-4-6")
    OPENAI_API_KEY:                 str = Field(...)

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
        return LLM(
            model=f'{Config.LLM_PROVIDER}/{Config.LLM_MODEL}',
            base_url=Config.CLAUDE_PROXY_URL,
            api_key=Config.MCP_PROXY_AUTH_TOKEN,
        )


TestConfig = TestSettings()
