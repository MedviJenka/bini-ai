from backend.ai.agents.vision_agent.crew import vision_agent
from pydantic import BaseModel, Field
from crewai.flow import Flow, listen, start, router
from typing import Optional, Union
from backend.utils.logger import Logger


log = Logger(name="VisionFlow")

MAX_RETRIES = 3

MIN_CONFIDENCE = 95


class ContentState(BaseModel):
    prompt:       str                        = ''
    image_path:   str                        = ''
    sample_image: Optional[Union[list, str]] = Field(default_factory=list)
    cache:        dict                       = {}
    retries:      int                        = 0


class VisionFlow(Flow[ContentState]):

    @start()
    def run_vision_agent(self) -> dict:
        self.state.cache = vision_agent(prompt=self.state.prompt, image_path=self.state.image_path, sample_image=self.state.sample_image)
        return self.state.cache

    @router(run_vision_agent)
    def evaluate_confidence(self) -> str:
        confidence = self.state.cache["final_decision"]["confidence_level"]
        if confidence >= MIN_CONFIDENCE:
            return "Success"
        if self.state.retries >= MAX_RETRIES:
            log.fire.warning(f"Max retries ({MAX_RETRIES}) reached at confidence {confidence}")
            return "Success"
        return "Retry"

    @listen("Success")
    def on_success(self) -> dict:
        return self.state.cache

    @listen("Retry")
    def on_retry(self) -> dict:
        self.state.retries += 1
        confidence = self.state.cache["final_decision"]["confidence_level"]
        log.fire.info(f"Confidence {confidence} below {MIN_CONFIDENCE}, retry {self.state.retries}/{MAX_RETRIES}")
        self.state.cache = vision_agent(
            prompt=self.state.prompt,
            image_path=self.state.image_path,
            sample_image=self.state.sample_image,
        )
        return self.state.cache

    @router(on_retry)
    def evaluate_retry(self) -> str:
        return self.evaluate_confidence()


if __name__ == '__main__':
    import json
    result = VisionFlow().kickoff(inputs={
        'prompt': 'is playwright displayed',
        'image_path': r'C:\Users\medvi\OneDrive\Desktop\bini-ai\data\images\main.png',
    })
    print(json.dumps(result, indent=4))
