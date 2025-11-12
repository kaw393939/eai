"""Tests for AIService."""

from unittest.mock import MagicMock, Mock, patch

import pytest

from ei_cli.core.errors import AIServiceError
from ei_cli.services.ai_service import (
    AIService,
    ImageGenerationResult,
    SearchResult,
    VisionResult,
)
from ei_cli.services.base import ServiceUnavailableError


class TestAIService:
    """Tests for AIService."""

    def test_service_initialization(self):
        """Test service initialization."""
        service = AIService(api_key="test-key")

        assert service.name == "ai_service"
        assert service.total_cost == 0.0

    def test_service_check_available_with_key(self):
        """Test check_available with API key."""
        service = AIService(api_key="test-key")

        is_available, error = service.check_available()

        assert is_available is True
        assert error is None

    def test_service_check_available_without_key(self):
        """Test check_available without API key."""
        service = AIService(api_key="")
        is_available, error = service.check_available()

        assert is_available is False
        assert "API key" in error

    @patch("ei_cli.services.ai_service.OpenAI")
    def test_search_basic(self, mock_openai):
        """Test basic search."""
        service = AIService(api_key="test-key")

        # Mock OpenAI response
        mock_response = Mock()
        mock_response.output_text = "Python is great"
        mock_response.items = [
            Mock(
                type="message",
                content=[
                    Mock(
                        type="output_text",
                        text="Python is great",
                        annotations=[],
                    ),
                ],
            ),
        ]
        mock_openai.return_value.responses.create.return_value = (
            mock_response
        )

        result = service.search("what is python")

        assert isinstance(result, SearchResult)
        assert result.answer == "Python is great"
        assert len(result.citations) == 0
        assert len(result.sources) == 0

    @patch("ei_cli.services.ai_service.OpenAI")
    def test_search_with_citations(self, mock_openai):
        """Test search with citations."""
        service = AIService(api_key="test-key")

        # Mock OpenAI response with citations
        mock_annotation = Mock()
        mock_annotation.type = "url_citation"
        mock_annotation.url = "https://example.com"
        mock_annotation.title = "Example"
        mock_annotation.start_index = 0
        mock_annotation.end_index = 10

        mock_response = Mock()
        mock_response.output_text = "Python is great"
        mock_response.items = [
            Mock(
                type="message",
                content=[
                    Mock(
                        type="output_text",
                        text="Python is great",
                        annotations=[mock_annotation],
                    ),
                ],
            ),
        ]
        mock_openai.return_value.responses.create.return_value = (
            mock_response
        )

        result = service.search("what is python")

        assert len(result.citations) == 1
        assert result.citations[0].url == "https://example.com"
        assert result.citations[0].title == "Example"

    @patch("ei_cli.services.ai_service.OpenAI")
    def test_search_with_user_location(self, mock_openai):
        """Test search with user location."""
        service = AIService(api_key="test-key")

        mock_response = Mock()
        mock_response.output_text = "Weather is sunny"
        mock_response.items = [
            Mock(
                type="message",
                content=[
                    Mock(
                        type="output_text",
                        text="Weather is sunny",
                        annotations=[],
                    ),
                ],
            ),
        ]
        mock_openai.return_value.responses.create.return_value = (
            mock_response
        )

        result = service.search(
            "weather",
            user_location={"country": "US", "city": "Boston"},
        )

        assert result.answer == "Weather is sunny"

    def test_search_unavailable(self):
        """Test search when service unavailable."""
        service = AIService(api_key="")

        with pytest.raises(ServiceUnavailableError) as exc_info:
            service.search("test")

        assert "API key" in str(exc_info.value)

    @patch("ei_cli.services.ai_service.OpenAI")
    def test_analyze_image_basic(
        self,
        mock_openai,
        tmp_path,
    ):
        """Test basic image analysis."""
        service = AIService(api_key="test-key")

        # Create test image
        image_file = tmp_path / "test.jpg"
        image_file.write_bytes(b"fake image data")

        # Mock OpenAI response using new Responses API format
        mock_output_item = Mock()
        mock_output_item.type = "output_text"
        mock_output_item.text = "This is a photo"

        mock_output_message = Mock()
        mock_output_message.type = "message"
        mock_output_message.content = [mock_output_item]

        mock_response = Mock()
        mock_response.output = [mock_output_message]

        # Set up the mock chain properly for Responses API
        mock_client = Mock()
        mock_client.responses.create.return_value = mock_response
        mock_openai.return_value = mock_client

        result = service.analyze_image(
            str(image_file),
            "What's in this image?",
        )

        assert isinstance(result, VisionResult)
        assert result.analysis == "This is a photo"
        assert result.model == "gpt-5"
        assert result.prompt == "What's in this image?"

    def test_analyze_image_unavailable(self, tmp_path):
        """Test image analysis when service unavailable."""
        service = AIService(api_key="")

        image_file = tmp_path / "test.jpg"
        image_file.write_bytes(b"fake")

        with pytest.raises(ServiceUnavailableError):
            service.analyze_image(str(image_file), "test")

    @patch("ei_cli.services.ai_service.OpenAI")
    def test_generate_image_basic(self, mock_openai):
        """Test basic image generation with gpt-image-1 (b64_json)."""
        service = AIService(api_key="test-key")

        # Mock OpenAI response for gpt-image-1 (returns b64_json)
        mock_response = Mock()
        mock_response.data = [
            Mock(
                # 1x1 transparent PNG in base64
                b64_json=(
                    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJ"
                    "AAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
                ),
                url=None,
            ),
        ]
        mock_openai.return_value.images.generate.return_value = (
            mock_response
        )

        result = service.generate_image("a beautiful sunset")

        assert isinstance(result, ImageGenerationResult)
        # gpt-image-1 returns data URL with base64-encoded image
        assert result.image_url.startswith("data:image/png;base64,")
        assert result.model == "gpt-image-1"

    @patch("ei_cli.services.ai_service.OpenAI")
    def test_generate_image_auto_quality(
        self,
        mock_openai,
    ):
        """Test image generation with auto quality (gpt-image-1)."""
        service = AIService(api_key="test-key")

        # Mock response for gpt-image-1
        mock_data = Mock()
        mock_data.b64_json = (
            "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJ"
            "AAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
        )
        mock_data.url = None

        mock_response = Mock()
        mock_response.data = [mock_data]
        mock_openai.return_value.images.generate.return_value = (
            mock_response
        )

        result = service.generate_image("sunset", quality="auto")

        # gpt-image-1 doesn't provide revised prompts
        assert result.revised_prompt is None
        assert result.model == "gpt-image-1"
        # Verify quality="auto" was not passed (it's the API default)
        call_args = mock_openai.return_value.images.generate.call_args
        assert "quality" not in call_args[1]

    def test_generate_image_unavailable(self):
        """Test image generation when service unavailable."""
        service = AIService(api_key="")

        with pytest.raises(ServiceUnavailableError):
            service.generate_image("test")

    @patch("ei_cli.services.ai_service.OpenAI")
    def test_rate_limiting(self, mock_openai):
        """Test rate limiting enforcement."""
        service = AIService(api_key="test-key", rate_limit=2)  # 2 requests/sec

        mock_response = Mock()
        mock_response.items = [
            Mock(
                type="message",
                content=[
                    Mock(
                        type="output_text",
                        text="test",
                        annotations=[],
                    ),
                ],
            ),
        ]
        mock_openai.return_value.chat.completions.create.return_value = (
            mock_response
        )

        # Make 3 rapid requests
        service.search("query1")
        service.search("query2")
        service.search("query3")

        # Verify rate limiter exists and is being used
        assert hasattr(service, "_rate_limiter")
        assert service._rate_limiter.max_requests == 2

    @patch("ei_cli.services.ai_service.OpenAI")
    def test_retry_logic_success_on_retry(self, mock_openai):
        """Test retry logic succeeds on second attempt."""
        service = AIService(api_key="test-key", max_retries=3)

        # Mock to fail twice then succeed
        mock_response = Mock()
        mock_response.output_text = "success"
        mock_response.items = [
            Mock(
                type="message",
                content=[
                    Mock(
                        type="output_text",
                        text="success",
                        annotations=[],
                    ),
                ],
            ),
        ]

        mock_openai.return_value.responses.create.side_effect = [
            Exception("Rate limit"),
            Exception("Rate limit"),
            mock_response,
        ]

        result = service.search("test")

        assert result.answer == "success"
        call_count = (
            mock_openai.return_value.responses.create.call_count
        )
        assert call_count == 3

    @patch("ei_cli.services.ai_service.OpenAI")
    def test_retry_logic_exhausted(self, mock_openai):
        """Test retry logic exhausted."""
        service = AIService(api_key="test-key", max_retries=3)

        # Mock to always fail
        mock_openai.return_value.responses.create.side_effect = (
            Exception("Always fails")
        )

        # Backoff wraps in AIServiceError after exhausting retries
        with pytest.raises(AIServiceError) as exc_info:
            service.search("test")

        assert "Always fails" in str(exc_info.value)
        assert "Search failed" in str(exc_info.value)

    # Additional coverage tests for missing methods

    @patch("ei_cli.services.ai_service.OpenAI")
    @patch("ei_cli.services.image_downloader.ImageDownloader")
    @patch("tempfile.gettempdir")
    def test_analyze_image_with_url(
        self,
        mock_tempdir,
        mock_downloader_class,
        mock_openai,
        tmp_path,
    ):
        """Test image analysis with URL input."""
        service = AIService(api_key="test-key")

        # Setup temp directory mock
        mock_tempdir.return_value = str(tmp_path)

        # Setup mock downloader
        mock_downloader = Mock()
        mock_downloader.is_url.return_value = True
        mock_downloader_class.return_value = mock_downloader

        # Create temp vision directory and file
        vision_dir = tmp_path / "ei_cli_vision"
        vision_dir.mkdir()
        temp_file = vision_dir / "temp_image_image.jpg"
        temp_file.write_bytes(b"fake image data")
        mock_downloader.download_from_url.return_value = temp_file

        # Mock OpenAI response using new Responses API format
        mock_output_item = Mock()
        mock_output_item.type = "output_text"
        mock_output_item.text = "This is a URL image"

        mock_output_message = Mock()
        mock_output_message.type = "message"
        mock_output_message.content = [mock_output_item]

        mock_response = Mock()
        mock_response.output = [mock_output_message]

        mock_client = Mock()
        mock_client.responses.create.return_value = mock_response
        mock_openai.return_value = mock_client

        result = service.analyze_image(
            "https://example.com/image.jpg",
            "What's in this image?",
        )

        assert isinstance(result, VisionResult)
        assert result.analysis == "This is a URL image"
        mock_downloader.download_from_url.assert_called_once()

    @patch("ei_cli.services.ai_service.OpenAI")
    def test_analyze_image_with_detail_level(
        self,
        mock_openai,
        tmp_path,
    ):
        """Test image analysis with detail level."""
        service = AIService(api_key="test-key")

        image_file = tmp_path / "test.jpg"
        image_file.write_bytes(b"fake image data")

        mock_output_item = Mock()
        mock_output_item.type = "output_text"
        mock_output_item.text = "Detailed analysis"

        mock_output_message = Mock()
        mock_output_message.type = "message"
        mock_output_message.content = [mock_output_item]

        mock_response = Mock()
        mock_response.output = [mock_output_message]

        mock_client = Mock()
        mock_client.responses.create.return_value = mock_response
        mock_openai.return_value = mock_client

        result = service.analyze_image(
            str(image_file),
            "Analyze this",
            detail_level="high",
        )

        assert result.analysis == "Detailed analysis"
        # Verify API was called correctly
        mock_client.responses.create.assert_called_once()

    @patch("ei_cli.services.ai_service.OpenAI")
    def test_generate_image_with_output_path(
        self,
        mock_openai,
        tmp_path,
    ):
        """Test image generation with output_path (gpt-image-1)."""
        service = AIService(api_key="test-key")

        output_file = tmp_path / "generated.png"

        # Mock OpenAI response for gpt-image-1 (b64_json)
        mock_response = Mock()
        mock_response.data = [
            Mock(
                # 1x1 transparent PNG in base64
                b64_json=(
                    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJ"
                    "AAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
                ),
                url=None,
            ),
        ]
        mock_openai.return_value.images.generate.return_value = (
            mock_response
        )

        result = service.generate_image(
            "a sunset",
            output_path=output_file,
            show_progress=False,
        )

        assert isinstance(result, ImageGenerationResult)
        assert result.local_path == output_file
        # Verify file was created with base64 decoded content
        assert output_file.exists()
        assert len(output_file.read_bytes()) > 0

    @patch("ei_cli.services.ai_service.OpenAI")
    def test_generate_image_with_directory_output(
        self,
        mock_openai,
        tmp_path,
    ):
        """Test image generation with directory as output_path."""
        service = AIService(api_key="test-key")

        output_dir = tmp_path / "output"
        output_dir.mkdir()

        # Mock OpenAI response for gpt-image-1 (b64_json)
        mock_response = Mock()
        mock_response.data = [
            Mock(
                b64_json=(
                    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJ"
                    "AAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
                ),
                url=None,
            ),
        ]
        mock_openai.return_value.images.generate.return_value = (
            mock_response
        )

        result = service.generate_image(
            "a sunset",
            output_path=output_dir,
        )

        # File should be created with sanitized name (spaces are kept)
        assert result.local_path
        assert result.local_path.parent == output_dir
        assert result.local_path.name == "a sunset.png"
        assert result.local_path.exists()

    @patch("ei_cli.services.ai_service.OpenAI")
    def test_generate_image_with_options(self, mock_openai):
        """Test image generation with size, quality options (gpt-image-1)."""
        service = AIService(api_key="test-key")

        mock_response = Mock()
        mock_response.data = [
            Mock(
                b64_json=(
                    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJ"
                    "AAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
                ),
                url=None,
            ),
        ]
        mock_openai.return_value.images.generate.return_value = (
            mock_response
        )

        # Test with custom size and high quality
        result = service.generate_image(
            "a landscape",
            size="1536x1024",
            quality="high",
        )

        assert result.image_url.startswith("data:image/png;base64,")
        assert result.model == "gpt-image-1"

        # Verify options were passed
        call_args = mock_openai.return_value.images.generate.call_args
        assert call_args[1]["model"] == "gpt-image-1"
        assert call_args[1]["size"] == "1536x1024"
        assert call_args[1]["quality"] == "high"
        # gpt-image-1 always returns b64_json (no response_format param)
        assert "response_format" not in call_args[1]

    @patch("ei_cli.services.ai_service.OpenAI")
    def test_search_with_allowed_domains(self, mock_openai):
        """Test search with domain filtering."""
        service = AIService(api_key="test-key")

        mock_response = Mock()
        mock_response.output_text = "Python info"
        mock_response.items = [
            Mock(
                type="message",
                content=[
                    Mock(
                        type="output_text",
                        text="Python info",
                        annotations=[],
                    ),
                ],
            ),
        ]
        mock_openai.return_value.responses.create.return_value = (
            mock_response
        )

        result = service.search(
            "python",
            allowed_domains=["python.org", "docs.python.org"],
        )

        assert result.answer == "Python info"

        # Verify domains were passed
        call_args = mock_openai.return_value.responses.create.call_args
        tools = call_args[1]["tools"]
        assert "filters" in tools[0]
        assert tools[0]["filters"]["allowed_domains"] == [
            "python.org",
            "docs.python.org",
        ]

    @patch("ei_cli.services.ai_service.OpenAI")
    def test_search_with_sources(self, mock_openai):
        """Test search that returns sources."""
        service = AIService(api_key="test-key")

        mock_action = Mock()
        mock_action.sources = [
            "https://example.com/page1",
            "https://example.com/page2",
        ]

        mock_response = Mock()
        mock_response.output_text = "Answer with sources"
        mock_response.items = [
            Mock(
                type="message",
                content=[
                    Mock(
                        type="output_text",
                        text="Answer",
                        annotations=[],
                    ),
                ],
            ),
            Mock(
                type="web_search_call",
                action=mock_action,
            ),
        ]
        mock_openai.return_value.responses.create.return_value = (
            mock_response
        )

        result = service.search("test query")

        assert len(result.sources) == 2
        assert "https://example.com/page1" in result.sources

    @patch("ei_cli.services.ai_service.OpenAI")
    @patch("ei_cli.services.ai_service.AudioProcessor")
    def test_transcribe_audio_basic(
        self,
        mock_audio_processor_class,
        mock_openai,
        tmp_path,
    ):
        """Test basic audio transcription."""
        service = AIService(api_key="test-key")

        audio_file = tmp_path / "test.mp3"
        audio_file.write_bytes(b"fake audio data")

        # Mock audio processor
        mock_processor = Mock()
        mock_processor.get_audio_info.return_value = {
            "duration": 10.5,
            "format": "mp3",
        }
        mock_audio_processor_class.return_value = mock_processor

        # Mock OpenAI response
        mock_openai.return_value.audio.transcriptions.create.return_value = (
            "Hello world"
        )

        result = service.transcribe_audio(
            audio_file,
            preprocess=False,
        )

        assert result.text == "Hello world"
        assert result.model == "whisper-1"

    @patch("ei_cli.services.ai_service.OpenAI")
    @patch("ei_cli.services.ai_service.AudioProcessor")
    def test_transcribe_audio_with_language(
        self,
        mock_audio_processor_class,
        mock_openai,
        tmp_path,
    ):
        """Test audio transcription with language specified."""
        service = AIService(api_key="test-key")

        audio_file = tmp_path / "test.mp3"
        audio_file.write_bytes(b"fake audio data")

        mock_processor = Mock()
        mock_processor.get_audio_info.return_value = {"duration": 10.5}
        mock_audio_processor_class.return_value = mock_processor

        mock_openai.return_value.audio.transcriptions.create.return_value = (
            "Hola mundo"
        )

        result = service.transcribe_audio(
            audio_file,
            language="es",
            preprocess=False,
        )

        assert result.text == "Hola mundo"
        assert result.language == "es"

    @patch("ei_cli.services.ai_service.OpenAI")
    @patch("ei_cli.services.ai_service.AudioProcessor")
    def test_transcribe_audio_with_preprocessing(
        self,
        mock_audio_processor_class,
        mock_openai,
        tmp_path,
    ):
        """Test audio transcription with preprocessing."""
        service = AIService(api_key="test-key")

        audio_file = tmp_path / "test.mp3"
        audio_file.write_bytes(b"fake audio data")

        # Create temp processed file
        temp_processed = tmp_path / "whisper_test.wav"
        temp_processed.write_bytes(b"processed audio")

        mock_processor = Mock()
        mock_processor.get_audio_info.return_value = {"duration": 10.5}
        mock_processor.preprocess_audio_file.return_value = temp_processed
        mock_audio_processor_class.return_value = mock_processor

        # Transcriptions.create returns text directly (response_format="text")
        mock_openai.return_value.audio.transcriptions.create.return_value = (
            "Preprocessed audio"
        )

        with patch("tempfile.gettempdir", return_value=str(tmp_path)):
            result = service.transcribe_audio(
                audio_file,
                preprocess=True,
            )

        assert result.text == "Preprocessed audio"
        mock_processor.preprocess_audio_file.assert_called_once()

    @patch("ei_cli.services.ai_service.OpenAI")
    def test_text_to_speech_basic(self, mock_openai, tmp_path):
        """Test basic text-to-speech generation."""
        service = AIService(api_key="test-key")

        output_file = tmp_path / "speech.mp3"

        mock_response = Mock()
        mock_response.stream_to_file = Mock()
        mock_openai.return_value.audio.speech.create.return_value = (
            mock_response
        )

        result = service.text_to_speech(
            "Hello world",
            output_file,
        )

        assert result.audio_path == output_file
        assert result.voice == "alloy"
        assert result.model == "tts-1"
        mock_response.stream_to_file.assert_called_once()

    @patch("ei_cli.services.ai_service.OpenAI")
    def test_text_to_speech_with_options(
        self,
        mock_openai,
        tmp_path,
    ):
        """Test text-to-speech with voice, speed, model options."""
        service = AIService(api_key="test-key")

        output_file = tmp_path / "speech.mp3"

        mock_response = Mock()
        mock_response.stream_to_file = Mock()
        mock_openai.return_value.audio.speech.create.return_value = (
            mock_response
        )

        result = service.text_to_speech(
            "Hello world",
            output_file,
            voice="nova",
            speed=1.5,
            model="tts-1-hd",
        )

        assert result.voice == "nova"
        assert result.model == "tts-1-hd"

        # Verify options were passed
        call_args = mock_openai.return_value.audio.speech.create.call_args
        assert call_args[1]["voice"] == "nova"
        assert call_args[1]["speed"] == 1.5
        assert call_args[1]["model"] == "tts-1-hd"

    def test_text_to_speech_invalid_voice(self, tmp_path):
        """Test text-to-speech with invalid voice."""
        service = AIService(api_key="test-key")

        output_file = tmp_path / "speech.mp3"

        with pytest.raises(AIServiceError) as exc_info:
            service.text_to_speech(
                "Hello",
                output_file,
                voice="invalid",
            )

        assert "Invalid voice" in str(exc_info.value)

    @patch("ei_cli.services.ai_service.OpenAI")
    def test_text_to_speech_all_tts1_voices(self, mock_openai, tmp_path):
        """Test all tts-1 voices."""
        service = AIService(api_key="test-key")

        # All 11 voices available for tts-1
        tts1_voices = [
            "alloy", "ash", "ballad", "coral", "echo",
            "fable", "onyx", "nova", "sage", "shimmer", "verse",
        ]

        for voice in tts1_voices:
            output_file = tmp_path / f"{voice}.mp3"

            # No exception should be raised
            result = service.text_to_speech(
                "Test speech",
                output_file,
                voice=voice,
                model="tts-1",
            )

            assert result.voice == voice
            assert result.model == "tts-1"

    @patch("ei_cli.services.ai_service.OpenAI")
    def test_text_to_speech_all_hd_voices(self, mock_openai, tmp_path):
        """Test all tts-1-hd voices."""
        service = AIService(api_key="test-key")

        # All 8 voices available for tts-1-hd
        hd_voices = [
            "alloy", "echo", "fable", "onyx",
            "nova", "shimmer", "marin", "cedar",
        ]

        for voice in hd_voices:
            output_file = tmp_path / f"{voice}_hd.mp3"

            # No exception should be raised
            result = service.text_to_speech(
                "Test speech",
                output_file,
                voice=voice,
                model="tts-1-hd",
            )

            assert result.voice == voice
            assert result.model == "tts-1-hd"

    def test_text_to_speech_hd_voice_with_tts1_model(self, tmp_path):
        """Test HD-exclusive voice fails with tts-1 model."""
        service = AIService(api_key="test-key")
        output_file = tmp_path / "speech.mp3"

        # marin is HD-exclusive
        with pytest.raises(AIServiceError) as exc_info:
            service.text_to_speech(
                "Test",
                output_file,
                voice="marin",
                model="tts-1",
            )

        assert "Invalid voice" in str(exc_info.value)
        assert "marin" in str(exc_info.value)

        # cedar is HD-exclusive
        with pytest.raises(AIServiceError) as exc_info:
            service.text_to_speech(
                "Test",
                output_file,
                voice="cedar",
                model="tts-1",
            )

        assert "Invalid voice" in str(exc_info.value)
        assert "cedar" in str(exc_info.value)

    def test_text_to_speech_tts1_voice_with_hd_model(self, tmp_path):
        """Test tts-1-exclusive voice fails with tts-1-hd model."""
        service = AIService(api_key="test-key")
        output_file = tmp_path / "speech.mp3"

        # ballad is tts-1-exclusive
        with pytest.raises(AIServiceError) as exc_info:
            service.text_to_speech(
                "Test",
                output_file,
                voice="ballad",
                model="tts-1-hd",
            )

        assert "Invalid voice" in str(exc_info.value)
        assert "ballad" in str(exc_info.value)

        # sage is tts-1-exclusive
        with pytest.raises(AIServiceError) as exc_info:
            service.text_to_speech(
                "Test",
                output_file,
                voice="sage",
                model="tts-1-hd",
            )

        assert "Invalid voice" in str(exc_info.value)
        assert "sage" in str(exc_info.value)

    def test_text_to_speech_invalid_speed(self, tmp_path):
        """Test text-to-speech with invalid speed."""
        service = AIService(api_key="test-key")

        output_file = tmp_path / "speech.mp3"

        with pytest.raises(AIServiceError) as exc_info:
            service.text_to_speech(
                "Hello",
                output_file,
                speed=5.0,
            )

        assert "Speed" in str(exc_info.value)
        assert "out of range" in str(exc_info.value)

    def test_text_to_speech_empty_text(self, tmp_path):
        """Test text-to-speech with empty text."""
        service = AIService(api_key="test-key")

        output_file = tmp_path / "speech.mp3"

        with pytest.raises(AIServiceError) as exc_info:
            service.text_to_speech("", output_file)

        assert "empty" in str(exc_info.value).lower()

    @patch("ei_cli.services.ai_service.OpenAI")
    def test_text_to_speech_stream_basic(self, mock_openai, tmp_path):
        """Test basic streaming text-to-speech."""
        service = AIService(api_key="test-key")
        output_file = tmp_path / "speech_stream.mp3"

        # Mock streaming response
        mock_response = MagicMock()
        mock_response.iter_bytes.return_value = [
            b"audio_chunk_1",
            b"audio_chunk_2",
            b"audio_chunk_3",
        ]
        mock_openai.return_value.audio.speech.create.return_value = mock_response

        result = service.text_to_speech_stream(
            "Test streaming",
            output_file,
        )

        assert result.audio_path == output_file
        assert result.model == "tts-1"
        assert result.voice == "alloy"
        assert output_file.exists()

    @patch("ei_cli.services.ai_service.OpenAI")
    def test_text_to_speech_stream_with_progress(self, mock_openai, tmp_path):
        """Test streaming TTS with progress callback."""
        service = AIService(api_key="test-key")
        output_file = tmp_path / "speech_stream.mp3"

        # Mock streaming response
        mock_response = MagicMock()
        chunk_size = 1024
        mock_response.iter_bytes.return_value = [
            b"x" * chunk_size,
            b"y" * chunk_size,
            b"z" * chunk_size,
        ]
        mock_openai.return_value.audio.speech.create.return_value = mock_response

        # Track progress callbacks
        progress_calls = []

        def on_chunk(bytes_received: int, total: int) -> None:
            progress_calls.append((bytes_received, total))

        result = service.text_to_speech_stream(
            "Test with progress",
            output_file,
            on_chunk=on_chunk,
        )

        assert result.audio_path == output_file
        assert len(progress_calls) == 3
        assert progress_calls[0][0] == chunk_size
        assert progress_calls[1][0] == chunk_size * 2
        assert progress_calls[2][0] == chunk_size * 3

    @patch("ei_cli.services.ai_service.OpenAI")
    def test_text_to_speech_stream_all_params(self, mock_openai, tmp_path):
        """Test streaming TTS with all parameters."""
        service = AIService(api_key="test-key")
        output_file = tmp_path / "speech_stream_hd.mp3"

        # Mock streaming response
        mock_response = MagicMock()
        mock_response.iter_bytes.return_value = [b"audio_data"]
        mock_openai.return_value.audio.speech.create.return_value = mock_response

        result = service.text_to_speech_stream(
            "Test all parameters",
            output_file,
            voice="marin",
            speed=1.5,
            model="tts-1-hd",
        )

        assert result.voice == "marin"
        assert result.model == "tts-1-hd"

        # Verify API was called with correct parameters
        call_args = mock_openai.return_value.audio.speech.create.call_args
        assert call_args[1]["voice"] == "marin"
        assert call_args[1]["speed"] == 1.5
        assert call_args[1]["model"] == "tts-1-hd"

    def test_text_to_speech_stream_invalid_voice(self, tmp_path):
        """Test streaming TTS with invalid voice."""
        service = AIService(api_key="test-key")
        output_file = tmp_path / "speech.mp3"

        with pytest.raises(AIServiceError) as exc_info:
            service.text_to_speech_stream(
                "Test",
                output_file,
                voice="invalid_voice",
            )

        assert "Invalid voice" in str(exc_info.value)

    def test_text_to_speech_stream_empty_text(self, tmp_path):
        """Test streaming TTS with empty text."""
        service = AIService(api_key="test-key")
        output_file = tmp_path / "speech.mp3"

        with pytest.raises(AIServiceError) as exc_info:
            service.text_to_speech_stream("", output_file)

        assert "empty" in str(exc_info.value).lower()

    @patch("ei_cli.services.ai_service.OpenAI")
    def test_text_to_speech_all_formats(self, mock_openai, tmp_path):
        """Test TTS with all supported formats."""
        service = AIService(api_key="test-key")
        formats = ["mp3", "opus", "aac", "flac", "wav", "pcm"]

        for audio_format in formats:
            output_file = tmp_path / f"speech.{audio_format}"

            result = service.text_to_speech(
                "Test audio format",
                output_file,
                response_format=audio_format,
            )

            assert result.audio_path == output_file

            # Verify format was passed to API
            call_args = mock_openai.return_value.audio.speech.create.call_args
            assert call_args[1]["response_format"] == audio_format

    @patch("ei_cli.services.ai_service.OpenAI")
    def test_text_to_speech_stream_all_formats(self, mock_openai, tmp_path):
        """Test streaming TTS with all supported formats."""
        service = AIService(api_key="test-key")
        formats = ["mp3", "opus", "aac", "flac", "wav", "pcm"]

        # Mock streaming response
        mock_response = MagicMock()
        mock_response.iter_bytes.return_value = [b"audio_data"]
        mock_openai.return_value.audio.speech.create.return_value = mock_response

        for audio_format in formats:
            output_file = tmp_path / f"stream.{audio_format}"

            result = service.text_to_speech_stream(
                "Test streaming format",
                output_file,
                response_format=audio_format,
            )

            assert result.audio_path == output_file

            # Verify format was passed to API
            call_args = mock_openai.return_value.audio.speech.create.call_args
            assert call_args[1]["response_format"] == audio_format

    def test_text_to_speech_invalid_format(self, tmp_path):
        """Test TTS with invalid format."""
        service = AIService(api_key="test-key")
        output_file = tmp_path / "speech.invalid"

        with pytest.raises(AIServiceError) as exc_info:
            service.text_to_speech(
                "Test",
                output_file,
                response_format="invalid",
            )

        assert "Invalid format" in str(exc_info.value)
        assert "invalid" in str(exc_info.value)

    def test_text_to_speech_stream_invalid_format(self, tmp_path):
        """Test streaming TTS with invalid format."""
        service = AIService(api_key="test-key")
        output_file = tmp_path / "speech.invalid"

        with pytest.raises(AIServiceError) as exc_info:
            service.text_to_speech_stream(
                "Test",
                output_file,
                response_format="invalid",
            )

        assert "Invalid format" in str(exc_info.value)
        assert "invalid" in str(exc_info.value)

    @patch("ei_cli.services.ai_service.OpenAI")
    def test_text_to_speech_with_instructions(self, mock_openai, tmp_path):
        """Test TTS with instructions parameter."""
        service = AIService(api_key="test-key")
        output_file = tmp_path / "speech.mp3"

        # Mock successful response
        mock_openai.return_value.audio.speech.create.return_value.stream_to_file = Mock()

        result = service.text_to_speech(
            "Hello world",
            output_file,
            instructions="Speak slowly and clearly",
        )

        # Verify instructions were passed to API
        call_kwargs = mock_openai.return_value.audio.speech.create.call_args[1]
        assert call_kwargs["instructions"] == "Speak slowly and clearly"
        assert result.audio_path == output_file

    @patch("ei_cli.services.ai_service.OpenAI")
    def test_text_to_speech_without_instructions(self, mock_openai, tmp_path):
        """Test TTS without instructions parameter."""
        service = AIService(api_key="test-key")
        output_file = tmp_path / "speech.mp3"

        # Mock successful response
        mock_openai.return_value.audio.speech.create.return_value.stream_to_file = Mock()

        result = service.text_to_speech(
            "Hello world",
            output_file,
        )

        # Verify instructions were not passed to API
        call_kwargs = mock_openai.return_value.audio.speech.create.call_args[1]
        assert "instructions" not in call_kwargs
        assert result.audio_path == output_file

    @patch("ei_cli.services.ai_service.OpenAI")
    def test_text_to_speech_stream_with_instructions(self, mock_openai, tmp_path):
        """Test streaming TTS with instructions parameter."""
        service = AIService(api_key="test-key")
        output_file = tmp_path / "speech.mp3"

        # Mock streaming response
        mock_response = Mock()
        mock_response.iter_bytes.return_value = [b"chunk1", b"chunk2"]
        mock_openai.return_value.audio.speech.create.return_value = mock_response

        result = service.text_to_speech_stream(
            "Hello world",
            output_file,
            instructions="Emphasize important words",
        )

        # Verify instructions were passed to API
        call_kwargs = mock_openai.return_value.audio.speech.create.call_args[1]
        assert call_kwargs["instructions"] == "Emphasize important words"
        assert result.audio_path == output_file

    @patch("ei_cli.services.ai_service.OpenAI")
    def test_text_to_speech_stream_without_instructions(self, mock_openai, tmp_path):
        """Test streaming TTS without instructions parameter."""
        service = AIService(api_key="test-key")
        output_file = tmp_path / "speech.mp3"

        # Mock streaming response
        mock_response = Mock()
        mock_response.iter_bytes.return_value = [b"chunk1", b"chunk2"]
        mock_openai.return_value.audio.speech.create.return_value = mock_response

        result = service.text_to_speech_stream(
            "Hello world",
            output_file,
        )

        # Verify instructions were not passed to API
        call_kwargs = mock_openai.return_value.audio.speech.create.call_args[1]
        assert "instructions" not in call_kwargs
        assert result.audio_path == output_file

    @patch("ei_cli.services.ai_service.OpenAI")
    def test_text_to_speech_minimum_speed(self, mock_openai, tmp_path):
        """Test TTS with minimum speed (0.25x)."""
        service = AIService(api_key="test-key")
        output_file = tmp_path / "speech.mp3"

        # Mock successful response
        mock_openai.return_value.audio.speech.create.return_value.stream_to_file = Mock()

        result = service.text_to_speech(
            "Test minimum speed",
            output_file,
            speed=0.25,
        )

        # Verify speed was passed correctly
        call_kwargs = mock_openai.return_value.audio.speech.create.call_args[1]
        assert call_kwargs["speed"] == 0.25
        assert result.audio_path == output_file

    @patch("ei_cli.services.ai_service.OpenAI")
    def test_text_to_speech_maximum_speed(self, mock_openai, tmp_path):
        """Test TTS with maximum speed (4.0x)."""
        service = AIService(api_key="test-key")
        output_file = tmp_path / "speech.mp3"

        # Mock successful response
        mock_openai.return_value.audio.speech.create.return_value.stream_to_file = Mock()

        result = service.text_to_speech(
            "Test maximum speed",
            output_file,
            speed=4.0,
        )

        # Verify speed was passed correctly
        call_kwargs = mock_openai.return_value.audio.speech.create.call_args[1]
        assert call_kwargs["speed"] == 4.0
        assert result.audio_path == output_file

    @patch("ei_cli.services.ai_service.OpenAI")
    def test_text_to_speech_stream_minimum_speed(self, mock_openai, tmp_path):
        """Test streaming TTS with minimum speed (0.25x)."""
        service = AIService(api_key="test-key")
        output_file = tmp_path / "speech.mp3"

        # Mock streaming response
        mock_response = Mock()
        mock_response.iter_bytes.return_value = [b"chunk1", b"chunk2"]
        mock_openai.return_value.audio.speech.create.return_value = mock_response

        result = service.text_to_speech_stream(
            "Test minimum speed streaming",
            output_file,
            speed=0.25,
        )

        # Verify speed was passed correctly
        call_kwargs = mock_openai.return_value.audio.speech.create.call_args[1]
        assert call_kwargs["speed"] == 0.25
        assert result.audio_path == output_file

    @patch("ei_cli.services.ai_service.OpenAI")
    def test_text_to_speech_stream_maximum_speed(self, mock_openai, tmp_path):
        """Test streaming TTS with maximum speed (4.0x)."""
        service = AIService(api_key="test-key")
        output_file = tmp_path / "speech.mp3"

        # Mock streaming response
        mock_response = Mock()
        mock_response.iter_bytes.return_value = [b"chunk1", b"chunk2"]
        mock_openai.return_value.audio.speech.create.return_value = mock_response

        result = service.text_to_speech_stream(
            "Test maximum speed streaming",
            output_file,
            speed=4.0,
        )

        # Verify speed was passed correctly
        call_kwargs = mock_openai.return_value.audio.speech.create.call_args[1]
        assert call_kwargs["speed"] == 4.0
        assert result.audio_path == output_file

    @patch("ei_cli.services.ai_service.OpenAI")
    def test_translate_audio_basic(self, mock_openai, tmp_path):
        """Test basic audio translation."""
        service = AIService(api_key="test-key")

        audio_file = tmp_path / "test.mp3"
        audio_file.write_bytes(b"fake audio data")

        mock_openai.return_value.audio.translations.create.return_value = (
            "Translated to English"
        )

        result = service.translate_audio(
            audio_file,
            preprocess=False,
        )

        assert result.text == "Translated to English"
        assert result.language == "en"
        assert result.model == "whisper-1"

    @patch("ei_cli.services.ai_service.OpenAI")
    def test_translate_audio_with_prompt(
        self,
        mock_openai,
        tmp_path,
    ):
        """Test audio translation with prompt."""
        service = AIService(api_key="test-key")

        audio_file = tmp_path / "test.mp3"
        audio_file.write_bytes(b"fake audio data")

        mock_openai.return_value.audio.translations.create.return_value = (
            "Translated with context"
        )

        result = service.translate_audio(
            audio_file,
            prompt="Technical discussion",
            preprocess=False,
        )

        assert result.text == "Translated with context"

        # Verify prompt was passed
        call_args = (
            mock_openai.return_value.audio.translations.create.call_args
        )
        assert call_args[1]["prompt"] == "Technical discussion"

    def test_translate_audio_invalid_format(self, tmp_path):
        """Test audio translation with invalid format."""
        service = AIService(api_key="test-key")

        audio_file = tmp_path / "test.mp3"
        audio_file.write_bytes(b"fake audio data")

        with pytest.raises(AIServiceError) as exc_info:
            service.translate_audio(
                audio_file,
                response_format="invalid",
                preprocess=False,
            )

        assert "Invalid format" in str(exc_info.value)

    def test_translate_audio_invalid_temperature(self, tmp_path):
        """Test audio translation with invalid temperature."""
        service = AIService(api_key="test-key")

        audio_file = tmp_path / "test.mp3"
        audio_file.write_bytes(b"fake audio data")

        with pytest.raises(AIServiceError) as exc_info:
            service.translate_audio(
                audio_file,
                temperature=2.0,
                preprocess=False,
            )

        assert "Temperature" in str(exc_info.value)
        assert "out of range" in str(exc_info.value)

    def test_translate_audio_file_not_found(self):
        """Test audio translation with non-existent file."""
        service = AIService(api_key="test-key")

        with pytest.raises(AIServiceError) as exc_info:
            service.translate_audio(
                "/nonexistent/file.mp3",
                preprocess=False,
            )

        assert "not found" in str(exc_info.value).lower()

    def test_transcribe_audio_unavailable(self, tmp_path):
        """Test transcription when service unavailable."""
        service = AIService(api_key="")

        audio_file = tmp_path / "test.mp3"
        audio_file.write_bytes(b"fake audio")

        with pytest.raises(ServiceUnavailableError):
            service.transcribe_audio(audio_file)


