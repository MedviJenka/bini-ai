from crewai import Agent, Crew, Task, Process
from crewai.project import CrewBase, agent, crew, task
from crewai_tools import FileWriterTool, VisionTool
from backend.ai.agents.html_agent.schemas import PageBaseCSVSchema
from backend.settings import ImagePaths
from backend.utils.infrastructure import AgentInfrastructure
from playwright.sync_api import sync_playwright


def get_html() -> str:
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.goto("https://google.com")
        html = page.content()
        browser.close()
    return html


@CrewBase
class ElementsAgent(AgentInfrastructure):

    """Extracts UI elements from HTML and writes a page-based CSV file."""

    @agent
    def agent(self) -> Agent:
        return Agent(config=self.agents_config["agent"], llm=self.llm, tools=[FileWriterTool(), VisionTool()], verbose=False)

    @task
    def extract_elements(self, **kwargs) -> Task:
        return Task(config=self.tasks_config["extract_elements"], output_pydantic=PageBaseCSVSchema, **kwargs)

    @task
    def write_csv(self, **kwargs) -> Task:
        return Task(config=self.tasks_config["write_csv"], **kwargs)

    @crew
    def crew(self) -> Crew:
        return Crew(agents=self.agents, tasks=self.tasks, process=Process.sequential)


ElementsAgent().crew().kickoff(inputs={
    'image_path_url': ImagePaths.GOOGLE_MAIN_PAGE,
    "filename": "page_elements.csv",
    "directory": "./",
    "content": get_html()
})
