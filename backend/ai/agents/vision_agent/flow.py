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

class VisionFlow(Flow[ContentState]):

    @start()
    def run_vision_agent(self) -> dict:
        self.state.cache = vision_agent(prompt=self.state.prompt, image_path=self.state.image_path, sample_image=self.state.sample_image)
        return self.state.cache

    @router(run_vision_agent)
    def decision_point_1(self) -> str:
        return 'Success' if self.state.cache['final_decision']['confidence_level'] > 100 else 'Fail'

    @listen('Proceed')
    def on_success(self) -> None:
        import json
        print(json.dumps(self.state.cache, indent=4))

    @listen('Fail')
    def on_fail(self):
        print(f'agent confidence level is {self.state.cache['final_decision']['confidence_level']}, re running')
        return 'Fail'

    @router(on_fail)
    def decision_point_2(self) -> None:
        self.run_vision_agent()

    # @listeen('Proceed')
    # def save_content(self):
    #     print("Saving content")
    #     output_dir = Path("output")
    #     output_dir.mkdir(exist_ok=True)
    #     with open(output_dir / "post.md", "w") as f:
    #         f.write(f'{self.state.cache}')
    #     print("Post saved to output/post.md")


if __name__ == '__main__':
    a = VisionFlow().kickoff(inputs={'prompt': 'is playwright displayed', 'image_path': r'/Users/medvijenia/dev/bini-ai/data/images/main.png'})
    import json
    print(json.dumps(a, indent=4))
