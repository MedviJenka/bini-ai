import json
import os
import tempfile
from typing import Any, Dict, Tuple, Type
from pydantic import BaseModel, Field, create_model
from backend.utils.logger import Logfire
from fastapi import HTTPException, UploadFile


log = Logfire(name='bini-helper-functions')

ALLOWED_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp"}
ALLOWED_AUDIO_EXTENSIONS = {".wav", ".mp3", ".ogg", ".flac", ".m4a", ".webm"}

MAX_FILE_SIZE = 100 * 1024 * 1024

TEXT_ALLOWED_EXTENSIONS = {".txt", ".json", ".csv"}


class StructuredOutputError(ValueError):
    """Raised when model output does not match the requested dynamic schema."""


def json_schema_to_pydantic(schema: Dict[str, Any]) -> Type[BaseModel]:
    """Convert JSON schema dict to a Pydantic BaseModel class. Handles $defs enums."""
    from enum import Enum as PyEnum

    defs = schema.get('$defs', {})
    enum_map = {}

    for def_name, def_schema in defs.items():
        if 'enum' in def_schema:
            # Create enum with values as both name and value for LLM compatibility
            enum_values = {f'VALUE_{i}': val for i, val in enumerate(def_schema['enum'])}
            enum_map[def_name] = PyEnum(def_name, enum_values)

    type_map = {
        'string': str,
        'integer': int,
        'number': float,
        'boolean': bool,
        'object': dict[str, Any],
    }

    def resolve_field_type(field_info: Dict[str, Any]) -> Any:
        if '$ref' in field_info:
            ref_name = field_info['$ref'].split('/')[-1]
            if ref_name in enum_map:
                return enum_map[ref_name]
            if ref_name in defs:
                return resolve_field_type(defs[ref_name])
            return Any

        if 'enum' in field_info:
            enum_name = field_info.get('title', 'InlineEnum')
            enum_values = {f'VALUE_{i}': val for i, val in enumerate(field_info['enum'])}
            return PyEnum(enum_name, enum_values)

        if 'anyOf' in field_info:
            non_null_variants = [variant for variant in field_info['anyOf'] if variant.get('type') != 'null']
            if len(non_null_variants) == 1:
                return resolve_field_type(non_null_variants[0]) | None
            return Any

        field_type_name = field_info.get('type', 'string')
        if field_type_name == 'array':
            item_schema = field_info.get('items', {})
            item_type = resolve_field_type(item_schema) if item_schema else Any
            return list[item_type]

        return type_map.get(field_type_name, str)

    fields = {}
    properties = schema.get('properties', {})
    required = set(schema.get('required', []))

    for field_name, field_info in properties.items():
        field_type = resolve_field_type(field_info)
        default = ... if field_name in required else field_info.get('default', None)

        constraints = {}
        if 'description' in field_info:
            constraints['description'] = field_info['description']
        if 'minimum' in field_info:
            constraints['ge'] = field_info['minimum']
        if 'maximum' in field_info:
            constraints['le'] = field_info['maximum']

        if constraints:
            fields[field_name] = (field_type, Field(default, **constraints))
        else:
            fields[field_name] = (field_type, default)

    return create_model(schema.get('title', 'DynamicModel'), **fields)


def parse_schema_output(schema_raw: str | None) -> Tuple[Type[BaseModel] | None, str | None]:
    """Parse JSON schema string to Pydantic model. Returns (model, None) or (None, error)."""
    if not schema_raw or not schema_raw.strip():
        return None, None
    try:
        schema = json.loads(schema_raw)
    except json.JSONDecodeError as e:
        return None, f"Invalid JSON in schema_output: {e}"
    if not isinstance(schema, dict):
        return None, "schema_output must be a JSON object"
    try:
        return json_schema_to_pydantic(schema), None
    except Exception as e:
        log.fire.warning(f"Schema parsing failed: {e}")
        return None, str(e)


def validate_structured_output(schema_model: Type[BaseModel], payload: Any) -> dict[str, Any]:
    """Validate arbitrary model output against the requested dynamic schema."""
    if isinstance(payload, BaseModel):
        candidate: Any = payload.model_dump(mode="json")
    elif isinstance(payload, dict):
        candidate = payload
    elif isinstance(payload, str):
        try:
            candidate = json.loads(payload)
        except json.JSONDecodeError as exc:
            raise StructuredOutputError("Model returned non-JSON output for schema_output") from exc
    else:
        raise StructuredOutputError(f"Unsupported structured output type: {type(payload).__name__}")

    if not isinstance(candidate, dict):
        raise StructuredOutputError("Structured output must be a JSON object")

    try:
        return schema_model.model_validate(candidate).model_dump(mode="json")
    except Exception as exc:
        raise StructuredOutputError(f"Model output did not match requested schema: {exc}") from exc


def validate_image_file(filename: str, size: int) -> str:
    """Validate uploaded image; return extension."""
    if not filename:
        raise HTTPException(status_code=400, detail="No filename provided")

    file_ext = os.path.splitext(filename)[1].lower()
    if file_ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type. Allowed: {', '.join(ALLOWED_EXTENSIONS)}"
        )

    if size > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="File too large")

    return file_ext


def validate_text_file(filename: str, size: int) -> str:
    if not filename:
        raise HTTPException(status_code=400, detail="No filename provided")
    ext = os.path.splitext(filename)[1].lower()
    if ext not in TEXT_ALLOWED_EXTENSIONS:
        allowed = ", ".join(sorted(TEXT_ALLOWED_EXTENSIONS))
        raise HTTPException(status_code=400, detail=f"Invalid file type. Allowed: {allowed}")
    if size > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="File too large")
    return ext


def decode_text_bytes(data: bytes) -> str:
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError:
        for enc in ("utf-16", "latin-1"):
            try:
                return data.decode(enc)
            except UnicodeDecodeError:
                continue
    return data.decode("utf-8", errors="replace")


async def save_temp_image(file: UploadFile) -> str:
    """Validate and save uploaded image to a temporary file."""
    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Uploaded image is empty.")
    ext = validate_image_file(file.filename, len(content))
    with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp:
        tmp.write(content)
        return tmp.name


async def save_temp_audio(file: UploadFile) -> str:
    """Validate and save uploaded audio to a temporary file."""
    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Uploaded audio file is empty.")
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided")
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in ALLOWED_AUDIO_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid audio file type. Allowed: {', '.join(sorted(ALLOWED_AUDIO_EXTENSIONS))}"
        )
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="Audio file too large")
    with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp:
        tmp.write(content)
        return tmp.name


def cleanup_files(paths: list[str]) -> None:
    """Safely delete temp files after use."""
    for path in paths:
        try:
            if os.path.exists(path):
                os.unlink(path)
                log.fire.info(f"Deleted temp file: {path}")
        except Exception as cleanup_err:
            log.fire.warning(f"Cleanup failed for {path}: {cleanup_err}")

