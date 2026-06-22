from crewai import Flow, Agent, LLM
from crewai.flow import start, listen, router
from pydantic import BaseModel, Field
from typing import Optional, Type, Generic, TypeVar
from settings import Config
from dataclasses import dataclass

T = TypeVar('T', bound=BaseModel)


@dataclass
class SingleAgent(Generic[T]):

    role: str
    goal: str
    backstory: str
    llm_model: str = 'gpt-4o'
    tools: Optional[list] = None
    schema: Optional[Type[BaseModel]] = None

    def __post_init__(self) -> None:
        self.llm = LLM(model=self.llm_model, api_key=Config.OPENAI_API_KEY)

    @property
    def _fetch_agent(self) -> Agent:
        return Agent(role=self.role, llm=self.llm, goal=self.goal, backstory=self.backstory, verbose=True, tools=self.tools, output_pydantic=self.schema)

    def run(self, prompt: str) -> dict | str:
        if self.schema:
            return self._fetch_agent.kickoff(prompt, response_format=self.schema)
        return self._fetch_agent.kickoff(prompt).raw


class InitialState(BaseModel):
    prompt: str = Field('')
    str_cache: str = Field('')
    cached_dict: dict = Field(default_factory=dict)


class JokeSchema(BaseModel):
    score: float = Field(..., ge=0, le=100)

class AgentFlow(Flow[InitialState]):
    @start()
    def step_1(self) -> str:
        return SingleAgent(role='joke', goal='funny', backstory='funny').run(self.state.prompt)

if __name__ == '__main__':
    print(AgentFlow().kickoff({'prompt': 'tell a joke'}))