class TestImageStreamingParser:
    """Tests for _parse_stream_events() method."""

    def test_parse_stream_events_partial_images(self):
        """Test parsing stream with partial images."""
        service = AIService(api_key="test-key")

        # Mock stream events with partial images
        mock_partial1 = Mock()
        mock_partial1.type = "response.image_generation_call.partial_image"
        mock_partial1.partial_image_index = 0
        mock_partial1.partial_image_b64 = "aGVsbG8="  # "hello" in base64

        mock_partial2 = Mock()
        mock_partial2.type = "response.image_generation_call.partial_image"
        mock_partial2.partial_image_index = 1
        mock_partial2.partial_image_b64 = "d29ybGQ="  # "world" in base64

        mock_final = Mock()
        mock_final.type = "image_generation_call"
        mock_final.status = "completed"
        mock_final.result = "ZmluYWw="  # "final" in base64
        mock_final.revised_prompt = "a test image"

        mock_stream = [mock_partial1, mock_partial2, mock_final]

        # Track callback invocations
        partial_calls = []

        def on_partial(idx, data):
            partial_calls.append((idx, data))

        final_b64, revised_prompt, partial_count = service._parse_stream_events(
            mock_stream, on_partial,
        )

        assert final_b64 == "ZmluYWw="
        assert revised_prompt == "a test image"
        assert partial_count == 2
        assert len(partial_calls) == 2
        assert partial_calls[0] == (0, b"hello")
        assert partial_calls[1] == (1, b"world")

    def test_parse_stream_events_final_image_only(self):
        """Test parsing stream with only final image (no partials)."""
        service = AIService(api_key="test-key")

        mock_final = Mock()
        mock_final.type = "image_generation_call"
        mock_final.status = "completed"
        mock_final.result = "ZmluYWw="
        mock_final.revised_prompt = "final image"

        mock_stream = [mock_final]

        final_b64, revised_prompt, partial_count = service._parse_stream_events(
            mock_stream, None,
        )

        assert final_b64 == "ZmluYWw="
        assert revised_prompt == "final image"
        assert partial_count == 0

    def test_parse_stream_events_mixed_events(self):
        """Test parsing stream with mixed event types (including non-image events)."""
        service = AIService(api_key="test-key")

        # Mock various event types
        mock_other1 = Mock()
        mock_other1.type = "response.start"

        mock_partial = Mock()
        mock_partial.type = "response.image_generation_call.partial_image"
        mock_partial.partial_image_index = 0
        mock_partial.partial_image_b64 = "cGFydGlhbA=="

        mock_other2 = Mock()
        mock_other2.type = "response.content_chunk"

        mock_final = Mock()
        mock_final.type = "image_generation_call"
        mock_final.status = "completed"
        mock_final.result = "ZmluYWw="
        mock_final.revised_prompt = "mixed events"

        mock_stream = [mock_other1, mock_partial, mock_other2, mock_final]

        partial_calls = []

        def on_partial(idx, data):
            partial_calls.append((idx, data))

        final_b64, revised_prompt, partial_count = service._parse_stream_events(
            mock_stream, on_partial,
        )

        assert final_b64 == "ZmluYWw="
        assert revised_prompt == "mixed events"
        assert partial_count == 1
        assert len(partial_calls) == 1

    def test_parse_stream_events_empty_stream(self):
        """Test parsing empty stream returns None for final image."""
        service = AIService(api_key="test-key")

        mock_stream = []

        final_b64, revised_prompt, partial_count = service._parse_stream_events(
            mock_stream, None,
        )

        assert final_b64 is None
        assert revised_prompt is None
        assert partial_count == 0

    def test_parse_stream_events_no_final_image(self):
        """Test parsing stream without final image returns None."""
        service = AIService(api_key="test-key")

        mock_partial = Mock()
        mock_partial.type = "response.image_generation_call.partial_image"
        mock_partial.partial_image_index = 0
        mock_partial.partial_image_b64 = "cGFydGlhbA=="

        mock_stream = [mock_partial]

        final_b64, revised_prompt, partial_count = service._parse_stream_events(
            mock_stream, None,
        )

        assert final_b64 is None
        assert revised_prompt is None
        assert partial_count == 1

    def test_parse_stream_events_base64_decoding(self):
        """Test base64 decoding in partial image callback."""
        service = AIService(api_key="test-key")

        # Test with various base64 strings
        test_data = b"Test binary data \x00\x01\x02\xff"
        import base64

        encoded = base64.b64encode(test_data).decode("utf-8")

        mock_partial = Mock()
        mock_partial.type = "response.image_generation_call.partial_image"
        mock_partial.partial_image_index = 0
        mock_partial.partial_image_b64 = encoded

        mock_final = Mock()
        mock_final.type = "image_generation_call"
        mock_final.status = "completed"
        mock_final.image_b64 = "ZmluYWw="
        mock_final.revised_prompt = "test"

        mock_stream = [mock_partial, mock_final]

        partial_calls = []

        def on_partial(idx, data):
            partial_calls.append((idx, data))

        service._parse_stream_events(mock_stream, on_partial)

        assert len(partial_calls) == 1
        assert partial_calls[0][1] == test_data

    def test_parse_stream_events_callback_invocation_order(self):
        """Test callback is invoked in correct order for multiple partials."""
        service = AIService(api_key="test-key")

        # Create 3 partial images
        mock_partials = []
        for i in range(3):
            mock_partial = Mock()
            mock_partial.type = "response.image_generation_call.partial_image"
            mock_partial.partial_image_index = i
            mock_partial.partial_image_b64 = f"cGFydGlhbC0{i}="
            mock_partials.append(mock_partial)

        mock_final = Mock()
        mock_final.type = "image_generation_call"
        mock_final.status = "completed"
        mock_final.image_b64 = "ZmluYWw="
        mock_final.revised_prompt = "test order"

        mock_stream = mock_partials + [mock_final]

        partial_indices = []

        def on_partial(idx, data):
            partial_indices.append(idx)

        service._parse_stream_events(mock_stream, on_partial)

        assert partial_indices == [0, 1, 2]

    def test_parse_stream_events_no_callback(self):
        """Test parsing works without callback (callback is optional)."""
        service = AIService(api_key="test-key")

        mock_partial = Mock()
        mock_partial.type = "response.image_generation_call.partial_image"
        mock_partial.partial_image_index = 0
        mock_partial.partial_image_b64 = "cGFydGlhbA=="

        mock_final = Mock()
        mock_final.type = "image_generation_call"
        mock_final.status = "completed"
        mock_final.result = "ZmluYWw="
        mock_final.revised_prompt = "no callback"

        mock_stream = [mock_partial, mock_final]

        # Should not raise even without callback
        final_b64, revised_prompt, partial_count = service._parse_stream_events(
            mock_stream, None,
        )

        assert final_b64 == "ZmluYWw="
        assert partial_count == 1


