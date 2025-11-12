````markdown
# EverydayAI CLI (ei-cli)

**Personal AI toolkit for regular people**  
**Status:** 🟡 Alpha - Core tools working, more features planned

Created by Keith Williams - Director of Enterprise AI @ NJIT

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Code Coverage](https://img.shields.io/badge/coverage-25.35%25-orange.svg)](https://github.com/kaw393939/ei-cli)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Status: Alpha](https://img.shields.io/badge/status-alpha-orange.svg)](https://github.com/kaw393939/ei-cli)

## What is EverydayAI CLI?

A command-line toolkit that makes AI-powered image processing and content
analysis accessible to everyone - not just developers. Built for teachers,
accountants, managers, small business owners, and anyone who wants to leverage
AI without writing code.

## Features

### ✅ Currently Available

- 🖼️ **Image Analysis**: AI-powered image understanding with GPT-4 Vision
- ✂️ **Smart Cropping**: Intelligent image cropping with aspect ratio control
- 🎨 **Background Removal**: Remove backgrounds from images automatically
- 🔍 **AI Search**: Semantic search powered by AI
- 📸 **Image Generation**: Create images with AI assistance
- 🗣️ **Text-to-Speech**: Professional voice synthesis with 19 voices, 6 formats,
  streaming support
- ⚙️ **Flexible Configuration**: YAML config + environment variables
- 🎯 **Robust Error Handling**: Structured errors with helpful suggestions

### 🚧 Coming Soon (See [ROADMAP.md](ROADMAP.md))

- 📦 Template System: Pre-built templates for common tasks
- 🔄 Iteration Tracking: AI-assisted iterative workflows
- � Deployment Tools: Easy deployment to various platforms
- 🔌 Plugin Architecture: Extensible command system

## Installation

```bash
# From PyPI (coming soon)
pip install ei-cli

# From source
git clone https://github.com/kaw393939/ei-cli.git
cd ei-cli
poetry install

# Verify installation
ei --version
```

## Quick Start

```bash
# Analyze an image with AI
ei vision analyze photo.jpg --prompt "Describe this image in detail"

# Remove background from an image
ei remove-bg input.jpg --output output.png

# Smart crop with aspect ratio
ei crop image.jpg --aspect-ratio 16:9 --output cropped.jpg

# Generate an image
ei image generate "A serene mountain landscape" --output mountain.png

# AI-powered search (coming soon)
ei search "machine learning tutorials"

# Generate professional speech from text
ei speak "Welcome to our presentation" -o welcome.mp3

# Use premium voice with high quality
ei speak "Important announcement" -o announce.mp3 -v marin -m tts-1-hd

# Stream long-form content with progress
ei speak --input long_script.txt -o audiobook.mp3 --stream
```

## Commands

### `ei vision`

Analyze images using AI vision models.

```bash
ei vision analyze IMAGE_PATH [OPTIONS]

Options:
  --prompt TEXT       What to analyze in the image
  --model TEXT        AI model to use (default: gpt-4-vision)
  --max-tokens INT    Maximum tokens for response
  --detail TEXT       Detail level: low, high, auto (default: auto)
```

### `ei crop`

Smart image cropping with AI assistance.

```bash
ei crop IMAGE_PATH [OPTIONS]

Options:
  --output PATH           Output file path
  --aspect-ratio TEXT     Target aspect ratio (e.g., 16:9, 4:3)
  --width INT            Target width in pixels
  --height INT           Target height in pixels
  --focus TEXT           Focus area: center, face, auto
```

### `ei remove-bg`

Remove background from images.

```bash
ei remove-bg IMAGE_PATH [OPTIONS]

Options:
  --output PATH      Output file path
  --format TEXT      Output format: png, jpg (default: png)
```

### `ei image`

Generate or manipulate images with AI.

```bash
ei image generate PROMPT [OPTIONS]

Options:
  --output PATH      Output file path
  --size TEXT        Image size: 256x256, 512x512, 1024x1024
  --model TEXT       Model to use (default: dall-e-3)
```

### `ei search`

AI-powered semantic search (experimental).

```bash
ei search QUERY [OPTIONS]

Options:
  --limit INT       Number of results (default: 10)
  --format TEXT     Output format: json, table (default: table)
```

### `ei speak`

Generate professional speech from text using AI.

```bash
ei speak TEXT [OPTIONS]
ei speak --input FILE [OPTIONS]

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
  ei speak "Hello world" -o hello.mp3

  # Premium voice with high quality
  ei speak "Professional recording" -o pro.mp3 -v marin -m tts-1-hd

  # Long-form with streaming
  ei speak --input script.txt -o audiobook.mp3 --stream

  # Custom pronunciation guidance
  ei speak "Dr. Nguyen at CERN" -o speech.mp3 \
    --instructions "Pronounce 'Nguyen' as 'win', 'CERN' as 'sern'"

  # Small file size for streaming
  ei speak "Compact audio" -o compact.opus -f opus

  # Generate and play immediately
  ei speak "Listen now" -o demo.mp3 --play
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
git clone https://github.com/kaw393939/ei-cli.git
cd ei-cli

# Install dependencies
poetry install

# Run in development mode
poetry run ei --help
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

Current test coverage: **25.35%** (Target: 90%)

- ✅ Configuration system: 100% coverage
- ✅ Error handling: 100% coverage
- ✅ Tool registry: 100% coverage
- 🚧 Tool implementations: 0% coverage (in progress)
- 🚧 CLI commands: 0% coverage (in progress)

We're actively working toward 90% coverage. See
[TECHNICAL_DEBT_AUDIT.md](TECHNICAL_DEBT_AUDIT.md) for details.

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
- **GitHub**: [github.com/kaw393939/ei-cli](https://github.com/kaw393939/ei-cli)
- **Documentation**:
  - [TECHNICAL_DEBT_AUDIT.md](TECHNICAL_DEBT_AUDIT.md) - Current status
  - [ROADMAP.md](ROADMAP.md) - Planned features
- **Issues**:
  [github.com/kaw393939/ei-cli/issues](https://github.com/kaw393939/ei-cli/issues)

---

**Status:** 🟡 Alpha - Core features working, comprehensive testing in
progress  
**Version:** 0.1.0  
**Coverage:** 25.35% → Target: 90%
````
