# EverydayAI CLI - Documentation

This directory contains organized documentation for the EverydayAI CLI toolkit.

## Directory Structure

### `/agents/` - Agent Integration Documentation

Strategic documentation for integrating the CLI with OpenAI Agents SDK:

- **OPENAI_AGENTS_INTEGRATION.md** - Comprehensive integration roadmap with 8
  opportunities
- **QA_AGENTS_ANALYSIS.md** - Retrospective analysis of QA agents system and
  patterns

### `/guides/` - Reference Guides

How-to guides and reference documentation:

- **COOKIE_EXPORT_GUIDE.md** - Export cookies for authenticated video downloads
- **ELEVENLABS_STT_RESEARCH.md** - ElevenLabs speech-to-text research
- **TESTING.md** - Testing strategy and guidelines
- **COVERAGE_BASELINE.md** - Code coverage baseline (90.12%)

### `/sprints/` - Sprint Archive

Historical sprint documentation (completed work):

- SPRINT_1_COMPLETE.md through SPRINT_5_COMPLETE.md
- TRANSCRIPTION_REFACTOR_SPRINTS.md
- TRANSCRIPTION_SPRINT_2_COMPLETE.md

### `/archive/` - Historical Documentation

Legacy documentation preserved for context:

- Technical debt audits and analyses
- Manual QA reports and test workspaces
- Real-world test results
- Optimization summaries

## Active Documentation (Root Level)

The following documentation remains in the CLI root directory for active
development:

- **README.md** - Main project documentation
- **ARCHITECTURE.md** - System architecture and design
- **ROADMAP.md** - Future development roadmap
- **PLAN.md** - Current development plan

## Quick Links

### For Users

- [Main README](../README.md) - Getting started, installation, usage
- [Testing Guide](guides/TESTING.md) - How to run tests

### For Developers

- [Architecture](../ARCHITECTURE.md) - System design and patterns
- [Development Roadmap](../ROADMAP.md) - Upcoming features
- [Coverage Baseline](guides/COVERAGE_BASELINE.md) - Quality metrics

### For Agent Integration

- [OpenAI Agents Integration](agents/OPENAI_AGENTS_INTEGRATION.md) - Complete
  integration plan
- [QA Agents Analysis](agents/QA_AGENTS_ANALYSIS.md) - Lessons from prior agent
  work

## Documentation Standards

When adding new documentation:

1. **Guides** - How-to content, tutorials, reference material → `/guides/`
2. **Agents** - Agent integration, orchestration, patterns → `/agents/`
3. **Sprints** - Completed sprint summaries → `/sprints/`
4. **Archive** - Historical context, deprecated docs → `/archive/`
5. **Root** - Active planning and architecture → CLI root

---

**Last Updated:** November 10, 2025  
**Status:** Production-ready, preparing for agent integration phase
