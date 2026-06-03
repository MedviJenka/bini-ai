from backend.ai.agents.vision_agent.crew import vision_agent
from pathlib import Path
from pydantic import BaseModel, Field
from crewai.flow import Flow, listen, start, router
from typing import Optional, Union


class ContentState(BaseModel):
    prompt:       str                        = ''
    image_path:   str                        = ''
    sample_image: Optional[Union[list, str]] = Field(default_factory=list)
    cache:        dict                       = {}

class ContentFlow(Flow[ContentState]):

    @start()
    def run_vision_agent(self) -> dict:
        self.state.cache = vision_agent(prompt=self.state.prompt, image_path=self.state.image_path, sample_image=self.state.sample_image)
        return self.state.cache

    @router(run_vision_agent)
    def generate_content(self):
        return 'Proceed' if self.state.cache['final_decision']['confidence_level'] > 90 else 'Revaluate'

    @listen('Proceed')
    def proceed_vision_agent(self): ...
    @listen('Revaluate')
    def revaluate_vision_agent(self): ...

    @listen(generate_content)
    def save_content(self):
        print("Saving content")
        output_dir = Path("output")
        output_dir.mkdir(exist_ok=True)
        with open(output_dir / "post.md", "w") as f:
            f.write(self.state.final_post)
        print("Post saved to output/post.md")
