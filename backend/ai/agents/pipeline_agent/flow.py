from pathlib import Path
from pydantic import BaseModel
from typing import Optional
from crewai.flow import Flow, listen, start
from backend.ai.agents.pipeline_agent.crew import run_agent_and_skill, generate_command_md
from backend.ai.agents.pipeline_agent.schemas import (
    PipelineInput,
    PipelineFlowInput,
    PipelineFlowOutput,
    ItemOutput,
)


def _project_root() -> Path:
    p = Path(__file__).resolve()
    while p != p.parent:
        if (p / '.git').exists():
            return p
        p = p.parent
    raise RuntimeError("Could not locate project root (.git not found)")


class PipelineState(BaseModel):
    flow_input: Optional[PipelineFlowInput] = None
    item_outputs: list[ItemOutput] = []
    command_md: str = ""


class PipelineFlow(Flow[PipelineState]):

    @start()
    def generate_artifacts(self) -> list[ItemOutput]:
        claude_dir = _project_root() / '.claude'
        outputs = [
            run_agent_and_skill(item, claude_dir)
            for item in self.state.flow_input.items
        ]
        self.state.item_outputs = outputs
        return outputs

    @listen(generate_artifacts)
    def generate_command(self) -> str:
        claude_dir = _project_root() / '.claude'
        cmd_md = generate_command_md(
            flow_input=self.state.flow_input,
            item_outputs=self.state.item_outputs,
            claude_dir=claude_dir,
        )
        self.state.command_md = cmd_md
        return cmd_md


def run_pipeline_flow(flow_input: PipelineFlowInput) -> PipelineFlowOutput:
    flow = PipelineFlow()
    flow.state.flow_input = flow_input
    flow.kickoff()
    return PipelineFlowOutput(
        items=flow.state.item_outputs,
        command_md=flow.state.command_md,
    )


if __name__ == '__main__':
    import json

    out = run_pipeline_flow(PipelineFlowInput(
        items=[
            PipelineInput(
                name="change-analyzer",
                purpose="Analyze changed files for test coverage gaps and missing test files",
                tools="Read, Grep, Glob, Edit",
                workflow="Read QA standards → scan changed files → detect missing tests → write JSON findings to qa-reports/.cache/change-analysis.json",
            ),
            PipelineInput(
                name="react-pattern-agent",
                purpose="Audit React components for pattern violations (hooks, lifecycle, DOM mutations)",
                tools="Grep, Glob, Read, Edit",
                workflow="Glob components → grep each pattern rule → collect violations → write JSON findings to qa-reports/.cache/react-patterns.json",
            ),
        ],
        command_name="qa-full",
        command_purpose="Run a full QA regression pipeline: analyze changes, check React patterns, and produce a risk report",
        command_trigger="/qa-full",
        command_workflow=(
            "Phase 1: load qa-methodology and react-patterns skills. "
            "Phase 2: run change-analyzer and react-pattern-agent in parallel. "
            "Phase 3: run qa-reporter to aggregate findings. "
            "Phase 4: print risk summary to console."
        ),
    ))
    print(json.dumps(out.model_dump(), indent=4))
