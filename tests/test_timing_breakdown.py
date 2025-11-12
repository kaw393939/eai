#!/usr/bin/env python3
"""
Test script to measure timing breakdown of YouTube video transcription.
This will help identify the actual bottleneck in the pipeline.
"""

import time
from pathlib import Path
import tempfile
import sys

# Add project to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from ei_cli.services.factory import ServiceFactory
from ei_cli.services.video_downloader import VideoDownloader

# Test video - shorter video for testing (change to longer video for real benchmarks)
TEST_URL = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"  # Rick Astley - Never Gonna Give You Up (~3.5 min)

def format_duration(seconds: float) -> str:
    """Format seconds as MM:SS"""
    mins = int(seconds // 60)
    secs = int(seconds % 60)
    return f"{mins:02d}:{secs:02d}"

def main():
    print("=" * 70)
    print("YOUTUBE TRANSCRIPTION TIMING BREAKDOWN")
    print("=" * 70)
    print(f"\nTest URL: {TEST_URL}\n")
    
    timing_results = {}
    audio_file = None
    
    try:
        # ===================================================================
        # PHASE 1: VIDEO INFO
        # ===================================================================
        print("\n[1/5] FETCHING VIDEO INFO...")
        start = time.time()
        
        downloader = VideoDownloader()
        info = downloader.get_video_info(TEST_URL)
        
        timing_results['video_info'] = time.time() - start
        
        print(f"  ✓ Title: {info['title']}")
        if info.get('duration'):
            duration_min = info['duration'] / 60
            print(f"  ✓ Duration: {duration_min:.1f} min")
        print(f"  ⏱ Time: {format_duration(timing_results['video_info'])}")
        
        # ===================================================================
        # PHASE 2: AUDIO DOWNLOAD
        # ===================================================================
        print("\n[2/5] DOWNLOADING AUDIO...")
        start = time.time()
        
        temp_file = tempfile.NamedTemporaryFile(suffix=".m4a", delete=False)
        audio_file = Path(temp_file.name)
        temp_file.close()
        
        audio_file = downloader.download_audio(
            url=TEST_URL,
            output_path=audio_file,
            format_preference="m4a",
            show_progress=True,
        )
        
        timing_results['download'] = time.time() - start
        
        file_size_mb = audio_file.stat().st_size / (1024 * 1024)
        print(f"  ✓ Downloaded: {file_size_mb:.1f} MB")
        print(f"  ⏱ Time: {format_duration(timing_results['download'])}")
        
        # Get AI service
        service_factory = ServiceFactory()
        ai_service = service_factory.get_ai_service()
        
        # ===================================================================
        # PHASE 3: TRANSCRIPTION (includes preprocessing, chunking, and API)
        # ===================================================================
        print("\n[3/4] TRANSCRIBING (parallel mode, max_concurrent=4)...")
        start = time.time()
        
        def progress_callback(completed: int, total: int):
            """Show progress"""
            print(f"  → Progress: {completed}/{total} chunks", end='\r')
        
        result = ai_service.transcribe_audio_parallel(
            audio_path=audio_file,
            language=None,
            prompt=None,
            response_format="text",
            temperature=0.0,
            max_concurrent=4,  # OpenAI throttles above this
            progress_callback=progress_callback,
        )
        
        timing_results['transcription_total'] = time.time() - start
        
        print(f"\n  ✓ Transcribed {len(result.text)} characters")
        print(f"  ⏱ Time: {format_duration(timing_results['transcription_total'])}")
        
        # ===================================================================
        # PHASE 4: RESULTS SUMMARY
        # ===================================================================
        print("\n[4/4] COMPLETE!")
        
        timing_results['total'] = sum(timing_results.values())
        
        print("\n" + "=" * 70)
        print("TIMING BREAKDOWN")
        print("=" * 70)
        
        # Calculate percentages
        total = timing_results['total']
        
        phases = [
            ("Video Info", timing_results['video_info']),
            ("Audio Download", timing_results['download']),
            ("API Transcription", timing_results['transcription_total']),
        ]
        
        for phase_name, phase_time in phases:
            percentage = (phase_time / total) * 100
            bar_length = int(percentage / 2)  # 50 chars = 100%
            bar = "█" * bar_length + "░" * (50 - bar_length)
            print(f"\n{phase_name:20} {format_duration(phase_time):>8}  {percentage:5.1f}%")
            print(f"  {bar}")
        
        print(f"\n{'TOTAL':20} {format_duration(total):>8}  100.0%")
        print("=" * 70)
        
        # Calculate throughput
        video_duration_min = info.get('duration', 0) / 60
        throughput = video_duration_min / (total / 60) if total > 0 else 0
        
        print(f"\nVideo Duration: {video_duration_min:.1f} minutes")
        print(f"Processing Time: {total / 60:.1f} minutes")
        print(f"Throughput: {throughput:.2f}x real-time")
        
        print("\n" + "=" * 70)
        print("BOTTLENECK ANALYSIS")
        print("=" * 70)
        
        # Find bottleneck
        max_phase = max(phases, key=lambda x: x[1])
        print(f"\n🎯 PRIMARY BOTTLENECK: {max_phase[0]}")
        print(f"   Takes {(max_phase[1] / total) * 100:.1f}% of total time")
        
        if max_phase[0] == "API Transcription":
            print("\n💡 OPTIMIZATION RECOMMENDATIONS:")
            print("   1. Local Whisper (faster-whisper) - could be 2-3x faster")
            print("   2. GPU acceleration for local Whisper")
            print("   3. Consider larger local models for better speed/accuracy balance")
            print("   4. API already throttled at 4 concurrent - can't increase")
        elif max_phase[0] == "Audio Download":
            print("\n💡 OPTIMIZATION RECOMMENDATIONS:")
            print("   1. Stream download + transcode simultaneously")
            print("   2. Better format selection (prefer opus/m4a over mp3)")
            print("   3. Lower quality audio (16kHz mono sufficient for Whisper)")
        elif max_phase[0] in ["Preprocessing", "Chunking"]:
            print("\n💡 OPTIMIZATION RECOMMENDATIONS:")
            print("   1. GPU-accelerated FFmpeg")
            print("   2. Parallel preprocessing + chunking")
            print("   3. Skip unnecessary audio filters")
        
    finally:
        # Cleanup
        if audio_file and audio_file.exists():
            audio_file.unlink()

if __name__ == "__main__":
    main()