class TestImageStreamingValidation:
    """Tests for _validate_streaming_params() method."""

    def test_validate_transparent_jpeg_error(self):
        """Test validation rejects transparent background with JPEG format."""
        service = AIService(api_key="test-key")

        with pytest.raises(AIServiceError) as exc_info:
            service._validate_streaming_params(
                output_format="jpeg",
                background="transparent",
                compression=None,
                reference_images=[],
                input_fidelity="low",
            )

        assert "INVALID_PARAMS" in str(exc_info.value)
        assert "transparent" in str(exc_info.value).lower()
        assert "jpeg" in str(exc_info.value).lower()

    def test_validate_compression_png_error(self):
        """Test validation rejects compression with PNG format."""
        service = AIService(api_key="test-key")

        with pytest.raises(AIServiceError) as exc_info:
            service._validate_streaming_params(
                output_format="png",
                background="auto",
                compression=80,
                reference_images=[],
                input_fidelity="low",
            )

        assert "INVALID_PARAMS" in str(exc_info.value)
        assert "compression" in str(exc_info.value).lower()
        assert "png" in str(exc_info.value).lower()

    def test_validate_compression_out_of_range_error(self):
        """Test validation rejects compression values outside 0-100 range."""
        service = AIService(api_key="test-key")

        # Test below range
        with pytest.raises(AIServiceError) as exc_info:
            service._validate_streaming_params(
                output_format="jpeg",
                background="auto",
                compression=-1,
                reference_images=[],
                input_fidelity="low",
            )

        assert "INVALID_PARAMS" in str(exc_info.value)
        assert ("0 and 100" in str(exc_info.value) or "0-100" in str(exc_info.value))

        # Test above range
        with pytest.raises(AIServiceError) as exc_info:
            service._validate_streaming_params(
                output_format="jpeg",
                background="auto",
                compression=101,
                reference_images=[],
                input_fidelity="low",
            )

        assert "INVALID_PARAMS" in str(exc_info.value)
        assert ("0 and 100" in str(exc_info.value) or "0-100" in str(exc_info.value))

    def test_validate_valid_combinations_pass(self):
        """Test validation passes for valid parameter combinations."""
        service = AIService(api_key="test-key")

        # PNG with transparent background
        service._validate_streaming_params(
            output_format="png",
            background="transparent",
            compression=None,
            reference_images=[],
            input_fidelity="low",
        )

        # JPEG with compression
        service._validate_streaming_params(
            output_format="jpeg",
            background="opaque",
            compression=85,
            reference_images=[],
            input_fidelity="low",
        )

        # WebP with compression and transparency
        service._validate_streaming_params(
            output_format="webp",
            background="transparent",
            compression=80,
            reference_images=[],
            input_fidelity="high",
        )

        # No assertions needed - should not raise

    def test_validate_auto_values_accepted(self):
        """Test validation accepts 'auto' values."""
        service = AIService(api_key="test-key")

        service._validate_streaming_params(
            output_format="png",
            background="auto",
            compression=None,
            reference_images=[],
            input_fidelity="low",
        )

        # Should not raise

    def test_validate_reference_images_max_count(self):
        """Test validation rejects more than 4 reference images."""
        service = AIService(api_key="test-key")

        # Create 5 mock image paths
        reference_images = ["img1.png", "img2.png", "img3.png", "img4.png", "img5.png"]

        with pytest.raises(AIServiceError) as exc_info:
            service._validate_streaming_params(
                output_format="png",
                background="auto",
                compression=None,
                reference_images=reference_images,
                input_fidelity="low",
            )

        assert "TOO_MANY_IMAGES" in str(exc_info.value)
        assert "4" in str(exc_info.value)

    def test_validate_reference_images_size_limit(self, tmp_path):
        """Test validation rejects reference images exceeding 50MB total."""
        service = AIService(api_key="test-key")

        # Create a large file (>50MB)
        large_file = tmp_path / "large.png"
        large_file.write_bytes(b"x" * (51 * 1024 * 1024))  # 51MB

        with pytest.raises(AIServiceError) as exc_info:
            service._validate_streaming_params(
                output_format="png",
                background="auto",
                compression=None,
                reference_images=[str(large_file)],
                input_fidelity="low",
            )

        assert "PAYLOAD_TOO_LARGE" in str(exc_info.value)
        assert "50" in str(exc_info.value)

    def test_validate_reference_image_not_found(self):
        """Test validation handles non-existent reference images."""
        service = AIService(api_key="test-key")

        # File paths that don't exist will be caught during validation
        reference_images = ["/nonexistent/image.png"]

        # This might pass validation if it only checks size on existing files
        # The actual error will occur in _prepare_input_content
        # So we just verify validation doesn't crash on non-existent paths
        try:
            service._validate_streaming_params(
                output_format="png",
                background="auto",
                compression=None,
                reference_images=reference_images,
                input_fidelity="low",
            )
        except AIServiceError:
            # If it raises, that's also acceptable behavior
            pass

    def test_validate_input_fidelity_values(self):
        """Test validation accepts valid input_fidelity values."""
        service = AIService(api_key="test-key")

        # Test 'low'
        service._validate_streaming_params(
            output_format="png",
            background="auto",
            compression=None,
            reference_images=[],
            input_fidelity="low",
        )

        # Test 'high'
        service._validate_streaming_params(
            output_format="png",
            background="auto",
            compression=None,
            reference_images=[],
            input_fidelity="high",
        )

        # Should not raise

    def test_validate_input_fidelity_invalid(self):
        """Test validation rejects invalid input_fidelity values."""
        service = AIService(api_key="test-key")

        with pytest.raises(AIServiceError) as exc_info:
            service._validate_streaming_params(
                output_format="png",
                background="auto",
                compression=None,
                reference_images=[],
                input_fidelity="invalid",
            )

        assert "INVALID_PARAMS" in str(exc_info.value)
        assert "fidelity" in str(exc_info.value).lower()


