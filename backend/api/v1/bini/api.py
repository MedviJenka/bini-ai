import json
from contextlib import asynccontextmanager
from typing import Annotated, Any, AsyncGenerator, Dict, Optional
from fastapi import APIRouter, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import JSONResponse, PlainTextResponse, Response
from pydantic import BaseModel
from backend.settings import Config
from backend.utils.logger import Logfire
from backend.ai.agents.text_agent.crew import text_agent
from backend.ai.agents.vision_agent.flow import bini_image
from backend.api.v1.bini.logic import StructuredOutputError, cleanup_files, json_schema_to_pydantic, parse_schema_output, save_temp_audio, save_temp_image


log = Logfire(name="bini-api")


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncGenerator:
    log.fire.info("Bini service started successfully")
    yield
    log.fire.info("Bini service shutting down")


router = APIRouter(prefix=f"/api/{Config.API_VERSION}/bini", tags=["bini"])


def _is_llm_config_error(exc: Exception) -> bool:
    return _llm_error_detail(exc) is not None


def _llm_error_detail(exc: Exception) -> str | None:
    exc_name = type(exc).__name__
    msg = str(exc)
    if "LLM Provider NOT provided" in msg:
        return "LLM provider is not configured"
    if exc_name in {"BadRequestError"} and "model=" in msg:
        return "LLM model or deployment is misconfigured"
    if "Azure endpoint not found" in msg or "Resource not found" in msg:
        return "Azure endpoint or deployment was not found. Check AZURE_API_BASE/AZURE_DEPLOYMENT_NAME or AZURE_VISION_API_BASE/AZURE_VISION_DEPLOYMENT_NAME."
    if "Azure" in msg and "not configured" in msg:
        return msg
    return None


def _plain_text_response(response: Any) -> PlainTextResponse:
    content = response if isinstance(response, str) else json.dumps(response, ensure_ascii=True)
    return PlainTextResponse(content=content)


def _structured_json_response(response: Any) -> JSONResponse:
    if not isinstance(response, dict):
        raise HTTPException(status_code=502, detail="Model output did not match requested schema")
    return JSONResponse(content=response)


@router.post("/image", response_model=None)
async def analyze_image(
    prompt: str = Form(),
    image: UploadFile = File(),
    schema_output: Annotated[str | None, Form()] = None,
    sample_image: Annotated[list[UploadFile] | None, File()] = None,
) -> Response:
    """With schema_output: returns structured JSON. With None: returns plain text."""
    pydantic_class, schema_error = parse_schema_output(schema_output)
    if schema_error:
        raise HTTPException(status_code=400, detail=schema_error)

    temp_files: list[str] = []

    try:
        main_image_path = await save_temp_image(image)
        temp_files.append(main_image_path)

        sample_paths: list[str] = []
        if sample_image:
            for sample in sample_image:
                path = await save_temp_image(sample)
                sample_paths.append(path)
                temp_files.append(path)

        try:
            response = await bini_image(
                prompt=prompt,
                image=main_image_path,
                sample_image=sample_paths or None,
                schema_output=pydantic_class,
            )
        except RuntimeError as e:
            raise HTTPException(status_code=503, detail=str(e))
        except StructuredOutputError as e:
            raise HTTPException(status_code=502, detail=str(e))
        except Exception as e:
            llm_error_detail = _llm_error_detail(e)
            if llm_error_detail:
                log.fire.error(f"LLM config error: {type(e).__name__}: {e}")
                raise HTTPException(status_code=503, detail=llm_error_detail)
            log.fire.error(f"Vision processing failed: {type(e).__name__}: {e}")
            raise HTTPException(status_code=500, detail="Vision processing failed")

        return _structured_json_response(response) if pydantic_class else _plain_text_response(response)

    finally:
        cleanup_files(temp_files)


class TextRequestSchema(BaseModel):
    prompt: str
    schema_output: Optional[Dict[str, Any]] = None


@router.post(path="/text", response_model=None)
async def analyze_text(body: TextRequestSchema) -> Response:
    """With schema_output: returns structured JSON. With None: returns plain text."""
    if body.schema_output is not None:
        try:
            json_schema_to_pydantic(body.schema_output)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Invalid schema_output: {e}")

    try:
        response = await text_agent(prompt=body.prompt, schema_output=body.schema_output)
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except StructuredOutputError as e:
        raise HTTPException(status_code=502, detail=str(e))
    except Exception as e:
        llm_error_detail = _llm_error_detail(e)
        if llm_error_detail:
            log.fire.error(f"LLM config error: {type(e).__name__}: {e}")
            raise HTTPException(status_code=503, detail=llm_error_detail)
        log.fire.error(f"Text processing failed: {type(e).__name__}: {e}")
        raise HTTPException(status_code=500, detail="Text processing failed")

    return _structured_json_response(response) if body.schema_output is not None else _plain_text_response(response)


@router.post("/audio", response_model=None)
async def analyze_voice(
    prompt: str = Form(),
    audio: UploadFile = File(),
    schema_output: Annotated[str | None, Form()] = None,
) -> Response:
    """Analyze an audio file with an optional output schema."""
    from backend.ai.agents.stt_agent.crew import bini_voice

    pydantic_class, schema_error = parse_schema_output(schema_output)
    if schema_error:
        raise HTTPException(status_code=400, detail=schema_error)

    temp_files: list[str] = []
    try:
        audio_path = await save_temp_audio(audio)
        temp_files.append(audio_path)

        try:
            response = await bini_voice(
                audio_file=audio_path,
                prompt=prompt,
                schema_output=pydantic_class,
            )
        except RuntimeError as e:
            raise HTTPException(status_code=503, detail=str(e))
        except StructuredOutputError as e:
            raise HTTPException(status_code=502, detail=str(e))
        except Exception as e:
            llm_error_detail = _llm_error_detail(e)
            if llm_error_detail:
                log.fire.error(f"LLM config error: {type(e).__name__}: {e}")
                raise HTTPException(status_code=503, detail=llm_error_detail)
            log.fire.error(f"Audio processing failed: {type(e).__name__}: {e}")
            raise HTTPException(status_code=500, detail="Audio processing failed")

        return _structured_json_response(response) if pydantic_class else _plain_text_response(response)

    finally:
        cleanup_files(temp_files)
