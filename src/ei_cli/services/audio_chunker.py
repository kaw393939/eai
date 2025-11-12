"""Audio chunking utilities for handling large files."""

import json
import math
import re
import subprocess
from pathlib import Path
from typing import TYPE_CHECKING

from rich.console import Console

if TYPE_CHECKING:
    from ei_cli.services.audio_processor import AudioProcessor

console = Console()


class AudioChunkerError(Exception):
    """Error during audio chunking operations."""

    def __init__(self, message: str, details: dict | None = None) -> None:
        """
        Initialize audio chunker error.

        Args:
            message: Error message
            details: Optional error details
        """
        super().__init__(message)
        self.message = message
        self.details = details or {}


class AudioChunker:
    """Handles splitting and merging audio files for processing."""

    # Whisper API limit is 25MB
    MAX_FILE_SIZE_MB = 25

    def __init__(self, processor: "AudioProcessor") -> None:
        """
        Initialize audio chunker.

        Args:
            processor: AudioProcessor instance for file operations
        """
        self.processor = processor

    def needs_chunking(self, audio_path: Path) -> bool:
        """
        Check if audio file needs chunking.

        Args:
            audio_path: Path to audio file

        Returns:
            True if file is larger than MAX_FILE_SIZE_MB
        """
        if not audio_path.exists():
            raise AudioChunkerError(
                message=f"Audio file not found: {audio_path}",
            )

        size_mb = audio_path.stat().st_size / (1024 * 1024)
        return size_mb > self.MAX_FILE_SIZE_MB

    def split_audio(
        self,
        audio_path: Path,
        output_dir: Path,
        chunk_duration: int = 300,
    ) -> list[Path]:
        """
        Split audio file into chunks using FFmpeg fast seeking.

        Args:
            audio_path: Path to input audio file
            output_dir: Directory for output chunks
            chunk_duration: Duration of each chunk in seconds (default: 5 min)
                5 minutes = 300 seconds guarantees < 25MB per chunk for
                16kHz mono WAV (9.6MB actual vs 25MB API limit)

        Returns:
            List of paths to chunk files

        Raises:
            AudioChunkerError: If splitting fails
        """
        try:
            # Get audio info
            info = self.processor.get_audio_info(audio_path)
            total_duration = info["duration"]

            if total_duration is None:
                raise AudioChunkerError(
                    message="Could not determine audio duration",
                    details={"file": str(audio_path)},
                )

            # Calculate number of chunks
            num_chunks = math.ceil(total_duration / chunk_duration)

            # Create output directory
            output_dir.mkdir(parents=True, exist_ok=True)

            # Split audio into chunks
            chunks: list[Path] = []
            for i in range(num_chunks):
                start_time = i * chunk_duration
                chunk_path = output_dir / f"chunk_{i:04d}.wav"

                # Use FFmpeg to extract chunk
                self._extract_chunk(
                    input_path=audio_path,
                    output_path=chunk_path,
                    start_time=start_time,
                    duration=chunk_duration,
                )

                chunks.append(chunk_path)

            return chunks

        except Exception as e:
            raise AudioChunkerError(
                message=f"Failed to split audio: {e}",
                details={"file": str(audio_path)},
            ) from e

    def _extract_chunk(
        self,
        input_path: Path,
        output_path: Path,
        start_time: int,
        duration: int,
    ) -> None:
        """
        Extract a chunk from audio file using FFmpeg fast seeking.

        OPTIMIZATION: Place -ss BEFORE -i for input seeking (10-20× faster).
        This allows FFmpeg to seek directly in the input file without
        decoding from the beginning.

        Args:
            input_path: Input audio file
            output_path: Output chunk file
            start_time: Start time in seconds
            duration: Duration in seconds
        """
        try:
            # FAST SEEKING: -ss BEFORE -i seeks in input file (no decode)
            # This is 10-20× faster than seeking after decode (-ss after -i)
            cmd = [
                "ffmpeg",
                "-y",  # Overwrite output
                "-ss",
                str(start_time),  # Seek in INPUT (fast)
                "-i",
                str(input_path),
                "-t",
                str(duration),  # Duration to extract
                "-acodec",
                "pcm_s16le",  # PCM 16-bit
                "-ar",
                "16000",  # 16kHz sample rate
                "-ac",
                "1",  # Mono
                "-avoid_negative_ts", "make_zero",  # Fix timestamp issues
                str(output_path),
            ]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=False,
            )

            if result.returncode != 0:
                error_msg = result.stderr or "Unknown FFmpeg error"
                raise AudioChunkerError(
                    message=f"FFmpeg chunk extraction failed: {error_msg}",
                    details={
                        "command": " ".join(cmd),
                        "returncode": result.returncode,
                    },
                )

        except FileNotFoundError as e:
            raise AudioChunkerError(
                message="FFmpeg not found. Please install FFmpeg.",
                details={"error": str(e)},
            ) from e

    def merge_transcriptions(
        self,
        chunks: list[str],
        format_type: str = "text",
    ) -> str:
        """
        Merge transcriptions from multiple chunks.

        Args:
            chunks: List of transcription texts
            format_type: Output format (text/json/srt/vtt)

        Returns:
            Merged transcription text

        Raises:
            AudioChunkerError: If merging fails
        """
        if format_type == "text":
            # Simple concatenation with space
            return " ".join(chunks)

        if format_type == "json":
            # Merge JSON objects
            merged_text = " ".join(
                json.loads(chunk).get("text", "") for chunk in chunks
            )
            return json.dumps({"text": merged_text})

        if format_type in ("srt", "vtt"):
            # Merge subtitle files with adjusted timestamps
            return self._merge_subtitles(chunks, format_type)

        raise AudioChunkerError(
            message=f"Unsupported format for merging: {format_type}",
        )

    def _merge_subtitles(self, chunks: list[str], format_type: str) -> str:
        """
        Merge SRT or VTT subtitle chunks with adjusted timestamps.

        Args:
            chunks: List of subtitle texts
            format_type: srt or vtt

        Returns:
            Merged subtitle text
        """

        merged_lines: list[str] = []
        time_offset = 0.0
        subtitle_index = 1

        for chunk in chunks:
            lines = chunk.strip().split("\n")

            # Skip VTT header
            if format_type == "vtt" and lines and lines[0].startswith("WEBVTT"):
                lines = lines[1:]

            i = 0
            while i < len(lines):
                line = lines[i].strip()

                # Check if this is a subtitle index
                if line.isdigit():
                    # Replace with sequential index
                    merged_lines.append(str(subtitle_index))
                    subtitle_index += 1
                    i += 1
                    continue

                # Check if this is a timestamp line
                time_pattern = r"(\d{2}:\d{2}:\d{2}[.,]\d{3})"
                if re.search(time_pattern, line):
                    # Adjust timestamps
                    adjusted_line = self._adjust_timestamp(line, time_offset)
                    merged_lines.append(adjusted_line)
                    i += 1

                    # Add subtitle text until blank line
                    while i < len(lines) and lines[i].strip():
                        merged_lines.append(lines[i])
                        i += 1

                    # Add blank line
                    merged_lines.append("")
                else:
                    i += 1

            # Extract last timestamp to calculate offset for next chunk
            # This is approximate - assumes 10 minute chunks
            time_offset += 600.0

        # Add VTT header if needed
        if format_type == "vtt":
            merged_lines.insert(0, "WEBVTT\n")

        return "\n".join(merged_lines)

    def _adjust_timestamp(self, timestamp_line: str, offset: float) -> str:
        """
        Adjust SRT/VTT timestamp by adding offset.

        Args:
            timestamp_line: Line with timestamps (e.g., "00:00:01,000 --> 00:00:05,000")
            offset: Offset in seconds

        Returns:
            Adjusted timestamp line
        """

        def add_offset(match: re.Match) -> str:
            """Add offset to a timestamp."""
            time_str = match.group(1)
            # Parse time
            parts = time_str.replace(",", ".").split(":")
            hours = int(parts[0])
            minutes = int(parts[1])
            seconds = float(parts[2])

            # Add offset
            total_seconds = hours * 3600 + minutes * 60 + seconds + offset
            new_hours = int(total_seconds // 3600)
            new_minutes = int((total_seconds % 3600) // 60)
            new_seconds = total_seconds % 60

            # Format back
            separator = "," if "," in time_str else "."
            return (
                f"{new_hours:02d}:{new_minutes:02d}:"
                f"{new_seconds:06.3f}".replace(".", separator)
            )

        pattern = r"(\d{2}:\d{2}:\d{2}[.,]\d{3})"
        return re.sub(pattern, add_offset, timestamp_line)

    def cleanup_chunks(self, chunks: list[Path]) -> None:
        """
        Delete chunk files.

        Args:
            chunks: List of chunk file paths
        """
        for chunk in chunks:
            try:
                if chunk.exists():
                    chunk.unlink()
            except Exception:
                # Silently ignore cleanup errors
                pass

    def __repr__(self) -> str:
        """Return string representation."""
        return f"AudioChunker(max_size={self.MAX_FILE_SIZE_MB}MB)"


class SmartAudioChunker:
    """Intelligent audio chunking with auto-detection and progress tracking."""

    def __init__(
        self,
        processor: "AudioProcessor",
        max_chunk_size_mb: float = 23.0,  # Leave buffer below 25MB limit
        save_intermediate: bool = False,
    ) -> None:
        """
        Initialize smart audio chunker.

        Args:
            processor: AudioProcessor instance
            max_chunk_size_mb: Maximum chunk size in MB (default: 23MB)
            save_intermediate: Whether to keep chunk files after processing
        """
        self.chunker = AudioChunker(processor)
        self.processor = processor
        self.max_chunk_size_mb = max_chunk_size_mb
        self.save_intermediate = save_intermediate

    def should_chunk(self, audio_file: Path) -> bool:
        """
        Determine if file needs chunking.

        Args:
            audio_file: Path to audio file

        Returns:
            True if file exceeds size threshold
        """
        if not audio_file.exists():
            return False

        size_mb = audio_file.stat().st_size / (1024 * 1024)
        return size_mb > self.max_chunk_size_mb

    def calculate_optimal_chunks(
        self,
        audio_file: Path,
        estimated_preprocessed_mb: float | None = None,
    ) -> tuple[int, int]:
        """
        Calculate optimal number of chunks and duration per chunk.

        Args:
            audio_file: Path to audio file
            estimated_preprocessed_mb: Estimated size after preprocessing (optional)
                If provided, will be used instead of original file size for chunk calculation

        Returns:
            Tuple of (num_chunks, chunk_duration_seconds)
        """
        size_mb = audio_file.stat().st_size / (1024 * 1024)

        # Use estimated preprocessed size if provided (more accurate)
        target_size_mb = estimated_preprocessed_mb if estimated_preprocessed_mb else size_mb

        # Get audio duration
        try:
            info = self.processor.get_audio_info(audio_file)
            duration = info.get("duration", 0)
        except Exception:
            # Estimate based on size (very rough: ~1MB per minute for typical audio)
            duration = size_mb * 60

        if duration == 0:
            # Fallback: calculate based on size
            num_chunks = int(target_size_mb / self.max_chunk_size_mb) + 1
            chunk_duration = 600  # 10 minutes default
        else:
            # Calculate chunks needed to stay under size limit
            # Use target_size_mb for calculation to account for preprocessing
            num_chunks = int(target_size_mb / self.max_chunk_size_mb) + 1
            chunk_duration = int(duration / num_chunks)

        console.print(f"[yellow]📊 Audio file: {size_mb:.1f}MB, {duration/60:.1f} minutes[/yellow]")
        if estimated_preprocessed_mb:
            console.print(f"[yellow]📏 Estimated preprocessed size: {estimated_preprocessed_mb:.1f}MB[/yellow]")
        console.print(
            f"[cyan]✂️  Splitting into {num_chunks} chunks "
            f"({chunk_duration//60}min {chunk_duration%60}sec each)[/cyan]",
        )

        return num_chunks, chunk_duration

    def chunk_and_process(
        self,
        audio_file: Path,
        output_dir: Path,
        processor_func: callable,
        **processor_kwargs,
    ) -> str:
        """
        Smart chunking: automatically chunk if needed and process all parts.

        Args:
            audio_file: Path to audio file
            output_dir: Directory for output and temporary chunks
            processor_func: Function to process each chunk (e.g., transcribe)
            **processor_kwargs: Additional arguments for processor function

        Returns:
            Combined result from all chunks
        """
        if not self.should_chunk(audio_file):
            # Single file processing
            console.print(f"[green]✓ File size OK ({audio_file.stat().st_size / (1024*1024):.1f}MB), processing directly[/green]")
            return processor_func(audio_file, **processor_kwargs)

        # Multi-chunk processing
        num_chunks, chunk_duration = self.calculate_optimal_chunks(audio_file)

        # Create chunks directory
        chunk_dir = output_dir / "chunks"
        chunk_dir.mkdir(parents=True, exist_ok=True)

        # Split audio
        console.print("\n[cyan]🔪 Splitting audio...[/cyan]")
        chunks = self.chunker.split_audio(
            audio_path=audio_file,
            output_dir=chunk_dir,
            chunk_duration=chunk_duration,
        )

        console.print(f"[green]✓ Created {len(chunks)} chunks[/green]")

        # Process each chunk with progress
        results = []
        console.print("\n[cyan]🎯 Processing chunks...[/cyan]")

        for i, chunk in enumerate(chunks, 1):
            console.print(f"\n[bold]Chunk {i}/{len(chunks)}[/bold] ({chunk.name})")

            try:
                result = processor_func(chunk, **processor_kwargs)
                results.append(result)
                console.print(f"[green]✓ Chunk {i} complete[/green]")

            except Exception as e:
                console.print(f"[red]✗ Chunk {i} failed: {e}[/red]")
                raise AudioChunkerError(
                    message=f"Failed to process chunk {i}/{len(chunks)}",
                    details={"chunk": str(chunk), "error": str(e)},
                ) from e

        # Combine results
        console.print("\n[cyan]🔗 Combining results...[/cyan]")

        # Determine format from processor_kwargs or results
        format_type = processor_kwargs.get("response_format", "text")
        combined = self.chunker.merge_transcriptions(results, format_type)

        # Cleanup chunks if not saving intermediate files
        if not self.save_intermediate:
            console.print("[dim]🧹 Cleaning up temporary chunks...[/dim]")
            self.chunker.cleanup_chunks(chunks)
            try:
                chunk_dir.rmdir()
            except OSError:
                pass  # Directory not empty or other error

        console.print("[green bold]✓ All chunks processed successfully![/green bold]")
        return combined

    def __repr__(self) -> str:
        """Return string representation."""
        return (
            f"SmartAudioChunker(max_chunk={self.max_chunk_size_mb}MB, "
            f"save_intermediate={self.save_intermediate})"
        )

