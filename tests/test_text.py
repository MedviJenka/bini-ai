from enum import Enum
import pytest
import uvicorn
import threading
from time import sleep
from services.bini import app
from pydantic import BaseModel, Field
from typing import Generator, Type
from client.bini import BiniClient
from backend.utils.logger import Logfire
from crewai.project.wrappers import CrewClass
from backend.ai.agents.text_agent.crew import TextAgent
from tests.data.schemas import ConfidenceSchema, ConfidenceSchema2, OutputSchema, ChatOutputSchema


log = Logfire(name='bini-service-test')


TEXT = """
US Public Meeting Minutes based on Agenda<br><br><div dir=ltr><div>
<h1>CITY OF BAKERSFIELD</h1>
<h2>CITY COUNCIL<br>REGULAR MEETING<br>August 27, 2025</h2>
<p style="text-align:center; font-style:italic;">Meeting called to order at 3:30 PM in the Council Chambers, City Hall, 1501 Truxtun Avenue.</p>

<h3>1. ROLL CALL</h3>
<p><strong>Meeting Called to Order:</strong> 3:30 PM on August 27th, 2025</p>
<p><strong>Presiding Officer:</strong> Mayor Karen Goh</p>
<p><strong>Roll Call Conducted By:</strong> City Clerk Julie Drimakis</p>
<p><strong>Members Present:</strong></p>
<ul>
<li>Mayor Goh</li>
<li>Vice Mayor Core</li>
<li>Councilmember Weir</li>
<li>Councilmember Smith</li>
<li>Councilmember Coleman</li>
<li>Councilmember Bashir Tosh</li>
</ul>
<p><strong>Members Absent:</strong></p>
<ul>
<li>Councilmember Arias</li>
<li>Councilmember Gonzalez</li>
</ul>
<p><strong>Quorum Established:</strong> Yes</p>

<h3>2. PUBLIC STATEMENTS</h3>

<h4>a. Non-Agenda Item Public Statements</h4>
<p><strong>Public Statement Rules:</strong> Rules were read with a time limit of 2 minutes per speaker and total time limit of 20 minutes.</p>
<p><strong>Public Speakers:</strong></p>
<ul>
<li><strong>Dave Domenowski, Home Builders Association of Kern County:</strong> Spoke about governor's budget trailer bill including vehicle miles travel tax on new single family and multifamily development. Cited Caltrans study showing potential impact fees over $200,000 for single family homes and rent increases up to $1,300/month in LA County. Requested council consider taking position supporting repeal of VMT provisions in Section 58 of AB130.</li>
</ul>
<p><strong>Council Discussion:</strong> Councilmember Weir requested opposition letter. City Manager Christian Clegg confirmed staff has been following the trailer bill and recommended bringing back letter of opposition for council vote. Councilmember Coleman made referral for staff to prepare letter of support for immediate repeal of Section 58 in Assembly Bill 130.</p>
<p><strong>Action Taken:</strong> Staff directed to prepare letter of opposition to VMT provisions and bring back to council for consideration.</p>

<h4>b. Agenda Item Public Statements</h4>
<p style="font-style:italic; color:#666; margin-left:20px;"><em>No specific action or detailed discussion was recorded for this agenda item.</em></p>

<h3>3. REPORTS</h3>

<h4>a. Update on City Council Priority Initiatives and Council Referrals</h4>
<p><strong>Staff Presenter:</strong> City Manager Christian Clegg</p>
<p><strong>Staff Presentation Summary:</strong> Provided comprehensive update on city council priority initiatives and referrals. Presented annual work plan covering council priority initiatives, reporting 57 of 88 previous initiatives completed, 31 ongoing. Council identified 6 priorities: 1) Enhance accountability in criminal justice system, 2) Revitalize urban core, 3) Finish undeveloped parks, 4) Enhance performance management systems, 5) Habitat conservation plan, 6) Smart growth and master planning. Detailed components and timelines for each priority area including jail bed capacity, downtown vision plan, park development, performance audits, habitat conservation framework, and development standards updates.</p>

<p>The presentation also covered Complete Streets projects, energy efficiency studies, community choice aggregation feasibility analysis, solar street lighting projects, various transportation projects (Higman flyover, Chester Ave, MLK, Niles, Monterey, California Ave), fueling stations, facilities master plan, smart growth initiatives, special events process update, illegal dumping, tree canopy and heat island effect referrals, neighborhood business zones, highway corridor beautification, water and wastewater rates, urban water management plan, budget community engagement, motel registry, vacant building ordinance, operational review of departments, key performance indicators, staffing study, real-time information center, financial reporting catch-up, ERP implementation challenges with HR module, and various technology tools.</p>

<p><strong>Council Discussion:</strong> Mayor Goh questioned impact of referrals outside the six priorities on staff's ability to focus, noting nearly 60% of referrals go outside priorities. She reminded council of formal referral process and option to express disagreement during meetings. Council Member Coleman discussed minimizing referrals, suggested review process for overlapping referrals, asked about four-hour rule implementation, inquired about One Stop Shop delays and EOA program updates. City Manager explained referral tracking system, duplicate referral closure process, four-hour rule procedures, One Stop Shop progress with physical space completion expected in couple months, permit streamlining challenges with electronic permitting software, and EOA program policy review including potential new EOA areas.</p>

<p><strong>Motion:</strong> Motion to receive and file</p>
<p><strong>Moved by:</strong> Vice Mayor</p>
<p><strong>Vote Result:</strong> Carried with Council Members Arias and Gonzalez absent and one member voting no</p>
<p><strong>Action Taken:</strong> Report received and filed with recommendation for council discussion and affirmation related to prioritization of city initiatives and council referrals.</p>

<h3>4. CLOSED SESSION</h3>

<h4>a. Conference with Legal Counsel - Existing Litigation</h4>
<p><strong>Matter:</strong> Closed Session pursuant to Government Code Section 54956.9(d)(1) regarding Stephanie Deniece Martin v. Griffin Michael Turner; City of Bakersfield; and Does 1 to 10 Kern County Superior Court Case No. BCV-23-104141</p>
<p><strong>Action:</strong> Council adjourned to closed session at 4:38 PM and reconvened at 4:53 PM</p>

<h3>5. CLOSED SESSION ACTION</h3>
<p><strong>Report by City Attorney:</strong> City Attorney reported there was one item in closed session and by a 5-0 vote with Council Members Arias and Gonzalez absent, the City Attorney's office was given direction regarding the litigation matter.</p>

<h3>6. ADJOURNMENT</h3>
<p><strong>Meeting Adjourned:</strong> 4:54 PM</p>

<hr>
<p><strong>ATTESTATION</strong></p>
<p>I hereby certify that the foregoing minutes are a true and correct record of the proceedings of the Bakersfield City Council Regular Meeting held on August 27, 2025.</p>
<br>
<p>_________________________________</p>
<p>Julie Drimakis, City Clerk</p>
<br>
<p>Date: _____________________</p>
</div></div><br><br>
"""


