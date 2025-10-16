# Documentation Hub

**Welcome to the Memory System Documentation**

Last Updated: 2025-10-16

---

## 📚 Documentation Structure

This documentation is organized by audience and use case:

```
docs_new/
├── getting-started/     # New developers: Setup, quickstart, first contribution
├── architecture/        # Understanding system design and structure
├── development/         # Day-to-day development workflows
├── api/                 # API documentation and examples
├── database/            # Schema, models, migrations
├── testing/             # Testing strategy and guides
└── reference/           # Configuration, heuristics, glossary
```

---

## 🚀 Getting Started

**New to the project?** Start here:

1. [**QUICKSTART.md**](getting-started/QUICKSTART.md) - Get running in 5 minutes
2. [**OVERVIEW.md**](architecture/OVERVIEW.md) - Understand the architecture
3. [**WORKFLOW.md**](development/WORKFLOW.md) - Make your first contribution

---

## 📖 Documentation by Role

### For New Developers

**Day 1: Get Running**
1. [QUICKSTART.md](getting-started/QUICKSTART.md) - Installation and first API call
2. [architecture/OVERVIEW.md](architecture/OVERVIEW.md) - How the system is structured

**Week 1: Understand the System**
1. [database/SCHEMA.md](database/SCHEMA.md) - Database tables and relationships
2. [api/ENDPOINTS.md](api/ENDPOINTS.md) - API endpoints and examples
3. [testing/GUIDE.md](testing/GUIDE.md) - How to write and run tests

**Week 2: Start Contributing**
1. [development/WORKFLOW.md](development/WORKFLOW.md) - Development workflow
2. [development/DEBUGGING.md](development/DEBUGGING.md) - Common issues and solutions
3. [reference/GLOSSARY.md](reference/GLOSSARY.md) - Key terms and concepts

### For Experienced Developers

**Understanding Design**:
- [../docs/vision/VISION.md](../docs/vision/VISION.md) - Philosophical foundation (PROTECTED)
- [../docs/vision/DESIGN_PHILOSOPHY.md](../docs/vision/DESIGN_PHILOSOPHY.md) - Design decision framework (PROTECTED)
- [architecture/LAYERS.md](architecture/LAYERS.md) - Layer responsibilities in detail
- [architecture/PATTERNS.md](architecture/PATTERNS.md) - Design patterns used

**Implementation Details**:
- [database/MIGRATIONS.md](database/MIGRATIONS.md) - How to create and apply migrations
- [development/TESTING_PATTERNS.md](development/TESTING_PATTERNS.md) - Testing best practices
- [api/AUTHENTICATION.md](api/AUTHENTICATION.md) - Auth and security

### For Architects

**System Design**:
- [../CLAUDE.md](../CLAUDE.md) - Development philosophy and standards (PROTECTED)
- [../ProjectDescription.md](../ProjectDescription.md) - Project overview (PROTECTED)
- [architecture/DECISIONS.md](architecture/DECISIONS.md) - Key architectural decisions
- [reference/TECH_STACK.md](reference/TECH_STACK.md) - Technology choices and rationale

**Historical Context**:
- [../archive/](../archive/) - Historical documentation (preserved for context)

---

## 🔍 Quick Reference

### Common Tasks

| Task | Documentation |
|------|---------------|
| Install and run | [QUICKSTART.md](getting-started/QUICKSTART.md) |
| Make API call | [api/ENDPOINTS.md](api/ENDPOINTS.md) |
| Understand architecture | [architecture/OVERVIEW.md](architecture/OVERVIEW.md) |
| Write a test | [testing/GUIDE.md](testing/GUIDE.md) |
| Create migration | [database/MIGRATIONS.md](database/MIGRATIONS.md) |
| Debug an issue | [development/DEBUGGING.md](development/DEBUGGING.md) |
| Deploy system | [deployment/GUIDE.md](deployment/GUIDE.md) |

### Key Concepts

