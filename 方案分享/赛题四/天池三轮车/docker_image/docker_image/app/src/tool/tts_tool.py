import base64
import json
import uuid
from enum import Enum
from pathlib import Path
from typing import Any, Dict, Optional

import requests
from pydantic import BaseModel, Field

from src.config import config
from src.logger import logger
from src.tool.base import BaseTool, ToolResult


_TTS_DESCRIPTION = """Text-to-Speech tool that converts text to audio using Volcengine TTS API.
Call this tool to generate speech from text."""


class TTSRequest(BaseModel):
    """Request model for TTS API"""

    text: str = Field(..., description="Text to convert to speech")
    encoding: str = Field("mp3", description="Audio encoding format")
    speed_ratio: float = Field(
        1.0, description="Speech speed ratio (0.5-2.0)", ge=0.5, le=2.0
    )
    volume_ratio: float = Field(
        1.0, description="Speech volume ratio (0.5-2.0)", ge=0.5, le=2.0
    )
    pitch_ratio: float = Field(
        1.0, description="Speech pitch ratio (0.5-2.0)", ge=0.5, le=2.0
    )
    text_type: str = Field("plain", description="Text type (plain or ssml)")
    with_frontend: int = Field(1, description="Whether to use frontend processing")
    frontend_type: str = Field("unitTson", description="Frontend type")
    uid: str = Field(default_factory=lambda: str(uuid.uuid4()), description="User ID")


class VoiceType(str, Enum):
    """Voice types available for TTS"""

    BEIJING_MALE = "zh_male_beijingxiaoye_moon_bigtts"
    FEMALE_CHUANMEI = "zh_female_daimengchuanmei_moon_bigtts"
    FEMALE_SAJIAO = "zh_female_sajiaonvyou_moon_bigtts"
    MALE_SHAONIAN = "zh_male_shaonianzixin_moon_bigtts"


class TTSResponse(BaseModel):
    """Response model for TTS operation"""

    success: bool = Field(..., description="Whether the TTS operation was successful")
    response: Optional[Dict[str, Any]] = Field(None, description="Raw API response")
    audio_data: Optional[str] = Field(None, description="Base64 encoded audio data")
    error: Optional[str] = Field(None, description="Error message if any")


class TTS:
    """
    Client for volcengine Text-to-Speech API.
    """

    def __init__(
        self,
        appid: str,
        access_token: str,
        cluster: str = "volcano_tts",
        voice_type: str = "BV700_V2_streaming",
        host: str = "openspeech.bytedance.com",
    ):
        """
        Initialize the volcengine TTS client.

        Args:
            appid: Platform application ID
            access_token: Access token for authentication
            cluster: TTS cluster name
            voice_type: Voice type to use
            host: API host
        """
        self.appid = appid
        self.access_token = access_token
        self.cluster = cluster
        self.voice_type = voice_type
        self.host = host
        self.api_url = f"https://{host}/api/v1/tts"
        self.header = {"Authorization": f"Bearer;{access_token}"}

    def text_to_speech(self, **kwargs) -> TTSResponse:
        """
        Convert text to speech using volcengine TTS API.

        Args:
            text: Text to convert to speech
            encoding: Audio encoding format
            speed_ratio: Speech speed ratio
            volume_ratio: Speech volume ratio
            pitch_ratio: Speech pitch ratio
            text_type: Text type (plain or ssml)
            with_frontend: Whether to use frontend processing
            frontend_type: Frontend type
            uid: User ID (generated if not provided)

        Returns:
            Dictionary containing the API response and base64-encoded audio data
        """
        # Create request model
        request = TTSRequest(**kwargs)

        request_json = {
            "app": {
                "appid": self.appid,
                "token": self.access_token,
                "cluster": self.cluster,
            },
            "user": {"uid": request.uid},
            "audio": {
                "voice_type": self.voice_type,
                "encoding": request.encoding,
                "speed_ratio": request.speed_ratio,
                "volume_ratio": request.volume_ratio,
                "pitch_ratio": request.pitch_ratio,
            },
            "request": {
                "reqid": str(uuid.uuid4()),
                "text": request.text,
                "text_type": request.text_type,
                "operation": "query",
                "with_frontend": request.with_frontend,
                "frontend_type": request.frontend_type,
            },
        }

        try:
            logger.debug(f"Sending TTS request for text: {request.text[:50]}...")
            response = requests.post(
                self.api_url, json.dumps(request_json), headers=self.header
            )
            response_json = response.json()

            if response.status_code != 200:
                logger.error(f"TTS API error: {response_json}")
                return TTSResponse(success=False, error=str(response_json))

            if "data" not in response_json:
                logger.error(f"TTS API returned no data: {response_json}")
                return TTSResponse(success=False, error="No audio data returned")

            return TTSResponse(
                success=True,
                response=response_json,
                audio_data=response_json["data"],
            )

        except Exception as e:
            logger.exception(f"Error in TTS API call: {str(e)}")
            return TTSResponse(success=False, error=str(e))


