import json
import base64
import requests
from pathlib import Path
from typing import Optional
from dataclasses import dataclass, field
from utils.logger import Logger


log = Logger(name='vision-mcp-function')


@dataclass
class BiniMCPClient:

    base_url: str = "http://localhost:6000/mcp"
    _session_id: Optional[str] = field(default=None, init=False, repr=False)

    @property
    def _headers(self) -> dict:
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
        }
        if self._session_id:
            headers["Mcp-Session-Id"] = self._session_id
        return headers

    def connect(self) -> None:
        response = requests.post(self.base_url, headers=self._headers, json={
            "jsonrpc": "2.0",
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "bini-client", "version": "1.0"},
            },
            "id": 0,
        })
        response.raise_for_status()
        self._session_id = response.headers.get("Mcp-Session-Id")
        log.fire.info("MCP session established", session_id=self._session_id)

    def analyze_image(self, prompt: str, image_path: str, sample_images: Optional[list[str]] = None) -> dict:
        if not self._session_id:
            self.connect()

        image_b64 = self._encode_image(image_path)
        arguments = {"prompt": prompt, "image": image_b64}
        if sample_images:
            arguments["sample_image"] = [self._encode_image(p) for p in sample_images]

        response = requests.post(self.base_url, headers=self._headers, json={
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {"name": "Vision", "arguments": arguments},
            "id": 1,
        })
        response.raise_for_status()
        result = self._parse_response(response)
        crew_response = result["result"]["structuredContent"]
        log.fire.info(f"Vision response received\n{json.dumps(crew_response, indent=4)}")
        return crew_response

    @staticmethod
    def _parse_response(response: requests.Response) -> dict:
        content_type = response.headers.get("Content-Type", "")
        if "text/event-stream" in content_type:
            for line in response.text.splitlines():
                if line.startswith("data:"):
                    payload = line[len("data:"):].strip()
                    if payload:
                        return json.loads(payload)
            raise ValueError("No data found in SSE response")
        return response.json()

    @staticmethod
    def _encode_image(path: str) -> str:
        data = Path(path).read_bytes()
        return base64.b64encode(data).decode()


if __name__ == "__main__":
    bini = BiniMCPClient()
    print(bini.analyze_image(prompt='what is displayed?', image_path=r'C:\Users\medvi\OneDrive\Desktop\bini-ai\data\images\main.png'))