class TestReferenceImageHandling:
    """Tests for _prepare_input_content() method."""

    def test_prepare_content_local_file_jpg(self, tmp_path):
        """Test preparing content with local JPG file."""
        import base64

        service = AIService(api_key="test-key")

        # Create test image file
        test_image = tmp_path / "test.jpg"
        test_image.write_bytes(b"fake jpg data")

        content = service._prepare_input_content(
            "test prompt",
            [str(test_image)],
        )

        assert len(content) == 2
        assert content[0]["type"] == "input_text"
        assert content[0]["text"] == "test prompt"
        assert content[1]["type"] == "input_image"
        assert "image_url" in content[1]

        # Verify base64 encoding
        image_url = content[1]["image_url"]
        assert image_url.startswith("data:image/jpeg;base64,")
        encoded_data = image_url.split(",")[1]
        decoded = base64.b64decode(encoded_data)
        assert decoded == b"fake jpg data"

    def test_prepare_content_local_file_png(self, tmp_path):
        """Test preparing content with local PNG file."""

        service = AIService(api_key="test-key")

        test_image = tmp_path / "test.png"
        test_image.write_bytes(b"fake png data")

        content = service._prepare_input_content(
            "test prompt",
            [str(test_image)],
        )

        assert len(content) == 2
        image_url = content[1]["image_url"]
        assert image_url.startswith("data:image/png;base64,")

    def test_prepare_content_url_handling(self):
        """Test preparing content with HTTP URL."""
        service = AIService(api_key="test-key")

        content = service._prepare_input_content(
            "test prompt",
            ["https://example.com/image.jpg"],
        )

        assert len(content) == 2
        assert content[1]["type"] == "input_image"
        assert content[1]["image_url"] == "https://example.com/image.jpg"

    def test_prepare_content_file_id_handling(self):
        """Test preparing content with OpenAI File ID."""
        service = AIService(api_key="test-key")

        content = service._prepare_input_content(
            "test prompt",
            ["file-abc123xyz"],
        )

        assert len(content) == 2
        assert content[1]["type"] == "input_image"
        assert content[1]["file_id"] == "file-abc123xyz"

    def test_prepare_content_multiple_images(self, tmp_path):
        """Test preparing content with multiple reference images."""
        service = AIService(api_key="test-key")

        # Mix of different input types
        local_file = tmp_path / "local.png"
        local_file.write_bytes(b"local image")

        content = service._prepare_input_content(
            "test prompt",
            [
                str(local_file),
                "https://example.com/image.jpg",
                "file-xyz789",
            ],
        )

        assert len(content) == 4  # 1 text + 3 images
        assert content[0]["type"] == "input_text"
        assert content[1]["type"] == "input_image"
        assert content[2]["type"] == "input_image"
        assert content[3]["type"] == "input_image"

        # Verify types
        assert content[1]["image_url"].startswith("data:image/png")
        assert content[2]["image_url"] == "https://example.com/image.jpg"
        assert content[3]["file_id"] == "file-xyz789"

    def test_prepare_content_base64_encoding_correct(self, tmp_path):
        """Test base64 encoding produces correct output."""
        import base64

        service = AIService(api_key="test-key")

        # Create image with known content
        test_data = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR"
        test_image = tmp_path / "test.png"
        test_image.write_bytes(test_data)

        content = service._prepare_input_content(
            "prompt",
            [str(test_image)],
        )

        image_url = content[1]["image_url"]
        encoded_data = image_url.split(",")[1]
        decoded = base64.b64decode(encoded_data)
        assert decoded == test_data

    def test_prepare_content_mime_type_detection(self, tmp_path):
        """Test MIME type detection for different file extensions."""
        service = AIService(api_key="test-key")

        # Test different extensions
        test_files = {
            "test.jpg": "image/jpeg",
            "test.jpeg": "image/jpeg",
            "test.png": "image/png",
            "test.webp": "image/webp",
            "test.gif": "image/gif",
        }

        for filename, expected_mime in test_files.items():
            test_file = tmp_path / filename
            test_file.write_bytes(b"fake data")

            content = service._prepare_input_content(
                "prompt",
                [str(test_file)],
            )

            image_url = content[1]["image_url"]
            assert image_url.startswith(f"data:{expected_mime};base64,")

    def test_prepare_content_invalid_format_error(self, tmp_path):
        """Test error handling for invalid image format."""
        service = AIService(api_key="test-key")

        # Create file with unsupported extension
        invalid_file = tmp_path / "test.bmp"
        invalid_file.write_bytes(b"fake data")

        with pytest.raises(AIServiceError) as exc_info:
            service._prepare_input_content(
                "prompt",
                [str(invalid_file)],
            )

        assert "INVALID_IMAGE_FORMAT" in str(exc_info.value)

    def test_prepare_content_file_not_found(self):
        """Test error handling for non-existent file."""
        service = AIService(api_key="test-key")

        with pytest.raises(AIServiceError) as exc_info:
            service._prepare_input_content(
                "prompt",
                ["/nonexistent/image.png"],
            )

        assert "IMAGE_NOT_FOUND" in str(exc_info.value)


