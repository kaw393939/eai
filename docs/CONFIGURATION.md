# EI-CLI Configuration Guide

Complete guide to configuring EI-CLI for your needs.

## Table of Contents

1. [Quick Start](#quick-start)
2. [Configuration File](#configuration-file)
3. [Environment Variables](#environment-variables)
4. [API Keys](#api-keys)
5. [Advanced Configuration](#advanced-configuration)
6. [Troubleshooting](#troubleshooting)

## Quick Start

### Initial Setup

```bash
# Initialize configuration (creates ~/.ei_cli/config.yaml)
ei-cli config init

# Set your OpenAI API key
ei-cli config set API__OPENAI_API_KEY=your-api-key-here

# Verify configuration
ei-cli config show
```

### YouTube Setup (Optional)

For downloading private/age-restricted videos:

```bash
# Extract cookies from your browser
ei-cli youtube setup --browser chrome

# Check cookie status
ei-cli youtube check

# Clear cookies (if needed)
ei-cli youtube clear
```

## Configuration File

EI-CLI uses a YAML configuration file located at `~/.ei_cli/config.yaml`.

### File Structure

```yaml
# ~/.ei_cli/config.yaml

# API Configuration
api:
  openai_api_key: "sk-..." # Your OpenAI API key
  timeout: 60 # API timeout in seconds
  max_retries: 3 # Maximum retry attempts

# Audio Processing
audio:
  format: "mp3" # Output format: mp3, wav, m4a
  quality: "medium" # Quality: low, medium, high
  sample_rate: 16000 # Sample rate in Hz
  max_chunk_size_mb: 23 # Maximum chunk size for large files

# Video Processing
video:
  format: "mp4" # Download format
  quality: "best" # Quality: best, worst, or height (720, 1080)
  download_dir: "~/Downloads" # Download directory

# Transcription
transcription:
  model: "whisper-1" # Whisper model
  language: null # Auto-detect language (or specify: en, es, etc.)
  prompt: "" # Context prompt for better accuracy
  temperature: 0.0 # 0=deterministic, 1=creative

# Caching
cache:
  enabled: true # Enable/disable caching
  directory: "~/.ei_cli/cache" # Cache directory
  ttl_hours: 24 # Time to live in hours
  max_size_gb: 5 # Maximum cache size

# Logging
logging:
  level: "INFO" # DEBUG, INFO, WARNING, ERROR, CRITICAL
  file: "~/.ei_cli/logs/ei-cli.log" # Log file path
  max_size_mb: 100 # Maximum log file size
  backup_count: 5 # Number of backup files

# Workflow
workflow:
  state_dir: "~/.ei_cli/workflows" # Workflow state directory
  auto_resume: true # Automatically resume failed workflows
  cleanup_on_success: false # Clean up intermediate files
```

### Creating a Custom Configuration

```bash
# Create configuration file manually
mkdir -p ~/.ei_cli
cat > ~/.ei_cli/config.yaml << EOF
api:
  openai_api_key: "sk-your-key-here"
  timeout: 90

audio:
  quality: "high"
  max_chunk_size_mb: 20

cache:
  enabled: true
  ttl_hours: 48
EOF
```

## Environment Variables

EI-CLI supports configuration via environment variables. Variables use a double
underscore (`__`) to denote nested keys.

### Priority Order

1. Command-line arguments (highest priority)
2. Environment variables
3. Configuration file
4. Default values (lowest priority)

### Common Environment Variables

```bash
# API Configuration
export API__OPENAI_API_KEY="sk-your-key-here"
export API__TIMEOUT=60
export API__MAX_RETRIES=3

# Audio Settings
export AUDIO__FORMAT="mp3"
export AUDIO__QUALITY="high"
export AUDIO__MAX_CHUNK_SIZE_MB=25

# Video Settings
export VIDEO__QUALITY="1080"
export VIDEO__DOWNLOAD_DIR="/path/to/downloads"

# Transcription
export TRANSCRIPTION__MODEL="whisper-1"
export TRANSCRIPTION__LANGUAGE="en"

# Caching
export CACHE__ENABLED="true"
export CACHE__TTL_HOURS=48

# Logging
export LOGGING__LEVEL="DEBUG"
```

### Setting Variables

**Bash/Zsh (Linux/macOS):**

```bash
# Temporary (current session)
export API__OPENAI_API_KEY="sk-your-key"

# Permanent (add to ~/.bashrc or ~/.zshrc)
echo 'export API__OPENAI_API_KEY="sk-your-key"' >> ~/.bashrc
source ~/.bashrc
```

**PowerShell (Windows):**

```powershell
# Temporary (current session)
$env:API__OPENAI_API_KEY="sk-your-key"

# Permanent (system-wide)
[System.Environment]::SetEnvironmentVariable(
    "API__OPENAI_API_KEY",
    "sk-your-key",
    [System.EnvironmentVariableTarget]::User
)
```

## API Keys

### OpenAI API Key

**Required for:** Transcription, image analysis, AI features

**Get your key:**

1. Visit [platform.openai.com/api-keys](https://platform.openai.com/api-keys)
2. Create a new API key
3. Copy the key (starts with `sk-`)

**Set the key:**

```bash
# Option 1: CLI command (recommended)
ei-cli config set API__OPENAI_API_KEY=sk-your-key

# Option 2: Environment variable
export API__OPENAI_API_KEY="sk-your-key"

# Option 3: Configuration file
# Edit ~/.ei_cli/config.yaml
api:
  openai_api_key: "sk-your-key"
```

**Verify it works:**

```bash
ei-cli config show | grep openai_api_key
```

### YouTube Cookies (Optional)

**Required for:** Age-restricted or private YouTube videos

**Set up cookies:**

```bash
# Extract from browser (Chrome recommended)
ei-cli youtube setup --browser chrome

# Check status
ei-cli youtube check

# Output:
# ✓ Cookies found
# Age: 2 days
# Status: Fresh (< 7 days)
```

**Supported browsers:**

- chrome
- firefox
- safari
- edge

## Advanced Configuration

### Multiple Profiles

You can use different configuration files for different projects:

```bash
# Create project-specific config
ei-cli --config /path/to/project/config.yaml config init

# Use specific config
ei-cli --config /path/to/project/config.yaml transcribe video.mp4
```

### Custom Cache Directory

```bash
# Set cache directory
export CACHE__DIRECTORY="/path/to/large/disk/cache"

# Or in config file
cache:
  directory: "/path/to/large/disk/cache"
```

### Workflow State Persistence

```bash
# Enable auto-resume
ei-cli config set WORKFLOW__AUTO_RESUME=true

# Set custom state directory
export WORKFLOW__STATE_DIR="/path/to/workflow/states"
```

### Logging Configuration

```bash
# Enable debug logging
export LOGGING__LEVEL="DEBUG"
export LOGGING__FILE="$HOME/.ei_cli/logs/debug.log"

# Or via config file
logging:
  level: "DEBUG"
  file: "~/.ei_cli/logs/debug.log"
  max_size_mb: 200
  backup_count: 10
```

### Performance Tuning

```yaml
# ~/.ei_cli/config.yaml

# Parallel execution
parallel:
  max_workers: 5 # Number of parallel tasks (default: 3)

# API settings
api:
  timeout: 120 # Increase for slow connections
  max_retries: 5 # More retries for unreliable networks

# Audio chunking
audio:
  max_chunk_size_mb: 20 # Smaller chunks for stability

# Caching
cache:
  enabled: true # Enable for faster repeated operations
  ttl_hours: 72 # Keep cache longer for expensive operations
```

## Troubleshooting

### Configuration Not Loading

```bash
# Check config file location
ls -la ~/.ei_cli/config.yaml

# Verify syntax (must be valid YAML)
python -c "import yaml; yaml.safe_load(open('$HOME/.ei_cli/config.yaml'))"

# Reset to defaults
ei-cli config reset
```

### API Key Issues

```bash
# Verify key is set
ei-cli config show | grep api_key

# Test API connectivity
ei-cli config test-api

# Common issues:
# - Key starts with wrong prefix (should be sk-)
# - Extra spaces in key
# - Key expired or revoked
```

### Environment Variable Priority

If environment variables aren't working:

```bash
# Check if variable is set
echo $API__OPENAI_API_KEY

# Verify no typos (double underscore)
env | grep API__

# Check priority: env vars override config file
ei-cli config show --include-source
```

### Cache Issues

```bash
# Check cache size
du -sh ~/.ei_cli/cache

# Clear cache
rm -rf ~/.ei_cli/cache/*

# Disable cache temporarily
ei-cli --no-cache transcribe video.mp4
```

### YouTube Cookie Problems

```bash
# Check cookie status
ei-cli youtube check

# Re-extract cookies
ei-cli youtube setup --browser chrome --refresh

# Clear and start fresh
ei-cli youtube clear
ei-cli youtube setup --browser chrome
```

## Example Configurations

### Minimal Setup (Defaults)

```yaml
# ~/.ei_cli/config.yaml
api:
  openai_api_key: "sk-your-key-here"
```

### High-Performance Setup

```yaml
# ~/.ei_cli/config.yaml
api:
  openai_api_key: "sk-your-key-here"
  timeout: 120
  max_retries: 5

parallel:
  max_workers: 5

audio:
  quality: "high"
  max_chunk_size_mb: 20

cache:
  enabled: true
  ttl_hours: 72
  max_size_gb: 10

logging:
  level: "INFO"
```

### Development Setup

```yaml
# ~/.ei_cli/config.yaml
api:
  openai_api_key: "sk-your-key-here"
  timeout: 60

logging:
  level: "DEBUG"
  file: "~/.ei_cli/logs/debug.log"
  max_size_mb: 200

workflow:
  auto_resume: false # Manual control in development
  cleanup_on_success: false # Keep all intermediate files

cache:
  enabled: false # Disable for testing
```

## Next Steps

- [Troubleshooting Guide](TROUBLESHOOTING.md) - Fix common issues
- [Recipe Book](RECIPES.md) - Common workflow examples
- [API Documentation](API.md) - Python API reference