class SummaryRanksSchema(str, Enum):
    VERY_POOR = "1: The summary is missing most of the key points and lacks coherence. It fails to capture the essence of the meeting and provides little to no value to the reader."
    POOR      = "2: The summary includes some key points but is incomplete and lacks clarity. It may contain inaccuracies or irrelevant information, making it difficult for the reader to understand the main outcomes of the meeting."
    FAIR      = "3: The summary covers the main points of the meeting but may miss some details. It is generally coherent but could be more concise and better organized to enhance readability."
    GOOD      = "4: The summary is comprehensive and captures the key points of the meeting"
    EXCELLENT = "5: The summary is thorough and captures all key points of the meeting with"


class EvaluationSchema(BaseModel):
    summary_evaluation_score: SummaryRanksSchema = Field(..., description="summary evaluation score")
    evaluation_score:         int                = Field(..., description="Numeric score 1-5", ge=1, le=5)


@pytest.fixture(scope='function')
def agent() -> CrewClass:
    """Provides a fresh ChatAgent instance for each test."""
    return TextAgent()


@pytest.fixture(scope="session", autouse=True)
def client() -> Generator:
    """to run parallel: pytest -n auto --dist=loadscope --disable-warnings"""
    config = uvicorn.Config(app=app, host="0.0.0.0", port=9999, log_level="critical", workers=4, lifespan='on')
    uvicorn_server = uvicorn.Server(config)
    thread = threading.Thread(target=uvicorn_server.run, daemon=True)
    thread.start()
    sleep(2)
    bini_client = BiniClient(host="localhost", port=9999)
    yield bini_client
    uvicorn_server.should_exit = True
    thread.join(timeout=5)


