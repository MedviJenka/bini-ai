from typing import Optional, Type
from pydantic import BaseModel, Field
from crewai.flow import Flow, start, listen, router
from backend.ai.agents.text_agent.crew import text_agent
from backend.utils.logger import Logfire


log = Logfire("bini-text-flow")


class TextFlowState(BaseModel):
    prompt: str = ''
    schema_output: Optional[Type[BaseModel]] = None
    cache: dict = Field(default_factory=dict)


class BiniTextFlow(Flow[TextFlowState]):

    @start()
    async def run_text_agent(self) -> dict:
        log.fire.info(
            f"Starting text flow | prompt_length={len(self.state.prompt)} | structured_output={self.state.schema_output is not None}"
        )
        result = await text_agent(prompt=self.state.prompt, schema_output=self.state.schema_output)
        self.state.cache = result
        log.fire.info(f"Text flow completed agent step | response_type={type(result).__name__}")
        log.fire.debug(f"Text agent output: {result}")
        return result

    @router(run_text_agent)
    async def decision_point(self) -> str:
        decision = "Failed" if not self.state.cache or "N/A" in str(self.state.cache) else "Success"
        log.fire.info(f"Text flow decision point routed to: {decision}")
        if decision == "Failed":
            return "Failed"
        return "Success"

    @listen("Success")
    async def on_success(self) -> dict:
        log.fire.info("Text agent completed successfully.")
        return self.state.cache

    @listen("Failed")
    async def on_fail(self) -> None:
        log.fire.error("Text agent failed to process the prompt.")
        raise RuntimeError("Text agent evaluation failed")