class TTSTool(BaseTool):
    name: str = "text_to_speech"
    description: str = _TTS_DESCRIPTION

    parameters: dict = {
        "type": "object",
        "properties": {
            "text": {
                "type": "string",
                "description": "The text to convert to speech",
            },
            "voice_type": {
                "type": "string",
                "description": "The voice type to use for synthesis",
                "default": VoiceType.BEIJING_MALE,
                "enum": [v.value for v in VoiceType],
            },
            "output_file": {
                "type": "string",
                "description": "Path to save the output audio file",
                "default": "output.mp3",
            },
            "speed_ratio": {
                "type": "number",
                "description": "Speech speed ratio (0.5-2.0)",
                "default": 1.0,
                "minimum": 0.5,
                "maximum": 2.0,
            },
            "volume_ratio": {
                "type": "number",
                "description": "Speech volume ratio (0.5-2.0)",
                "default": 1.0,
                "minimum": 0.5,
                "maximum": 2.0,
            },
            "pitch_ratio": {
                "type": "number",
                "description": "Speech pitch ratio (0.5-2.0)",
                "default": 1.0,
                "minimum": 0.5,
                "maximum": 2.0,
            },
        },
        "required": ["text"],
    }

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # 从config中获取TTS配置或使用传入的参数覆盖
        self._tts_config = config.tts_config

    async def execute(self, **kwargs) -> ToolResult:
        """Convert text to speech using Volcengine TTS API"""
        try:
            # 直接获取参数，无需使用TTSToolConfig
            text = kwargs.get("text")
            voice_type = kwargs.get("voice_type", self._tts_config.default_voice_type)

            # 构建输出文件路径
            output_file = kwargs.get("output_file")
            if not output_file:
                # 生成默认输出文件名
                filename = f"tts_{uuid.uuid4().hex[:8]}.mp3"
                output_file = str(Path(self._tts_config.default_output_dir) / filename)

            speed_ratio = kwargs.get("speed_ratio", 1.0)
            volume_ratio = kwargs.get("volume_ratio", 1.0)
            pitch_ratio = kwargs.get("pitch_ratio", 1.0)

            # 参数验证
            if not text:
                return ToolResult(error="Text parameter is required")

            if (
                not isinstance(speed_ratio, (int, float))
                or not 0.5 <= speed_ratio <= 2.0
            ):
                return ToolResult(error="Speed ratio must be between 0.5 and 2.0")

            if (
                not isinstance(volume_ratio, (int, float))
                or not 0.5 <= volume_ratio <= 2.0
            ):
                return ToolResult(error="Volume ratio must be between 0.5 and 2.0")

            if (
                not isinstance(pitch_ratio, (int, float))
                or not 0.5 <= pitch_ratio <= 2.0
            ):
                return ToolResult(error="Pitch ratio must be between 0.5 and 2.0")

            # Initialize TTS client
            tts_client = TTS(
                appid=self._tts_config.appid,
                access_token=self._tts_config.access_token,
                cluster=self._tts_config.cluster,
                voice_type=voice_type,
                host=self._tts_config.host,
            )

            # Convert text to speech
            result = tts_client.text_to_speech(
                text=text,
                speed_ratio=speed_ratio,
                volume_ratio=volume_ratio,
                pitch_ratio=pitch_ratio,
            )

            if not result.success:
                return ToolResult(
                    error=f"Text-to-speech conversion failed: {result.error}"
                )

            # Save the audio data to a file
            audio_data = base64.b64decode(result.audio_data)

            # Ensure directory exists
            output_path = Path(output_file)
            output_path.parent.mkdir(parents=True, exist_ok=True)

            with open(output_path, "wb") as f:
                f.write(audio_data)

            # 可选：自动播放音频
            self.play_audio(str(output_path))

            return ToolResult(
                output=f"Text-to-speech conversion successful! Audio saved to {output_file}"
            )

        except Exception as e:
            return ToolResult(error=f"Error in text-to-speech conversion: {str(e)}")

    @staticmethod
    def play_audio(audio_file: str) -> None:
        """Play the audio file using platform-specific methods"""
        try:
            import platform

            system = platform.system()

            if system == "Windows":
                import winsound

                winsound.PlaySound(audio_file, winsound.SND_FILENAME)
            elif system == "Darwin":  # macOS
                import subprocess

                subprocess.run(["afplay", audio_file])
            else:  # Linux and others
                import subprocess

                players = ["mpg123", "play"]

                for player in players:
                    try:
                        subprocess.run([player, audio_file], check=False)
                        return  # Successfully played the audio
                    except FileNotFoundError:
                        continue

                logger.warning(
                    f"Could not play audio: No suitable player found. Audio saved to {audio_file}"
                )
        except Exception as e:
            logger.error(f"Error playing audio: {str(e)}")