@pytest.fixture(scope='function')
def bini() -> BiniClient:
    log.fire.info(f'bini client: {BiniClient.__name__}')
    return BiniClient()


def read_html() -> str:
    with open(r'C:\Users\evgenyp\Bini\Bini\tests\data\tenants.html', 'r', encoding='utf-8') as file:
        return file.read()


@pytest.fixture(scope='function')
def text_agent() -> CrewClass:
    """Provides a fresh TextAgent instance for each test."""
    return TextAgent()


class TestBiniChatFlow:
    """Test cases for ChatAgent and BiniChatFlow execution."""

    @pytest.fixture(autouse=True)
    def setup(self) -> None:
        """Setup before each test."""
        self.agent = TextAgent()

    def test_sanity(self) -> None:
        """Ensure the agent executes without a schema."""
        response = self.agent.crew().kickoff({'prompt': "what is the capital of France?"})
        assert response.raw is not None, log.fire.error("Expected a non-empty response")

    def test_sanity_2(self) -> None:
        self.agent.schema_output = ConfidenceSchema2
        response = self.agent.crew().kickoff({'prompt': "What is the capital of France?"}).model_dump()
        assert isinstance(response, dict), log.fire.error("Expected response to be a dictionary")
        assert response, log.fire.error("Confidence score should be non-negative")

    @pytest.mark.parametrize(
        "schema,prompt",
        [
            (OutputSchema, "Extract image metadata in JSON"),
            (ConfidenceSchema, "Explain this code and return a confidence score"),
        ],
    )
    def test_dynamic_schema_execution(self, schema: Type[BaseModel], prompt: str) -> None:
        """Ensure the agent executes correctly with dynamic schemas."""
        self.agent.schema_output = schema
        response = self.agent.crew().kickoff({'prompt': prompt}).model_dump()
        assert response is not None
        assert isinstance(response, dict), "Expected string output before parsing"

    def test_evaluation(self) -> None:
        self.agent.schema_output = EvaluationSchema
        with open(r'C:\Users\evgenyp\Bini\Bini\tests\data\meetings\summary.txt', 'r') as text:
            response = self.agent.crew().kickoff({'prompt': text.read()})
            log.fire.info(f'bini client response: {response}')
            print(response)
            assert response

    def test_html_file(self) -> None:
        assert self.agent.crew().kickoff({'prompt': f"Analyze this HTML content: {read_html()}"})


class TestTextService:

    @pytest.fixture(autouse=True)
    def setup(self, client: BiniClient) -> None:
        self.bini = client

    @pytest.mark.parametrize('city, answer', [
        ('France', 'Paris'),
        ('Germany', 'Berlin'),
        ('Italy', 'Rome')
    ])
    def test_without_schema(self, city: str, answer: str) -> None:
        response = self.bini.run_text(prompt=f'what is the capital of {city}?')
        print(response)
        assert answer in response, log.fire.error(f"Test failed with response")

    @pytest.mark.parametrize('city, answer', [
        ('France', 'Paris'),
        ('Germany', 'Berlin'),
        ('Italy', 'Rome')
    ])
    def test_sanity_with_schema(self, city: str, answer: str) -> None:
        response = self.bini.run_text(prompt=f'what is the capital of {city}?', schema_output=ChatOutputSchema)
        log.fire.info(f'bini client response: {response}')
        assert response.get('confidence_in_precent') > 90, log.fire.error(f"Test failed with response")
        print(response)

    def test_evaluation_api(self) -> None:
        with open(r'C:\Users\evgenyp\Bini\Bini\tests\data\meetings\summary.txt', 'r') as text:
            response = self.bini.run_text(prompt=text.read(), schema_output=EvaluationSchema)
            log.fire.info(f'bini client response: {response}')
        print(response)
        assert response.get('evaluation_score') == 5