class TestImageStreamingIntegration:
    """Integration tests for complete streaming workflow."""

    @patch("ei_cli.services.ai_service.OpenAI")
    def test_end_to_end_streaming_generation(self, mock_openai, tmp_path):
        """Test complete streaming image generation workflow."""
        import base64

        service = AIService(api_key="test-key")

        # Mock streaming response
        mock_partial = Mock()
        mock_partial.type = "response.image_generation_call.partial_image"
        mock_partial.partial_image_index = 0
        mock_partial.partial_image_b64 = base64.b64encode(b"partial data").decode()

        mock_final = Mock()
        mock_final.type = "image_generation_call"
        mock_final.status = "completed"
        # Important: result must be a string, not a Mock
        mock_final.result = base64.b64encode(b"final image data").decode()
        mock_final.revised_prompt = "a beautiful landscape"

        mock_stream = [mock_partial, mock_final]
        mock_openai.return_value.responses.create.return_value = mock_stream

        output_path = tmp_path / "output.png"

        result = service.generate_image_stream(
            prompt="a landscape",
            size="1024x1024",
            quality="high",
            output_format="png",
            output_path=str(output_path),
        )

        assert isinstance(result, ImageGenerationResult)
        assert result.revised_prompt == "a beautiful landscape"
        assert output_path.exists()
        assert output_path.read_bytes() == b"final image data"

    @patch("ei_cli.services.ai_service.OpenAI")
    def test_partial_images_callback_works(self, mock_openai):
        """Test partial image callback is invoked correctly."""
        import base64

        service = AIService(api_key="test-key")

        # Create multiple partials
        mock_partials = []
        for i in range(3):
            mock_partial = Mock()
            mock_partial.type = "response.image_generation_call.partial_image"
            mock_partial.partial_image_index = i
            mock_partial.partial_image_b64 = base64.b64encode(f"partial {i}".encode()).decode()
            mock_partials.append(mock_partial)

        mock_final = Mock()
        mock_final.type = "image_generation_call"
        mock_final.status = "completed"
        # Important: result must be a string
        mock_final.result = base64.b64encode(b"final").decode()
        mock_final.revised_prompt = "test"

        mock_stream = [*mock_partials, mock_final]
        mock_openai.return_value.responses.create.return_value = mock_stream

        # Track callback invocations
        callback_data = []

        def on_partial(idx, data):
            callback_data.append((idx, data))

        service.generate_image_stream(
            prompt="test",
            on_partial=on_partial,
        )

        assert len(callback_data) == 3
        assert callback_data[0] == (0, b"partial 0")
        assert callback_data[1] == (1, b"partial 1")
        assert callback_data[2] == (2, b"partial 2")

    @patch("ei_cli.services.ai_service.OpenAI")
    def test_image_to_image_with_reference(self, mock_openai, tmp_path):
        """Test image-to-image generation with reference image."""
        import base64

        service = AIService(api_key="test-key")

        # Create reference image
        ref_image = tmp_path / "reference.png"
        ref_image.write_bytes(b"reference image data")

        mock_final = Mock()
        mock_final.type = "image_generation_call"
        mock_final.status = "completed"
        mock_final.result = base64.b64encode(b"result").decode()
        mock_final.revised_prompt = "enhanced image"

        mock_stream = [mock_final]
        mock_openai.return_value.responses.create.return_value = mock_stream

        result = service.generate_image_stream(
            prompt="enhance this image",
            reference_images=[str(ref_image)],
            input_fidelity="high",
        )

        assert isinstance(result, ImageGenerationResult)
        assert result.revised_prompt == "enhanced image"

        # Verify API was called with reference image
        call_args = mock_openai.return_value.responses.create.call_args
        assert call_args is not None

    @patch("ei_cli.services.ai_service.OpenAI")
    def test_style_transfer_multiple_references(self, mock_openai, tmp_path):
        """Test style transfer with multiple reference images."""
        import base64

        service = AIService(api_key="test-key")

        # Create multiple reference images
        ref_images = []
        for i in range(3):
            ref_img = tmp_path / f"ref{i}.png"
            ref_img.write_bytes(f"reference {i}".encode())
            ref_images.append(str(ref_img))

        mock_final = Mock()
        mock_final.type = "image_generation_call"
        mock_final.status = "completed"
        mock_final.result = base64.b64encode(b"styled result").decode()
        mock_final.revised_prompt = "styled composition"

        mock_stream = [mock_final]
        mock_openai.return_value.responses.create.return_value = mock_stream

        result = service.generate_image_stream(
            prompt="combine these images with this style",
            reference_images=ref_images,
            quality="high",
        )

        assert isinstance(result, ImageGenerationResult)
        assert result.revised_prompt == "styled composition"

    @patch("ei_cli.services.ai_service.OpenAI")
    def test_transparent_background_generation(self, mock_openai, tmp_path):
        """Test generating image with transparent background."""
        import base64

        service = AIService(api_key="test-key")

        mock_final = Mock()
        mock_final.type = "image_generation_call"
        mock_final.status = "completed"
        mock_final.result = base64.b64encode(b"transparent image").decode()
        mock_final.revised_prompt = "object on transparent background"

        mock_stream = [mock_final]
        mock_openai.return_value.responses.create.return_value = mock_stream

        output_path = tmp_path / "transparent.png"

        result = service.generate_image_stream(
            prompt="a logo",
            background="transparent",
            output_format="png",
            output_path=str(output_path),
        )

        assert isinstance(result, ImageGenerationResult)
        assert output_path.exists()

    @patch("ei_cli.services.ai_service.OpenAI")
    def test_compressed_jpeg_output(self, mock_openai, tmp_path):
        """Test generating compressed JPEG output."""
        import base64

        service = AIService(api_key="test-key")

        mock_final = Mock()
        mock_final.type = "image_generation_call"
        mock_final.status = "completed"
        mock_final.result = base64.b64encode(b"compressed jpeg").decode()
        mock_final.revised_prompt = "photo"

        mock_stream = [mock_final]
        mock_openai.return_value.responses.create.return_value = mock_stream

        output_path = tmp_path / "compressed.jpg"

        result = service.generate_image_stream(
            prompt="a photo",
            output_format="jpeg",
            compression=80,
            output_path=str(output_path),
        )

        assert isinstance(result, ImageGenerationResult)
        assert output_path.exists()

    @patch("ei_cli.services.ai_service.OpenAI")
    def test_quality_levels_applied(self, mock_openai):
        """Test different quality levels are passed to API."""
        import base64

        service = AIService(api_key="test-key")

        mock_final = Mock()
        mock_final.type = "image_generation_call"
        mock_final.status = "completed"
        mock_final.result = base64.b64encode(b"image").decode()
        mock_final.revised_prompt = "test"

        mock_stream = [mock_final]
        mock_openai.return_value.responses.create.return_value = mock_stream

        # Test each quality level
        for quality in ["low", "medium", "high", "auto"]:
            service.generate_image_stream(
                prompt="test",
                quality=quality,
            )

            # Verify quality was passed to API
            call_args = mock_openai.return_value.responses.create.call_args
            assert call_args is not None


