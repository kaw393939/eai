# Changelog

All notable changes to the EverydayAI CLI project will be documented in this
file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Planned

- OpenAI Agents SDK integration for multi-agent workflows
- Content triage system for batch processing optimization
- Sequential tool chain orchestration
- Cross-media pattern detection
- Session memory for conversation context

## [0.3.0] - 2025-11-10

### Added

- Comprehensive documentation reorganization
  - Created `/docs/agents/` for agent integration plans
  - Created `/docs/guides/` for reference documentation
  - Created `/docs/sprints/` for historical sprint summaries
  - Created `/docs/archive/` for legacy documentation
- Agent integration research and analysis
  - `OPENAI_AGENTS_INTEGRATION.md` - Complete integration roadmap
  - `QA_AGENTS_ANALYSIS.md` - Retrospective of prior agent work
- Documentation index at `docs/README.md`

### Changed

- Moved completed sprint documentation to archives
- Moved technical debt audits to archives
- Organized reference guides into dedicated directory
- Updated `.gitignore` to exclude build artifacts and test outputs

### Removed

- Temporary test audio files from root directory
- Obsolete manual QA test files
- Duplicate documentation files

## [0.2.0] - 2025-11-09

### Added

- Parallel transcription processing for videos
- Multi-provider AI support (OpenAI, Anthropic, ElevenLabs)
- Comprehensive test coverage (90.12%)
- 14 CLI commands for multimedia processing
- 11 service modules with factory pattern
- Progress tracking and error handling
- YouTube video download support
- Multi-vision analysis capabilities

### Fixed

- Audio chunking for long transcriptions
- Error handling in transcription pipeline
- File format validation
- Progress bar accuracy

## [0.1.0] - 2025-11-01

### Added

- Initial CLI toolkit structure
- Basic transcription functionality
- Text-to-speech generation
- Image analysis capabilities
- Configuration management
- Basic test suite

---

## Version History Context

### Sprint Completion Summary

- **Sprint 1-5**: Core CLI development, transcription optimization, multi-modal
  support
- **Sprint 6-7**: ElevenLabs integration, advanced vision features
- All sprint documentation preserved in `docs/sprints/`

### Technical Milestones

- **90.12% test coverage** achieved (281 tests)
- **11,739 lines of code** across 44 Python files
- **14 production-ready commands** with JSON output
- **Grade: A- (87.6/100)** in comprehensive evaluation

### Development Principles

- Agent-native design (JSON output, scriptability)
- Production readiness focus (error handling, progress tracking)
- Multi-provider flexibility (OpenAI, Anthropic, ElevenLabs)
- Comprehensive documentation

---

## Upgrade Guide

### From 0.2.0 to 0.3.0

No breaking changes. Documentation has been reorganized:

- Active docs remain in root: `README.md`, `ARCHITECTURE.md`, `ROADMAP.md`,
  `PLAN.md`
- Historical docs moved to `docs/` subdirectories
- All CLI functionality unchanged

### Configuration

No configuration changes required in this release.

---

## Links

- [Documentation](./README.md)
- [Architecture](./ARCHITECTURE.md)
- [Development Roadmap](./ROADMAP.md)
- [Agent Integration Plan](./docs/agents/OPENAI_AGENTS_INTEGRATION.md)

---

**Next Release Target**: 0.4.0 - OpenAI Agents SDK Integration (Q1 2026)
