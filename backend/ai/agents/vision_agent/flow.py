import asyncio
from typing import Optional, Type, Union
from pydantic import BaseModel
from backend.utils.logger import Logfire
from backend.ai.agents.english_agent.crew import english_agent
from backend.ai.agents.vision_agent.crew import computer_vision_agent


log = Logfire(name="bini-flow")


async def bini_image(
    prompt: str,
    image: str,
    sample_image: Union[str, list, None] = None,
    schema_output: Optional[Type[BaseModel]] = None,
) -> dict | str:
    samples = [sample_image] if isinstance(sample_image, str) else (sample_image or [])
    log.fire.info(
        f"Starting image flow | image={image} | sample_count={len(samples)} | structured_output={schema_output is not None}"
    )

    try:
        refined_prompt = await asyncio.to_thread(english_agent, prompt=prompt)
        log.fire.debug(f"Refined prompt: {refined_prompt}")

        response = await asyncio.to_thread(
            computer_vision_agent,
            prompt=refined_prompt,
            image_path=image,
            sample_image=samples,
            schema_output=schema_output,
        )
    except Exception:
        log.fire.exception(f"Image flow failed | image={image} | sample_count={len(samples)}")
        raise

    log.fire.info(f"Image flow completed | response_type={type(response).__name__}")
    log.fire.debug(f"Image flow response payload: {response}")
    return response


if __name__ == '__main__':
    from backend.paths import ImagePaths
    from tests.data.schemas import InteractionsRecordingOutputSchema

    _response = bini_image(
        prompt='is sample image displayed in the main image?',
        image=ImagePaths.IR_IMAGE,
        sample_image=ImagePaths.IR_PLAY_BUTTON_SAMPLE_IMAGE,
        schema_output=InteractionsRecordingOutputSchema,
    )

    print(asyncio.run(_response))
