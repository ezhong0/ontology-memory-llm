# Documentation Structure

This directory contains all design and planning documentation for the Ontology-Aware Memory System.

## Directory Organization

### 📖 `/vision` - Vision and Philosophy
Foundational documents defining the system's purpose, principles, and design philosophy.

- **VISION.md** - System vision, core metaphor ("experienced colleague"), and guiding principles
- **DESIGN_PHILOSOPHY.md** - Design decision framework, Three Questions, normalization guidelines

**Start here** if you're new to the project.

### 🏗️ `/design` - Technical Design Documents
Detailed technical specifications for each subsystem.

- **DESIGN.md** - Database schema, core tables, and data model
- **LIFECYCLE_DESIGN.md** - Memory states, reinforcement, decay, and consolidation
- **ENTITY_RESOLUTION_DESIGN.md** - Five-stage entity resolution algorithm
- **RETRIEVAL_DESIGN.md** - Multi-signal retrieval and ranking strategies
- **LEARNING_DESIGN.md** - Phase 2/3 learning and adaptation features
- **API_DESIGN.md** - REST API contracts, endpoints, and SDK design

**Read these** when implementing specific subsystems.

### ✅ `/quality` - Quality Assurance
Quality evaluation and production readiness assessments.

- **QUALITY_EVALUATION.md** - Comprehensive design quality evaluation (9.74/10)
- **IMPLEMENTATION_READINESS.md** - Production readiness report and Phase 1 checklist

**Consult these** before beginning implementation and at milestones.

### 📚 `/reference` - Reference Materials
Supporting documentation and calibration references.

- **HEURISTICS_CALIBRATION.md** - All 43 numeric parameters with Phase 2 tuning requirements
- **Model_Strategy.md** - LLM model selection and usage strategy

**Use these** during implementation for parameter values and configuration.

## Reading Paths

### For Product Managers
1. `/vision/VISION.md` - Understand the system vision
2. `/design/API_DESIGN.md` - See user-facing capabilities
3. `/quality/IMPLEMENTATION_READINESS.md` - Review phase roadmap and timeline

### For Engineers
1. `/vision/DESIGN_PHILOSOPHY.md` - Understand design principles
2. `/design/DESIGN.md` - Study database schema
3. Relevant subsystem documents in `/design/`
4. `/reference/HEURISTICS_CALIBRATION.md` - Configuration values

### For Architects
1. `/vision/VISION.md` + `/vision/DESIGN_PHILOSOPHY.md` - Philosophy
2. `/design/DESIGN.md` - Core data model
3. All documents in `/design/` - Subsystem interactions
4. `/quality/QUALITY_EVALUATION.md` - Design decisions and tradeoffs

### For QA/Testing
1. `/design/API_DESIGN.md` - API contracts and error handling
2. `/quality/IMPLEMENTATION_READINESS.md` - Phase 1 scope and testing requirements
3. `/reference/HEURISTICS_CALIBRATION.md` - Expected parameter behaviors

## Design Quality

**Overall Score**: 9.74/10 (Exceptional)
**Philosophy Alignment**: 97%
**Status**: ✅ Production-ready for Phase 1 implementation

## Key Principles

From `DESIGN_PHILOSOPHY.md`:
> "Complexity is not the enemy. Unjustified complexity is the enemy. Every piece of this system should earn its place by serving the vision."

**Three Questions Framework** (ask for every design decision):
1. Which vision principle does this serve?
2. Does this contribute enough to justify its cost?
3. Is this the right phase for this complexity?

## Phase Roadmap

**Phase 1 (Essential)**: Core conversation interface, entity resolution, retrieval, basic lifecycle
**Phase 2 (Enhancements)**: Learning from operational data, conflict management, streaming
**Phase 3 (Advanced Learning)**: Meta-memories, cross-user patterns, continuous adaptation

See `IMPLEMENTATION_READINESS.md` for detailed phase breakdown.

## Document Revision History

All documents revised and aligned with vision/philosophy on 2024-01-15.

**Latest Updates**:
- Added phase tags to all API endpoints
- Created HEURISTICS_CALIBRATION.md consolidating all numeric parameters
- Completed QUALITY_EVALUATION.md and IMPLEMENTATION_READINESS.md

## Questions?

For design clarifications, refer to the Three Questions Framework in `DESIGN_PHILOSOPHY.md`.
For implementation details, consult the specific subsystem document in `/design/`.
