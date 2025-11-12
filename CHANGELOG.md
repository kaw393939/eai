# Changelog

All notable changes to the EverydayAI CLI project will be documented in this
file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Planned

- OpenAI Agents SDK integration for multi-agent workflows
- Plugin marketplace and discovery
- Workflow chain orchestration
- Batch processing for multiple files
- Enhanced image tools with better quality

## [0.2.0] - 2025-11-11

### Added

- **Plugin Architecture**: Extensible command system with dynamic discovery
  - `CommandPlugin` protocol with `@runtime_checkable` decorator
  - `BaseCommandPlugin` abstract base class
  - `PluginLoader` for automatic plugin discovery
  - Support for third-party plugins via entry points (`eai.plugins`)
- **Manual Testing**: Comprehensive end-to-end validation of all commands
  - Generated test media (images, audio, video transcripts)
  - Validated all 10 commands working correctly
  - YouTube integration tested with real videos
- **Test Coverage**: Increased from 25% to 64% (559 tests passing)
- **Documentation**: Updated for plugin system and new architecture

### Changed

- **BREAKING**: Migrated all commands from hardcoded registration to plugin system
  - Commands now loaded dynamically via `PluginLoader`
  - `app.py` simplified from 12 imports to 3 lines of plugin loading
  - All commands converted to plugin format with `plugin = PluginClass()` pattern
- **Architecture**: Cleaner separation of concerns
  - `/cli/commands/` → `/plugins/` directory structure
  - Each command is now a self-contained plugin module
  - Dynamic command registration replaces static imports

### Removed

- **crop command**: Removed due to poor reliability and quality issues
- **remove_bg command**: Removed due to inconsistent results
- `/cli/commands/` directory: Replaced by `/plugins/` architecture

### Fixed

- All test imports updated from `ei_cli.cli.commands` to `ei_cli.plugins`
- Mock patch paths corrected for new plugin locations
- Package installation issues with .pth file generation

### Technical

- 559 tests passing, 41 skipped (image streaming not implemented)
- Full plugin system with protocol-based design
- Entry point support for third-party extensions
- Comprehensive manual testing completed

## [0.1.1] - 2025-11-11

### Changed

- **BREAKING**: Changed CLI command from `ei` to `eai` (EverydayAI)
  - Better brand alignment and less name collision
  - More descriptive and memorable command name
  - All documentation updated to reflect new command

### Fixed

- Updated all examples and documentation to use `eai` command

## [0.1.0] - 2025-11-11

### Added

- Initial PyPI release as `everydayai-cli`
- Migrated to PEP 621 format in pyproject.toml
- Fixed all Poetry deprecation warnings (12 → 0)

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
