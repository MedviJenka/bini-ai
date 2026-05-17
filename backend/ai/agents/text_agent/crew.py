import asyncio
from pydantic import BaseModel
from crewai import Agent, Crew, Task
from typing import Optional, Type, Dict, Any
from crewai.project import CrewBase, agent, crew, task
from backend.api.v1.bini.logic import validate_structured_output
from backend.utils.infrastructure import AgentInfrastructure
from backend.utils.logger import Logfire


log = Logfire(name="text-agent")


@CrewBase
class TextAgent(AgentInfrastructure):

    """Dynamic ChatAgent that allows runtime schema injection."""

    def __init__(self, schema_output: Optional[Type[BaseModel]] = None) -> None:
        self.schema_output = schema_output

    @agent
    def agent(self, **kwargs) -> Agent:
        return Agent(config=self.agents_config["agent"], llm=self.llm, verbose=False, **kwargs)

    @task
    def extract_information(self, **kwargs) -> Task:
        return Task(config=self.tasks_config["extract_information"], tools=[], **kwargs)

    @task
    def chat_assistant(self, **kwargs) -> Task:
        return Task(config=self.tasks_config["chat_assistant"], output_pydantic=self.schema_output, **kwargs)

    @crew
    def crew(self) -> Crew:
        return Crew(agents=self.agents, tasks=self.tasks, verbose=False)


def _run_text_crew(prompt: str, pydantic_schema: Optional[Type[BaseModel]]) -> str | dict:
    """Blocking crew execution — always called via asyncio.to_thread."""
    response = TextAgent(schema_output=pydantic_schema).crew().kickoff({"prompt": prompt})
    if pydantic_schema:
        if response.pydantic is not None:
            return validate_structured_output(pydantic_schema, response.pydantic)
        return validate_structured_output(pydantic_schema, response.raw)
    return response.raw


async def text_agent(prompt: str, schema_output: Optional[Dict[str, Any] | Type[BaseModel]] = None) -> str | dict:
    """Text agent that accepts either a Pydantic class or JSON schema dict."""

    pydantic_schema = None
    log.fire.info(
        f"Starting text agent | prompt_length={len(prompt)} | schema_type={type(schema_output).__name__ if schema_output is not None else 'None'}"
    )

    if schema_output:
        if isinstance(schema_output, type) and issubclass(schema_output, BaseModel):
            # Direct Pydantic class (local use)
            pydantic_schema = schema_output
        elif isinstance(schema_output, dict):
            # JSON schema dict (from API) - convert to Pydantic
            from backend.api.v1.bini.logic import json_schema_to_pydantic
            pydantic_schema = json_schema_to_pydantic(schema_output)

    try:
        response = await asyncio.to_thread(_run_text_crew, prompt, pydantic_schema)
    except Exception:
        log.fire.exception("Text agent execution failed")
        raise

    log.fire.info(f"Text agent completed | response_type={type(response).__name__}")
    log.fire.debug(f"Text agent response payload: {response}")
    return response
