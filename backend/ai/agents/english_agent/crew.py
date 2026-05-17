from crewai import Agent, Crew, Task
from crewai.project import CrewBase, agent, crew, task
from backend.utils.infrastructure import AgentInfrastructure


@CrewBase
class EnglishAgent(AgentInfrastructure):

    """EnglishAgent is a CrewBase class that defines a crew for refining English prompts."""

    @agent
    def agent(self) -> Agent:
        return Agent(config=self.agents_config['agent'], llm=self.llm)

    @task
    def grammar(self, **kwargs) -> Task:
        return Task(config=self.tasks_config['grammar'], **kwargs)

    @crew
    def crew(self) -> Crew:
        return Crew(agents=self.agents, tasks=self.tasks, verbose=False)


def english_agent(prompt: str) -> str:
    return EnglishAgent().crew().kickoff(inputs={'prompt': prompt}).raw


if __name__ == '__main__':
    english_agent("What is the capital of France?")
