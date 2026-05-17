from dataclasses import dataclass, field
from typing import Optional, Union, Any, Dict
from pydantic import BaseModel
from mcp import ClientSession
from mcp.types import CallToolResult, ListToolsResult
from mcp.client.streamable_http import streamablehttp_client
from backend.utils.logger import Logfire

log = Logfire(name="mcp-manager")


@dataclass
class MCPManager:
    url: str
    config: Dict[str, Any] = field(default_factory=dict)

    async def list_tools(self) -> ListToolsResult:
        async with streamablehttp_client(self.url) as (reader, writer, _):
            async with ClientSession(reader, writer) as session:
                await session.initialize()
                tools = await session.list_tools()
                log.fire.info(f"Available tools: {tools}")
                return tools

    async def call_tool(
        self,
        name: str,
        arguments: Optional[Union[BaseModel, dict]] = None
    ) -> CallToolResult:
        args = arguments.model_dump() if isinstance(arguments, BaseModel) else (arguments or {})
        async with streamablehttp_client(self.url) as (reader, writer, _):
            async with ClientSession(reader, writer) as session:
                await session.initialize()
                result = await session.call_tool(name=name, arguments=args)
                log.fire.info(f"Tool '{name}' result: {result}")
                return result


if __name__ == "__main__":
    import asyncio

    grafana_data = {
      "mcpServers": {
        "grafana": {
          "command": "mcp-grafana",
          "args": [],
          "env": {
            "GRAFANA_URL": "http://10.8.2.35:3001",
            "GRAFANA_USERNAME": "admin",
            "GRAFANA_PASSWORD": "admin",
            "GRAFANA_ORG_ID": "2"
          }
        }
      }
    }

    manager = MCPManager(
        url="ws://localhost:8000",
        config=grafana_data
    )

    async def run():
        await manager.list_tools()
        await manager.call_tool("hello", {"name": "Jenia"})

    asyncio.run(run())
