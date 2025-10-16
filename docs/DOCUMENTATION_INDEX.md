# Documentation Index

**Last Updated**: 2025-10-16
**Purpose**: Guide to navigating the documentation structure

---

## Quick Start

**New to the project?** Start here:
1. [ProjectDescription.md](../ProjectDescription.md) - What this project does
2. [docs/vision/VISION.md](vision/VISION.md) - Philosophical foundation
3. [docs/design/DESIGN.md](design/DESIGN.md) - Complete system specification
4. [docs/demo/QUICK_START.md](demo/QUICK_START.md) - Run the demo in 5 minutes

**Implementing a feature?** Check:
- [docs/quality/PHASE1_ROADMAP.md](quality/PHASE1_ROADMAP.md) - Implementation roadmap
- [docs/reference/HEURISTICS_CALIBRATION.md](reference/HEURISTICS_CALIBRATION.md) - Tunable parameters
- [docs/quality/TESTING_PHILOSOPHY.md](quality/TESTING_PHILOSOPHY.md) - How to test

**Current state?** See:
- [docs/implementation/FINAL_QUALITY_METRICS.md](implementation/FINAL_QUALITY_METRICS.md) - Latest metrics
- [docs/implementation/CODE_QUALITY_COMPLETION_REPORT.md](implementation/CODE_QUALITY_COMPLETION_REPORT.md) - Quality improvements

---

## Documentation Structure

### 📋 Root Documentation

**Location**: `/ProjectDescription.md`, `/CLAUDE.md`, `/README.md`

- **[ProjectDescription.md](../ProjectDescription.md)**: High-level project overview
- **[CLAUDE.md](../CLAUDE.md)**: Development philosophy and coding standards (1,000+ lines)
- **[README.md](../README.md)**: Getting started, setup, commands

---

### 🎯 Vision & Philosophy (`docs/vision/`)

**Purpose**: Why this system exists and how it should think

- **[VISION.md](vision/VISION.md)** (720 lines)
  - Memory philosophy (correspondence vs contextual truth)
  - 6-layer memory architecture
  - Core principles: Epistemic humility, provenance, graceful forgetting
  - Start here for philosophical foundation

- **[DESIGN_PHILOSOPHY.md](vision/DESIGN_PHILOSOPHY.md)** (323 lines)
  - Three Questions Framework: Which principle? Enough contribution? Right phase?
  - Decision-making guidelines
  - Complexity justification

---

### 🏗️ Design Specifications (`docs/design/`)

**Purpose**: Complete system design with algorithms, schemas, and rationale

**Core Specification**:
- **[DESIGN.md](design/DESIGN.md)** (1,509 lines)
  - **THE authoritative specification**
  - Complete database schema (10 tables)
  - All algorithms with pseudocode
  - Justification for every decision
  - Cross-references to vision principles

**Specialized Design Docs**:
- **[API_DESIGN.md](design/API_DESIGN.md)**: Request/response models for all endpoints
- **[LIFECYCLE_DESIGN.md](design/LIFECYCLE_DESIGN.md)**: Memory state transitions, confidence decay, reinforcement
- **[RETRIEVAL_DESIGN.md](design/RETRIEVAL_DESIGN.md)**: Multi-signal scoring formula and strategy weights
- **[ENTITY_RESOLUTION_DESIGN_V2.md](design/ENTITY_RESOLUTION_DESIGN_V2.md)**: 5-stage hybrid resolution algorithm
- **[LLM_INTEGRATION_STRATEGY.md](design/LLM_INTEGRATION_STRATEGY.md)**: Surgical LLM usage (where and why)
- **[LEARNING_DESIGN.md](design/LEARNING_DESIGN.md)**: Procedural memory extraction (Phase 1D+)
- **[ARCHIVE_DESIGN_EVOLUTION.md](design/ARCHIVE_DESIGN_EVOLUTION.md)**: Historical design changes

