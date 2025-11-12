# GPT-5 Vision & Image Guide

Complete guide to using GPT-5 for image analysis, editing, and generation.

## Table of Contents

1. [Vision Capabilities](#vision-capabilities)
2. [Prompting Best Practices](#prompting-best-practices)
3. [Image Editing & Inpainting](#image-editing--inpainting)
4. [Use Cases](#use-cases)
5. [CLI Usage Examples](#cli-usage-examples)
6. [Advanced Techniques](#advanced-techniques)

---

## Vision Capabilities

### What GPT-5 Vision Can Do

#### 1. **Optical Character Recognition (OCR)**

- Extract printed and handwritten text from images
- Process invoices, receipts, forms, and documents
- Extract structured data (invoice numbers, dates, line items, totals)
- High accuracy for business document processing

**Example:**

```bash
ei vision invoice.jpg --prompt "Extract all text and organize by: invoice number, date, vendor, line items, and total"
```

#### 2. **Object Recognition & Scene Understanding**

- Identify objects within images
- Understand spatial relationships between objects
- Analyze complex scenes and their context
- Determine object states (e.g., LED lights on/off)

**Example:**

```bash
ei vision server_rack.jpg --prompt "Which server has an orange LED lit? Provide details about the unit."
```

#### 3. **Image Description & Analysis**

- Generate detailed descriptions of images
- Identify colors, textures, and patterns
- Understand mood and atmosphere
- Describe scenes for accessibility (alt-text generation)

**Example:**

```bash
ei vision artwork.jpg --prompt "Describe this image for a blind person, including colors, composition, and mood"
```

#### 4. **Spatial Reasoning**

- Understand object positioning and layout
- Analyze diagrams and charts
- Limited precision for object counting (use specialized models for high
  precision)

### Limitations

- **Object Counting**: Variable performance, not as precise as specialized
  models
- **Measurement**: Struggles with precise spatial measurements
- **Complex Spatial Tasks**: May require specialized computer vision models

---

## Prompting Best Practices

### 1. **Use Specific Nudge Phrases**

Add phrases at the end of prompts to encourage deeper reasoning:

```bash
ei vision complex_diagram.png --prompt "Analyze this circuit diagram and explain its function. Think hard about this."
```

**Effective nudge phrases:**

- "Think hard about this"
- "Provide detailed reasoning"
- "Consider all aspects carefully"
- "Think step by step"

### 2. **Provide Comprehensive Context**

Give the model all relevant background information upfront:

```bash
ei vision medical_scan.jpg --prompt "This is a chest X-ray from a 45-year-old patient with respiratory symptoms. Identify any abnormalities, focusing on lung fields and cardiac silhouette."
```

### 3. **Use Structured Prompts**

Organize prompts with clear sections for better results:

```bash
ei vision product.jpg --prompt "
TASK: Product analysis
FOCUS:
- Brand identification
- Condition assessment
- Notable features
FORMAT: Bullet points
TONE: Professional"
```

### 4. **Specify Output Format Explicitly**

Tell GPT-5 exactly how you want the response:

```bash
ei vision chart.jpg --prompt "Extract data from this chart. Return as JSON with keys: title, x_axis, y_axis, data_points"
```

**Format options:**

- Bullet points
- Numbered list
- JSON structure
- Table format
- Paragraph form
- Technical report style

### 5. **Specify Reasoning Level**

For complex tasks, request high reasoning effort:

```bash
ei vision engineering_drawing.png --model gpt-5 --max-tokens 2000 --prompt "Analyze this engineering drawing with maximum detail and reasoning. Identify all measurements, tolerances, and specifications."
```

**Reasoning levels by model:**

- `gpt-5`: High reasoning, detailed analysis
- `gpt-5-mini`: Balanced reasoning, cost-effective
- `gpt-5-nano`: Fast, lower reasoning depth

### 6. **Avoid Conflicting Instructions**

Keep instructions logically consistent:

❌ **Bad:**

```bash
ei vision doc.jpg --prompt "Summarize this document but don't shorten anything"
```

✅ **Good:**

```bash
ei vision doc.jpg --prompt "Provide a comprehensive summary of this document, including all key points"
```

### 7. **Use Meta-Prompting**

Ask GPT-5 to improve your prompts:

```bash
ei vision image.jpg --prompt "First, suggest a better way to ask about this image, then answer using that improved prompt"
```

### 8. **Encourage Self-Reflection**

Have the model review its own output:

```bash
ei vision data_viz.jpg --prompt "Analyze this data visualization. After your analysis, review your response for accuracy and completeness, then provide any corrections."
```

---

## Image Editing & Inpainting

### Overview

GPT-5 supports advanced image editing through **inpainting**, which fills in
masked areas of an image with new content.

### Capabilities

1. **Partial Image Editing**: Replace specific parts of an image
2. **Color Tone Changes**: Modify colors without disrupting atmosphere
3. **Background Removal/Replacement**: Change backgrounds seamlessly
4. **Object Removal**: Remove unwanted elements from photos
5. **Style Adjustments**: Modify artistic style of image portions

### Editing Modes

#### 1. **Text-to-Image** (Generation)

Create new images from textual descriptions.

```bash
ei image "a serene mountain landscape at sunset" --model gpt-image-1
```

#### 2. **Image-to-Image** (Editing)

Modify existing images based on prompts and masks.

**API Endpoint:** `POST https://api.openai.com/v1/images/edit`

**Required Parameters:**

- `image`: Original image file (PNG)
- `mask`: Mask image with transparent areas indicating edits
- `prompt`: Description of desired edit
- `size`: Output dimensions (256x256, 512x512, 1024x1024, etc.)

### Mask Creation

A **mask** is a PNG image where:

- **Transparent areas** (alpha channel) = regions to edit
- **Opaque areas** = regions to preserve
- **Must match dimensions** of original image

**Creating masks:**

1. Manual: Use image editing software (Photoshop, GIMP)
2. Automatic: GPT Image API can generate masks

### Example API Call

```bash
curl https://api.openai.com/v1/images/edit \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -F "image=@original.png" \
  -F "mask=@mask.png" \
  -F "prompt=Replace the sky with a sunset" \
  -F "size=1024x1024"
```

### Python Example

```python
from openai import OpenAI

client = OpenAI(api_key="your-key")

response = client.images.edit(
    image=open("original.png", "rb"),
    mask=open("mask.png", "rb"),
    prompt="Replace the background with a modern office",
    size="1024x1024",
    n=1
)

image_url = response.data[0].url
```

---

## Use Cases

### 1. **Document Processing**

- Invoice extraction and data entry
- Form processing automation
- Receipt digitization
- Contract analysis

**Example:**

```bash
ei vision invoice.pdf --prompt "Extract: invoice #, date, vendor, items with prices, subtotal, tax, total. Format as JSON."
```

### 2. **Accessibility**

- Generate alt-text for images
- Describe visual content for visually impaired users
- Create detailed image descriptions

**Example:**

```bash
ei vision photo.jpg --prompt "Generate descriptive alt-text suitable for screen readers"
```

### 3. **E-commerce**

- Product identification and categorization
- Quality control and defect detection
- Inventory management
- Product description generation

**Example:**

```bash
ei vision product.jpg --prompt "Identify brand, model, condition, and notable features. Suggest category and keywords."
```

### 4. **Content Creation**

- Social media caption generation
- Image-based storytelling
- Marketing copy from product images
- Visual content analysis

**Example:**

```bash
ei vision lifestyle.jpg --prompt "Generate 3 engaging social media captions with relevant hashtags"
```

### 5. **Education**

- Diagram and chart interpretation
- Math problem solving from images
- Science visualization analysis
- Historical photo analysis

**Example:**

```bash
ei vision math_problem.jpg --prompt "Solve this math problem step by step, showing all work"
```

### 6. **Quality Control**

- Manufacturing defect detection
- Product inspection
- Compliance verification
- Visual standards checking

**Example:**

```bash
ei vision pcb.jpg --prompt "Inspect this circuit board for defects: solder issues, component placement, traces"
```

### 7. **Healthcare** (with appropriate disclaimers)

- Medical image preliminary analysis
- Patient document processing
- Equipment status monitoring
- Facility compliance checks

**Example:**

```bash
ei vision xray.jpg --prompt "Educational analysis only: Identify visible structures and any notable features"
```

### 8. **Real Estate**

- Property description generation
- Room identification and measurement
- Feature highlighting
- Virtual tour enhancement

**Example:**

```bash
ei vision house.jpg --prompt "Describe this room for a real estate listing: style, features, condition, appeal"
```

---

## CLI Usage Examples

### Basic Image Analysis

```bash
# Simple description
ei vision photo.jpg

# Custom prompt
ei vision image.png --prompt "What is the main subject of this image?"

# Specific model
ei vision diagram.jpg --model gpt-5 --detail high

# JSON output
ei vision data.png --json
```

### OCR and Text Extraction

```bash
# Extract all text
ei vision document.jpg --prompt "Extract all text from this image"

# Structured data extraction
ei vision receipt.jpg --prompt "Extract: merchant, date, items, prices, total as JSON"

# Handwriting recognition
ei vision notes.jpg --prompt "Transcribe this handwritten text"
```

### Object Detection

```bash
# Count objects
ei vision shelf.jpg --prompt "Count and list all products visible"

# Identify specific items
ei vision scene.jpg --prompt "List all vehicles in this image with their colors"

# Spatial analysis
ei vision room.jpg --prompt "Describe the layout and position of furniture"
```

### Color and Style Analysis

```bash
# Color palette
ei vision artwork.jpg --model gpt-5-nano --prompt "What colors are present?"

# Style identification
ei vision painting.jpg --prompt "Identify the artistic style and influences"

# Mood assessment
ei vision photo.jpg --prompt "Describe the mood and atmosphere"
```

### Technical Analysis

```bash
# Chart interpretation
ei vision chart.png --prompt "Extract data points and trends from this chart"

# Diagram analysis
ei vision flowchart.png --prompt "Explain this flowchart step by step"

# Code screenshot
ei vision code.png --prompt "Explain what this code does"
```

### Comparison Tasks

```bash
# Before/after (requires multiple image support)
ei vision before.jpg --prompt "Describe changes compared to reference"

# Quality assessment
ei vision product.jpg --prompt "Rate quality: 1-10 with explanation"
```

---

## Advanced Techniques

### Multi-Step Reasoning

For complex analysis, break down the task:

```bash
ei vision complex.jpg --prompt "
Step 1: Identify all objects
Step 2: Analyze spatial relationships
Step 3: Determine the scene's purpose
Step 4: Provide overall interpretation
Use maximum reasoning depth."
```

### Contextual Analysis

Provide context for better results:

```bash
ei vision medical.jpg --prompt "
Context: This is a dental X-ray from a routine checkup
Patient: Adult, no prior dental issues
Task: Identify any abnormalities
Required: Professional terminology"
```

### Iterative Refinement

Use model output to refine prompts:

```bash
# First pass
ei vision image.jpg --prompt "What questions should I ask about this image?"

# Second pass (using questions from first)
ei vision image.jpg --prompt "[refined questions from previous output]"
```

### Detail Level Control

```bash
# Low detail (faster, cheaper)
ei vision thumbnail.jpg --detail low --model gpt-5-nano

# High detail (more accurate, higher cost)
ei vision detailed_diagram.jpg --detail high --model gpt-5 --max-tokens 2000
```

### Specialized Prompts by Domain

#### Medical

```bash
ei vision scan.jpg --prompt "Anatomical analysis: Identify structures, note abnormalities, use medical terminology"
```

#### Legal

```bash
ei vision contract.jpg --prompt "Extract: parties, dates, key terms, obligations. Flag concerning clauses."
```

#### Technical

```bash
ei vision schematic.jpg --prompt "Circuit analysis: components, connections, signal flow, potential issues"
```

#### Creative

```bash
ei vision art.jpg --prompt "Art critique: composition, technique, color theory, emotional impact, cultural context"
```

---

## Model Selection Guide

| Model           | Speed      | Cost        | Best For                                                       |
| --------------- | ---------- | ----------- | -------------------------------------------------------------- |
| **gpt-5**       | Standard   | $1.25/$10   | Complex analysis, detailed descriptions, high accuracy needs   |
| **gpt-5-mini**  | Fast       | $0.25/$2    | General purpose, balanced quality/cost, most use cases         |
| **gpt-5-nano**  | Ultra-fast | $0.05/$0.40 | Simple questions, real-time apps, high volume, color detection |
| **gpt-5-chat**  | Standard   | $1.25/$10   | Conversational context, storytelling, narrative descriptions   |
| **gpt-4o**      | Standard   | Medium      | Previous gen, stable, well-tested                              |
| **gpt-4-turbo** | Fast       | Medium      | Previous gen, faster alternative                               |
| **gpt-4o-mini** | Fast       | Low         | Previous gen, economical option                                |

---

## Tips for Best Results

### 1. Image Quality

- Use high-resolution images for detailed analysis
- Ensure good lighting and clear focus
- Crop to relevant area before analysis
- Use `--detail high` for complex images

### 2. Prompt Engineering

- Be specific about what you need
- Specify output format explicitly
- Provide context when relevant
- Use examples in prompts when possible

### 3. Token Management

- Default: 1000 tokens
- Simple queries: 500-1000 tokens
- Detailed analysis: 1500-2000 tokens
- Very complex: 2000+ tokens

### 4. Error Handling

- Check image format (PNG, JPEG, GIF, WebP)
- Verify file size limits
- Ensure clear image quality
- Try different detail levels if results are poor

### 5. Cost Optimization

- Use `gpt-5-nano` for simple tasks
- Use `--detail low` when appropriate
- Reduce `--max-tokens` for concise answers
- Batch similar images for efficiency

---

## Future Capabilities (Coming Soon)

Based on research, GPT-5 and future versions may include:

- **Video Analysis**: Frame-by-frame and temporal understanding
- **3D Image Understanding**: Depth perception and 3D reconstruction
- **Enhanced Inpainting**: More precise mask-based editing
- **Style Transfer**: Apply artistic styles to images
- **Image Variations**: Generate multiple variations of an image
- **Multi-Image Analysis**: Compare and contrast multiple images
- **Real-time Processing**: Faster analysis for video streams

---

## Resources

- **OpenAI Documentation**: https://help.openai.com/
- **GPT Image API Guide**: https://help.openai.com/en/articles/11128753
- **Code Examples**: https://cookbook.openai.com/
- **Community**: https://community.openai.com/

---

## Quick Reference Card

```bash
# Basic analysis
ei vision image.jpg

# Custom prompt
ei vision image.jpg --prompt "Your question here"

# Choose model
ei vision image.jpg --model gpt-5-mini

# High detail
ei vision image.jpg --detail high --max-tokens 2000

# JSON output
ei vision image.jpg --json

# Fast analysis
ei vision image.jpg --model gpt-5-nano --detail low

# OCR
ei vision document.jpg --prompt "Extract all text"

# Object counting
ei vision scene.jpg --prompt "Count all objects"

# Color analysis
ei vision image.jpg --prompt "List all colors"
```

---

_Last Updated: November 7, 2025_
