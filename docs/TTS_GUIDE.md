# Text-to-Speech (TTS) Guide

Complete guide for using the OpenAI Text-to-Speech features in the EI CLI.

## Table of Contents

- [Quick Start](#quick-start)
- [Voice Options](#voice-options)
- [Audio Formats](#audio-formats)
- [Streaming Mode](#streaming-mode)
- [Instructions Parameter](#instructions-parameter)
- [Playback Options](#playback-options)
- [Speed Control](#speed-control)
- [Advanced Usage](#advanced-usage)
- [Troubleshooting](#troubleshooting)

## Quick Start

Generate speech from text:

```bash
ei speak "Hello, world!" -o hello.mp3
```

Read text from a file:

```bash
ei speak --input script.txt --output speech.mp3
```

## Voice Options

The `ei speak` command supports 19 different voices across two quality tiers.

### Standard Voices (All Models)

Available on both `tts-1` and `tts-1-hd`:

| Voice       | Characteristics        | Best For                   |
| ----------- | ---------------------- | -------------------------- |
| **alloy**   | Neutral, balanced tone | General purpose, narration |
| **echo**    | Clear, professional    | Presentations, podcasts    |
| **fable**   | Warm, expressive       | Storytelling, audiobooks   |
| **onyx**    | Deep, authoritative    | News, professional content |
| **nova**    | Energetic, friendly    | Marketing, tutorials       |
| **shimmer** | Soft, smooth           | Meditation, relaxation     |

### tts-1 Exclusive Voices

Additional voices only available with the `tts-1` model:

| Voice      | Characteristics   | Best For                    |
| ---------- | ----------------- | --------------------------- |
| **ash**    | Crisp, clear      | Technical content           |
| **ballad** | Melodic, soothing | Poetry, creative writing    |
| **coral**  | Vibrant, lively   | Entertainment, kids content |
| **sage**   | Wise, measured    | Educational content         |
| **verse**  | Rhythmic, flowing | Prose, literature           |

### tts-1-hd Premium Voices

High-definition voices available only with `tts-1-hd` model:

| Voice     | Characteristics          | Best For                | Recommended Use           |
| --------- | ------------------------ | ----------------------- | ------------------------- |
| **marin** | Most natural, human-like | Professional recordings | ⭐ **Highly Recommended** |
| **cedar** | Rich, warm depth         | Premium audiobooks      | ⭐ **Highly Recommended** |

### Voice Examples

```bash
# Use standard voice (works with any model)
ei speak "Hello" -v alloy -o hello.mp3

# Use tts-1 exclusive voice
ei speak "Welcome" -v ballad -m tts-1 -o welcome.mp3

# Use premium HD voice (best quality)
ei speak "Premium audio" -v marin -m tts-1-hd -o premium.mp3
```

### Voice/Model Compatibility

**Important**: Some voices are model-specific:

- ✅ **Standard voices** (alloy, echo, fable, onyx, nova, shimmer): Work with
  both models
- ✅ **tts-1 voices** (ash, ballad, coral, sage, verse): Only with `tts-1` model
- ✅ **tts-1-hd voices** (marin, cedar): Only with `tts-1-hd` model

Attempting to use an HD voice with `tts-1` will result in an error.

## Audio Formats

Six audio formats are supported, each optimized for different use cases.

### Format Comparison

| Format   | Type         | Typical Size | Quality   | Best For                           |
| -------- | ------------ | ------------ | --------- | ---------------------------------- |
| **mp3**  | Compressed   | ~30 KB       | Good      | General use, default               |
| **opus** | Compressed   | ~7 KB        | Good      | Streaming, low latency             |
| **aac**  | Compressed   | ~25 KB       | Good      | Apple devices, broad compatibility |
| **flac** | Lossless     | ~38 KB       | Excellent | Archival, production               |
| **wav**  | Uncompressed | ~93 KB       | Excellent | Editing, processing                |
| **pcm**  | Raw          | ~93 KB       | Excellent | Audio engineering                  |

_Size estimates based on ~5 seconds of speech_

### Format Usage Examples

```bash
# Default MP3 (widely compatible)
ei speak "Hello" -o hello.mp3

# Opus for streaming (smallest file)
ei speak "Stream" -o stream.opus -f opus

# FLAC for archival quality
ei speak "Archive" -o archive.flac -f flac

# WAV for editing
ei speak "Edit me" -o source.wav -f wav
```

### Format Selection Guide

**Use MP3** when:

- You need wide compatibility
- File size matters but quality is still important
- Default choice for most applications

**Use Opus** when:

- Streaming audio in real-time
- Bandwidth is limited
- Need smallest possible file size

**Use AAC** when:

- Targeting Apple devices/ecosystem
- Need good quality with reasonable size
- Building iOS/macOS applications

**Use FLAC** when:

- Archiving important audio
- Need lossless compression
- Audio will be transcoded later

**Use WAV** when:

- Editing audio in DAW software
- Need highest quality uncompressed
- Processing audio with effects

**Use PCM** when:

- Working with raw audio data
- Building audio processing pipelines
- Need lowest-level audio format

## Streaming Mode

Streaming mode generates audio incrementally with progress feedback.

### Benefits

- **Progress Visibility**: See real-time progress as audio is generated
- **Early Detection**: Catch errors quickly without waiting for full generation
- **Large Files**: Better experience for long-form content

### Streaming Examples

```bash
# Basic streaming with progress
ei speak "Long text..." -o output.mp3 --stream

# Stream from file (good for long scripts)
ei speak --input long_script.txt -o audiobook.mp3 --stream

# Streaming with high-quality format
ei speak --input chapter.txt -o chapter.flac -f flac --stream
```

### Progress Output

When streaming, you'll see:

```
Generating speech...
  Voice: alloy
  Model: tts-1
  Format: mp3
  Speed: 1.0x
  Mode: Streaming
Progress: 92.6 KB received...

✓ Speech generated!
  Output: /path/to/output.mp3
```

### When to Use Streaming

**Use streaming for:**

- Long-form content (>500 words)
- Real-time feedback requirements
- Debugging TTS generation
- Large script processing

**Use standard mode for:**

- Short phrases (<100 words)
- Batch processing many files
- When progress feedback isn't needed

## Instructions Parameter

The `--instructions` option guides pronunciation, pacing, and speaking style.

### What Instructions Control

- **Pronunciation**: Guide how specific words should be pronounced
- **Pacing**: Control speaking speed and rhythm
- **Emphasis**: Highlight important words or phrases
- **Emotion**: Influence tone and emotional delivery
- **Accent**: Request specific accent or speaking style

### Instructions Examples

#### Pronunciation Guidance

```bash
# Guide pronunciation of names
ei speak "Dr. Nguyen works at CERN" -o speech.mp3 \
  --instructions "Pronounce 'Nguyen' as 'win', pronounce CERN as 'sern'"

# Technical terms
ei speak "Configure the nginx server" -o tech.mp3 \
  --instructions "Pronounce 'nginx' as 'engine-x'"
```

#### Pacing and Emphasis

```bash
# Slow, emphasized delivery
ei speak "Important announcement!" -o urgent.mp3 \
  --instructions "Speak slowly with urgency"

# Emphasize specific words
ei speak "This is critically important" -o emphasis.mp3 \
  --instructions "Emphasize the words 'critically' and 'important'"
```

#### Emotional Tone

```bash
# Friendly, upbeat tone
ei speak "Welcome to our podcast!" -o intro.mp3 \
  --instructions "Speak with enthusiasm and warmth"

# Serious, professional tone
ei speak "Financial report summary" -o report.mp3 \
  --instructions "Speak formally and clearly"
```

#### Accent and Style

```bash
# Request specific accent
ei speak "Shakespeare quote" -o quote.mp3 \
  --instructions "Use a British accent"

# Narrative style
ei speak "Once upon a time..." -o story.mp3 \
  --instructions "Use a storytelling narrative style, with dramatic pauses"
```

### Instructions Best Practices

**Do:**

- ✅ Be specific and clear
- ✅ Focus on one or two aspects
- ✅ Test different phrasings
- ✅ Use for technical terms and names
- ✅ Keep instructions under 4096 characters

**Don't:**

- ❌ Use overly complex instructions
- ❌ Expect radical voice changes
- ❌ Rely solely on instructions for quality
- ❌ Use instructions for every generation

### Instructions Limitations

- Instructions are **guidance**, not commands
- Results may vary between voices
- Not all instructions will be followed perfectly
- Consider combining with appropriate voice selection

## Playback Options

Play generated audio immediately after creation.

### Setup Requirements

Install optional dependencies:

```bash
pip install pydub simpleaudio
```

### Playback Examples

```bash
# Generate and play immediately
ei speak "Hello world" -o hello.mp3 --play

# Stream with playback
ei speak "Live demo" -o demo.mp3 --stream --play

# Different formats work too
ei speak "High quality" -o hq.flac -f flac --play
```

### Playback Behavior

**If dependencies are installed:**

```
Generating speech...
✓ Speech generated!
  Output: /path/to/audio.mp3

Playing audio...
✓ Playback complete!
```

**If dependencies are missing:**

```
Generating speech...
✓ Speech generated!
  Output: /path/to/audio.mp3

⚠ Playback unavailable: Missing dependencies
  Install with: pip install pydub simpleaudio
```

**If playback fails:**

```
Generating speech...
✓ Speech generated!
  Output: /path/to/audio.mp3

⚠ Playback failed: [error message]
```

### Cross-Platform Support

- ✅ **macOS**: Full support via CoreAudio
- ✅ **Linux**: Requires ALSA or PulseAudio
- ✅ **Windows**: Full support via Windows Audio

### Troubleshooting Playback

**macOS**: No additional setup needed

**Linux**: Install audio libraries

```bash
sudo apt-get install python3-dev libasound2-dev
pip install pydub simpleaudio
```

**Windows**: No additional setup needed

**Audio Issues**:

- Check system volume
- Verify audio output device
- Test with a different format
- Try without streaming first

## Speed Control

Control playback speed from 0.25x (very slow) to 4.0x (very fast).

### Speed Range

- **Minimum**: 0.25x (quarter speed)
- **Default**: 1.0x (normal speed)
- **Maximum**: 4.0x (four times speed)

### Speed Examples

```bash
# Very slow (for learning/accessibility)
ei speak "Slow speech" -o slow.mp3 -s 0.5

# Normal speed (default)
ei speak "Normal speech" -o normal.mp3

# Faster (time-efficient)
ei speak "Quick speech" -o fast.mp3 -s 1.5

# Very fast (rapid consumption)
ei speak "Speed reading" -o veryfast.mp3 -s 2.0
```

### Speed Recommendations

| Speed    | Use Case                           | Quality       |
| -------- | ---------------------------------- | ------------- |
| 0.25x    | Language learning, clarity         | Excellent     |
| 0.5x     | Educational content, accessibility | Excellent     |
| 0.75x    | Careful listening                  | Excellent     |
| **1.0x** | **Default, natural speech**        | **Excellent** |
| 1.25x    | Efficient listening                | Excellent     |
| 1.5x     | Podcast consumption                | Very Good     |
| 2.0x     | Speed listening                    | Good          |
| 3.0x     | Rapid review                       | Fair          |
| 4.0x     | Ultra-fast (harder to understand)  | Limited       |

### Speed with Other Options

```bash
# Slow, high-quality premium voice
ei speak "Careful explanation" -o explain.mp3 \
  -v marin -m tts-1-hd -s 0.75

# Fast streaming for time efficiency
ei speak --input long_text.txt -o fast.mp3 \
  -s 1.5 --stream
```

## Advanced Usage

### Combining All Features

```bash
# Full-featured example
ei speak --input script.txt \
  -o premium_audiobook.flac \
  -v marin \
  -m tts-1-hd \
  -s 0.9 \
  -f flac \
  --instructions "Speak with a warm, narrative style" \
  --stream \
  --play
```

### Batch Processing

Process multiple files:

```bash
# Process multiple chapters
for chapter in chapter_*.txt; do
  ei speak --input "$chapter" \
    -o "audio_${chapter%.txt}.mp3" \
    -v fable \
    --stream
done
```

### Quality Tiers

Choose quality based on use case:

```bash
# Maximum quality (archival)
ei speak "Archive" -o archive.flac \
  -v marin -m tts-1-hd -f flac

# Balanced quality (most use cases)
ei speak "Standard" -o standard.mp3 \
  -v alloy -m tts-1

# Minimum size (streaming)
ei speak "Stream" -o stream.opus \
  -v alloy -m tts-1 -f opus
```

### Cost Optimization

Tips for managing API costs:

1. **Use tts-1 for drafts**: Test with standard model first
2. **Save HD for finals**: Use tts-1-hd only for final production
3. **Choose efficient formats**: Opus/MP3 for streaming
4. **Batch similar content**: Generate related content together
5. **Cache results**: Keep generated audio for reuse

## Troubleshooting

### Common Issues

#### "Voice X is only available with model Y"

**Problem**: Using incompatible voice/model combination

**Solution**:

- Use marin/cedar only with `tts-1-hd`
- Use ash/ballad/coral/sage/verse only with `tts-1`
- Standard voices work with both models

```bash
# ❌ Wrong
ei speak "Test" -o test.mp3 -v marin -m tts-1

# ✅ Correct
ei speak "Test" -o test.mp3 -v marin -m tts-1-hd
```

#### "Playback unavailable: Missing dependencies"

**Problem**: Playback libraries not installed

**Solution**:

```bash
pip install pydub simpleaudio
```

#### "Invalid format"

**Problem**: Unsupported audio format specified

**Solution**: Use one of: mp3, opus, aac, flac, wav, pcm

```bash
# ❌ Wrong
ei speak "Test" -o test.mp4 -f mp4

# ✅ Correct
ei speak "Test" -o test.mp3 -f mp3
```

#### "Speed must be between 0.25 and 4.0"

**Problem**: Speed value out of range

**Solution**: Use speed between 0.25 and 4.0

```bash
# ❌ Wrong
ei speak "Test" -o test.mp3 -s 5.0

# ✅ Correct
ei speak "Test" -o test.mp3 -s 2.0
```

#### Streaming not showing progress

**Problem**: Progress output being buffered

**Solution**: Ensure you're using `--stream` flag and output isn't redirected

#### Audio quality issues

**Solutions**:

1. Try `tts-1-hd` model for better quality
2. Use lossless format (flac/wav)
3. Test different voices
4. Adjust speed closer to 1.0x
5. Review instructions if using

### Getting Help

If you encounter issues:

1. Check this guide's troubleshooting section
2. Verify your OpenAI API key is configured
3. Test with minimal options first
4. Review error messages carefully
5. Check internet connectivity
6. Verify OpenAI API status

### Performance Tips

**For faster generation:**

- Use `tts-1` (standard) instead of `tts-1-hd`
- Choose compressed formats (opus, mp3)
- Avoid streaming for short texts
- Use streaming for long texts

**For better quality:**

- Use `tts-1-hd` model
- Choose premium voices (marin, cedar)
- Use lossless formats (flac, wav)
- Keep speed close to 1.0x
- Use instructions for pronunciation

**For smaller files:**

- Use opus format (~7 KB)
- Use `tts-1` model
- Consider compression settings
- Avoid lossless formats

---

## Quick Reference

### Most Common Commands

```bash
# Basic usage
ei speak "Hello" -o hello.mp3

# High quality
ei speak "Premium" -o premium.mp3 -v marin -m tts-1-hd

# Streaming
ei speak --input long.txt -o output.mp3 --stream

# With instructions
ei speak "Dr. Smith" -o speech.mp3 --instructions "Pronounce 'Smith' clearly"

# Small file size
ei speak "Compact" -o compact.opus -f opus

# Generate and play
ei speak "Listen now" -o play.mp3 --play
```

### All Options

```
Options:
  --input, -i FILE          Read text from a file
  --output, -o FILE         Output audio file path (required)
  --voice, -v VOICE         Voice to use (default: alloy)
  --model, -m MODEL         TTS model: tts-1 or tts-1-hd (default: tts-1)
  --speed, -s FLOAT         Playback speed 0.25-4.0 (default: 1.0)
  --format, -f FORMAT       Audio format (default: mp3)
  --instructions TEXT       Pronunciation/style guidance
  --stream                  Enable streaming mode with progress
  --play                    Play audio after generation
```

---

**Need more help?** Check the main README.md or run `ei speak --help`
