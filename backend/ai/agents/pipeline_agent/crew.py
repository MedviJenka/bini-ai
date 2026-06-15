from pathlib import Path
from crewai import Agent, Crew, Task
from crewai.project import CrewBase, agent, crew, task
from backend.utils.infrastructure import AgentInfrastructure
from backend.ai.agents.pipeline_agent.schemas import (
    PipelineInput,
    PipelineFlowInput,
    ItemOutput,
    PipelineOutput,
)


def _project_root() -> Path:
    p = Path(__file__).resolve()
    while p != p.parent:
        if (p / '.git').exists():
            return p
        p = p.parent
    raise RuntimeError("Could not locate project root (.git not found)")


@CrewBase
class PipelineAgent(AgentInfrastructure):

    @agent
    def agent_md_author(self) -> Agent:
        return Agent(config=self.agents_config['agent_md_author'], llm=self.llm)

    @agent
    def skill_md_author(self) -> Agent:
        return Agent(config=self.agents_config['skill_md_author'], llm=self.llm)

    @agent
    def commands_author(self) -> Agent:
        return Agent(config=self.agents_config['commands_author'], llm=self.llm)

    @task
    def generate_agent_md(self) -> Task:
        return Task(config=self.tasks_config['generate_agent_md'])

    @task
    def generate_skill_md(self) -> Task:
        return Task(config=self.tasks_config['generate_skill_md'])

    @task
    def generate_commands(self) -> Task:
        return Task(config=self.tasks_config['generate_commands'])

    @crew
    def crew(self) -> Crew:
        return Crew(agents=self.agents, tasks=self.tasks, verbose=True)


def run_agent_and_skill(item: PipelineInput, claude_dir: Path) -> ItemOutput:
    """Generate one agent.md + one skill.md for a single item."""
    pipeline = PipelineAgent()
    c = pipeline.crew()

    agent_task, skill_task = c.tasks[0], c.tasks[1]
    agent_task.output_file = str(claude_dir / 'agents' / f'{item.name}.md')
    skill_task.output_file = str(claude_dir / 'skills' / f'{item.name}.md')
    skill_task.context = [agent_task]

    sub = Crew(
        agents=[c.agents[0], c.agents[1]],
        tasks=[agent_task, skill_task],
        verbose=True,
    )
    result = sub.kickoff(item.model_dump())
    return ItemOutput(
        name=item.name,
        agent_md=result.tasks_output[0].raw,
        skill_md=result.tasks_output[1].raw,
    )


def generate_command_md(
    flow_input: PipelineFlowInput,
    item_outputs: list[ItemOutput],
    claude_dir: Path,
) -> str:
    """Generate one command.md that orchestrates all agents/skills."""
    pipeline = PipelineAgent()
    c = pipeline.crew()

    cmd_task = c.tasks[2]
    cmd_task.output_file = str(claude_dir / 'commands' / f'{flow_input.command_name}.md')
    cmd_task.context = []  # inject content via the {context} input variable instead

    agents_block = "\n\n---\n\n".join(
        f"### Agent: {o.name}\n\n{o.agent_md}" for o in item_outputs
    )
    skills_block = "\n\n---\n\n".join(
        f"### Skill: {o.name}\n\n{o.skill_md}" for o in item_outputs
    )
    context_blob = "\n\n".join(filter(None, [
        flow_input.command_context,
        f"ALL GENERATED AGENT DEFINITIONS:\n\n{agents_block}",
        f"ALL GENERATED SKILL DEFINITIONS:\n\n{skills_block}",
    ]))

    sub = Crew(agents=[c.agents[2]], tasks=[cmd_task], verbose=True)
    result = sub.kickoff({
        "name":           flow_input.command_name,
        "purpose":        flow_input.command_purpose,
        "trigger":        flow_input.command_trigger,
        "related_agents": ", ".join(o.name for o in item_outputs),
        "related_skills": ", ".join(o.name for o in item_outputs),
        "workflow":       flow_input.command_workflow or f"Orchestrate: {', '.join(o.name for o in item_outputs)}",
        "tools":          "",
        "context":        context_blob,
    })
    return result.tasks_output[0].raw


# Legacy single-item entry point
def run_pipeline(inputs: PipelineInput) -> PipelineOutput:
    root = _project_root()
    claude_dir = root / '.claude'

    pipeline = PipelineAgent()
    c = pipeline.crew()
    c.tasks[0].output_file = str(claude_dir / 'agents'   / f'{inputs.name}.md')
    c.tasks[1].output_file = str(claude_dir / 'skills'   / f'{inputs.name}.md')
    c.tasks[2].output_file = str(claude_dir / 'commands' / f'{inputs.name}.md')

    result = c.kickoff(inputs.model_dump())
    tasks_output = result.tasks_output
    return PipelineOutput(
        agent_md=tasks_output[0].raw,
        skill_md=tasks_output[1].raw,
        commands_md=tasks_output[2].raw,
    )
