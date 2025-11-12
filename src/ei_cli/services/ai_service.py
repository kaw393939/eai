"""
AI Service for OpenAI-powered operations.

Handles search, vision analysis, image generation, and audio processing
with built-in rate limiting, retry logic, and cost tracking.
"""

import asyncio
import base64
import json
import os
import tempfile
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import backoff
from aiolimiter import AsyncLimiter
from openai import AsyncOpenAI, OpenAI
from rich.console import Console

from ei_cli.core.errors import AIServiceError, MissingAPIKeyError
from ei_cli.core.models import MODELS
from ei_cli.core.rate_limiter import RateLimiter
from ei_cli.services.audio_chunker import AudioChunker, SmartAudioChunker
from ei_cli.services.audio_processor import AudioProcessor
from ei_cli.services.base import Service, ServiceUnavailableError
from ei_cli.services.constants import (
    DEFAULT_CHUNK_DURATION_SEC,
    DEFAULT_MAX_CONCURRENT,
    MAX_SINGLE_FILE_SIZE_MB,
    MAX_TTS_SPEED,
    MIN_TTS_SPEED,
)


@dataclass
class SearchCitation:
    """Citation from web search results."""

    url: str
    title: str
    start_index: int
    end_index: int


@dataclass
class SearchResult:
    """Result from web search."""

    answer: str
    citations: list[SearchCitation]
    sources: list[str]


@dataclass
class VisionResult:
    """Result from image analysis."""

    analysis: str
    model: str = MODELS.vision
    image_source: str = ""
    prompt: str = ""


@dataclass
class ImageGenerationResult:
    """Result from image generation."""

    image_url: str
    revised_prompt: str | None = None
    model: str = MODELS.image
    local_path: Path | None = None


@dataclass
class ImageVariationsResult:
    """Result from image variations generation."""

    variations: list[ImageGenerationResult]
    base_prompt: str
    total_generated: int
    metadata: dict[str, Any]


@dataclass
class TranscriptionResult:
    """Result from audio transcription."""

    text: str
    language: str | None = None
    duration: float | None = None
    model: str = MODELS.transcription


@dataclass
class TextToSpeechResult:
    """Result from text-to-speech generation."""

    audio_path: Path
    model: str = MODELS.tts
    voice: str = "alloy"