---

### 🛠️ Implementation (`docs/implementation/`)

**Purpose**: Current implementation state, progress tracking, quality reports

**Current State** (Most Recent):
- **[FINAL_QUALITY_METRICS.md](implementation/FINAL_QUALITY_METRICS.md)**: Production readiness assessment
  - Code quality: A+ (95/100)
  - Test status: 198/198 passing
  - Metrics breakdown by category

- **[CODE_QUALITY_COMPLETION_REPORT.md](implementation/CODE_QUALITY_COMPLETION_REPORT.md)**: Quality improvement details
  - Phase 2: God Object Refactoring (683 → 277 lines)
  - Phase 3: Code Style (1,284 auto-fixes)
  - Phase 4: Exception Chaining (13 fixes)
  - Before/after comparisons

- **[REMAINING_LINTING_ANALYSIS.md](implementation/REMAINING_LINTING_ANALYSIS.md)**: Linting issue categorization
  - 107 intentional patterns (framework conventions)
  - 18 optional improvements
  - 3 quick wins (now fixed)

**Historical Documentation** (Archived):
- See `docs/archive/implementation/` for:
  - Phase completion reports (1A, 1B, 1C, 1D)
  - Progress summaries (Week 1, Week 2)
  - Code reviews (multiple iterations)
  - Strategic planning docs

---

### 🎮 Demo System (`docs/demo/`)

**Purpose**: Standalone demo application for testing and showcasing

**User Guides**:
- **[QUICK_START.md](demo/QUICK_START.md)**: Run the demo in 5 minutes
- **[CHAT_INTERFACE_GUIDE.md](demo/CHAT_INTERFACE_GUIDE.md)**: How to use the chat interface

**Technical**:
- **[DEMO_ARCHITECTURE.md](demo/DEMO_ARCHITECTURE.md)**: Demo system design
- **[DEMO_ISOLATION_GUARANTEES.md](demo/DEMO_ISOLATION_GUARANTEES.md)**: How demo is isolated from main system

**Historical Documentation** (Archived):
- See `docs/archive/demo/` for:
  - Implementation roadmaps
  - Phase enhancement plans
  - Weekly demo readmes

---

### 📊 Quality Assurance (`docs/quality/`)

**Purpose**: Testing philosophy, roadmaps, quality standards

**Active Documents**:
- **[PHASE1_ROADMAP.md](quality/PHASE1_ROADMAP.md)**: 8-week implementation plan
  - Phase 1A: Entity Resolution
  - Phase 1B: Semantic Extraction
  - Phase 1C: Intelligence (Domain Augmentation)
  - Phase 1D: Learning (Procedural Memory)

- **[TESTING_PHILOSOPHY.md](quality/TESTING_PHILOSOPHY.md)**: How to write and structure tests
  - Test pyramid: 70% unit | 20% integration | 10% E2E
  - Given-When-Then style
  - Coverage targets (90% domain, 80% API, 70% infrastructure)

**Historical Documentation** (Archived):
- See `docs/archive/quality/` for:
  - Design alignment analysis
  - Testing gap analysis
  - Quality evaluations

---

### 📚 Reference (`docs/reference/`)

**Purpose**: Lookup documentation for parameters and configurations

- **[HEURISTICS_CALIBRATION.md](reference/HEURISTICS_CALIBRATION.md)**: All 43 tunable parameters
  - Decay rates, thresholds, similarity cutoffs
  - Rationale for each value
  - Phase 2 calibration plan

- **[Model_Strategy.md](reference/Model_Strategy.md)**: LLM model selection strategy
  - When to use gpt-4o vs gpt-3.5-turbo
  - Cost vs accuracy tradeoffs

---

### 📁 Archive (`docs/archive/`)

**Purpose**: Historical documentation preserved for context

