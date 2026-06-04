import pytest
from backend.functions.common import BiniMCPClient


@pytest.fixture(scope="session")
def bini() -> BiniMCPClient:
    client = BiniMCPClient()
    client.connect()
    return client
