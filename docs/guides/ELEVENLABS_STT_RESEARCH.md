# ElevenLabs Speech-to-Text Research

## Overview

ElevenLabs offers Speech-to-Text (STT) capabilities alongside their well-known Text-to-Speech service. Based on research from their documentation and pricing pages.

---

## Pricing & Credits

### Credit System

ElevenLabs uses a **credit-based system** where credits can be used for either Text-to-Speech OR Speech-to-Text:

| Plan | Monthly Credits | Monthly Cost | STT Capability |
|------|-----------------|--------------|----------------|
| **Free** | 10,000 | $0 | ✅ Yes (with attribution) |
| **Starter** | 30,000 | $5 | ✅ Yes (commercial license) |
| **Creator** | 100,000 | $22 ($11 first month) | ✅ Yes |
| **Pro** | 500,000 | $99 | ✅ Yes |
| **Scale** | 2,000,000 | $330 | ✅ Yes |
| **Business** | 11,000,000 | $1,320 | ✅ Yes |
| **Enterprise** | Custom | Custom | ✅ Yes |

### Important Notes:

- **No separate STT pricing published** - uses same credit pool as TTS
- **Free tier requires attribution** (no commercial license)
- **Commercial use starts at $5/month** (Starter plan)
- Credits can be used for **either TTS or STT**, not both simultaneously

---

## API Capabilities

### Endpoints

Based on available documentation, ElevenLabs STT API provides:

**1. Create Transcription**
- `POST /v1/speech-to-text/transcripts`
- Submits audio file for transcription
- Returns transcription ID

**2. Get Transcript**
- `GET /v1/speech-to-text/transcripts/:transcription_id`
- Retrieves completed transcription
- Headers: `xi-api-key: YOUR_API_KEY`

**3. Delete Transcript**
- `DELETE /v1/speech-to-text/transcripts/:transcription_id`
- Removes transcript from system

### Response Format

```json
{
  "language_code": "string",
  "language_probability": 1.1,
  "text": "string",
  "words": [
    {
      "text": "string",
      "start": 1.1,
      "end": 1.1,
      "type": "word",
      "speaker_id": "string",
      "logprob": 1.1,
      "characters": [
        {
          "text": "string",
          "start": 1.1,
          "end": 1.1
        }
      ]
    }
  ],
  "channel_index": 1,
  "additional_formats": [
    {
      "requested_format": "string",
      "file_extension": "string",
      "content_type": "string",
      "is_base64_encoded": true,
      "content": "string"
    }
  ],
  "transcription_id": "string"
}
```

### Features

- ✅ **Word-level timestamps** (start/end times)
- ✅ **Character-level timestamps** (granular timing)
- ✅ **Language detection** (automatic with probability score)
- ✅ **Speaker identification** (speaker_id per word)
- ✅ **Multi-channel support** (channel_index)
- ✅ **Multiple output formats** (additional_formats array)
- ✅ **Confidence scores** (logprob per word)

---

## Python SDK

### Installation

```bash
pip install elevenlabs
```

### Current SDK Status

**⚠️ Speech-to-Text NOT in current Python SDK**

The ElevenLabs Python SDK (v2.22.0) currently supports:
- ✅ Text-to-Speech (TTS)
- ✅ Voice cloning
- ✅ Streaming audio
- ✅ Conversational AI agents
- ❌ **Speech-to-Text (NOT YET IMPLEMENTED)**

The SDK would need to be extended or we'd need to use direct HTTP API calls.

---

## Comparison: OpenAI Whisper vs ElevenLabs STT

| Feature | OpenAI Whisper | ElevenLabs STT | Winner |
|---------|---------------|----------------|--------|
| **Pricing** | $0.006/min | Unknown (credit-based) | ❓ Need to test |
| **Max file size** | 25MB | Unknown | ❓ |
| **Languages** | 50+ | Unknown | ❓ |
| **Timestamps** | Word-level | Word + Character level | 🏆 ElevenLabs |
| **Speaker ID** | No | Yes | 🏆 ElevenLabs |
| **Multi-channel** | No | Yes | 🏆 ElevenLabs |
| **Python SDK** | ✅ Full support | ❌ Not yet | 🏆 OpenAI |
| **Formats** | text/json/srt/vtt | Multiple via API | 🤝 Tie |
| **API maturity** | Stable, proven | Newer | 🏆 OpenAI |

---

## Cost Analysis

### OpenAI Whisper Current Costs

For a 25-minute video transcription:
- **Cost**: 25 min × $0.006/min = **$0.15**

### ElevenLabs Estimated Costs

