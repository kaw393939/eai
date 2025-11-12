````markdown
# EverydayAI CLI

**Personal AI toolkit for regular people**  
**Status:** 🟡 Alpha - Core tools working, more features planned

Created by Keith Williams - Director of Enterprise AI @ NJIT

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Code Coverage](https://img.shields.io/badge/coverage-63.79%25-yellow.svg)](https://github.com/kaw393939/eai)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Status: Alpha](https://img.shields.io/badge/status-alpha-orange.svg)](https://github.com/kaw393939/eai)
[![PyPI version](https://img.shields.io/pypi/v/everydayai-cli.svg)](https://pypi.org/project/everydayai-cli/)

## What is EverydayAI CLI?

A command-line toolkit that makes AI-powered multimedia processing accessible to everyone - not just developers. Built for content creators, educators, podcasters, marketers, and anyone who wants to leverage AI without writing code.

**v0.2.0 introduces a plugin architecture** making the CLI extensible and allowing third-party command additions.

## Features

### ✅ Currently Available

- 🖼️ **Image Generation**: Create images with DALL-E via gpt-image-1 model
- 👁️ **Vision Analysis**: Single and multi-image analysis with GPT-5
- 🗣️ **Text-to-Speech**: OpenAI TTS with 6 voices and ElevenLabs integration
- �️ **Audio Transcription**: Whisper-powered transcription with preprocessing
- 🌐 **Web Search**: AI-powered search with citations and sources
- � **YouTube Processing**: Video download, transcription, and translation
- � **Plugin Architecture**: Extensible command system with dynamic discovery
- ⚙️ **Flexible Configuration**: YAML config + environment variables
- 🎯 **Robust Error Handling**: Structured errors with helpful suggestions

### 🚧 Removed in v0.2.0

- ❌ **Smart Cropping**: Removed (didn't work reliably)
- ❌ **Background Removal**: Removed (poor quality results)

### 🚧 Coming Soon (See [ROADMAP.md](ROADMAP.md))

- 🤖 **OpenAI Agents SDK**: Multi-agent workflows and orchestration
- 📦 **Plugin Marketplace**: Community-contributed commands
- 🔄 **Workflow Chains**: Sequential tool orchestration
- 🎨 **Enhanced Image Tools**: Better quality smart crop and background removal
- � **Batch Processing**: Process multiple files efficiently

## Installation

```bash
# From PyPI - Live Now! 🎉
pip install everydayai-cli

# From source
git clone https://github.com/kaw393939/eai.git
cd eai
poetry install

# Verify installation
eai --version
```

## Quick Start

```bash
# Analyze an image with AI
eai vision photo.jpg --prompt "Describe this image in detail"

# Analyze multiple images at once
eai multi_vision image1.jpg image2.jpg image3.jpg --compare

# Generate an image
eai image "A serene mountain landscape" -o mountain.png

# AI-powered web search with citations
eai search "latest developments in AI 2024"

# Generate professional speech from text
eai speak "Welcome to our presentation" -o welcome.mp3

# Transcribe audio to text
eai transcribe podcast.mp3

# Download and transcribe YouTube video
eai transcribe_video "https://youtube.com/watch?v=..." -o transcript.txt

# Use ElevenLabs for premium voices
eai elevenlabs speak "Professional narration" -o narration.mp3 --voice adam
```

## Commands

### Core Commands

| Command | Description |
|---------|-------------|
| `eai image` | Generate images with DALL-E (gpt-image-1) |
| `eai vision` | Analyze single images with GPT-5 |
| `eai multi_vision` | Analyze multiple images simultaneously |
| `eai speak` | Text-to-speech with OpenAI voices |
| `eai transcribe` | Audio-to-text with Whisper |
| `eai search` | Web search with AI-powered answers |
| `eai youtube` | Manage YouTube authentication |
| `eai transcribe_video` | Download and transcribe videos |
| `eai translate_audio` | Translate audio to English |
| `eai elevenlabs` | Premium TTS with ElevenLabs |

### `eai image`

Generate images using DALL-E.

```bash
eai image PROMPT [OPTIONS]

Options:
  -o, --output PATH          Output file path
  -s, --size TEXT           Image size (256x256, 512x512, 1024x1024, 1024x1792, 1792x1024)
  -q, --quality TEXT        Quality: standard, hd
  --style TEXT              Style: vivid, natural
  --json                    Output JSON format
```

### `eai vision`

Analyze images using GPT-5 Vision.

```bash
eai vision IMAGE [OPTIONS]

Options:
  -p, --prompt TEXT         Question or instruction about the image
  -m, --model TEXT          Model to use (default: gpt-5)
  -d, --detail TEXT         Detail level: auto, low, high
  -t, --max-tokens INT      Maximum tokens in response
  --json                    Output as JSON
```

### `eai multi_vision`

Analyze multiple images simultaneously.

```bash
eai multi_vision IMAGE1 IMAGE2 [IMAGE3] [OPTIONS]

Options:
  -p, --prompt TEXT         Analysis prompt for all images
  -c, --compare             Enable detailed comparison mode
  -d, --detail TEXT         Detail level: auto, low, high
  --json                    Output as JSON
```

### `eai transcribe`

Transcribe audio files to text.

```bash
eai transcribe AUDIO_FILE [OPTIONS]

Options:
  -f, --format TEXT         Output format: text, json, srt, vtt
  -l, --language TEXT       Source language code (e.g., 'en', 'es')
  -o, --output FILE         Save to file
  --no-preprocess          Skip audio preprocessing
  --parallel               Use parallel processing (3-5x faster)
```

### `eai transcribe_video`

Download and transcribe videos.

```bash
eai transcribe_video URL [OPTIONS]

Options:
  -f, --format TEXT         Output format: text, json, srt, vtt
  -l, --language TEXT       Source language hint
  -o, --output FILE         Save transcript to file
  --keep-audio             Keep downloaded audio file
  --parallel               Use parallel processing
```

### `eai search`

AI-powered web search with citations.

```bash
eai search QUERY [OPTIONS]

Options:
  -o, --output FILE         Save results to file
  --json                    Output as JSON
  -d, --domains TEXT        Limit to specific domains
  --city TEXT              User location (city)
  --country TEXT           User location (country)
```

## Plugin Architecture

**New in v0.2.0**: Commands are now implemented as plugins, making the CLI extensible.

### Using Third-Party Plugins

Install plugins via pip with the `eai.plugins` entry point:

```bash
pip install eai-plugin-example
eai example-command  # Plugin commands auto-discovered
```

### Creating Plugins

Create your own commands by implementing the `CommandPlugin` protocol:

```python
from ei_cli.plugins import CommandPlugin, BaseCommandPlugin
import click

class MyPlugin(BaseCommandPlugin):
    name = "my-command"
    category = "custom"
    help_text = "My custom command"
    
    def get_command(self) -> click.Command:
        @click.command(name=self.name, help=self.help_text)
        def my_command():
            click.echo("Hello from my plugin!")
        return my_command

plugin = MyPlugin()
```

Register via entry points in your `pyproject.toml`:

```toml
[project.entry-points."eai.plugins"]
my-plugin = "my_package.plugin:plugin"
```

See plugin documentation for details on creating custom commands.

### `eai speak`

Generate professional speech from text using AI.

```bash
eai speak TEXT [OPTIONS]
eai speak --input FILE [OPTIONS]

Options:
  --input, -i PATH         Read text from file
  --output, -o PATH        Output audio file (required)
  --voice, -v VOICE        Voice: alloy, echo, fable, onyx, nova, shimmer,
                           ash, ballad, coral, sage, verse (tts-1),
                           marin, cedar (tts-1-hd) [default: alloy]
  --model, -m MODEL        Model: tts-1, tts-1-hd [default: tts-1]
  --speed, -s FLOAT        Playback speed 0.25-4.0 [default: 1.0]
  --format, -f FORMAT      Audio format: mp3, opus, aac, flac, wav, pcm
                           [default: mp3]
  --instructions TEXT      Pronunciation/style guidance (max 4096 chars)
  --stream                 Enable streaming mode with progress
  --play                   Play audio after generation

Examples:
  # Basic usage with default voice
  eai speak "Hello world" -o hello.mp3

  # Premium voice with high quality
  eai speak "Professional recording" -o pro.mp3 -v marin -m tts-1-hd

  # Long-form with streaming
  eai speak --input script.txt -o audiobook.mp3 --stream

  # Custom pronunciation guidance
  eai speak "Dr. Nguyen at CERN" -o speech.mp3 \
    --instructions "Pronounce 'Nguyen' as 'win', 'CERN' as 'sern'"

  # Small file size for streaming
  eai speak "Compact audio" -o compact.opus -f opus

  # Generate and play immediately
  eai speak "Listen now" -o demo.mp3 --play
```

**Voice Options:**

- **Standard** (all models): alloy, echo, fable, onyx, nova, shimmer
- **tts-1 only**: ash, ballad, coral, sage, verse
- **tts-1-hd only**: marin (most natural), cedar (rich depth)

**Format Guide:**

- **mp3**: Default, widely compatible (~30KB)
- **opus**: Streaming optimized (~7KB)
- **aac**: Apple devices (~25KB)
- **flac**: Lossless quality (~38KB)
- **wav**: Uncompressed editing (~93KB)
- **pcm**: Raw audio data (~93KB)

See [docs/TTS_GUIDE.md](docs/TTS_GUIDE.md) for comprehensive TTS documentation.

## Configuration

### Configuration File

Create `.ei/config.yaml` in your project or `~/.ei/config.yaml` for global
settings:

```yaml
ai:
  api_key: ${EI_API_KEY} # Or set directly (not recommended)
  model: gpt-4-vision-preview
  max_tokens: 2000

output:
  format: json # or "human"

logging:
  level: INFO
  format: json # or "text"
```

### Environment Variables

```bash
export EI_API_KEY="your-openai-api-key"
export EI_LOG_LEVEL="INFO"
export EI_OUTPUT_FORMAT="json"
```

### Configuration Hierarchy

Configuration sources (later overrides earlier):

1. Built-in defaults
2. Global config (`~/.ei/config.yaml`)
3. Project config (`./.ei/config.yaml`)
4. Environment variables (`EI_*`)
5. Command-line arguments (`--option`)

## Templates

Available templates:

- **email-writing**: Professional email composition
- **lesson-plans**: Educational lesson planning
- **simple-website**: Static website creation
- **project-planning**: Project structure and planning
- **data-analysis**: Simple data analysis tasks

Create custom templates in `~/.vibe/templates/`.

## Development

### Setup

```bash
# Clone repository
git clone https://github.com/kaw393939/eai.git
cd eai

# Install dependencies
poetry install

# Run in development mode
poetry run eai --help
```

### Testing

```bash
# Run all tests
poetry run pytest

# Run with coverage
poetry run pytest --cov=src/ei_cli --cov-report=html

# Run specific test category
poetry run pytest -m unit          # Unit tests only
poetry run pytest -m integration   # Integration tests only
```

### Quality Checks

```bash
# Linting
poetry run ruff check src/ tests/

# Type checking
poetry run mypy src/

# Security scanning
poetry run bandit -r src/

# Run all quality checks
poetry run pre-commit run --all-files
```

## Architecture

The CLI follows a clean layered architecture:

- **CLI Layer** (`cli/`): Command parsing and user interaction
- **Tools Layer** (`tools/`): Core AI and image processing tools
- **Core Layer** (`core/`): Configuration, errors, shared utilities

Key principles:

- **EAFP over LBYL**: "Easier to Ask Forgiveness than Permission"
- **Structured Errors**: All errors provide machine-readable context
- **Configuration Flexibility**: Multiple config sources, sensible defaults
- **Type Safety**: Full mypy strict mode compliance

See [TECHNICAL_DEBT_AUDIT.md](TECHNICAL_DEBT_AUDIT.md) for current architecture
status and [ROADMAP.md](ROADMAP.md) for planned improvements.

## Testing Strategy

Current test coverage: **63.79%** (Target: 90%)

**Test Results (v0.2.0):**
- ✅ 559 tests passing
- ⏭️ 41 tests skipped (image streaming not yet implemented)
- ✅ Configuration system: 100% coverage
- ✅ Error handling: High coverage
- ✅ Plugin system: Validated via integration tests
- ✅ All commands: Manually tested and working

### Running Tests

```bash
# All tests
poetry run pytest

# With coverage report
poetry run pytest --cov=src/ei_cli --cov-report=html

# Specific categories
poetry run pytest tests/python/unit/        # Unit tests
poetry run pytest tests/python/integration/ # Integration tests
```

We're actively working toward 90% coverage. See test documentation for details.

## Contributing

We welcome contributions! Here's how to get started:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Write tests first (TDD approach)
4. Implement your feature
5. Ensure all quality gates pass (`poetry run pre-commit run --all-files`)
6. Commit changes (`git commit -m 'Add amazing feature'`)
7. Push to branch (`git push origin feature/amazing-feature`)
8. Open a Pull Request

Please read [TECHNICAL_DEBT_AUDIT.md](TECHNICAL_DEBT_AUDIT.md) to understand
current priorities.

## License

MIT License - See [LICENSE](LICENSE) for details.

## Author

**Keith Williams**

- Director of Enterprise AI @ NJIT
- 23 years teaching computer science
- Building EverydayAI Newark
- [keithwilliams.io](https://keithwilliams.io)
- [@kaw393939](https://github.com/kaw393939)

## Acknowledgments

- Part of **EverydayAI Newark** - training everyone for distributed productivity
  gains
- Built to make AI accessible to non-developers
- Inspired by Swiss design principles - clarity, function, minimal complexity

## Links

- **Website**: [keithwilliams.io](https://keithwilliams.io)
- **GitHub**: [github.com/kaw393939/eai](https://github.com/kaw393939/eai)
- **PyPI**: [pypi.org/project/everydayai-cli](https://pypi.org/project/everydayai-cli)
- **Documentation**:
  - [TECHNICAL_DEBT_AUDIT.md](TECHNICAL_DEBT_AUDIT.md) - Current status
  - [ROADMAP.md](ROADMAP.md) - Planned features
- **Issues**:
  [github.com/kaw393939/eai/issues](https://github.com/kaw393939/eai/issues)

---

**Status:** 🟡 Alpha - Core features working, plugin system stable  
**Version:** 0.2.0  
**Coverage:** 63.79% → Target: 90%
````