**Contents**:
- `archive/implementation/`: Phase progress reports, code reviews, completion summaries
- `archive/design/`: Old design comparisons, architecture recommendations
- `archive/demo/`: Implementation roadmaps, enhancement plans
- `archive/quality/`: Testing gap analysis, design alignment docs
- `archive/week0/`: Initial domain database integration research

**Why Archive?**
- Context for understanding decisions
- Tracking how design evolved
- Reference for "why we changed X"
- Not actively maintained, but preserved

---

## Documentation Standards

### Markdown Style

- **Headings**: Use `#` for title, `##` for major sections, `###` for subsections
- **Code blocks**: Always specify language (```python, ```sql, ```bash)
- **Links**: Relative links within docs, absolute for external
- **Tables**: For comparisons, metrics, parameters

### When to Create New Docs

**Create new doc when**:
- Introducing new architectural layer
- Designing new major feature (Phase 1C, 1D, etc.)
- Documenting new API surface
- Recording major design decision

**DON'T create new doc for**:
- Progress updates (update existing completion reports)
- Bug fixes (document in code comments)
- Minor clarifications (edit existing docs)
- Redundant information (check if existing doc can be updated)

### When to Update vs Archive

**Update existing doc when**:
- Design evolves incrementally
- Adding clarifications
- Fixing errors
- Current phase progress

**Archive doc when**:
- Design has fundamentally changed (old doc no longer accurate)
- Progress doc is superseded by newer summary
- Multiple docs cover same topic redundantly
- Historical context valuable but not current

---

## Documentation Map by Audience

### For New Developers

**Day 1: Orientation**
1. ProjectDescription.md - What is this?
2. vision/VISION.md - Why does it exist?
3. CLAUDE.md - How do we build?

**Week 1: Core Concepts**
1. design/DESIGN.md - Complete specification
2. quality/PHASE1_ROADMAP.md - Implementation plan
3. reference/HEURISTICS_CALIBRATION.md - Configuration

### For Implementers

**Before starting feature**:
- Check design/DESIGN.md for specification
- Check quality/PHASE1_ROADMAP.md for phase scope
- Check implementation/FINAL_QUALITY_METRICS.md for current state

**During implementation**:
- Follow CLAUDE.md standards
- Reference design/*.md for algorithms
- Use quality/TESTING_PHILOSOPHY.md for tests

### For Reviewers

**Code quality check**:
- implementation/FINAL_QUALITY_METRICS.md - Current metrics
- implementation/CODE_QUALITY_COMPLETION_REPORT.md - Recent improvements
- CLAUDE.md - Coding standards

**Design alignment check**:
- design/DESIGN.md - Does implementation match spec?
- vision/DESIGN_PHILOSOPHY.md - Does it serve vision principles?

---

## Recent Changes (2025-10-16)

### Documentation Cleanup

**Archived**:
- 16 implementation progress/completion docs → `archive/implementation/`
- 5 demo planning docs → `archive/demo/`
- 2 design comparison docs → `archive/design/`
- 5 quality evaluation docs → `archive/quality/`

**Kept (Active)**:
- 2 vision docs (VISION.md, DESIGN_PHILOSOPHY.md)
- 7 design specs (DESIGN.md, API_DESIGN.md, LIFECYCLE_DESIGN.md, etc.)
- 3 implementation reports (most recent quality metrics)
- 4 demo guides (QUICK_START, DEMO_ARCHITECTURE, etc.)
- 2 quality docs (PHASE1_ROADMAP, TESTING_PHILOSOPHY)
- 2 reference docs (HEURISTICS_CALIBRATION, Model_Strategy)

**Result**: 20 active docs (down from 60+), clear structure, historical context preserved

---

## Contact & Feedback

**Found outdated docs?** Update or archive them.
**Need clarification?** Check design/DESIGN.md first, then ask.
**Adding new feature?** Follow Three Questions Framework (vision/DESIGN_PHILOSOPHY.md).

---

*Documentation is living. Keep it current, archive the old, preserve context.*
