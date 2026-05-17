import json
from typing import Type, Union, Optional
from pydantic import BaseModel
from crewai import Agent, Crew, Task
from crewai.project import CrewBase, agent, crew, task
from backend.api.v1.bini.logic import validate_structured_output
from backend.ai.tools.vision_tool import BiniVisionTool
from backend.utils.infrastructure import AgentInfrastructure


@CrewBase
class ComputerVisionAgent(AgentInfrastructure):

    def __init__(self, schema_output: Optional[Type[BaseModel]] = None) -> None:
        self.schema_output = schema_output

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
        return Task(config=self.tasks_config['validate_requirements'], output_pydantic=self.schema_output, **kwargs)

    @crew
    def crew(self) -> Crew:
        return Crew(agents=self.agents, tasks=self.tasks, verbose=True)


def computer_vision_agent(
    prompt: str,
    image_path: str,
    sample_image: Optional[Union[list, str]] = None,
    schema_output: Optional[Type[BaseModel]] = None
) -> dict | str:

    effective_prompt = prompt
    crew_schema = schema_output

    if schema_output is not None:
        schema_json = json.dumps(schema_output.model_json_schema(), ensure_ascii=True)
        effective_prompt = (
            f"{prompt}\n\n"
            "Return only a valid JSON object that matches the requested schema exactly.\n"
            f"JSON Schema: {schema_json}\n"
            "Rules:\n"
            "- Output must be a JSON object only.\n"
            "- Do not wrap the JSON in markdown or code fences.\n"
            "- Include every required field from the schema.\n"
            "- Do not add fields that are not defined in the schema.\n"
        )
        crew_schema = None

    cv = ComputerVisionAgent(schema_output=crew_schema)
    response = cv.crew().kickoff({"prompt": effective_prompt, "image": image_path, "sample_image": sample_image})
    if schema_output:
        if response.pydantic is not None:
            return validate_structured_output(schema_output, response.pydantic)
        return validate_structured_output(schema_output, response.raw)
    return response.raw


# ------------------- #
#       Example       #
# ------------------- #

if __name__ == '__main__':

    from backend.paths import ImagePaths
    from tests.data.schemas import InteractionsRecordingOutputSchema

    _response = computer_vision_agent(
        prompt='is sample image displayed in the main image?',
        image_path=ImagePaths.IR_IMAGE,
        sample_image=ImagePaths.IR_PLAY_BUTTON_SAMPLE_IMAGE,
        # schema_output=InteractionsRecordingOutputSchema
    )

    print('\n', _response)
