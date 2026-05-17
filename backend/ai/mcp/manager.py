from pydantic import BaseModel
from dataclasses import dataclass
from typing import Optional, Union
from mcp.types import CallToolResult
from backend.utils.logger import Logfire
from mcp import ClientSession, ListToolsResult
from mcp.client.streamable_http import streamablehttp_client


log = Logfire(name='mcp-manager')


@dataclass
class MCPManager:

    """MCP manager is a factory class for easy mcp functions creation and to prevent DRY"""

    url: str

    async def get_tools(self) -> ListToolsResult:
        """get available tools"""
        async with streamablehttp_client(self.url) as (r, w, _):
            async with ClientSession(r, w) as session:
                await session.initialize()
                tools = await session.list_tools()
                log.fire.info(f"available tools: {tools}")
                return tools

    async def create_session(self, name: str, arguments: Optional[Union[BaseModel, dict]] = None) -> CallToolResult:

        """
        visit: https://smithery.ai
        create remote session.
        - name retrieves from smithery tool name
        - arguments is a dict retrieved from smithery tool
        """

        if isinstance(arguments, BaseModel):
            arguments = arguments.model_dump()

        async with streamablehttp_client(self.url) as (r, w, _):
            async with ClientSession(r, w) as session:
                await session.initialize()
                result = await session.call_tool(name=name, arguments=arguments or {})
                log.fire.info(f"map result: {result}")
                return result


def example() -> None:
    import asyncio
    manager = MCPManager(url='https://smithery.ai/server/@kiennd/reference-servers')
    print(asyncio.run(manager.create_session(name='thought')))
