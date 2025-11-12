# EI-CLI Troubleshooting Guide

Solutions to common problems and error messages.

## Table of Contents

1. [Installation Issues](#installation-issues)
2. [API & Authentication](#api--authentication)
3. [Audio & Video Processing](#audio--video-processing)
4. [Workflow & State](#workflow--state)
5. [Performance Issues](#performance-issues)
6. [Error Messages](#error-messages)

## Installation Issues

### Python Version Error

**Error:** `Python 3.11+ required`

**Solution:**

```bash
# Check Python version
python --version

# Install Python 3.11+ (macOS with Homebrew)
brew install python@3.11

# Install Python 3.11+ (Ubuntu/Debian)
sudo apt update
sudo apt install python3.11

# Windows: Download from python.org
```

### FFmpeg Not Found

**Error:** `FFmpeg not installed`

**Solution:**

```bash
# macOS
brew install ffmpeg

# Ubuntu/Debian
sudo apt install ffmpeg

# Windows (with Chocolatey)
choco install ffmpeg

# Verify installation
ffmpeg -version
```

### yt-dlp Missing

**Error:** `yt-dlp not installed`

**Solution:**

```bash
# Install yt-dlp
pip install yt-dlp

# Update to latest version
pip install -U yt-dlp

# Verify
yt-dlp --version
```

## API & Authentication

### Missing API Key

**Error:** `[MISSING_API_KEY] OpenAI API key not found`

**Solution:**

```bash
# Set API key
ei-cli config set API__OPENAI_API_KEY=sk-your-key-here

# Verify
ei-cli config show | grep api_key

# Alternative: Environment variable
export API__OPENAI_API_KEY="sk-your-key"
```

### Invalid API Key

**Error:** `[API_UNAUTHORIZED] API authentication failed`

**Solutions:**

1. **Check key format:**

   ```bash
   # Key should start with 'sk-'
   echo $API__OPENAI_API_KEY
   ```

2. **Verify key is active:**
   - Visit [platform.openai.com/api-keys](https://platform.openai.com/api-keys)
   - Check if key exists and is enabled
   - Create new key if needed

3. **Check for extra spaces:**
   ```bash
   # Remove spaces
   ei-cli config set API__OPENAI_API_KEY=$(echo "sk-your-key" | tr -d ' ')
   ```

### Rate Limit Exceeded

**Error:** `[API_RATE_LIMIT] Rate limit exceeded`

**Solutions:**

1. **Wait and retry:**

   ```bash
   # Built-in retry with exponential backoff
   ei-cli transcribe video.mp4  # Automatically retries
   ```

2. **Check your usage:**
   - Visit [platform.openai.com/usage](https://platform.openai.com/usage)
   - Monitor API usage and limits

3. **Upgrade plan:**
   - Consider upgrading OpenAI plan
   - Or add API key with higher limits

### API Timeout

**Error:** `[NETWORK_TIMEOUT] Network request timed out`

**Solutions:**

1. **Increase timeout:**

   ```bash
   export API__TIMEOUT=120
   ei-cli transcribe large-video.mp4
   ```

2. **Check internet connection:**

   ```bash
   # Test connectivity
   curl -I https://api.openai.com
   ```

3. **Use chunking for large files:**
   ```bash
   # Auto-chunks files > 23MB
   ei-cli transcribe --chunk large-audio.mp3
   ```

## Audio & Video Processing

### File Too Large

**Error:** `[FILE_TOO_LARGE] File exceeds size limit`

**Solution:**

```bash
# Use automatic chunking
ei-cli transcribe --chunk large-file.mp3

# Manual chunking with custom size
ei-cli transcribe --chunk --chunk-size 20 large-file.mp3
```

### Unsupported Format

**Error:** `[INVALID_FORMAT] File format not supported`

**Supported formats:**

- Audio: mp3, mp4, mpeg, mpga, m4a, wav, webm
- Video: mp4, mov, avi, mkv, webm

**Solution:**

```bash
# Convert with FFmpeg
ffmpeg -i input.avi -c:a mp3 output.mp3

# Or specify output format
ei-cli transcribe video.avi --format mp3
```

### YouTube Download Fails

**Error:** `Video unavailable` or `Sign in to confirm your age`

**Solutions:**

1. **Set up YouTube cookies:**

   ```bash
   ei-cli youtube setup --browser chrome
   ei-cli youtube check
   ```

2. **Try different browser:**

   ```bash
   # If Chrome doesn't work
   ei-cli youtube setup --browser firefox
   ```

3. **Refresh cookies:**

   ```bash
   # Re-extract if cookies are old
   ei-cli youtube setup --browser chrome --refresh
   ```

4. **Manual cookie export:**
   - Install browser extension: "Get cookies.txt"
   - Export cookies for youtube.com
   - Save to: `~/.ei_cli/youtube_cookies.txt`

### FFmpeg Processing Error

**Error:** `FFmpeg failed to process file`

**Solutions:**

1. **Check file integrity:**

   ```bash
   # Try playing file
   ffplay input.mp4

   # Check with FFmpeg
   ffmpeg -v error -i input.mp4 -f null -
   ```

2. **Re-encode file:**

   ```bash
   # Re-encode to fix corruption
   ffmpeg -i input.mp4 -c copy output.mp4
   ```

3. **Verify FFmpeg installation:**
   ```bash
   # Should show version and codecs
   ffmpeg -version
   ffmpeg -codecs | grep mp3
   ```

## Workflow & State

### Workflow State Corrupted

**Error:** `[WORKFLOW_STATE_CORRUPT] Workflow state file is corrupted`

**Solution:**

```bash
# Delete corrupted state
rm .workflow_state.json

# Restart workflow
ei-cli transcribe video.mp4
```

### Cannot Resume Workflow

**Error:** `Cannot resume workflow`

**Solutions:**

1. **Check state file exists:**

   ```bash
   ls -la .workflow_state.json
   ```

2. **Verify artifacts:**

   ```bash
   # State tracks artifacts by checksum
   # Check if referenced files exist
   cat .workflow_state.json | jq '.artifacts'
   ```

3. **Force restart:**
   ```bash
   # Clear state and start fresh
   rm .workflow_state.json
   ei-cli transcribe video.mp4
   ```

### Artifacts Missing

**Error:** `Artifact validation failed`

**Solution:**

```bash
# Artifacts were deleted or moved
# Either restore them or restart workflow
ei-cli transcribe video.mp4  # Will restart if artifacts missing
```

## Performance Issues

### Slow Transcription

**Solutions:**

1. **Enable parallel processing:**

   ```bash
   export PARALLEL__MAX_WORKERS=5
   ei-cli transcribe video1.mp4 video2.mp4 video3.mp4
   ```

2. **Use caching:**

   ```bash
   # Enable cache for repeated operations
   export CACHE__ENABLED=true
   export CACHE__TTL_HOURS=48
   ```

3. **Optimize chunk size:**
   ```bash
   # Smaller chunks = more API calls but faster individual processing
   export AUDIO__MAX_CHUNK_SIZE_MB=15
   ```

### High Memory Usage

**Solutions:**

1. **Reduce chunk size:**

   ```bash
   export AUDIO__MAX_CHUNK_SIZE_MB=15
   ```

2. **Disable caching:**

   ```bash
   ei-cli --no-cache transcribe large-file.mp3
   ```

3. **Process sequentially:**
   ```bash
   # Reduce parallel workers
   export PARALLEL__MAX_WORKERS=1
   ```

### Cache Growing Too Large

**Solution:**

```bash
# Check cache size
du -sh ~/.ei_cli/cache

# Clear old cache
find ~/.ei_cli/cache -type f -mtime +7 -delete

# Set size limit
export CACHE__MAX_SIZE_GB=5

# Or disable cache
export CACHE__ENABLED=false
```

## Error Messages

### Configuration Errors

| Error Code        | Meaning        | Solution                                    |
| ----------------- | -------------- | ------------------------------------------- |
| `CONFIG_MISSING`  | No config file | `ei-cli config init`                        |
| `CONFIG_INVALID`  | Invalid YAML   | Check syntax at `~/.ei_cli/config.yaml`     |
| `MISSING_API_KEY` | No API key     | `ei-cli config set API__OPENAI_API_KEY=key` |

### Network Errors

| Error Code           | Meaning         | Solution                                     |
| -------------------- | --------------- | -------------------------------------------- |
| `NETWORK_TIMEOUT`    | Request timeout | Increase timeout or check connection         |
| `NETWORK_CONNECTION` | Cannot connect  | Check internet and firewall                  |
| `NETWORK_DNS`        | DNS failed      | Check DNS settings                           |
| `NETWORK_SSL`        | SSL error       | Update certificates or use `--no-verify-ssl` |

### API Errors

| Error Code           | Meaning        | Solution              |
| -------------------- | -------------- | --------------------- |
| `API_RATE_LIMIT`     | Rate limited   | Wait or upgrade plan  |
| `API_QUOTA_EXCEEDED` | Quota exceeded | Check usage dashboard |
| `API_UNAUTHORIZED`   | Invalid key    | Verify API key        |
| `API_SERVER_ERROR`   | OpenAI issue   | Try again later       |

### File Errors

| Error Code        | Meaning      | Solution           |
| ----------------- | ------------ | ------------------ |
| `FILE_NOT_FOUND`  | File missing | Check path         |
| `FILE_PERMISSION` | No access    | Check permissions  |
| `DISK_FULL`       | Out of space | Free up disk space |
| `FILE_TOO_LARGE`  | File > 25MB  | Use `--chunk`      |

### Validation Errors

| Error Code       | Meaning            | Solution             |
| ---------------- | ------------------ | -------------------- |
| `INVALID_INPUT`  | Bad input          | Check command syntax |
| `INVALID_FORMAT` | Unsupported format | Convert file         |
| `INVALID_URL`    | Bad URL            | Verify URL           |

## Common Workflows

### Full Troubleshooting Checklist

```bash
# 1. Verify installation
ei-cli --version
python --version
ffmpeg -version

# 2. Check configuration
ei-cli config show
echo $API__OPENAI_API_KEY

# 3. Test API connectivity
curl -H "Authorization: Bearer $API__OPENAI_API_KEY" \
  https://api.openai.com/v1/models

# 4. Check logs
tail -50 ~/.ei_cli/logs/ei-cli.log

# 5. Clear cache
rm -rf ~/.ei_cli/cache/*

# 6. Reset configuration
ei-cli config reset
ei-cli config set API__OPENAI_API_KEY=sk-your-key
```

### Enable Debug Logging

```bash
# Enable debug mode
export LOGGING__LEVEL=DEBUG

# Run command
ei-cli transcribe video.mp4

# Check detailed logs
tail -100 ~/.ei_cli/logs/ei-cli.log
```

### Test Individual Components

```bash
# Test FFmpeg
ffmpeg -version
ffmpeg -i test.mp4 -f null -

# Test yt-dlp
yt-dlp --version
yt-dlp --list-formats "VIDEO_URL"

# Test API key
curl -H "Authorization: Bearer $API__OPENAI_API_KEY" \
  https://api.openai.com/v1/models

# Test file access
ls -la input.mp4
file input.mp4
```

## Getting Help

### Before Opening an Issue

1. **Check this guide** for common solutions
2. **Enable debug logging** to see detailed errors
3. **Test with minimal example** to isolate problem
4. **Check recent changes** in [CHANGELOG.md](../CHANGELOG.md)

### Reporting Issues

Include this information:

```bash
# System information
ei-cli --version
python --version
ffmpeg -version
uname -a

# Configuration (remove API keys!)
ei-cli config show

# Recent logs
tail -50 ~/.ei_cli/logs/ei-cli.log

# Command that failed
ei-cli transcribe video.mp4  # (exact command)
```

### Community Support

- **GitHub Issues:**
  [github.com/kaw393939/ei-cli/issues](https://github.com/kaw393939/ei-cli/issues)
- **Discussions:**
  [github.com/kaw393939/ei-cli/discussions](https://github.com/kaw393939/ei-cli/discussions)
- **Email:** kaw393939@gmail.com

## Next Steps

- [Configuration Guide](CONFIGURATION.md) - Complete config reference
- [Recipe Book](RECIPES.md) - Common workflow examples
- [API Documentation](API.md) - Python API usage
