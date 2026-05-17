import asyncio
from pydantic import BaseModel
from crewai import Agent, Crew, Task, Process
from typing import Optional, Type
from crewai.project import CrewBase, agent, crew, task
from backend.api.v1.bini.logic import validate_structured_output
from backend.ai.tools.stt import STTTool
from backend.utils.infrastructure import AgentInfrastructure


@CrewBase
class STTAgent(AgentInfrastructure):

    def __init__(self, schema_output: Optional[Type[BaseModel]] = None) -> None:
        self.schema_output = schema_output

    def manager(self) -> Agent:
        return Agent(config=self.agents_config["manager"], llm=self.llm, verbose=False)

    @agent
    def agent(self, **kwargs) -> Agent:
        return Agent(config=self.agents_config["agent"], llm=self.llm, verbose=False, **kwargs)

    @task
    def audio_task(self, **kwargs) -> Task:
        return Task(config=self.tasks_config["audio_task"], tools=[STTTool()], **kwargs)

    @crew
    def crew(self) -> Crew:
        return Crew(agents=self.agents, tasks=self.tasks, verbose=False, process=Process.hierarchical, manager_llm=self.llm)


def _run_stt_crew(prompt: str, audio_file: str, schema_output: Optional[Type[BaseModel]]) -> str | dict:
    """Blocking crew execution — always called via asyncio.to_thread."""
    inputs = {"audio_file": audio_file, "prompt": prompt}
    response = STTAgent(schema_output=schema_output).crew().kickoff(inputs=inputs)
    if schema_output:
        if response.pydantic is not None:
            return validate_structured_output(schema_output, response.pydantic)
        return validate_structured_output(schema_output, response.raw)
    return response.raw


async def bini_voice(prompt: str, audio_file: str, schema_output: Optional[Type[BaseModel]] = None) -> str | dict:
    return await asyncio.to_thread(_run_stt_crew, prompt, audio_file, schema_output)
