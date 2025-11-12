# EI-CLI Recipe Book 🍳

**Practical workflows and common use cases for EI-CLI**

This guide provides ready-to-use examples for common tasks. Each recipe includes
complete commands, expected output, and practical tips.

---

## Table of Contents

1. [YouTube Video to Blog Post](#1-youtube-video-to-blog-post)
2. [Batch Video Transcription](#2-batch-video-transcription)
3. [Video Tutorial Analysis](#3-video-tutorial-analysis)
4. [Batch Image Background Removal](#4-batch-image-background-removal)
5. [Smart Image Cropping Pipeline](#5-smart-image-cropping-pipeline)
6. [AI-Powered Image Analysis](#6-ai-powered-image-analysis)
7. [Multi-Language Content Creation](#7-multi-language-content-creation)
8. [Podcast to Text with Chapters](#8-podcast-to-text-with-chapters)
9. [Automated Meeting Notes](#9-automated-meeting-notes)
10. [AI-Generated Voiceovers](#10-ai-generated-voiceovers)
11. [Video Subtitle Generation](#11-video-subtitle-generation)
12. [Batch AI Image Generation](#12-batch-ai-image-generation)
13. [Smart Content Research](#13-smart-content-research)
14. [Audio Translation Workflow](#14-audio-translation-workflow)
15. [Custom Automation Workflows](#15-custom-automation-workflows)

---

## 1. YouTube Video to Blog Post

**Goal**: Convert a YouTube video into a well-formatted blog post with title,
summary, and content.

### Step-by-Step

```bash
# 1. Transcribe the video
ei transcribe-video "https://youtube.com/watch?v=VIDEO_ID" \
    -o transcription.txt

# 2. Review the transcription
cat transcription.txt

# 3. Use AI to structure it as a blog post (manual editing)
# Copy transcription.txt content and paste into your editor
# Or use an AI writing tool to reformat it
```

### Advanced: With Custom Processing

```bash
# Transcribe with language hint for better accuracy
ei transcribe-video "https://youtube.com/watch?v=VIDEO_ID" \
    --language en \
    --output transcription.json \
    --format json

# The JSON includes metadata like duration and detected language
```

### Tips

- Use `--format json` to get structured data with timestamps
- For technical content, add `--prompt "Technical discussion about [topic]"` to
  improve accuracy
- Large videos are automatically chunked and processed in parallel

---

## 2. Batch Video Transcription

**Goal**: Transcribe multiple videos efficiently using parallel processing.

### Batch Script

```bash
#!/bin/bash
# transcribe_batch.sh

# List of video URLs
VIDEOS=(
    "https://youtube.com/watch?v=VIDEO1"
    "https://youtube.com/watch?v=VIDEO2"
    "https://youtube.com/watch?v=VIDEO3"
)

# Create output directory
mkdir -p transcriptions

# Transcribe each video
for i in "${!VIDEOS[@]}"; do
    VIDEO="${VIDEOS[$i]}"
    OUTPUT="transcriptions/video_$i.txt"

    echo "Processing video $((i+1))/${#VIDEOS[@]}..."
    ei transcribe-video "$VIDEO" -o "$OUTPUT" &
done

# Wait for all background jobs to complete
wait
echo "✓ All videos transcribed!"
```

### Tips

- Background jobs (`&`) enable parallel processing
- Use `--format srt` for subtitle files
- Add error handling for production use

---

## 3. Video Tutorial Analysis

**Goal**: Extract key insights from educational videos.

### Workflow

```bash
# 1. Download and transcribe
ei transcribe-video "https://youtube.com/watch?v=TUTORIAL_ID" \
    -o tutorial.txt \
    --prompt "Educational tutorial with step-by-step instructions"

# 2. Generate subtitles for reference
ei transcribe-video "https://youtube.com/watch?v=TUTORIAL_ID" \
    -o tutorial.srt \
    --format srt

# 3. Analyze the content (manual or with external AI)
# Use the transcription to:
# - Create study notes
# - Extract key timestamps
# - Generate quiz questions
```

### Tips

- SRT format includes timestamps for finding specific moments
- Use VTT format for web-based video players
- Combine with vision AI for slide analysis (see Recipe 6)

---

## 4. Batch Image Background Removal

**Goal**: Remove backgrounds from multiple product photos.

### Batch Processing

```bash
#!/bin/bash
# remove_backgrounds.sh

INPUT_DIR="product_photos"
OUTPUT_DIR="products_nobg"

mkdir -p "$OUTPUT_DIR"

# Process all images
for image in "$INPUT_DIR"/*.{jpg,png,jpeg}; do
    [ -f "$image" ] || continue

    filename=$(basename "$image")
    echo "Processing $filename..."

    ei remove-bg "$image" -o "$OUTPUT_DIR/${filename%.*}_nobg.png"
done

echo "✓ Background removal complete!"
```

### Tips

- PNG output preserves transparency
- Works with JPG, PNG, and other common formats
- Consider downscaling large images first for faster processing

---

## 5. Smart Image Cropping Pipeline

**Goal**: Crop images to specific dimensions using AI-powered smart detection.

### Face-Centered Cropping

```bash
# Crop profile photos to square format (1:1)
ei crop portrait.jpg -o profile_square.jpg \
    --width 800 \
    --height 800 \
    --subject-detect face

# Crop group photo focusing on people
ei crop group.jpg -o group_cropped.jpg \
    --width 1200 \
    --height 630 \
    --subject-detect person
```

### Social Media Formats

```bash
# Instagram post (1:1)
ei crop photo.jpg -o instagram.jpg --width 1080 --height 1080

# Twitter/X header (3:1)
ei crop photo.jpg -o twitter_header.jpg --width 1500 --height 500

# LinkedIn post (1.91:1)
ei crop photo.jpg -o linkedin.jpg --width 1200 --height 627

# Story format (9:16)
ei crop photo.jpg -o story.jpg --width 1080 --height 1920
```

### Batch Social Media Prep

```bash
#!/bin/bash
# social_media_batch.sh

IMAGE="$1"
BASE="${IMAGE%.*}"

echo "Creating social media formats for $IMAGE..."

ei crop "$IMAGE" -o "${BASE}_instagram.jpg" --width 1080 --height 1080
ei crop "$IMAGE" -o "${BASE}_twitter.jpg" --width 1200 --height 675
ei crop "$IMAGE" -o "${BASE}_facebook.jpg" --width 1200 --height 630
ei crop "$IMAGE" -o "${BASE}_linkedin.jpg" --width 1200 --height 627

echo "✓ All formats created!"
```

---

## 6. AI-Powered Image Analysis

**Goal**: Analyze images and extract detailed information.

### Basic Analysis

```bash
# Analyze a single image
ei vision image.jpg \
    --prompt "Describe this image in detail" \
    -o analysis.txt

# Extract specific information
ei vision product.jpg \
    --prompt "List all visible features and specifications" \
    -o features.txt
```

### Batch Analysis

```bash
#!/bin/bash
# analyze_images.sh

for image in images/*.jpg; do
    filename=$(basename "$image" .jpg)

    echo "Analyzing $filename..."
    ei vision "$image" \
        --prompt "Provide a detailed description suitable for alt text" \
        -o "descriptions/${filename}.txt"
done
```

### Use Cases

- **Accessibility**: Generate alt text for images
- **E-commerce**: Extract product details from photos
- **Content Moderation**: Analyze image content
- **Research**: Catalog visual data

---

## 7. Multi-Language Content Creation

**Goal**: Create content in multiple languages from source audio.

### Workflow

```bash
# 1. Transcribe English audio
ei transcribe english_audio.mp3 \
    --language en \
    -o english.txt

# 2. Translate to Spanish (manual or using translation tool)
# Save as spanish.txt

# 3. Generate Spanish voiceover
ei speak --input spanish.txt \
    --voice nova \
    --output spanish_audio.mp3

# 4. Generate French voiceover
ei speak --input french.txt \
    --voice shimmer \
    --output french_audio.mp3
```

### Tips

- Use `translate-audio` command for automatic translation (if available)
- Different voices work better for different languages
- Adjust speech speed with `--speed` for naturalness

---

## 8. Podcast to Text with Chapters

**Goal**: Convert podcast episodes to searchable text.

### Full Workflow

```bash
# 1. Transcribe podcast
ei transcribe podcast_ep01.mp3 \
    --format json \
    -o episode.json

# 2. Generate clean text version
ei transcribe podcast_ep01.mp3 \
    --format text \
    -o episode.txt

# 3. Generate VTT with timestamps for web player
ei transcribe podcast_ep01.mp3 \
    --format vtt \
    -o episode.vtt
```

### Tips

- JSON format includes timing data for chapter markers
- Use `--prompt "Podcast conversation about [topic]"` for better speaker
  detection
- VTT files work with most web audio players

---

## 9. Automated Meeting Notes

**Goal**: Transform meeting recordings into searchable notes.

### Process Recording

```bash
# 1. Transcribe meeting
ei transcribe meeting_2024_01_15.m4a \
    --prompt "Business meeting with multiple speakers" \
    --temperature 0.2 \
    -o meeting_transcript.txt

# 2. Review and edit
# Open meeting_transcript.txt and format as needed

# 3. Generate summary (manual or with AI tool)
```

### Best Practices

- Record in high quality (at least 16kHz, mono is fine)
- Use lower temperature (0.0-0.3) for factual accuracy
- Include meeting context in filename for organization

---

## 10. AI-Generated Voiceovers

**Goal**: Create professional voiceovers for videos or presentations.

### Single Voiceover

```bash
# Create script
cat > script.txt << 'EOF'
Welcome to our tutorial. Today we'll learn how to use AI tools effectively.
In this video, we'll cover three main topics: setup, usage, and best practices.
Let's get started!
EOF

# Generate audio
ei speak --input script.txt \
    --voice alloy \
    --model tts-1-hd \
    --output voiceover.mp3
```

### Multiple Sections

```bash
#!/bin/bash
# generate_voiceovers.sh

SECTIONS=("intro" "chapter1" "chapter2" "conclusion")
VOICE="onyx"  # Professional male voice

for section in "${SECTIONS[@]}"; do
    echo "Generating voiceover for $section..."
    ei speak --input "scripts/${section}.txt" \
        --voice "$VOICE" \
        --model tts-1-hd \
        --output "audio/${section}.mp3"
done

echo "✓ All voiceovers generated!"
```

### Voice Guide

- **alloy**: Neutral, versatile
- **echo**: Clear, professional male
- **fable**: Warm, storytelling
- **onyx**: Deep, authoritative male
- **nova**: Energetic, youthful
- **shimmer**: Professional female

---

## 11. Video Subtitle Generation

**Goal**: Create subtitle files for videos in multiple formats.

### SRT Subtitles

```bash
# Generate SRT format (most compatible)
ei transcribe-video "https://youtube.com/watch?v=VIDEO_ID" \
    --format srt \
    -o video_subtitles.srt

# For local video files
ei transcribe video.mp4 \
    --format srt \
    -o video.srt
```

### VTT Subtitles (Web)

```bash
# VTT format for HTML5 video
ei transcribe-video "https://youtube.com/watch?v=VIDEO_ID" \
    --format vtt \
    -o video.vtt
```

### Tips

- SRT works with most video editors and players
- VTT is best for web-based players
- Use `--language` parameter to improve accuracy

---

## 12. Batch AI Image Generation

**Goal**: Generate multiple AI images from prompts.

### Single Image

```bash
# Generate an image
ei image "A serene mountain landscape at sunset, photorealistic" \
    --size 1024x1024 \
    --quality hd \
    --output landscape.png
```

### Batch Generation

```bash
#!/bin/bash
# generate_images.sh

# Array of prompts
PROMPTS=(
    "Modern minimalist office interior, natural lighting"
    "Abstract geometric pattern, blue and gold colors"
    "Futuristic city skyline at night, neon lights"
)

mkdir -p generated_images

for i in "${!PROMPTS[@]}"; do
    PROMPT="${PROMPTS[$i]}"
    OUTPUT="generated_images/image_$i.png"

    echo "Generating image $((i+1))..."
    ei image "$PROMPT" \
        --quality hd \
        --size 1024x1024 \
        --output "$OUTPUT"

    sleep 2  # Rate limiting
done

echo "✓ All images generated!"
```

### Size Guide

- `1024x1024`: Square (social media, profiles)
- `1792x1024`: Landscape (headers, banners)
- `1024x1792`: Portrait (phone wallpapers, stories)

---

## 13. Smart Content Research

**Goal**: Use AI search and vision to research topics.

### Research Workflow

```bash
# 1. Search for information
ei search "artificial intelligence trends 2024" \
    --results 10 \
    -o research_results.json

# 2. Analyze related images
for image in research_images/*.jpg; do
    ei vision "$image" \
        --prompt "What does this image show about AI trends?" \
        -o "analysis/$(basename "$image" .jpg).txt"
done

# 3. Compile findings
cat analysis/*.txt > compiled_research.txt
```

### Tips

- Use specific search queries for better results
- Combine text search with image analysis
- Verify information from multiple sources

---

## 14. Audio Translation Workflow

**Goal**: Translate audio content to different languages.

### Full Pipeline

```bash
# 1. Transcribe original audio
ei transcribe original.mp3 \
    --language en \
    -o original_transcript.txt

# 2. Translate text (using external tool or manual translation)
# Save as: spanish_transcript.txt

# 3. Generate translated audio
ei speak --input spanish_transcript.txt \
    --voice nova \
    --speed 0.9 \
    --output translated_spanish.mp3

# 4. Verify and adjust
# Listen to translated_spanish.mp3 and adjust speed if needed
```

### Tips

- Match voice characteristics to content (professional/casual)
- Adjust speed for natural speech in target language
- Use `tts-1-hd` model for higher quality

---

## 15. Custom Automation Workflows

**Goal**: Combine multiple EI-CLI commands for complex automation.

### Example: Social Media Content Factory

```bash
#!/bin/bash
# social_media_factory.sh

VIDEO_URL="$1"
TOPIC="$2"

echo "Creating social media content for: $TOPIC"

# 1. Download and transcribe video
echo "Step 1: Transcribing video..."
ei transcribe-video "$VIDEO_URL" -o transcription.txt

# 2. Generate key quotes (extract manually or use AI)
# For this example, we'll create a sample quote
QUOTE="The future of AI is human-centered and ethical."

# 3. Generate visual for quote
echo "Step 2: Generating quote image..."
ei image "Minimalist design with text: $QUOTE, modern typography" \
    --size 1080x1080 \
    --quality hd \
    -o quote_image.png

# 4. Remove background for clean look
echo "Step 3: Processing image..."
ei remove-bg quote_image.png -o quote_final.png

# 5. Create multiple sizes for different platforms
echo "Step 4: Creating platform-specific sizes..."
ei crop quote_final.png -o instagram.png --width 1080 --height 1080
ei crop quote_final.png -o twitter.png --width 1200 --height 675
ei crop quote_final.png -o linkedin.png --width 1200 --height 627

# 6. Generate audio version of quote
echo "Step 5: Creating audio..."
echo "$QUOTE" > quote.txt
ei speak --input quote.txt --voice alloy -o quote_audio.mp3

echo "✓ Social media content pack ready!"
echo "  - Transcription: transcription.txt"
echo "  - Images: instagram.png, twitter.png, linkedin.png"
echo "  - Audio: quote_audio.mp3"
```

### Custom Automation Tips

1. **Error Handling**: Add checks for command failures

   ```bash
   if ! ei transcribe video.mp3 -o output.txt; then
       echo "Error: Transcription failed"
       exit 1
   fi
   ```

2. **Progress Tracking**: Show status updates

   ```bash
   echo "Progress: 3/5 steps complete..."
   ```

3. **Rate Limiting**: Add delays between API calls

   ```bash
   sleep 2  # Wait 2 seconds
   ```

4. **Parallel Processing**: Use background jobs
   ```bash
   command1 & command2 & command3 &
   wait  # Wait for all to complete
   ```

---

## Tips for Success

### Performance

- **Cache Results**: EI-CLI caches API responses for 24 hours by default
- **Parallel Processing**: Use `&` for independent tasks
- **Batch Operations**: Group similar tasks together

### Quality

- **Specify Language**: Use `--language` for better transcription accuracy
- **Add Context**: Use `--prompt` to guide AI understanding
- **Choose Right Model**: `tts-1-hd` for high quality audio

### Cost Optimization

- **Use Standard Quality**: `--quality standard` costs less
- **Test with Small Files**: Verify settings before batch processing
- **Reuse Cached Results**: Check cache before reprocessing

### Troubleshooting

- **Check API Keys**: Ensure `EI_API_KEY` environment variable is set
- **Verify File Formats**: Use supported formats (MP3, WAV, PNG, JPG)
- **Review Logs**: Add `-v` for verbose output
- **Test Incrementally**: Run commands one at a time first

---

## Getting Help

- **Documentation**: See `docs/` directory for detailed guides
- **Command Help**: Run `ei <command> --help` for options
- **Configuration**: Check `docs/CONFIGURATION.md`
- **Troubleshooting**: See `docs/TROUBLESHOOTING.md`

---

## Contributing Recipes

Have a useful workflow? Share it!

1. Create a recipe following this format
2. Test thoroughly
3. Submit a pull request with your recipe
4. Include example commands and expected output

---

**Happy Building! 🚀**

_Last updated: 2024-11-09_