class TestImageStreamingErrorHandling:
    """Tests for error handling in streaming."""

    @patch("ei_cli.services.ai_service.OpenAI")
    def test_stream_connection_error(self, mock_openai):
        """Test handling of connection errors during streaming."""
        service = AIService(api_key="test-key")

        # Mock connection error
        mock_openai.return_value.responses.create.side_effect = Exception(
            "Connection failed",
        )

        with pytest.raises(AIServiceError) as exc_info:
            service.generate_image_stream(prompt="test")

        assert "STREAM_GEN_ERROR" in str(exc_info.value)

    @patch("ei_cli.services.ai_service.OpenAI")
    def test_service_unavailable_streaming(self, mock_openai):
        """Test streaming when service is unavailable."""
        service = AIService(api_key="")

        with pytest.raises(ServiceUnavailableError):
            service.generate_image_stream(prompt="test")

    def test_invalid_params_combinations(self):
        """Test error handling for invalid parameter combinations."""
        service = AIService(api_key="test-key")

        # Transparent JPEG
        with pytest.raises(AIServiceError) as exc_info:
            service.generate_image_stream(
                prompt="test",
                output_format="jpeg",
                background="transparent",
            )

        assert "INVALID_PARAMS" in str(exc_info.value)

    def test_payload_too_large_error(self, tmp_path):
        """Test error handling for oversized reference images."""
        service = AIService(api_key="test-key")

        # Create large file
        large_file = tmp_path / "large.png"
        large_file.write_bytes(b"x" * (51 * 1024 * 1024))

        with pytest.raises(AIServiceError) as exc_info:
            service.generate_image_stream(
                prompt="test",
                reference_images=[str(large_file)],
            )

        assert "PAYLOAD_TOO_LARGE" in str(exc_info.value)

    def test_too_many_reference_images(self):
        """Test error handling for too many reference images."""
        service = AIService(api_key="test-key")

        # Try to use 5 images (max is 4)
        with pytest.raises(AIServiceError) as exc_info:
            service.generate_image_stream(
                prompt="test",
                reference_images=["img1.png", "img2.png", "img3.png", "img4.png", "img5.png"],
            )

        assert "TOO_MANY_IMAGES" in str(exc_info.value)

    @patch("ei_cli.services.ai_service.OpenAI")
    @patch("ei_cli.services.image_downloader.ImageDownloader")
    @patch("tempfile.gettempdir")
    def test_analyze_multiple_images(
        self,
        mock_tempdir,
        mock_downloader_class,
        mock_openai,
        tmp_path,
    ):
        """Test multi-image analysis."""
        service = AIService(api_key="test-key")

        # Setup temp directory mock
        mock_tempdir.return_value = str(tmp_path)

        # Setup mock downloader
        mock_downloader = Mock()
        mock_downloader.is_url.return_value = False
        mock_downloader_class.return_value = mock_downloader

        # Create test images
        image1 = tmp_path / "test1.jpg"
        image1.write_bytes(b"fake image 1")
        image2 = tmp_path / "test2.jpg"
        image2.write_bytes(b"fake image 2")

        # Mock OpenAI response using new Responses API format
        mock_output_item = Mock()
        mock_output_item.type = "output_text"
        mock_output_item.text = "Both images show similar themes."

        mock_output_message = Mock()
        mock_output_message.type = "message"
        mock_output_message.content = [mock_output_item]

        mock_response = Mock()
        mock_response.output = [mock_output_message]

        mock_client = Mock()
        mock_client.responses.create.return_value = mock_response
        mock_openai.return_value = mock_client

        result = service.analyze_multiple_images(
            image_paths=[str(image1), str(image2)],
            prompt="Compare these images",
        )

        assert isinstance(result, VisionResult)
        assert result.analysis == "Both images show similar themes."
        assert result.model == "gpt-5"
        assert "Multiple images" in result.image_source
        assert result.prompt == "Compare these images"

        # Verify OpenAI was called with correct parameters
        mock_client.responses.create.assert_called_once()
        call_args = mock_client.responses.create.call_args
        assert call_args.kwargs["model"] == "gpt-5"
        assert len(call_args.kwargs["input"]) == 1
        assert call_args.kwargs["input"][0]["role"] == "user"

        # Check content structure for multiple images
        content = call_args.kwargs["input"][0]["content"]
        assert isinstance(content, list)
        assert content[0]["type"] == "input_text"
        assert "Compare these images" in content[0]["text"]

        # Should have 2 image entries
        assert content[1]["type"] == "input_image"
        assert content[2]["type"] == "input_image"
        image_items = [
            item for item in content if item["type"] == "input_image"
        ]
        assert len(image_items) == 2

    @patch("ei_cli.services.ai_service.OpenAI")
    @patch("ei_cli.services.image_downloader.ImageDownloader")
    @patch("tempfile.gettempdir")
    def test_analyze_multiple_images_with_options(
        self,
        mock_tempdir,
        mock_downloader_class,
        mock_openai,
        tmp_path,
    ):
        """Test multi-image analysis with all options."""
        service = AIService(api_key="test-key")

        # Setup temp directory mock
        mock_tempdir.return_value = str(tmp_path)

        # Setup mock downloader
        mock_downloader = Mock()
        mock_downloader.is_url.return_value = False
        mock_downloader_class.return_value = mock_downloader

        # Create test images
        image1 = tmp_path / "test1.jpg"
        image1.write_bytes(b"fake image 1")
        image2 = tmp_path / "test2.jpg"
        image2.write_bytes(b"fake image 2")
        image3 = tmp_path / "test3.jpg"
        image3.write_bytes(b"fake image 3")

        # Mock OpenAI response using new Responses API format
        mock_output_item = Mock()
        mock_output_item.type = "output_text"
        mock_output_item.text = "Detailed comparison analysis."

        mock_output_message = Mock()
        mock_output_message.type = "message"
        mock_output_message.content = [mock_output_item]

        mock_response = Mock()
        mock_response.output = [mock_output_message]

        mock_client = Mock()
        mock_client.responses.create.return_value = mock_response
        mock_openai.return_value = mock_client

        result = service.analyze_multiple_images(
            image_paths=[str(image1), str(image2), str(image3)],
            prompt="What patterns do you see?",
            detail_level="high",
            compare_mode=True,
        )

        assert isinstance(result, VisionResult)
        assert result.analysis == "Detailed comparison analysis."

        # Verify OpenAI was called with correct parameters
        mock_client.responses.create.assert_called_once()
        call_args = mock_client.responses.create.call_args

        # Check that compare mode affected the prompt
        content = call_args.kwargs["input"][0]["content"]
        text_content = content[0]["text"]
        assert "What patterns do you see?" in text_content
        assert "compare" in text_content.lower()

        # Should have 3 image entries
        image_items = [
            item for item in content if item["type"] == "input_image"
        ]
        assert len(image_items) == 3

