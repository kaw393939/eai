"""
ElevenLabs audio generation service.

Implements high-quality text-to-speech, voice cloning, and dialogue generation
using the ElevenLabs API.
"""

from collections.abc import Iterator
from pathlib import Path

from elevenlabs.client import ElevenLabs
from elevenlabs.core.api_error import ApiError

from ei_cli.config import get_settings


class ElevenLabsAudioService:
    """
    Service for generating speech using ElevenLabs TTS.

    Supports:
    - Multiple models (Multilingual v2, Flash v2.5, Turbo v2.5)
    - High-quality voice synthesis
    - Streaming audio generation
    - Custom voice settings
    - Latency optimization
    """

    # Available models
    MODEL_MULTILINGUAL_V2 = "eleven_multilingual_v2"
    MODEL_FLASH_V2_5 = "eleven_flash_v2_5"
    MODEL_TURBO_V2_5 = "eleven_turbo_v2_5"

    # Default pre-made voices
    DEFAULT_VOICES = {
        "rachel": "21m00Tcm4TlvDq8ikWAM",  # American female
        "clyde": "2EiwWnXFnvU5JabPnv8n",  # American male
        "domi": "AZnzlk1XvdvUeBnXmlld",  # American female
        "dave": "CYw3kZ02Hs0563khs1Fj",  # British male
        "fin": "D38z5RcWu1voky8WS1ja",  # Irish male
        "bella": "EXAVITQu4vr4xnSDxMaL",  # American female
        "antoni": "ErXwobaYiN019PkySvjV",  # American male
        "thomas": "GBv7mTt0atIp3Br8iCZE",  # American male
        "charlie": "IKne3meq5aSn9XLyUdCD",  # Australian male
        "emily": "LcfcDJNUP1GQjkzn1xUU",  # American female
        "elli": "MF3mGyEYCl7XYWbV9V6O",  # American female
        "callum": "N2lVS1w4EtoT3dr4eOWO",  # American male
        "patrick": "ODq5zmih8GrVes37Dizd",  # American male
        "harry": "SOYHLrjzK2X1ezoPC6cr",  # American male
        "liam": "TX3LPaxmHKxFdv7VOQHJ",  # American male
        "dorothy": "ThT5KcBeYPX3keUQqHPh",  # British female
        "josh": "TxGEqnHWrfWFTfGW9XjX",  # American male
        "arnold": "VR6AewLTigWG4xSOukaG",  # American male
        "charlotte": "XB0fDUnXU5powFXDhCwa",  # English-Swedish female
        "alice": "Xb7hH8MSUJpSbSDYk0k2",  # British female
        "matilda": "XrExE9yKIg1WjnnlVkGX",  # American female
        "james": "ZQe5CZNOzWyzPSCn5a3c",  # Australian male
        "joseph": "Zlb1dXrM653N07WRdFW3",  # British male
        "jeremy": "bVMeCyTHy58xNoL34h3p",  # American male-Irish
        "michael": "flq6f7yk4E4fJM5XTYuZ",  # American male
        "ethan": "g5CIjZEefAph4nQFvHAz",  # American male
        "chris": "iP95p4xoKVk53GoZ742B",  # American male
        "gigi": "jBpfuIE2acCO8z3wKNLl",  # American female
        "freya": "jsCqWAovK2LkecY7zXl4",  # American female
        "brian": "nPczCjzI2devNBz1zQrb",  # American male
        "grace": "oWAxZDx7w5VEj9dCyTzz",  # American-Southern female
        "daniel": "onwK4e9ZLuTAKqWW03F9",  # British male
        "lily": "pFZP5JQG7iQjIQuC4Bku",  # British female
        "serena": "pMsXgVXv3BLzUgSXRplE",  # American female
        "adam": "pNInz6obpgDQGcFmaJgB",  # American male
        "nicole": "piTKgcLEGmPE4e6mEKli",  # American female
        "bill": "pqHfZKP75CvOlQylNhV4",  # American male
        "jessie": "t0jbNlBVZ17f02VDIeMI",  # American male
        "sam": "yoZ06aMxZJJ28mfd3POQ",  # American male
        "glinda": "z9fAnlkpzviPz146aGWa",  # American female
        "giovanni": "zcAOhNBS3c14rBihAFp1",  # English-Italian male
        "mimi": "zrHiDhphv9ZnVXBqCLjz",  # English-Swedish female
    }

    def __init__(self, api_key: str | None = None):
        """
        Initialize ElevenLabs service.

        Args:
            api_key: ElevenLabs API key. If not provided, will try to get from settings.
        """
        if api_key is None:
            settings = get_settings()
            if settings.api.elevenlabs_api_key:
                api_key = settings.api.elevenlabs_api_key.get_secret_value()
            else:
                raise ValueError(
                    "ElevenLabs API key not configured. "
                    "Set API__ELEVENLABS_API_KEY in your .env file.",
                )

        self.client = ElevenLabs(api_key=api_key)
        self.default_model = self.MODEL_MULTILINGUAL_V2
        self.default_voice = self.DEFAULT_VOICES["rachel"]

    def text_to_speech(
        self,
        text: str,
        *,
        voice: str | None = None,
        model: str | None = None,
        output_format: str = "mp3_44100_128",
        stability: float = 0.5,
        similarity_boost: float = 0.75,
        style: float = 0.0,
        use_speaker_boost: bool = True,
        optimize_streaming_latency: int | None = None,
    ) -> bytes:
        """
        Generate speech from text.

        Args:
            text: Text to convert to speech
            voice: Voice ID or name. Defaults to 'rachel'
            model: Model ID (eleven_multilingual_v2, eleven_flash_v2_5, eleven_turbo_v2_5)
            output_format: Audio format (mp3_44100_128, mp3_22050_32, pcm_16000, etc.)
            stability: Voice stability (0.0-1.0, higher = more consistent)
            similarity_boost: Voice similarity (0.0-1.0, higher = closer to original)
            style: Style exaggeration (0.0-1.0)
            use_speaker_boost: Enable speaker similarity enhancement
            optimize_streaming_latency: Latency optimization (0-4, None = default)

        Returns:
            Audio data as bytes

        Raises:
            ValueError: If voice or model is invalid
            ApiError: If API request fails
        """
        voice_id = self._resolve_voice_id(voice)
        model_id = model or self.default_model

        try:
            # Generate audio
            audio_generator = self.client.text_to_speech.convert(
                voice_id=voice_id,
                text=text,
                model_id=model_id,
                output_format=output_format,
                voice_settings={
                    "stability": stability,
                    "similarity_boost": similarity_boost,
                    "style": style,
                    "use_speaker_boost": use_speaker_boost,
                },
                optimize_streaming_latency=optimize_streaming_latency,
            )

            # Collect all audio chunks
            audio_bytes = b"".join(audio_generator)
            return audio_bytes

        except ApiError as e:
            raise RuntimeError(f"ElevenLabs API error: {e}") from e

    def text_to_speech_stream(
        self,
        text: str,
        *,
        voice: str | None = None,
        model: str | None = None,
        output_format: str = "mp3_44100_128",
        stability: float = 0.5,
        similarity_boost: float = 0.75,
        style: float = 0.0,
        use_speaker_boost: bool = True,
        optimize_streaming_latency: int = 0,
    ) -> Iterator[bytes]:
        """
        Generate speech from text with streaming.

        Args:
            text: Text to convert to speech
            voice: Voice ID or name. Defaults to 'rachel'
            model: Model ID
            output_format: Audio format
            stability: Voice stability (0.0-1.0)
            similarity_boost: Voice similarity (0.0-1.0)
            style: Style exaggeration (0.0-1.0)
            use_speaker_boost: Enable speaker similarity enhancement
            optimize_streaming_latency: Latency optimization (0-4)

        Yields:
            Audio chunks as bytes

        Raises:
            ValueError: If voice or model is invalid
            ApiError: If API request fails
        """
        voice_id = self._resolve_voice_id(voice)
        model_id = model or self.default_model

        try:
            # Generate audio with streaming
            audio_generator = self.client.text_to_speech.convert(
                voice_id=voice_id,
                text=text,
                model_id=model_id,
                output_format=output_format,
                voice_settings={
                    "stability": stability,
                    "similarity_boost": similarity_boost,
                    "style": style,
                    "use_speaker_boost": use_speaker_boost,
                },
                optimize_streaming_latency=optimize_streaming_latency,
            )

            # Yield audio chunks
            for chunk in audio_generator:
                yield chunk

        except ApiError as e:
            raise RuntimeError(f"ElevenLabs API error: {e}") from e

    def save_audio(self, audio_data: bytes, output_path: Path) -> None:
        """
        Save audio data to file.

        Args:
            audio_data: Audio bytes to save
            output_path: Path where audio should be saved
        """
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(audio_data)

    def _resolve_voice_id(self, voice: str | None) -> str:
        """
        Resolve voice name to voice ID.

        Args:
            voice: Voice name or ID

        Returns:
            Voice ID

        Raises:
            ValueError: If voice is invalid
        """
        if voice is None:
            return self.default_voice

        # Check if it's a named voice
        if voice.lower() in self.DEFAULT_VOICES:
            return self.DEFAULT_VOICES[voice.lower()]

        # Assume it's a voice ID
        return voice

    def list_available_voices(self) -> dict[str, str]:
        """
        Get list of available default voices.

        Returns:
            Dictionary mapping voice names to voice IDs
        """
        return self.DEFAULT_VOICES.copy()

    def get_available_models(self) -> list[str]:
        """
        Get list of available models.

        Returns:
            List of model IDs
        """
        return [
            self.MODEL_MULTILINGUAL_V2,
            self.MODEL_FLASH_V2_5,
            self.MODEL_TURBO_V2_5,
        ]
