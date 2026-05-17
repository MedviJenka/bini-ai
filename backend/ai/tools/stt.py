import time
from dataclasses import dataclass
from functools import cached_property
from typing import MutableSequence, Type
import azure.cognitiveservices.speech as speech
from crewai.tools import BaseTool
from pydantic import BaseModel, Field
from backend.settings import Config
from backend.utils.logger import Logfire


log = Logfire(name="stt-tool")


class SpeakerSegment(BaseModel):
    start: float
    end: float
    text: str


@dataclass
class AzureSpeechEngine:

    def __post_init__(self) -> None:
        if not Config.BINI_STT_API_KEY or not Config.BINI_STT_REGION:
            raise RuntimeError(
                "Azure STT is not configured. Set BINI_STT_API_KEY and BINI_STT_REGION environment variables."
            )
        self.speech_config = speech.SpeechConfig(subscription=Config.BINI_STT_API_KEY, region=Config.BINI_STT_REGION)
        self.speech_config.speech_recognition_language = "en-US"
        self.speech_config.enable_automatic_punctuation = True

    def recognize(self, audio_file: str, timeout_sec: int = 300) -> MutableSequence[str]:

        results: list[str] = []
        done = False

        def on_recognized(event: speech.SpeechRecognitionEventArgs) -> None:
            if event.result.text:
                results.append(event.result.text)

        def on_stop(_: speech.SessionEventArgs) -> None:
            nonlocal done
            done = True

        audio_config = speech.audio.AudioConfig(filename=audio_file)
        recognizer = speech.SpeechRecognizer(speech_config=self.speech_config, audio_config=audio_config,)
        recognizer.recognized.connect(on_recognized)
        recognizer.session_stopped.connect(on_stop)
        recognizer.canceled.connect(on_stop)

        recognizer.start_continuous_recognition()

        start_time = time.time()
        log.fire.info(f"Azure STT recognition started at: {start_time}")

        while not done:
            if time.time() - start_time > timeout_sec:
                recognizer.stop_continuous_recognition()
                raise TimeoutError("Azure STT recognition timed out")
            time.sleep(0.1)

        recognizer.stop_continuous_recognition()
        log.fire.info(f"Azure STT recognition completed with {len(results)} segments.")
        log.fire.info(f"Transcription results: {results}")
        return results


class VoiceToolInput(BaseModel):
    audio_file: str = Field(..., description="Path to an audio file (WAV PCM recommended)")


class STTTool(BaseTool):

    name: str = "Speech-to-Text Tool"
    description: str = "Transcribes speech from audio files using Azure Speech-to-Text."
    args_schema: Type[BaseModel] = VoiceToolInput

    def __init__(self) -> None:
        super().__init__()

    @cached_property
    def engine(self) -> AzureSpeechEngine:
        return AzureSpeechEngine()

    def _run(self, **kwargs: str) -> MutableSequence[str]:
        audio_file = kwargs["audio_file"]
        log.fire.info("Running Azure STT")

        try:
            return self.engine.recognize(audio_file)
        except Exception as exc:
            log.fire.error(f"Azure STT failed: {exc}")
            raise
