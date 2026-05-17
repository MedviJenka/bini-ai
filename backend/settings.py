import os
from dotenv import load_dotenv
from dataclasses import dataclass
from functools import cached_property
from crewai import LLM
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from backend.paths import ROOT_DIR


load_dotenv()


class Settings(BaseSettings):

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    API_VERSION:       str = os.getenv("API_VERSION", "v1")
    ENV:               str = os.getenv("ENV", "development")
    HOST:              str = "0.0.0.0"
    PORT:              int = os.getenv("PORT")
    LOG_DIR:           str = str(ROOT_DIR / "logs")
    LOG_LEVEL:         str = "DEBUG"
    AZURE_API_KEY:     str = os.getenv("AZURE_API_KEY")
    AZURE_ENDPOINT:    str = os.getenv("AZURE_ENDPOINT")
    AZURE_API_VERSION: str = os.getenv("AZURE_API_VERSION")

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
        """Initiates openai with azure"""

        return LLM(
            model="azure/gpt-5.4-mini",
            api_key=Config.AZURE_API_KEY,
            endpoint=Config.AZURE_ENDPOINT,
            api_version=Config.AZURE_API_VERSION,
        )


TestConfig = TestSettings()
