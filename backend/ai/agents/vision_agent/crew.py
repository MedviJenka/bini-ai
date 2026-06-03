from typing import Union, Optional
from crewai import Agent, Crew, Task
from crewai.project import CrewBase, agent, crew, task
from backend.ai.tools.vision_tool import BiniVisionTool
from backend.utils.infrastructure import AgentInfrastructure
from backend.ai.agents.vision_agent.schemas import VisionSchema


@CrewBase
class ComputerVisionAgent(AgentInfrastructure):

    @agent
    def image_analysis_agent(self) -> Agent:
        return Agent(config=self.agents_config['image_analysis_agent'], llm=self.llm)

    @agent
    def decision_agent(self) -> Agent:
        return Agent(config=self.agents_config['decision_agent'], llm=self.llm, max_iter=4)

    @task
    def extract_visual_data(self, **kwargs) -> Task:
        return Task(config=self.tasks_config['extract_visual_data'], tools=[BiniVisionTool(llm=self.llm)], **kwargs)

    @task
    def validate_requirements(self, **kwargs) -> Task:
        return Task(config=self.tasks_config['validate_requirements'], output_pydantic=VisionSchema, **kwargs)

    @crew
    def crew(self) -> Crew:
        return Crew(agents=self.agents, tasks=self.tasks, verbose=True, )


def vision_agent(prompt: str, image_path: str, sample_image: Optional[Union[list, str]] = None) -> dict:
    cv = ComputerVisionAgent()
    response = cv.crew().kickoff({"prompt": prompt, "image": image_path, "sample_image": sample_image})
    return response.pydantic.model_dump()


if __name__ == '__main__':
    a = vision_agent(prompt='is playwright displayed', image_path=r'/Users/medvijenia/dev/bini-ai/data/images/main.png')
    import json
    print(json.dumps(a, indent=4))
