from crewai import Agent, Crew, Task
from crewai.project import CrewBase, agent, crew, task
from backend.utils.infrastructure import AgentInfrastructure
from backend.ai.agents.pipeline_agent.schemas import PipelineInput, PipelineOutput


@CrewBase
class PipelineAgent(AgentInfrastructure):

    def __init__(self, schema: PipelineInput) -> None:
        self.schema = schema

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
        return Task(config=self.tasks_config['generate_agent_md'], output_file=f'.claude/agents/{self.schema.agent_name}.md')

    @task
    def generate_skill_md(self) -> Task:
        return Task(config=self.tasks_config['generate_skill_md'], output_file=f'.claude/skills/{self.schema.skill_name}.md')

    @task
    def generate_commands(self) -> Task:
        return Task(config=self.tasks_config['generate_commands'], output_file=f'.claude/commands/{self.schema.command_name}.md')

    @crew
    def crew(self) -> Crew:
        return Crew(agents=self.agents, tasks=self.tasks, verbose=True)


def run_pipeline(name: str, purpose: str, trigger: str = "", tools: str = "", context: str = "") -> PipelineOutput:
    inputs = PipelineInput(name=name, purpose=purpose, trigger=trigger, tools=tools, context=context)
    result = PipelineAgent().crew().kickoff(inputs.model_dump())

    tasks_output = result.tasks_output
    return PipelineOutput(
        agent_md=tasks_output[0].raw,
        skill_md=tasks_output[1].raw,
        commands_md=tasks_output[2].raw,
    )


if __name__ == '__main__':
    import json
    out = run_pipeline(
        name="my-agent",
        purpose="Analyze screenshots and report UI regressions",
        trigger="/my-agent",
        tools="BiniVisionTool, ScreenshotTool",
        context="Used inside Claude Code for QA workflows",
    )
    print(json.dumps(out.model_dump(), indent=4))
