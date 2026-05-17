import os
import json
import requests
import mimetypes
from pathlib import Path
from pydantic import BaseModel
from contextlib import ExitStack
from dataclasses import dataclass
from backend.settings import Config
from functools import cached_property
from backend.utils.logger import Logfire
from typing import Any, Iterable, Optional, Type, Union


type PathLike = Union[str, os.PathLike]

log = Logfire(name='bini-client')


@dataclass
class BiniClient:

    host: str = Config.HOST
    port: int | str = Config.PORT
    endpoint: str = "/api/v1/bini"
    timeout: int = 5 * 60

    @cached_property
    def _session(self) -> requests.Session:
        return requests.Session()

    @property
    def _server_url(self) -> str:
        url = f"http://{self.host}:{self.port}{self.endpoint}"
        log.fire.info(f'bini endpoint service located in: {url}')
        return url

    @staticmethod
    def _content_type(path: PathLike) -> str:
        return mimetypes.guess_type(path)[0] or 'application/octet-stream'

    @staticmethod
    def _decode_response(response: requests.Response, expect_structured: bool) -> Union[dict, str]:
        if expect_structured:
            payload = response.json()
            if not isinstance(payload, dict):
                raise ValueError("Expected structured JSON object response")
            return payload

        content_type = response.headers.get("content-type", "").lower()
        if "application/json" in content_type:
            try:
                payload = response.json()
            except ValueError:
                return response.text
            if isinstance(payload, dict):
                return payload.get("result") or payload.get("response") or response.text
            if isinstance(payload, str):
                return payload
        return response.text

    @staticmethod
    def _raise_for_status(response: requests.Response) -> None:
        try:
            response.raise_for_status()
        except requests.HTTPError as exc:
            detail = None
            content_type = response.headers.get("content-type", "").lower()
            if "application/json" in content_type:
                try:
                    payload = response.json()
                except ValueError:
                    payload = None
                if isinstance(payload, dict):
                    detail = payload.get("detail")
            if detail:
                raise requests.HTTPError(f"{exc}. Response detail: {detail}", response=response) from exc
            raise

    def run_image(self,
                  prompt: str,
                  image: PathLike,
                  sample_image: Optional[Union[PathLike, Iterable[PathLike]]] = None,
                  schema_output: Optional[Type[BaseModel]] = None
                  ) -> Union[dict, str]:
        """
        POST image(s) and prompt to the /bini/image endpoint.
        Sends schema as a raw JSON string, relying on server deserialization.
        """

        main = Path(image)
        log.fire.info(f"Preparing to send image to Bini image endpoint: {main}")

        if not main.is_file():
            return {"status": 400, "error": f"Main image not found: {main}"}

        data = {"prompt": prompt}

        if schema_output:
            data["schema_output"] = json.dumps(schema_output.model_json_schema())

        file_payload = []

        try:
            with ExitStack() as stack:
                # Main image
                file_payload.append(
                    (
                        "image",
                        (
                            main.name,
                            stack.enter_context(open(main, "rb")),
                            self._content_type(main),
                        ),
                    )
                )

                # Normalize sample_image to a list
                if sample_image:
                    if isinstance(sample_image, (str, Path)):
                        sample_images = [sample_image]
                    else:
                        sample_images = list(sample_image)

                    for path in sample_images:
                        sp = Path(path)
                        if not sp.is_file():
                            raise FileNotFoundError(f"Sample image not found: {sp}")

                        file_payload.append(
                            (
                                "sample_image",
                                (
                                    sp.name,
                                    stack.enter_context(open(sp, "rb")),
                                    self._content_type(sp),
                                )
                            )
                        )

                response = self._session.post(url=f"{self._server_url}/image", data=data, files=file_payload, timeout=self.timeout)
                self._raise_for_status(response)
                result = self._decode_response(response, expect_structured=schema_output is not None)

                log.fire.info(
                    f"Received response from Bini image endpoint: {result} "
                    f"with status code: {response.status_code}"
                )

                return result

        except requests.Timeout:
            log.fire.error("Request to Bini image endpoint timed out")
            raise
        except requests.RequestException as e:
            log.fire.error(f"Request to Bini image endpoint failed: {e}")
            raise

    def run_text(self, prompt: str, schema_output: Optional[Type[BaseModel]] = None) -> Union[dict, str]:

        url = f"{self._server_url}/text"

        payload: dict[str, Any] = {"prompt": prompt}

        if schema_output:
            payload["schema_output"] = schema_output.model_json_schema()

        try:
            response = self._session.post(
                url=url,
                json=payload,
                timeout=self.timeout
            )

            self._raise_for_status(response)
            result = self._decode_response(response, expect_structured=schema_output is not None)

            log.fire.info(
                f"Received response from Bini text endpoint: {result} "
                f"with status code: {response.status_code}"
            )

            return result

        except requests.Timeout:
            log.fire.error("Request to Bini text endpoint timed out")
            raise

        except requests.RequestException as e:
            log.fire.error(f"Request to Bini text endpoint failed: {e}")
            raise

    def run_audio(self) -> None:
        raise NotImplementedError

    def run_video(self) -> None:
        raise NotImplementedError

    def close(self) -> None:
        self._session.close()