**Problem**: No public per-minute STT pricing

**Reverse Engineering from Credits**:
- Free tier: 10k credits = "10 minutes of high-quality TTS"
- Therefore: **~1,000 credits per minute** for TTS

**Assumption**: If STT uses similar credit rates:
- 25-minute transcription = 25,000 credits
- **Free tier**: Depletes entire monthly allowance
- **Starter ($5/mo)**: 30k credits = only 1.2 transcriptions/month
- **Creator ($22/mo)**: 100k credits = 4 transcriptions/month

**Estimated per-minute cost** (if using Creator plan):
- $22 / 100 minutes = **$0.22/minute** (37× more expensive than OpenAI)

⚠️ **This is speculative** - actual STT credit consumption may be different

---

## Implementation Considerations

### Pros of ElevenLabs STT:
1. ✅ **Better metadata** - speaker ID, character-level timestamps
2. ✅ **Multi-channel support** - useful for interviews/conversations
3. ✅ **Already have ElevenLabs integration** - for TTS in codebase
4. ✅ **Unified credit pool** - simplifies billing if using both TTS and STT

### Cons of ElevenLabs STT:
1. ❌ **No Python SDK support yet** - need to implement HTTP calls manually
2. ❌ **Unknown pricing** - no transparency on STT credit consumption
3. ❌ **Likely more expensive** - based on credit estimates
4. ❌ **Less mature** - newer API, less documentation/examples
5. ❌ **Unknown file size limits** - no published maximums
6. ❌ **Unknown language support** - no published list

### Recommendation: **Stick with OpenAI Whisper**

**Reasons**:
1. **Proven cost-effectiveness**: $0.006/min is transparent and cheap
2. **Mature Python SDK**: Already integrated and working perfectly
3. **Known limitations**: 25MB, 50+ languages, clear docs
4. **Better for MVP**: No surprises, predictable costs
5. **Parallel processing**: Already optimized (3-5× speedup)

**When to Consider ElevenLabs STT**:
- Need speaker identification for multi-speaker audio
- Need character-level timestamps for precise alignment
- Already using lots of ElevenLabs credits for TTS (might as well use STT too)
- Multi-channel audio sources (stereo interviews)

---

## Implementation Effort

If we wanted to add ElevenLabs STT support:

### Required Work:
1. **Extend ElevenLabsAudioService** (~2 hours)
   - Add `speech_to_text()` method
   - Add `speech_to_text_async()` for parallel
   - HTTP client for API calls (no SDK yet)
   
2. **Add CLI command** (~1 hour)
   - `ei transcribe-audio --provider elevenlabs`
   - `ei transcribe-video --provider elevenlabs`
   
3. **Testing & Documentation** (~2 hours)
   - Test with various audio formats
   - Document credit consumption
   - Compare quality vs OpenAI
   
4. **Cost tracking** (~1 hour)
   - Monitor credit usage
   - Alert when approaching limits

**Total effort**: ~6 hours

---

## Existing Codebase

**Location**: `/cli/src/ei_cli/services/elevenlabs_service.py`

**Current capabilities**:
- ✅ Text-to-Speech (multiple models)
- ✅ Streaming TTS
- ✅ Voice cloning references
- ✅ 40+ pre-configured voices
- ❌ **No STT implementation**

**Integration readiness**: Medium
- API key already configured
- Client already initialized
- Would need to add HTTP calls manually

---

## Conclusion

**Current Status**: 
- ElevenLabs STT exists and has advanced features
- Not yet in Python SDK
- Pricing unclear but likely more expensive
- Better metadata (speakers, fine-grained timestamps)

**Recommendation**: 
**Continue using OpenAI Whisper** for now because:
- ✅ Already working perfectly
- ✅ Clear, cheap pricing ($0.006/min)
- ✅ Mature SDK and parallel processing
- ✅ Sufficient features for most use cases

**Future consideration**:
- Monitor ElevenLabs Python SDK for STT support
- Re-evaluate if they publish transparent per-minute pricing
- Consider for specialized use cases (speaker ID, multi-channel)

---

## Research Sources

1. **ElevenLabs Pricing**: https://elevenlabs.io/pricing
2. **ElevenLabs API Reference**: https://elevenlabs.io/docs/api-reference/speech-to-text
3. **ElevenLabs Python SDK**: https://github.com/elevenlabs/elevenlabs-python
4. **Current Implementation**: `/cli/src/ei_cli/services/elevenlabs_service.py`

---

*Research completed: November 10, 2025*
*Recommendation: Stick with OpenAI Whisper for transcription*