class AIService(Service):
    """
    AI service for OpenAI-powered operations.

    Provides web search, vision analysis, and image generation
    with built-in rate limiting and retry logic.
    """

    def __init__(
        self,
        api_key: str,
        *,
        rate_limit: int = 5,
        max_retries: int = 3,
    ):
        """
        Initialize AI service.

        Args:
            api_key: OpenAI API key
            rate_limit: Max requests per second (default: 5)
            max_retries: Max retry attempts on failure (default: 3)
        """
        self._api_key = api_key
        self._rate_limit = rate_limit
        self._max_retries = max_retries
        self._client: OpenAI | None = None
        self._async_client: AsyncOpenAI | None = None
        # Sync rate limiter for sequential operations
        self._rate_limiter = RateLimiter(max_requests=rate_limit)
        # Async rate limiter for parallel operations (aiolimiter)
        # 60 second window matches RateLimiter default
        self._async_rate_limiter = AsyncLimiter(max_rate=rate_limit, time_period=60)
        self._audio_processor: AudioProcessor | None = None
        self._total_cost = 0.0
        
        # Phase 4: Intelligent caching system
        self._cache: dict[str, tuple[ImageGenerationResult, float]] = {}
        self._cache_max_age = 3600.0  # 1 hour cache lifetime
        self._cache_similarity_threshold = 0.85  # Similarity threshold
        self._cache_hits = 0
        self._cache_misses = 0

    @property
    def name(self) -> str:
        """Service name."""
        return "ai_service"

    @property
    def total_cost(self) -> float:
        """Get total API cost tracked."""
        return self._total_cost

    def check_available(self) -> tuple[bool, str | None]:
        """
        Check if service is available.

        Returns:
            Tuple of (is_available, error_message)
        """
        if not self._api_key:
            return (
                False,
                "Missing API key: API__OPENAI_API_KEY not set",
            )
        return (True, None)

    def _get_client(self) -> OpenAI:
        """Get or create OpenAI client."""
        if self._client is None:
            if not self._api_key:  # pragma: no cover
                raise MissingAPIKeyError(
                    message="OpenAI API key not found",
                )
            self._client = OpenAI(api_key=self._api_key)
        return self._client

    def _get_async_client(self) -> AsyncOpenAI:
        """Get or create async OpenAI client."""
        if self._async_client is None:
            if not self._api_key:  # pragma: no cover
                raise MissingAPIKeyError(
                    message="OpenAI API key not found",
                )
            self._async_client = AsyncOpenAI(api_key=self._api_key)
        return self._async_client

    def _get_audio_processor(self) -> AudioProcessor:
        """Get or create audio processor."""
        if self._audio_processor is None:
            self._audio_processor = AudioProcessor()
        return self._audio_processor

    def _get_audio_chunker(self) -> AudioChunker:
        """Get or create audio chunker."""
        processor = self._get_audio_processor()
        return AudioChunker(processor)

    def _get_smart_audio_chunker(self, max_chunk_size_mb: float = 23.0, save_intermediate: bool = False) -> SmartAudioChunker:
        """Get or create smart audio chunker with auto-detection."""
        processor = self._get_audio_processor()
        return SmartAudioChunker(
            processor=processor,
            max_chunk_size_mb=max_chunk_size_mb,
            save_intermediate=save_intermediate,
        )

    def _enforce_rate_limit(self) -> None:
        """Enforce rate limiting using sliding window algorithm."""
        self._rate_limiter.wait_if_needed()

    @backoff.on_exception(
        backoff.expo,
        Exception,
        max_tries=3,
        max_time=30,
    )
    def _make_api_call(self, func: Any, *args: Any, **kwargs: Any) -> Any:
        """
        Make API call with automatic exponential backoff retry.

        Args:
            func: Function to call
            *args: Positional arguments
            **kwargs: Keyword arguments

        Returns:
            Result from function call
        """
        return func(*args, **kwargs)

    def search(
        self,
        query: str,
        *,
        user_location: dict[str, str] | None = None,
        allowed_domains: list[str] | None = None,
        num_results: int = 5,
    ) -> SearchResult:
        """
        Perform web search with citations.

        Args:
            query: Search query
            user_location: Optional user location (country, city)
            allowed_domains: Optional list of allowed domains
            num_results: Number of results to return

        Returns:
            SearchResult with answer, citations, and sources

        Raises:
            ServiceUnavailableError: If service not available
            AIServiceError: If search fails
        """
        is_available, error = self.check_available()
        if not is_available:
            raise ServiceUnavailableError(
                error or "Service not available",
                service_name=self.name,
            )

        self._enforce_rate_limit()

        def _perform_search() -> SearchResult:
            client = self._get_client()

            # Build tool configuration
            tool_config: dict[str, Any] = {"type": "web_search"}
            if allowed_domains:
                tool_config["filters"] = {
                    "allowed_domains": allowed_domains,
                }
            if user_location:
                tool_config["user_location"] = {
                    "type": "approximate",
                    **user_location,
                }

            # Perform search using Responses API
            response = client.responses.create(
                model=MODELS.search,
                input=query,
                tools=[tool_config],
            )

            # Extract answer - use output_text for simple access
            answer = response.output_text if hasattr(response, "output_text") else ""

            citations: list[SearchCitation] = []
            sources: list[str] = []

            # Extract citations and sources from response items if available
            if hasattr(response, "items"):
                for item in response.items:
                    if item.type == "message":
                        for content in item.content:
                            if content.type == "output_text" and hasattr(content, "annotations"):
                                for ann in content.annotations:
                                    if ann.type == "url_citation":
                                        citations.append(
                                            SearchCitation(
                                                url=ann.url,
                                                title=ann.title,
                                                start_index=ann.start_index,
                                                end_index=ann.end_index,
                                            ),
                                        )
                    elif item.type == "web_search_call" and hasattr(item, "action"):
                        if hasattr(item.action, "sources"):
                            sources.extend(item.action.sources)

            return SearchResult(
                answer=answer,
                citations=citations,
                sources=sources,
            )

        try:
            return self._make_api_call(_perform_search)
        except Exception as e:
            raise AIServiceError(
                message=f"Search failed: {e}",
                code="SEARCH_ERROR",
            ) from e

    def search_stream(
        self,
        query: str,
        *,
        user_location: dict[str, str] | None = None,
        allowed_domains: list[str] | None = None,
        num_results: int = 5,
    ):
        """
        Perform streaming web search with citations.

        Args:
            query: Search query
            user_location: Optional user location (country, city)
            allowed_domains: Optional list of allowed domains
            num_results: Number of results to return

        Yields:
            SearchResult items as they stream in

        Raises:
            ServiceUnavailableError: If service not available
            AIServiceError: If search fails
        """
        is_available, error = self.check_available()
        if not is_available:
            raise ServiceUnavailableError(
                error or "Service not available",
                service_name=self.name,
            )

        self._enforce_rate_limit()

        def _perform_streaming_search():
            client = self._get_client()

            # Build tool configuration
            tool_config: dict[str, Any] = {"type": "web_search"}
            if allowed_domains:
                tool_config["filters"] = {
                    "allowed_domains": allowed_domains,
                }
            if user_location:
                tool_config["user_location"] = {
                    "type": "approximate",
                    **user_location,
                }

            # Perform streaming search using Responses API
            for event in client.responses.create(
                model=MODELS.search,
                input=query,
                tools=[tool_config],
                stream=True,
            ):
                # Process streaming events
                if hasattr(event, "type"):
                    if event.type == "content_delta":
                        # Yield text content as it comes in
                        if hasattr(event, "delta") and hasattr(event.delta, "text"):
                            yield {"type": "text_delta", "content": event.delta.text}
                    elif event.type == "response.done":
                        # Final response with all citations and sources
                        response = event.response

                        citations: list[SearchCitation] = []
                        sources: list[str] = []

                        # Extract citations and sources from response items
                        if hasattr(response, "items"):
                            for item in response.items:
                                if item.type == "message":
                                    for content in item.content:
                                        if (content.type == "output_text" and
                                            hasattr(content, "annotations")):
                                            for ann in content.annotations:
                                                if ann.type == "url_citation":
                                                    citations.append(
                                                        SearchCitation(
                                                            url=ann.url,
                                                            title=ann.title,
                                                            start_index=ann.start_index,
                                                            end_index=ann.end_index,
                                                        ),
                                                    )
                                elif (item.type == "web_search_call" and
                                      hasattr(item, "action")):
                                    if hasattr(item.action, "sources"):
                                        sources.extend(item.action.sources)

                        yield {
                            "type": "search_complete",
                            "citations": citations,
                            "sources": sources,
                        }

        try:
            yield from self._make_api_call(_perform_streaming_search)
        except Exception as e:
            raise AIServiceError(
                message=f"Streaming search failed: {e}",
                code="SEARCH_STREAM_ERROR",
            ) from e

    def analyze_image(
        self,
        image_path: str,
        prompt: str,
        *,
        detail_level: str = "auto",
    ) -> VisionResult:
        """
        Analyze image with GPT-4 Vision.

        Args:
            image_path: Path to image file or URL
            prompt: Analysis prompt
            detail_level: Detail level (low, high, auto)

        Returns:
            VisionResult with analysis

        Raises:
            ServiceUnavailableError: If service not available
            AIServiceError: If analysis fails
        """
        is_available, error = self.check_available()
        if not is_available:
            raise ServiceUnavailableError(
                error or "Service not available",
                service_name=self.name,
            )

        self._enforce_rate_limit()

        def _perform_analysis() -> VisionResult:
            from ei_cli.services.image_downloader import ImageDownloader

            client = self._get_client()
            downloader = ImageDownloader()
            temp_file = None

            try:
                # Check if input is a URL
                if downloader.is_url(image_path):
                    # Download to temporary file
                    temp_dir = Path(tempfile.gettempdir()) / "ei_cli_vision"
                    temp_dir.mkdir(exist_ok=True)
                    temp_file = temp_dir / f"temp_image_{Path(image_path).name}"

                    downloader.download_from_url(
                        image_path,
                        temp_file,
                        show_progress=False,  # No progress in service layer
                    )
                    image_source = image_path  # Keep original URL for display
                    file_to_read = temp_file
                else:
                    # Local file path
                    image_source = image_path
                    file_to_read = Path(image_path)

                # Read and encode image
                image_data = file_to_read.read_bytes()
                base64_image = base64.b64encode(image_data).decode("utf-8")

                # Perform analysis using Responses API with correct format for vision
                response = client.responses.create(
                    model=MODELS.vision,
                    input=[
                        {
                            "role": "user",
                            "content": [
                                {"type": "input_text", "text": prompt},
                                {
                                    "type": "input_image",
                                    "image_url": f"data:image/jpeg;base64,{base64_image}",
                                },
                            ],
                        },
                    ],
                )

                # Extract analysis from Responses API response
                # Response format: response.output is list of outputs
                analysis = ""
                for output in response.output:
                    if output.type == "message":
                        for item in output.content:
                            if item.type == "output_text":
                                analysis += item.text

                return VisionResult(
                    analysis=analysis,
                    model=MODELS.vision,
                    image_source=image_source,
                    prompt=prompt,
                )
            finally:
                # Clean up temp file
                if temp_file and temp_file.exists():
                    temp_file.unlink()

        try:
            return self._make_api_call(_perform_analysis)
        except Exception as e:  # pragma: no cover
            raise AIServiceError(
                message=f"Vision analysis failed: {e}",
                code="VISION_ERROR",
            ) from e

    def analyze_multiple_images(
        self,
        image_paths: list[str],
        prompt: str,
        *,
        detail_level: str = "auto",
        compare_mode: bool = False,
    ) -> VisionResult:
        """
        Analyze multiple images simultaneously with GPT-5 Vision.

        Args:
            image_paths: List of paths to image files or URLs (max 4)
            prompt: Analysis prompt for all images
            detail_level: Detail level (low, high, auto)
            compare_mode: If True, focuses on comparing/contrasting images

        Returns:
            VisionResult with combined analysis

        Raises:
            ServiceUnavailableError: If service not available
            AIServiceError: If analysis fails
        """
        is_available, error = self.check_available()
        if not is_available:
            raise ServiceUnavailableError(
                error or "Service not available",
                service_name=self.name,
            )

        if len(image_paths) > 4:
            raise AIServiceError(
                message="Maximum 4 images allowed for multi-image analysis",
                code="MULTI_VISION_ERROR",
            )

        if len(image_paths) < 2:
            raise AIServiceError(
                message="At least 2 images required for multi-image analysis",
                code="MULTI_VISION_ERROR",
            )

        self._enforce_rate_limit()

        def _perform_multi_analysis() -> VisionResult:
            from ei_cli.services.image_downloader import ImageDownloader

            client = self._get_client()
            downloader = ImageDownloader()
            temp_files = []

            try:
                content_items = [{"type": "text", "text": prompt}]

                # Process each image
                for i, image_path in enumerate(image_paths):
                    temp_file = None

                    # Check if input is a URL
                    if downloader.is_url(image_path):
                        # Download to temporary file
                        temp_dir = Path(tempfile.gettempdir()) / "ei_cli_vision"
                        temp_dir.mkdir(exist_ok=True)
                        temp_file = temp_dir / f"temp_multi_image_{i}_{Path(image_path).name}"

                        downloader.download_from_url(
                            image_path,
                            temp_file,
                            show_progress=False,
                        )
                        file_to_read = temp_file
                        temp_files.append(temp_file)
                    else:
                        # Local file path
                        file_to_read = Path(image_path)

                    # Read and encode image
                    image_data = file_to_read.read_bytes()
                    base64_image = base64.b64encode(image_data).decode("utf-8")

                    # Add image to content
                    content_items.append({
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{base64_image}",
                            "detail": detail_level,
                        },
                    })

                # Enhance prompt for comparison if needed
                if compare_mode:
                    comparison_text = (
                        f"{prompt}\n\nPlease compare and contrast "
                        f"these {len(image_paths)} images, highlighting "
                        f"similarities, differences, and key observations."
                    )
                    content_items[0]["text"] = comparison_text

                # Perform analysis using Responses API with correct format
                response = client.responses.create(
                    model=MODELS.vision,
                    input=[
                        {
                            "role": "user",
                            "content": [
                                {
                                    "type": "input_text",
                                    "text": content_items[0]["text"],
                                },
                            ] + [
                                {
                                    "type": "input_image",
                                    "image_url": item["image_url"]["url"],
                                }
                                for item in content_items[1:]
                            ],
                        },
                    ],
                )

                # Extract analysis from Responses API response
                analysis = ""
                for output in response.output:
                    if output.type == "message":
                        for item in output.content:
                            if item.type == "output_text":
                                analysis += item.text

                # Create combined image source display
                image_sources = ", ".join([Path(p).name for p in image_paths])

                return VisionResult(
                    analysis=analysis,
                    model=MODELS.vision,
                    image_source=f"Multiple images: {image_sources}",
                    prompt=prompt,
                )
            finally:
                # Clean up temp files
                for temp_file in temp_files:
                    if temp_file and temp_file.exists():
                        temp_file.unlink()

        try:
            return self._make_api_call(_perform_multi_analysis)
        except Exception as e:  # pragma: no cover
            raise AIServiceError(
                message=f"Multi-image analysis failed: {e}",
                code="MULTI_VISION_ERROR",
            ) from e

    def _enhance_prompt(self, prompt: str) -> str:
        """
        Enhance image prompt for better gpt-image-1 results.

        Applies research-backed optimizations:
        - Adds style descriptors for artistic coherence
        - Enhances lighting and composition details
        - Improves technical quality keywords
        - Maintains original creative intent

        Args:
            prompt: Original user prompt

        Returns:
            Enhanced prompt optimized for gpt-image-1
        """
        # Don't enhance if prompt is already detailed
        descriptive_words = [
            "detailed", "realistic", "cinematic", "professional",
            "high-quality", "artistic", "beautiful", "stunning"
        ]
        has_descriptive = any(
            word in prompt.lower() for word in descriptive_words
        )
        if len(prompt) > 100 and has_descriptive:
            return prompt

        # Detect prompt category for targeted enhancement
        artistic_keywords = ["art", "painting", "drawing", "sketch"]
        photo_keywords = ["photo", "photograph", "realistic", "portrait"]
        fantasy_keywords = ["fantasy", "magical", "dragon", "wizard"]
        tech_keywords = ["robot", "cyberpunk", "futuristic", "sci-fi"]

        prompt_lower = prompt.lower()

        # Base quality enhancers for gpt-image-1
        quality_base = "high quality, detailed, professional"

        # Category-specific enhancements
        if any(kw in prompt_lower for kw in artistic_keywords):
            enhancement = (
                f"{quality_base}, masterpiece, fine art, "
                "beautiful composition, perfect lighting"
            )
        elif any(kw in prompt_lower for kw in photo_keywords):
            enhancement = (
                f"{quality_base}, photorealistic, sharp focus, "
                "perfect lighting, cinematic"
            )
        elif any(kw in prompt_lower for kw in fantasy_keywords):
            enhancement = (
                f"{quality_base}, fantasy art, magical atmosphere, "
                "dramatic lighting, ethereal"
            )
        elif any(kw in prompt_lower for kw in tech_keywords):
            enhancement = (
                f"{quality_base}, futuristic, sleek design, "
                "dynamic lighting, modern"
            )
        else:
            # General enhancement
            enhancement = f"{quality_base}, beautiful, well-composed"

        return f"{prompt}, {enhancement}"

    def _select_smart_quality(self, prompt: str, size: str) -> str:
        """
        Intelligently select optimal quality based on prompt and size.

        Uses research-backed heuristics:
        - Complex/detailed prompts → high quality for precision
        - Simple/abstract prompts → medium quality for speed
        - Large sizes → prefer higher quality
        - Portrait/face content → high quality for detail

        Args:
            prompt: Image generation prompt
            size: Target image size

        Returns:
            Optimal quality setting ("low", "medium", "high")
        """
        prompt_lower = prompt.lower()

        # Factors that suggest high quality needed
        detail_keywords = [
            "detailed", "intricate", "complex", "fine", "precise", "sharp"
        ]
        portrait_keywords = [
            "portrait", "face", "person", "people", "human", "character"
        ]
        professional_keywords = [
            "professional", "commercial", "marketing", "business"
        ]

        # Count complexity indicators
        complexity_score = 0
        complexity_score += sum(
            1 for kw in detail_keywords if kw in prompt_lower
        )
        # Faces need high quality
        complexity_score += sum(
            1 for kw in portrait_keywords if kw in prompt_lower
        ) * 2
        complexity_score += sum(
            1 for kw in professional_keywords if kw in prompt_lower
        )

        # Check for simple/abstract content
        simple_keywords = ["simple", "minimal", "abstract", "basic", "plain"]
        is_simple = any(kw in prompt_lower for kw in simple_keywords)

        # Size factor (larger images benefit more from high quality)
        size_parts = size.split('x')
        if len(size_parts) == 2:
            width, height = int(size_parts[0]), int(size_parts[1])
            total_pixels = width * height
            is_large = total_pixels > 1024 * 1024  # Larger than 1024x1024
        else:
            is_large = False

        # Decision logic
        if complexity_score >= 3 or (complexity_score >= 1 and is_large):
            return "high"
        elif is_simple and not is_large:
            return "low"
        else:
            return "medium"

    def generate_image(
        self,
        prompt: str,
        *,
        size: str = "1024x1024",
        quality: str = "auto",
        output_path: Path | str | None = None,
        show_progress: bool = True,
        enhance_prompt: bool = True,
        use_cache: bool = True,
    ) -> ImageGenerationResult:
        """
        Generate image using gpt-image-1 with intelligent optimizations.

        Uses gpt-image-1 with research-backed enhancements:
        - Smart prompt optimization for better results
        - Intelligent quality selection based on content analysis
        - Optimized parameter combinations for gpt-image-1

        Args:
            prompt: Image generation prompt (max 32000 characters)
            size: Image size (1024x1024, 1536x1024, 1024x1536)
                  Default: 1024x1024
            quality: Quality level (low, medium, high, or auto)
                     auto = intelligent selection based on prompt analysis
                     Default: auto (recommended)
            output_path: Path to save the generated image
                        Can be a file path or directory
                        If directory, filename is auto-generated from prompt
            show_progress: Show progress during save (not used for
                          gpt-image-1 as images are returned immediately)
            enhance_prompt: Apply intelligent prompt enhancements
                           Default: True (recommended)

        Returns:
            ImageGenerationResult with:
            - image_url: data URL with base64-encoded image
            - local_path: Path where image was saved (if output_path provided)
            - model: "gpt-image-1"
            - revised_prompt: Enhanced prompt (if enhance_prompt=True)

        Raises:
            ServiceUnavailableError: If service not available or missing key
            AIServiceError: If generation fails or invalid parameters

        Examples:
            # Basic generation with auto-optimization
            result = service.generate_image("a sunset over mountains")

            # Custom settings, no prompt enhancement
            result = service.generate_image(
                "detailed cyberpunk city at night",
                size="1536x1024",
                quality="high",
                enhance_prompt=False
            )

            # Save to specific file
            result = service.generate_image(
                "abstract art",
                output_path="my_art.png"
            )

            # Save to directory (auto-generates filename)
            result = service.generate_image(
                "a cute kitten",
                output_path="./images/"
            )
        """
        is_available, error = self.check_available()
        if not is_available:
            raise ServiceUnavailableError(
                error or "Service not available",
                service_name=self.name,
            )

        self._enforce_rate_limit()

        # Phase 4: Check intelligent cache first
        cached_result = None
        if use_cache:
            cached_result = self._check_cache(
                prompt, size, quality, enhance_prompt
            )
        if cached_result:
            # If saving to a new path, save the cached image
            if output_path and not cached_result.local_path:
                output_file = Path(output_path)
                if output_file.is_dir() or not output_file.suffix:
                    safe_name = "".join(
                        c if c.isalnum() or c in (" ", "-", "_") else "_"
                        for c in prompt
                    )
                    safe_name = safe_name[:50].strip()
                    if output_file.is_dir():
                        output_file = output_file / f"{safe_name}.png"
                    else:
                        output_file = output_file.with_name(f"{safe_name}.png")

                # Decode and save cached image
                if cached_result.image_url.startswith("data:image/png;base64,"):
                    base64_data = cached_result.image_url.split(",")[1]
                    output_file.parent.mkdir(parents=True, exist_ok=True)
                    image_bytes = base64.b64decode(base64_data)
                    output_file.write_bytes(image_bytes)
                    
                    # Return new result with updated local path
                    return ImageGenerationResult(
                        image_url=cached_result.image_url,
                        revised_prompt=cached_result.revised_prompt,
                        model=cached_result.model,
                        local_path=output_file,
                    )
            
            # Return cached result as-is
            return cached_result

        def _perform_generation() -> ImageGenerationResult:
            client = self._get_client()

            # Phase 3: Analyze prompt metadata for smart defaults and analytics
            metadata = self._analyze_prompt_metadata(prompt)
            
            # Apply intelligent prompt enhancement if enabled
            final_prompt = prompt
            if enhance_prompt:
                final_prompt = self._enhance_prompt(prompt)
                metadata["enhancement_applied"] = True
            else:
                metadata["enhancement_applied"] = False

            # Apply smart quality selection if auto
            final_quality = quality
            if quality == "auto":
                final_quality = self._select_smart_quality(final_prompt, size)

            # Build API call parameters for gpt-image-1
            # Note: gpt-image-1 always returns b64_json
            # (no response_format parameter needed)
            api_params: dict[str, Any] = {
                "model": MODELS.image,  # Always gpt-image-1
                "prompt": final_prompt,
                "size": size,  # type: ignore[arg-type]
                "n": 1,
            }

            # Add quality parameter (now intelligently selected)
            if final_quality != "auto":
                api_params["quality"] = final_quality  # type: ignore[arg-type]

            response = client.images.generate(**api_params)

            # Extract base64-encoded image from response
            image_b64 = response.data[0].b64_json or ""

            # Create data URL for display/reference
            image_url = f"data:image/png;base64,{image_b64}"

            # Return enhanced prompt if enhancement was applied
            revised_prompt = final_prompt if enhance_prompt else None

            # Save image if output path provided
            local_path = None
            if output_path:
                output_file = Path(output_path)

                # If output_path is a directory, create filename
                if output_file.is_dir() or not output_file.suffix:
                    # Create a filename from the prompt (sanitized)
                    safe_name = "".join(
                        c if c.isalnum() or c in (" ", "-", "_") else "_"
                        for c in prompt
                    )
                    safe_name = safe_name[:50].strip()  # Limit length
                    if output_file.is_dir():
                        output_file = output_file / f"{safe_name}.png"
                    else:
                        output_file = output_file.with_name(f"{safe_name}.png")

                # Decode and save base64 image directly
                output_file.parent.mkdir(parents=True, exist_ok=True)
                image_bytes = base64.b64decode(image_b64)
                output_file.write_bytes(image_bytes)
                local_path = output_file

            return ImageGenerationResult(
                image_url=image_url,
                revised_prompt=revised_prompt,
                model=MODELS.image,
                local_path=local_path,
            )

        # Initialize metadata for analytics
        metadata = self._analyze_prompt_metadata(prompt)
        
        try:
            result = self._make_api_call(_perform_generation)
            
            # Phase 4: Store result in cache for future use
            if use_cache:
                self._store_in_cache(
                    prompt, size, quality, enhance_prompt, result
                )
            
            # Log successful generation
            self._log_generation_analytics(prompt, metadata, True)
            return result
        except Exception as e:  # pragma: no cover
            # Log failed generation with enhanced error handling
            error_msg = self._enhanced_error_handling(e, prompt)
            self._log_generation_analytics(prompt, metadata, False, str(e))
            raise AIServiceError(
                message=error_msg,
                code="IMAGE_GEN_ERROR",
            ) from e

    def generate_image_variations(
        self,
        prompt: str,
        *,
        count: int = 3,
        size: str = "1024x1024",
        quality: str = "auto",
        output_dir: Path | str | None = None,
        show_progress: bool = True,
        enhance_prompt: bool = True,
        variation_strategy: str = "creative",
        use_cache: bool = True,
    ) -> ImageVariationsResult:
        """
        Generate multiple variations of the same prompt with intelligent parameter variations.

        Creates diverse interpretations of the same prompt using:
        - Style variations (artistic, photorealistic, minimalist, etc.)
        - Parameter combinations (quality, composition adjustments)
        - Creative prompt modifications while preserving core concept

        Args:
            prompt: Base image generation prompt
            count: Number of variations to generate (1-6, default: 3)
            size: Image size for all variations
            quality: Base quality level (auto recommended)
            output_dir: Directory to save variations (optional)
            show_progress: Show progress during generation
            enhance_prompt: Apply intelligent enhancements
            variation_strategy: Strategy for variations
                - "creative": Diverse artistic interpretations
                - "technical": Parameter and composition variations
                - "style": Different artistic styles
                - "mixed": Combination of all strategies

        Returns:
            ImageVariationsResult with list of generated variations

        Raises:
            ServiceUnavailableError: If service not available
            AIServiceError: If generation fails
        """
        if count < 1 or count > 6:
            raise AIServiceError(
                message="Variation count must be between 1 and 6",
                code="INVALID_VARIATION_COUNT",
            )

        is_available, error = self.check_available()
        if not is_available:
            raise ServiceUnavailableError(
                error or "Service not available",
                service_name=self.name,
            )

        # Analyze base prompt for intelligent variations
        base_metadata = self._analyze_prompt_metadata(prompt)
        
        # Generate variation prompts based on strategy
        variation_prompts = self._generate_variation_prompts(
            prompt, count, variation_strategy, base_metadata
        )

        variations = []
        console = Console() if show_progress else None
        
        for i, (var_prompt, var_params) in enumerate(variation_prompts):
            if console:
                console.print(
                    f"[cyan]Generating variation {i+1}/{count}...[/cyan]"
                )
            
            # Generate individual variation
            try:
                var_quality = var_params.get("quality", quality)
                var_size = var_params.get("size", size)
                
                # Set output path for this variation
                var_output_path = None
                if output_dir:
                    output_path = Path(output_dir)
                    output_path.mkdir(parents=True, exist_ok=True)
                    var_output_path = output_path / f"variation_{i+1}.png"

                result = self.generate_image(
                    prompt=var_prompt,
                    size=var_size,
                    quality=var_quality,
                    output_path=var_output_path,
                    show_progress=False,
                    enhance_prompt=enhance_prompt,
                    use_cache=use_cache,
                )
                variations.append(result)

            except Exception as e:
                # Log error but continue with other variations
                if console:
                    console.print(
                        f"[yellow]Warning: Variation {i+1} failed: {e}[/yellow]"
                    )
                continue

        if not variations:
            raise AIServiceError(
                message="Failed to generate any variations",
                code="ALL_VARIATIONS_FAILED",
            )

        return ImageVariationsResult(
            variations=variations,
            base_prompt=prompt,
            total_generated=len(variations),
            metadata={
                "strategy": variation_strategy,
                "requested_count": count,
                "base_metadata": base_metadata,
            },
        )

    def _generate_variation_prompts(
        self,
        base_prompt: str,
        count: int,
        strategy: str,
        metadata: dict[str, Any],
    ) -> list[tuple[str, dict[str, Any]]]:
        """Generate variation prompts based on strategy and metadata."""
        variations = []
        category = metadata.get("category", "general")
        
        if strategy == "creative":
            # Diverse artistic interpretations
            styles = [
                ("photorealistic", {"quality": "high"}),
                ("artistic painting style", {"quality": "medium"}),
                ("minimalist design", {"quality": "medium"}),
                ("dramatic lighting", {"quality": "high"}),
                ("watercolor style", {"quality": "medium"}),
                ("digital art style", {"quality": "high"}),
            ]
            
        elif strategy == "technical":
            # Parameter and composition variations
            styles = [
                ("wide angle composition", {"size": "1536x1024"}),
                ("close-up detailed view", {"quality": "high"}),
                ("bird's eye perspective", {"quality": "medium"}),
                ("macro photography style", {"quality": "high"}),
                ("panoramic view", {"size": "1536x1024"}),
                ("portrait orientation", {"size": "1024x1536"}),
            ]
            
        elif strategy == "style":
            # Different artistic styles
            styles = [
                ("impressionist painting style", {}),
                ("cyberpunk aesthetic", {}),
                ("vintage photography style", {}),
                ("modern abstract art", {}),
                ("classical realism", {}),
                ("pop art style", {}),
            ]
            
        else:  # mixed strategy
            styles = [
                ("photorealistic", {"quality": "high"}),
                ("artistic interpretation", {"quality": "medium"}),
                ("wide composition", {"size": "1536x1024"}),
                ("dramatic style", {"quality": "high"}),
                ("minimalist approach", {}),
                ("vintage aesthetic", {}),
            ]

        # Create variations by modifying the base prompt
        for i in range(min(count, len(styles))):
            style_modifier, params = styles[i]
            
            # Intelligently integrate style with base prompt
            if category == "portrait":
                var_prompt = f"{base_prompt}, {style_modifier}"
            elif category == "landscape":
                var_prompt = f"{style_modifier} of {base_prompt}"
            else:
                var_prompt = f"{base_prompt} in {style_modifier}"
            
            variations.append((var_prompt, params))

        # If we need more variations, cycle through styles with modifications
        while len(variations) < count:
            remaining = count - len(variations)
            base_idx = len(variations) % len(styles)
            style_modifier, params = styles[base_idx]
            
            # Add additional modifiers for extra variations
            extra_modifiers = [
                "high contrast",
                "soft lighting",
                "vivid colors",
                "muted tones",
                "sharp details",
            ]
            extra = extra_modifiers[len(variations) % len(extra_modifiers)]
            
            var_prompt = f"{base_prompt}, {style_modifier}, {extra}"
            variations.append((var_prompt, params))

        return variations[:count]

    def transcribe_audio(
        self,
        audio_path: str | Path,
        *,
        language: str | None = None,
        prompt: str | None = None,
        response_format: str = "text",
        temperature: float = 0.0,
        preprocess: bool = True,
    ) -> TranscriptionResult:
        """
        Transcribe audio file using OpenAI Whisper.

        Args:
            audio_path: Path to audio file
            language: Optional language code (e.g., 'en', 'es')
            prompt: Optional prompt to guide transcription
            response_format: Response format (text, json, srt, vtt)
            temperature: Sampling temperature (0.0-1.0)
            preprocess: Whether to preprocess audio for speech recognition

        Returns:
            TranscriptionResult with transcribed text

        Raises:
            ServiceUnavailableError: If service not available
            AIServiceError: If transcription fails
        """
        is_available, error = self.check_available()
        if not is_available:
            raise ServiceUnavailableError(
                error or "Service not available",
                service_name=self.name,
            )

        self._enforce_rate_limit()

        def _perform_transcription() -> TranscriptionResult:
            audio_path_obj = Path(audio_path)
            audio_processor = self._get_audio_processor()

            # SPRINT 1: PREPROCESS ONCE BEFORE CHUNKING DECISION
            # This is the key architectural change from the reference implementation
            preprocessed_path = None
            cleanup_preprocessed = False

            if preprocess:
                try:
                    # Preprocess audio ONCE using the new preprocess_audio_file method
                    # This uses caching and verification
                    preprocessed_path = audio_processor.preprocess_audio_file(
                        audio_path_obj,
                        use_cache=True,  # Enable caching for faster retries
                        sample_rate=16000,
                        channels=1,
                        apply_filters=True,
                    )
                    cleanup_preprocessed = False  # Don't delete cached file
                except Exception as e:
                    raise AIServiceError(
                        message=f"Audio preprocessing failed: {e}",
                        code="PREPROCESS_ERROR",
                    ) from e
            else:
                preprocessed_path = audio_path_obj

            # Check the ACTUAL preprocessed file size (not estimated)
            preprocessed_size_mb = preprocessed_path.stat().st_size / (1024 * 1024)

            # Use conservative 20MB threshold on ACTUAL preprocessed size
            # This leaves 5MB buffer below the 25MB API limit
            needs_chunking = preprocessed_size_mb > 20.0

            smart_chunker = self._get_smart_audio_chunker(
                max_chunk_size_mb=20.0,  # Based on estimated preprocessed size
                save_intermediate=False,
            )

            if needs_chunking:
                # CHUNKING REQUIRED: Preprocessed file exceeds 20MB threshold
                console = __import__("rich.console").console.Console()
                console.print(
                    f"[yellow]⚠️  Preprocessed file is "
                    f"{preprocessed_size_mb:.1f}MB (exceeds 20MB threshold). "
                    f"Chunking required.[/yellow]",
                )

                # Use smart chunker for large files
                def transcribe_single_chunk(chunk_path: Path) -> str:
                    """Transcribe a single chunk (already preprocessed)."""
                    # Pass preprocess=False since chunks from preprocessed WAV
                    # don't need additional preprocessing
                    return self._transcribe_single_file(
                        chunk_path,
                        language=language,
                        prompt=prompt,
                        response_format=response_format,
                        temperature=temperature,
                        preprocess=False,  # Already preprocessed!
                    ).text

                # Get audio duration for time-based chunking
                try:
                    duration_sec = audio_processor.get_audio_duration(
                        preprocessed_path,
                    )
                except Exception:
                    # Fallback to estimate from file size
                    # WAV: 16kHz * 1 channel * 2 bytes/sample = 32KB/sec
                    duration_sec = (
                        preprocessed_size_mb * 1024 * 1024 / 32000
                    )

                # Calculate optimal chunks based on duration
                # Use 5-minute chunks (guaranteed < 25MB for preprocessed WAV)
                chunk_duration_sec = 300  # 5 minutes
                num_chunks = int((duration_sec / chunk_duration_sec) + 0.999999)

                console.print(
                    f"[cyan]Audio duration: {duration_sec/60:.1f} minutes, "
                    f"splitting into {num_chunks} chunks of "
                    f"{chunk_duration_sec/60:.0f} minutes each[/cyan]",
                )

                # Create temp output dir for chunks
                temp_dir = Path(tempfile.gettempdir()) / "ei_cli_chunks"
                chunk_dir = temp_dir / "chunks"
                chunk_dir.mkdir(parents=True, exist_ok=True)

                try:
                    # Split the PREPROCESSED audio into chunks using FFmpeg
                    console.print("\n[cyan]🔪 Splitting audio...[/cyan]")
                    chunks = smart_chunker.chunker.split_audio(
                        audio_path=preprocessed_path,  # Use preprocessed WAV!
                        output_dir=chunk_dir,
                        chunk_duration=chunk_duration_sec,
                    )
                    console.print(
                        f"[green]✓ Created {len(chunks)} chunks[/green]",
                    )

                    # Process each chunk with progress
                    results = []
                    console.print("\n[cyan]🎯 Processing chunks...[/cyan]")

                    for i, chunk in enumerate(chunks, 1):
                        console.print(
                            f"\n[bold]Chunk {i}/{len(chunks)}[/bold] "
                            f"({chunk.name})",
                        )
                        result = transcribe_single_chunk(chunk)
                        results.append(result)
                        console.print(f"[green]✓ Chunk {i} complete[/green]")

                    # Combine results
                    combined_text = "\n".join(results)
                    console.print(
                        "\n[green]✓ All chunks processed "
                        "successfully![/green]",
                    )

                    return TranscriptionResult(
                        text=combined_text,
                        language=language,
                        duration=duration_sec,
                        model="whisper-1",
                    )
                finally:
                    # Cleanup temp dir
                    try:
                        if temp_dir.exists():
                            import shutil

                            shutil.rmtree(temp_dir, ignore_errors=True)
                    except Exception:
                        pass  # Best effort cleanup

            # Process single file (no chunking needed)
            # File is already preprocessed, so pass preprocess=False
            return self._transcribe_single_file(
                preprocessed_path,  # Use preprocessed file!
                language=language,
                prompt=prompt,
                response_format=response_format,
                temperature=temperature,
                preprocess=False,  # Already preprocessed!
            )

        try:
            return self._make_api_call(_perform_transcription)
        except AIServiceError:
            raise
        except Exception as e:
            raise AIServiceError(
                message=f"Transcription failed: {e}",
                code="TRANSCRIPTION_ERROR",
            ) from e

    def _transcribe_single_file(
        self,
        audio_path_obj: Path,
        *,
        language: str | None = None,
        prompt: str | None = None,
        response_format: str = "text",
        temperature: float = 0.0,
        preprocess: bool = True,
    ) -> TranscriptionResult:
        """
        Transcribe a single audio file.

        SPRINT 1 CHANGE: Preprocessing now happens in the caller
        (_perform_transcription), not here. This method expects
        the file to already be preprocessed when preprocess=False.

        Args:
            audio_path_obj: Path to audio file (may be preprocessed WAV)
            language: Language code (optional)
            prompt: Prompt to guide transcription (optional)
            response_format: Output format (text/json/srt/vtt)
            temperature: Sampling temperature (0-1)
            preprocess: Legacy parameter, kept for backward compatibility.
                       Should be False when called from new pipeline.

        Returns:
            TranscriptionResult with text and metadata
        """
        # Get audio info
        audio_processor = self._get_audio_processor()
        try:
            audio_info = audio_processor.get_audio_info(audio_path_obj)
        except Exception as e:
            raise AIServiceError(
                message=f"Failed to read audio file: {e}",
                code="AUDIO_READ_ERROR",
            ) from e

        # File size safety check (should already be validated in caller)
        file_size_mb = audio_path_obj.stat().st_size / (1024 * 1024)
        if file_size_mb > 24.5:  # 24.5MB = 500KB safety margin
            raise AIServiceError(
                message=(
                    f"Audio file too large: {file_size_mb:.2f}MB "
                    f"(API limit: 25MB). File should have been chunked."
                ),
                code="FILE_TOO_LARGE",
            )

        try:
            # Transcribe with Whisper (with OpenAI best practices)
            # OpenAI Python SDK handles automatic retries (default: 2)
            # for: 408 Timeout, 409 Conflict, 429 Rate Limit, >=500 errors
            client = self._get_client()

            # Show progress to user
            console = Console()
            file_size_mb = audio_path_obj.stat().st_size / (1024 * 1024)
            console.print(
                f"[cyan]Transcribing {audio_path_obj.name} "
                f"({file_size_mb:.1f}MB)...[/cyan]",
            )

            with audio_path_obj.open("rb") as audio_file:
                kwargs: dict[str, Any] = {
                    "file": audio_file,
                    "model": "whisper-1",
                    "response_format": response_format,
                    "temperature": temperature,
                }

                if language:
                    kwargs["language"] = language
                if prompt:
                    kwargs["prompt"] = prompt

                # OpenAI SDK automatically retries on transient failures
                # Timeout: 10 minutes default (sufficient for large files)
                response = client.audio.transcriptions.create(**kwargs)

            # Confirm completion
            response_len = len(str(response)) if response else 0
            console.print(
                f"[green]✓ Transcription complete ({response_len} chars)"
                f"[/green]",
            )

            # Extract text based on response format
            if response_format == "text":
                # For text format, response is already the text string
                text = response if isinstance(response, str) else str(response)
                detected_lang = None
            elif response_format in ("json", "verbose_json"):
                # For JSON format, return the full JSON structure
                if hasattr(response, "model_dump"):
                    # Pydantic v2 style
                    text = json.dumps(response.model_dump(), indent=2)
                elif hasattr(response, "dict"):
                    # Pydantic v1 style
                    text = json.dumps(response.dict(), indent=2)
                else:
                    # Fallback to string representation
                    text = str(response)
                detected_lang = getattr(response, "language", None)
            else:  # srt, vtt
                text = response if isinstance(response, str) else str(response)
                detected_lang = None

            return TranscriptionResult(
                text=text,
                language=(
                    detected_lang
                    if response_format == "json"
                    else language
                ),
                duration=audio_info.get("duration"),
                model="whisper-1",
            )

        except Exception as e:
            if "413" in str(e) or "Payload Too Large" in str(e):
                raise AIServiceError(
                    message=(
                        f"File too large for API (file size: "
                        f"{file_size_mb:.2f}MB). This should not happen "
                        f"- chunking should have been triggered."
                    ),
                    code="FILE_TOO_LARGE",
                ) from e
            raise

    async def _transcribe_chunk_async(
        self,
        chunk_path: Path,
        *,
        language: str | None = None,
        prompt: str | None = None,
        response_format: str = "text",
        temperature: float = 0.0,
        max_retries: int = 3,
    ) -> str:
        """
        Transcribe a single chunk asynchronously with retry logic.

        SPRINT 3: Async version for parallel processing.
        RESILIENCE: Retry with exponential backoff (1s, 2s, 4s).

        Args:
            chunk_path: Path to audio chunk (preprocessed WAV)
            language: Language code (optional)
            prompt: Prompt to guide transcription (optional)
            response_format: Output format (text/json/srt/vtt)
            temperature: Sampling temperature (0-1)
            max_retries: Maximum retry attempts (default: 3)

        Returns:
            Transcribed text

        Raises:
            AIServiceError: If all retries exhausted
        """
        client = self._get_async_client()
        last_error = None

        for attempt in range(max_retries):
            try:
                # Async rate limiting using aiolimiter
                async with self._async_rate_limiter:
                    with open(chunk_path, "rb") as audio_file:
                        response = await client.audio.transcriptions.create(
                            model="whisper-1",
                            file=audio_file,
                            language=language,
                            prompt=prompt,
                            temperature=temperature,
                            response_format=response_format,
                        )

                # For text format, OpenAI returns the text directly as a string
                # Ensure we return it as a plain string
                if isinstance(response, str):
                    return response
                # If it's an object with text attribute
                if hasattr(response, "text"):
                    return response.text
                # Fallback: convert to string
                return str(response)

            except Exception as e:
                last_error = e
                if attempt < max_retries - 1:
                    # Exponential backoff: 1s, 2s, 4s
                    backoff_time = 2**attempt
                    await asyncio.sleep(backoff_time)
                else:
                    # All retries exhausted for this chunk
                    pass

        # All retries exhausted
        raise AIServiceError(
            message=(
                f"Failed to transcribe {chunk_path.name} after "
                f"{max_retries} attempts: {last_error}"
            ),
            code="TRANSCRIPTION_RETRY_EXHAUSTED",
        ) from last_error

    async def _transcribe_chunks_parallel(
        self,
        chunks: list[Path],
        *,
        language: str | None = None,
        prompt: str | None = None,
        response_format: str = "text",
        temperature: float = 0.0,
        max_concurrent: int = 3,
        progress_callback: Callable[[int, int], None] | None = None,
    ) -> list[str]:
        """
        Transcribe multiple chunks in parallel with rate limiting.

        SPRINT 3: Process chunks concurrently for 3-5× speedup.
        RESILIENCE: Progress callback for real-time updates.

        Args:
            chunks: List of chunk file paths
            language: Language code (optional)
            prompt: Prompt to guide transcription (optional)
            response_format: Output format (text/json/srt/vtt)
            temperature: Sampling temperature (0-1)
            max_concurrent: Max concurrent requests (default: 3)
            progress_callback: Optional callback(completed, total)

        Returns:
            List of transcribed texts in original order
        """
        from rich.console import Console

        console = Console()
        total_chunks = len(chunks)
        results = [""] * total_chunks
        completed = 0

        # Create a semaphore to limit concurrency
        semaphore = asyncio.Semaphore(max_concurrent)

        async def transcribe_with_semaphore(idx: int, chunk: Path) -> None:
            """Transcribe a single chunk with concurrency control."""
            nonlocal completed
            async with semaphore:
                try:
                    result = await self._transcribe_chunk_async(
                        chunk,
                        language=language,
                        prompt=prompt,
                        response_format=response_format,
                        temperature=temperature,
                    )
                    results[idx] = result
                    completed += 1

                    console.print(
                        f"[green]✓ Chunk {idx+1}/{total_chunks} complete "
                        f"({len(result)} chars)[/green]",
                    )

                    # Report progress after each completion
                    if progress_callback:
                        progress_callback(completed, total_chunks)

                except Exception as e:
                    console.print(
                        f"[red]✗ Chunk {idx+1}/{total_chunks} failed: {e}[/red]",
                    )
                    raise AIServiceError(
                        message=f"Chunk {idx + 1} failed: {e}",
                        code="TRANSCRIPTION_ERROR",
                    ) from e

        # Create tasks for all chunks and gather them
        tasks = [
            transcribe_with_semaphore(idx, chunk) for idx, chunk in enumerate(chunks)
        ]

        # Run all tasks concurrently (semaphore limits actual concurrency)
        await asyncio.gather(*tasks)

        return results

    def transcribe_audio_parallel(
        self,
        audio_path: Path | str,
        *,
        language: str | None = None,
        prompt: str | None = None,
        response_format: str = "text",
        temperature: float = 0.0,
        max_concurrent: int = 3,
        progress_callback: Callable[[int, int], None] | None = None,
    ) -> TranscriptionResult:
        """
        Transcribe audio with async parallel processing for chunks.

        SPRINT 3: Async parallel version for 3-5× faster transcription.
        RESILIENCE: Progress callback for real-time updates.
        Uses the same preprocessing pipeline as transcribe_audio(),
        but processes chunks in parallel.

        Args:
            audio_path: Path to audio/video file
            language: Language code (optional, e.g., 'en', 'es')
            prompt: Prompt to guide transcription (optional)
            response_format: Output format (text/json/srt/vtt, default: text)
            temperature: Sampling temperature (0-1, default: 0)
            max_concurrent: Max concurrent chunk transcriptions (default: 3)
            progress_callback: Optional callback(completed, total)

        Returns:
            TranscriptionResult with combined text and metadata
        """

        def _perform_transcription() -> TranscriptionResult:
            """Inner function with preprocessing and chunking logic."""
            audio_path_obj = Path(audio_path)
            audio_processor = self._get_audio_processor()

            # SPRINT 1: Preprocess ONCE before chunking decision
            if audio_path_obj.suffix.lower() in {".wav", ".wave"}:
                preprocessed_path = audio_path_obj
            else:
                try:
                    preprocessed_path = audio_processor.preprocess_audio_file(
                        audio_path_obj,
                        use_cache=True,
                        sample_rate=16000,
                        channels=1,
                        apply_filters=True,
                    )
                except Exception as e:
                    raise AIServiceError(
                        message=f"Audio preprocessing failed: {e}",
                        code="PREPROCESS_ERROR",
                    ) from e

            # Check ACTUAL preprocessed file size
            preprocessed_size_mb = (
                preprocessed_path.stat().st_size / (1024 * 1024)
            )
            needs_chunking = preprocessed_size_mb > 20.0

            if needs_chunking:
                # CHUNKING with ASYNC PARALLEL processing
                from rich.console import Console

                console = Console()
                console.print(
                    f"[yellow]⚠️  Preprocessed file is "
                    f"{preprocessed_size_mb:.1f}MB. "
                    f"Using async parallel processing.[/yellow]",
                )

                # Get duration and create chunks
                try:
                    duration_sec = audio_processor.get_audio_duration(
                        preprocessed_path,
                    )
                except Exception:
                    duration_sec = preprocessed_size_mb * 1024 * 1024 / 32000

                chunk_duration_sec = DEFAULT_CHUNK_DURATION_SEC
                num_chunks = int((duration_sec / chunk_duration_sec) + 0.999999)

                console.print(
                    f"[cyan]Audio duration: {duration_sec/60:.1f} minutes, "
                    f"splitting into {num_chunks} chunks[/cyan]",
                )

                # Create chunks
                temp_dir = Path(tempfile.gettempdir()) / "ei_cli_chunks"
                chunk_dir = temp_dir / "chunks"
                chunk_dir.mkdir(parents=True, exist_ok=True)

                try:
                    smart_chunker = self._get_smart_audio_chunker(
                        max_chunk_size_mb=20.0,
                        save_intermediate=False,
                    )

                    console.print("\n[cyan]🔪 Splitting audio...[/cyan]")
                    chunks = smart_chunker.chunker.split_audio(
                        audio_path=preprocessed_path,
                        output_dir=chunk_dir,
                        chunk_duration=chunk_duration_sec,
                    )
                    console.print(
                        f"[green]✓ Created {len(chunks)} chunks[/green]",
                    )

                    # SPRINT 3: Process chunks in PARALLEL
                    console.print(
                        f"\n[cyan]🚀 Processing {len(chunks)} chunks "
                        f"in parallel (max {max_concurrent} concurrent)...[/cyan]",
                    )
                    console.print(
                        "[yellow]⏳ This may take a few minutes. "
                        "Processing in background...[/yellow]",
                    )

                    # Run async transcription
                    results = asyncio.run(
                        self._transcribe_chunks_parallel(
                            chunks,
                            language=language,
                            prompt=prompt,
                            response_format=response_format,
                            temperature=temperature,
                            max_concurrent=max_concurrent,
                            progress_callback=progress_callback,
                        ),
                    )

                    combined_text = "\n".join(results)
                    console.print(
                        "\n[green bold]✓ All chunks processed![/green bold]",
                    )

                    return TranscriptionResult(
                        text=combined_text,
                        language=language,
                        duration=duration_sec,
                        model="whisper-1",
                    )
                finally:
                    # Cleanup temp directory
                    if temp_dir.exists():
                        import shutil
                        import contextlib
                        with contextlib.suppress(OSError):
                            shutil.rmtree(temp_dir)

            # Single file (no chunking needed)
            return self._transcribe_single_file(
                preprocessed_path,
                language=language,
                prompt=prompt,
                response_format=response_format,
                temperature=temperature,
                preprocess=False,
            )

        try:
            return self._make_api_call(_perform_transcription)
        except AIServiceError:
            raise
        except Exception as e:
            raise AIServiceError(
                message=f"Transcription failed: {e}",
                code="TRANSCRIPTION_ERROR",
            ) from e

    def text_to_speech(
        self,
        text: str,
        output_path: Path | str,
        voice: str = "alloy",
        speed: float = 1.0,
        model: str = "tts-1",
        response_format: str = "mp3",
        instructions: str | None = None,
    ) -> TextToSpeechResult:
        """
        Generate speech audio from text using OpenAI TTS.

        Args:
            text: The text to convert to speech (max 4096 chars for tts-1)
            output_path: Where to save the audio file
            voice: Voice to use (alloy/ash/ballad/coral/echo/fable/onyx/nova/sage/shimmer/verse for tts-1,
                   or alloy/echo/fable/onyx/nova/shimmer/marin/cedar for tts-1-hd)
            speed: Playback speed (0.25 to 4.0, default 1.0)
            model: TTS model (tts-1 or tts-1-hd)
            response_format: Audio format (mp3, opus, aac, flac, wav, pcm)
            instructions: Optional guidance for pronunciation, pacing, or style (max 4096 chars)

        Returns:
            TextToSpeechResult with audio_path and metadata

        Raises:
            AIServiceError: If TTS generation fails
        """
        # Validate parameters
        # tts-1 supports 11 voices, tts-1-hd supports 8 voices (6 standard + marin/cedar)
        valid_voices_standard = {
            "alloy",
            "echo",
            "fable",
            "onyx",
            "nova",
            "shimmer",
        }
        valid_voices_tts1 = valid_voices_standard | {
            "ash",
            "ballad",
            "coral",
            "sage",
            "verse",
        }
        valid_voices_hd = valid_voices_standard | {
            "marin",
            "cedar",
        }

        # Validate format
        valid_formats = {"mp3", "opus", "aac", "flac", "wav", "pcm"}
        if response_format not in valid_formats:
            valid_list = ", ".join(sorted(valid_formats))
            raise AIServiceError(
                message=f"Invalid format '{response_format}'. Must be: {valid_list}",
                code="INVALID_FORMAT",
            )

        # Check voice validity based on model
        if model == "tts-1-hd":
            valid_voices = valid_voices_hd
            if voice not in valid_voices:
                valid_list = ", ".join(sorted(valid_voices))
                raise AIServiceError(
                    message=f"Invalid voice '{voice}' for {model}. Must be: {valid_list}",
                    code="INVALID_VOICE",
                )
        else:  # tts-1
            valid_voices = valid_voices_tts1
            if voice not in valid_voices:
                valid_list = ", ".join(sorted(valid_voices))
                raise AIServiceError(
                    message=f"Invalid voice '{voice}' for {model}. Must be: {valid_list}",
                    code="INVALID_VOICE",
                )

        if not MIN_TTS_SPEED <= speed <= MAX_TTS_SPEED:
            raise AIServiceError(
                message=f"Speed {speed} out of range. Must be 0.25-4.0",
                code="INVALID_SPEED",
            )

        if not text or not text.strip():
            raise AIServiceError(
                message="Text cannot be empty",
                code="EMPTY_TEXT",
            )

        # Convert to Path
        output_path = Path(output_path)

        # Enforce rate limit
        self._enforce_rate_limit()

        def _perform_tts() -> TextToSpeechResult:
            """Perform the actual TTS API call."""
            try:
                # Get client (initializes if needed)
                client = self._get_client()

                # Build API parameters
                api_params = {
                    "model": model,
                    "voice": voice,
                    "input": text,
                    "speed": speed,
                    "response_format": response_format,
                }

                # Add optional instructions if provided
                if instructions:
                    api_params["instructions"] = instructions

                # Call OpenAI TTS API
                response = client.audio.speech.create(**api_params)  # type: ignore[arg-type]

                # Create output directory if needed
                output_path.parent.mkdir(parents=True, exist_ok=True)

                # Stream audio to file
                response.stream_to_file(str(output_path))

                return TextToSpeechResult(
                    audio_path=output_path,
                    model=model,
                    voice=voice,
                )

            except Exception as e:
                error_msg = str(e)
                raise AIServiceError(
                    message=f"TTS generation failed: {error_msg}",
                    code="TTS_ERROR",
                ) from e

        try:
            return self._make_api_call(_perform_tts)
        except AIServiceError:
            raise
        except Exception as e:
            raise AIServiceError(
                message=f"Text-to-speech failed: {e}",
                code="TTS_ERROR",
            ) from e

    def text_to_speech_stream(
        self,
        text: str,
        output_path: Path | str,
        voice: str = "alloy",
        speed: float = 1.0,
        model: str = "tts-1",
        response_format: str = "mp3",
        on_chunk: Callable[[int, int], None] | None = None,
        instructions: str | None = None,
    ) -> TextToSpeechResult:
        """
        Generate speech audio from text with streaming support.

        Streams audio chunks as they're generated, allowing for progress
        indication and early cancellation. Writes incrementally to file.

        Args:
            text: The text to convert to speech (max 4096 chars for tts-1)
            output_path: Where to save the audio file
            voice: Voice to use (model-specific, see text_to_speech)
            speed: Playback speed (0.25 to 4.0, default 1.0)
            model: TTS model (tts-1 or tts-1-hd)
            response_format: Audio format (mp3, opus, aac, flac, wav, pcm)
            on_chunk: Optional callback(bytes_received, total_bytes) for progress
            instructions: Optional guidance for pronunciation, pacing, or style (max 4096 chars)

        Returns:
            TextToSpeechResult with audio_path and metadata

        Raises:
            AIServiceError: If TTS generation fails
        """
        # Validate parameters using same logic as text_to_speech
        valid_voices_standard = {
            "alloy",
            "echo",
            "fable",
            "onyx",
            "nova",
            "shimmer",
        }
        valid_voices_tts1 = valid_voices_standard | {
            "ash",
            "ballad",
            "coral",
            "sage",
            "verse",
        }
        valid_voices_hd = valid_voices_standard | {
            "marin",
            "cedar",
        }

        # Validate format
        valid_formats = {"mp3", "opus", "aac", "flac", "wav", "pcm"}
        if response_format not in valid_formats:
            valid_list = ", ".join(sorted(valid_formats))
            raise AIServiceError(
                message=f"Invalid format '{response_format}'. Must be: {valid_list}",
                code="INVALID_FORMAT",
            )

        # Check voice validity based on model
        if model == "tts-1-hd":
            valid_voices = valid_voices_hd
            if voice not in valid_voices:
                valid_list = ", ".join(sorted(valid_voices))
                raise AIServiceError(
                    message=f"Invalid voice '{voice}' for {model}. Must be: {valid_list}",
                    code="INVALID_VOICE",
                )
        else:  # tts-1
            valid_voices = valid_voices_tts1
            if voice not in valid_voices:
                valid_list = ", ".join(sorted(valid_voices))
                raise AIServiceError(
                    message=f"Invalid voice '{voice}' for {model}. Must be: {valid_list}",
                    code="INVALID_VOICE",
                )

        min_speed = 0.25
        max_speed = 4.0
        if not min_speed <= speed <= max_speed:
            raise AIServiceError(
                message=f"Speed {speed} out of range [{min_speed}, {max_speed}]",
                code="INVALID_SPEED",
            )

        if not text or not text.strip():
            raise AIServiceError(
                message="Text cannot be empty",
                code="EMPTY_TEXT",
            )

        output_path = Path(output_path)

        # Enforce rate limit
        self._enforce_rate_limit()

        def _perform_streaming_tts() -> TextToSpeechResult:
            try:
                # Get client (initializes if needed)
                client = self._get_client()

                # Build API parameters
                api_params = {
                    "model": model,
                    "voice": voice,
                    "input": text,
                    "speed": speed,
                    "response_format": response_format,
                }

                # Add optional instructions if provided
                if instructions:
                    api_params["instructions"] = instructions

                # Create streaming request
                response = client.audio.speech.create(**api_params)  # type: ignore[arg-type]

                # Stream to file with progress tracking
                bytes_received = 0
                chunk_size = 8192  # 8KB chunks

                output_path.parent.mkdir(parents=True, exist_ok=True)

                with output_path.open("wb") as f:
                    for chunk in response.iter_bytes(chunk_size=chunk_size):
                        if chunk:
                            f.write(chunk)
                            bytes_received += len(chunk)

                            # Call progress callback if provided
                            if on_chunk:
                                # Total size unknown for streaming, pass 0
                                on_chunk(bytes_received, 0)

                return TextToSpeechResult(
                    audio_path=output_path,
                    model=model,
                    voice=voice,
                )

            except Exception as e:
                error_msg = str(e)
                raise AIServiceError(
                    message=f"Streaming TTS generation failed: {error_msg}",
                    code="TTS_STREAMING_ERROR",
                ) from e

        try:
            return self._make_api_call(_perform_streaming_tts)
        except AIServiceError:
            raise
        except Exception as e:
            raise AIServiceError(
                message=f"Streaming text-to-speech failed: {e}",
                code="TTS_STREAMING_ERROR",
            ) from e

    def translate_audio(
        self,
        audio_path: Path | str,
        prompt: str | None = None,
        response_format: str = "text",
        temperature: float = 0.0,
        preprocess: bool = True,
    ) -> TranscriptionResult:
        """
        Translate audio from any language to English using Whisper.

        Args:
            audio_path: Path to audio file
            prompt: Optional text to guide translation
            response_format: Output format (text/json/srt/vtt)
            temperature: Sampling temperature (0.0-1.0)
            preprocess: Whether to preprocess audio (mono, 16kHz)

        Returns:
            TranscriptionResult with translated text and metadata

        Raises:
            AIServiceError: If translation fails
        """
        # Validate parameters
        valid_formats = {"text", "json", "srt", "vtt"}
        if response_format not in valid_formats:
            valid_list = ", ".join(sorted(valid_formats))
            raise AIServiceError(
                message=f"Invalid format '{response_format}'. Must be: {valid_list}",
                code="INVALID_FORMAT",
            )

        if not 0.0 <= temperature <= 1.0:
            raise AIServiceError(
                message=f"Temperature {temperature} out of range. Must be 0.0-1.0",
                code="INVALID_TEMPERATURE",
            )

        # Convert to Path
        audio_path = Path(audio_path)
        if not audio_path.exists():
            raise AIServiceError(
                message=f"Audio file not found: {audio_path}",
                code="FILE_NOT_FOUND",
            )

        # Enforce rate limit
        self._enforce_rate_limit()

        def _perform_translation() -> TranscriptionResult:
            """Perform the actual translation API call."""
            # Get audio processor if preprocessing is enabled
            processor = self._get_audio_processor() if preprocess else None

            # Preprocess audio if needed
            cleanup_needed = False
            processed_path = audio_path

            try:
                if processor:
                    try:
                        # Create temp file for processed audio
                        temp_fd, temp_path = tempfile.mkstemp(suffix=".wav")
                        os.close(temp_fd)
                        processed_path = Path(temp_path)

                        # Preprocess audio
                        processor.preprocess(
                            input_path=audio_path,
                            output_path=processed_path,
                        )
                        cleanup_needed = True

                    except Exception as e:
                        raise AIServiceError(
                            message=f"Audio preprocessing failed: {e}",
                            code="PREPROCESSING_ERROR",
                        ) from e

                # Open audio file
                with open(processed_path, "rb") as audio_file:
                    # Call Whisper translation API
                    client = self._get_client()
                    response = client.audio.translations.create(
                        model="whisper-1",
                        file=audio_file,
                        prompt=prompt,
                        response_format=response_format,
                        temperature=temperature,
                    )

                # Parse response based on format
                if response_format == "json":
                    # Response is a dict
                    text = response.text  # type: ignore[union-attr]
                    duration = getattr(response, "duration", None)
                else:
                    # Response is plain text
                    text = str(response)
                    duration = None

                return TranscriptionResult(
                    text=text,
                    language="en",  # Always English for translation
                    duration=duration,
                    model="whisper-1",
                )

            finally:
                # Cleanup temp file if needed
                if cleanup_needed and processed_path.exists():
                    processed_path.unlink()

        try:
            return self._make_api_call(_perform_translation)
        except AIServiceError:
            raise
        except Exception as e:
            raise AIServiceError(
                message=f"Audio translation failed: {e}",
                code="TRANSLATION_ERROR",
            ) from e

    # Phase 3: Smart Defaults and Analytics Methods
    def _analyze_prompt_metadata(self, prompt: str) -> dict:
        """
        Analyze prompt to extract metadata for analytics and smart defaults.
        Returns dictionary with prompt analysis results.
        """
        prompt_lower = prompt.lower()
        words = prompt.split()
        
        # Category classification
        categories = {
            'artistic': ['painting', 'artwork', 'artistic', 'style', 'brush',
                        'canvas'],
            'photographic': ['photo', 'photograph', 'camera', 'lens', 'shot'],
            'portrait': ['portrait', 'face', 'person', 'headshot', 'close-up'],
            'landscape': ['landscape', 'scenery', 'nature', 'outdoor',
                         'mountain'],
            'fantasy': ['fantasy', 'magical', 'dragon', 'wizard', 'mystical'],
            'technology': ['robot', 'cyberpunk', 'futuristic', 'sci-fi',
                          'digital'],
            'abstract': ['abstract', 'geometric', 'pattern', 'shapes']
        }
        
        detected_categories = []
        for category, keywords in categories.items():
            if any(keyword in prompt_lower for keyword in keywords):
                detected_categories.append(category)
        
        # If no specific category, default to 'general'
        if detected_categories:
            primary_category = detected_categories[0]
        else:
            primary_category = 'general'
        
        return {
            'word_count': len(words),
            'char_count': len(prompt),
            'primary_category': primary_category,
            'all_categories': detected_categories,
            'complexity_score': self._calculate_complexity_score(prompt),
            'recommended_quality': self._select_smart_quality(
                prompt, "1024x1024"),
            'enhancement_applied': True
        }

    def _calculate_complexity_score(self, prompt: str) -> float:
        """
        Calculate complexity score (0.0 to 1.0) based on various factors.
        """
        words = prompt.split()
        prompt_lower = prompt.lower()
        
        # Base score from word count (normalized to 0-0.4)
        word_score = min(len(words) / 25.0, 0.4)
        
        # Descriptive words bonus (0-0.3)
        descriptive_words = [
            "detailed", "intricate", "complex", "elaborate",
            "sophisticated", "ornate", "rich", "vibrant"
        ]
        desc_count = sum(
            1 for word in descriptive_words if word in prompt_lower
        )
        desc_score = min(desc_count * 0.1, 0.3)
        
        # Technical terms bonus (0-0.2)
        technical_words = [
            "professional", "high-resolution", "4k", "8k",
            "photorealistic", "hyperrealistic", "cinematic"
        ]
        tech_count = sum(
            1 for word in technical_words if word in prompt_lower
        )
        tech_score = min(tech_count * 0.1, 0.2)
        
        # Multi-element bonus (0-0.1)
        elements = [",", "and", "with", "in", "on", "under", "over"]
        element_count = sum(1 for elem in elements if elem in prompt_lower)
        element_score = min(element_count * 0.02, 0.1)
        
        return min(
            word_score + desc_score + tech_score + element_score, 1.0
        )

    def _get_smart_defaults(self, prompt: str, metadata: dict) -> dict:
        """
        Generate smart defaults based on prompt analysis.
        """
        defaults = {
            'quality': metadata['recommended_quality'],
            'style': 'natural'  # Default style
        }
        
        # Adjust style based on category
        category_styles = {
            "artistic": "vivid",
            "photographic": "natural",
            "portrait": "natural",
            "fantasy": "vivid",
            "technology": "vivid",
            "abstract": "vivid"
        }
        
        if metadata['primary_category'] in category_styles:
            defaults['style'] = category_styles[metadata['primary_category']]
        
        return defaults

    def _log_generation_analytics(
        self, prompt: str, metadata: dict, success: bool, error: str = None
    ) -> None:
        """
        Log analytics data for generation requests.
        This is a placeholder for future analytics implementation.
        """
        from datetime import datetime
        
        # Store analytics data for session
        analytics_data = {
            "timestamp": datetime.now().isoformat(),
            "prompt_metadata": metadata,
            "success": success,
            "error": error,
            "model": "gpt-image-1"
        }        # For now, just store in memory for this session
        if not hasattr(self, '_analytics_log'):
            self._analytics_log = []
        
        self._analytics_log.append(analytics_data)
        
        # Optional: Print analytics in development mode
        if success:
            complexity = metadata["complexity_score"]
            category = metadata["primary_category"]
            print(f"📊 Analytics: {category} (complexity: {complexity:.2f})")
        else:
            print(f"❌ Analytics: Generation failed - {error}")

    def _enhanced_error_handling(self, error: Exception, prompt: str) -> str:
        """
        Provide enhanced error messages with helpful suggestions.
        """
        error_msg = str(error)
        
        # Common error patterns and suggestions
        if "content_policy" in error_msg.lower():
            return (
                "Content policy violation. Try rephrasing to avoid "
                f"potentially sensitive content. Error: {error_msg}"
            )
        
        if "rate_limit" in error_msg.lower():
            return (
                "Rate limit exceeded. Please wait a moment before trying "
                f"again. Error: {error_msg}"
            )
        
        if "invalid_request" in error_msg.lower():
            return (
                "Invalid request. Check your prompt length and content. "
                f"Error: {error_msg}"
            )
        
        # Generic enhanced error
        return f"Image generation failed: {error_msg}"

    def get_analytics_summary(self) -> dict:
        """
        Get summary of analytics data for this session.
        """
        if not hasattr(self, "_analytics_log"):
            return {
                "total_requests": 0,
                "success_rate": 0.0,
                "categories": {},
            }
        
        total = len(self._analytics_log)
        successful = sum(
            1 for entry in self._analytics_log if entry["success"]
        )
        
        # Category breakdown
        categories = {}
        for entry in self._analytics_log:
            if entry["success"]:
                category = entry["prompt_metadata"]["primary_category"]
                categories[category] = categories.get(category, 0) + 1
        
        return {
            "total_requests": total,
            "successful_requests": successful,
            "success_rate": successful / total if total > 0 else 0.0,
            "categories": categories,
            "average_complexity": sum(
                entry["prompt_metadata"]["complexity_score"]
                for entry in self._analytics_log if entry["success"]
            ) / successful if successful > 0 else 0.0,
        }

    # Phase 4: Intelligent Caching System
    def _generate_cache_key(
        self, prompt: str, size: str, quality: str, enhanced: bool
    ) -> str:
        """Generate cache key for image generation request."""
        import hashlib
        
        # Create a normalized prompt for caching
        norm_prompt = prompt.strip().lower()
        
        # Include parameters in cache key
        cache_data = f"{norm_prompt}|{size}|{quality}|{enhanced}"
        
        return hashlib.md5(cache_data.encode()).hexdigest()

    def _calculate_prompt_similarity(self, prompt1: str, prompt2: str) -> float:
        """
        Calculate similarity between two prompts using word overlap.
        Returns similarity score between 0.0 and 1.0.
        """
        words1 = set(prompt1.lower().strip().split())
        words2 = set(prompt2.lower().strip().split())
        
        if not words1 or not words2:
            return 0.0
        
        # Calculate Jaccard similarity (intersection over union)
        intersection = len(words1.intersection(words2))
        union = len(words1.union(words2))
        
        return intersection / union if union > 0 else 0.0

    def _check_cache(
        self, prompt: str, size: str, quality: str, enhanced: bool
    ) -> ImageGenerationResult | None:
        """
        Check if a similar request exists in cache.
        Returns cached result if found, None otherwise.
        """
        import time
        
        current_time = time.time()
        
        # Clean expired entries
        expired_keys = []
        for key, (result, timestamp) in self._cache.items():
            if current_time - timestamp > self._cache_max_age:
                expired_keys.append(key)
        
        for key in expired_keys:
            del self._cache[key]
        
        # Check for exact match first
        cache_key = self._generate_cache_key(prompt, size, quality, enhanced)
        if cache_key in self._cache:
            result, _ = self._cache[cache_key]
            self._cache_hits += 1
            return result
        
        # Check for similar prompts
        for cached_result, _ in self._cache.values():
            similarity = self._calculate_prompt_similarity(
                prompt, cached_result.revised_prompt or "",
            )
            
            if similarity >= self._cache_similarity_threshold:
                self._cache_hits += 1
                return cached_result
        
        # No cache hit found
        self._cache_misses += 1
        return None

    def _store_in_cache(
        self,
        prompt: str,
        size: str,
        quality: str,
        enhanced: bool,
        result: ImageGenerationResult,
    ) -> None:
        """Store generation result in cache."""
        import time
        
        cache_key = self._generate_cache_key(prompt, size, quality, enhanced)
        self._cache[cache_key] = (result, time.time())
        
        # Limit cache size (keep last 100 entries)
        if len(self._cache) > 100:
            # Remove oldest entries
            oldest_keys = sorted(
                self._cache.keys(),
                key=lambda k: self._cache[k][1]
            )[:20]  # Remove 20 oldest
            
            for key in oldest_keys:
                del self._cache[key]

    def get_cache_stats(self) -> dict[str, Any]:
        """Get cache statistics."""
        import time
        
        current_time = time.time()
        valid_entries = sum(
            1 for _, timestamp in self._cache.values()
            if current_time - timestamp <= self._cache_max_age
        )
        
        return {
            "entries": len(self._cache),
            "valid_entries": valid_entries,
            "hits": self._cache_hits,
            "misses": self._cache_misses,
            "cache_max_age": self._cache_max_age,
            "similarity_threshold": self._cache_similarity_threshold,
        }