| Concept | Explanation | Documentation |
|---------|-------------|---------------|
| **Hexagonal Architecture** | Domain isolated from infrastructure | [architecture/OVERVIEW.md](architecture/OVERVIEW.md) |
| **Entity Resolution** | "Acme" → `customer:uuid` | [architecture/ENTITY_RESOLUTION.md](architecture/ENTITY_RESOLUTION.md) |
| **Semantic Memory** | Facts extracted from conversations | [database/SCHEMA.md](database/SCHEMA.md) |
| **Multi-Signal Retrieval** | Contextual memory retrieval | [architecture/RETRIEVAL.md](architecture/RETRIEVAL.md) |
| **Confidence Decay** | Epistemic humility over time | [reference/CONFIDENCE.md](reference/CONFIDENCE.md) |

---

## 📊 Code Statistics

**Production Code**: ~12,000 lines
- Domain: 6,000 lines (entities, services, ports, value objects)
- Application: 1,000 lines (use cases, DTOs)
- API: 1,700 lines (routes, models)
- Infrastructure: 3,000 lines (repositories, LLM, embeddings)

**Tests**: 337 test functions across 26 files

**Database**: 10 tables (PostgreSQL + pgvector)

**API Endpoints**: 3 main routes (chat, consolidation, procedural)

---

## 🏗️ Architecture at a Glance

```
API Layer (FastAPI)
    ↓ depends on
Application Layer (Use Cases + DTOs)
    ↓ depends on
Domain Layer (Pure Python - business logic)
    ↓ depends on (via ports/interfaces)
Infrastructure Layer (PostgreSQL, OpenAI, etc.)
```

**Key Principles**:
- Hexagonal Architecture (ports & adapters)
- Domain-Driven Design (rich domain models)
- Async-First (all I/O operations)
- Type Safety (100% type coverage)
- Dependency Injection

---

## 🧪 Testing Philosophy

**Test Pyramid**: 70% Unit | 20% Integration | 10% E2E

**Coverage Targets**:
- Domain: 90%+
- API: 80%+
- Infrastructure: 70%+

**Current Status**: 198/198 tests passing ✅

---

## 🗂️ Legacy Documentation

**Historical documentation** preserved in:
- `../docs/` - Original documentation (some still relevant)
- `../archive/` - Archived historical docs

**Protected Files** (untouched, still canonical):
- [../docs/vision/VISION.md](../docs/vision/VISION.md) - System vision
- [../docs/vision/DESIGN_PHILOSOPHY.md](../docs/vision/DESIGN_PHILOSOPHY.md) - Design framework
- [../CLAUDE.md](../CLAUDE.md) - Development standards
- [../ProjectDescription.md](../ProjectDescription.md) - Project overview

---

## 🔗 External Resources

- **API Documentation**: http://localhost:8000/docs (when running)
- **ReDoc**: http://localhost:8000/redoc
- **Health Check**: http://localhost:8000/api/v1/health

---

## 📝 Documentation Standards

### When Creating New Documentation

1. **Focus on "what is"** - Document actual implementation, not aspirational features
2. **Code examples** - Show real code from the codebase
3. **Clear structure** - Use headings, code blocks, tables
4. **Practical** - Answer "how do I..." questions
5. **Accurate** - Verify against actual code

### When Updating Documentation

1. **Check accuracy** - Ensure docs match current implementation
2. **Update timestamps** - Note when docs were last updated
3. **Preserve history** - Archive outdated docs, don't delete
4. **Link related docs** - Cross-reference related documentation

---

## 🤝 Contributing

Found inaccurate documentation? Please:
1. Check if docs match actual code
2. Update docs to reflect reality
3. Submit PR with clear description
4. Reference which code you verified against

---

## 📞 Getting Help

- **Documentation Issues**: Create issue with "docs:" prefix
- **Code Questions**: Check relevant documentation first
- **Philosophy Questions**: Read [VISION.md](../docs/vision/VISION.md) and [CLAUDE.md](../CLAUDE.md)

---

**Ready to start?** Begin with [QUICKSTART.md](getting-started/QUICKSTART.md) 🚀
