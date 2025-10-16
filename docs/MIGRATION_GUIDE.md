# Documentation Migration Guide

**Date**: 2025-10-16
**Action**: Complete documentation overhaul based on actual codebase

---

## What Happened?

The documentation has been completely reorganized to:
1. **Reflect actual implementation** (not aspirational features)
2. **Be organized by audience** (new developers, experienced developers, architects)
3. **Be practical and actionable** (how-to guides, not just theory)
4. **Remove duplication** (100+ docs → focused set)

---

## New Documentation Structure

```
docs/
├── README.md                    # Documentation hub (start here)
├── getting-started/
│   └── QUICKSTART.md            # 5-minute setup guide
├── architecture/
│   └── OVERVIEW.md              # System architecture explained
├── development/
│   └── WORKFLOW.md              # Day-to-day development (TBD)
├── api/
│   └── ENDPOINTS.md             # API documentation (TBD)
├── database/
│   └── SCHEMA.md                # Database tables (TBD)
├── testing/
│   └── GUIDE.md                 # Testing guide (TBD)
├── reference/
│   └── GLOSSARY.md              # Key terms (TBD)
└── vision/
    ├── VISION.md                # ✅ PROTECTED - Philosophical foundation
    └── DESIGN_PHILOSOPHY.md     # ✅ PROTECTED - Design framework
```

**Root Protected Files** (untouched):
- `/CLAUDE.md` - Development standards and philosophy
- `/ProjectDescription.md` - High-level project overview

---

## Where Did Everything Go?

### ✅ Protected Files (Unchanged)

These files were NOT modified (per your request):

| File | Location | Purpose |
|------|----------|---------|
| `VISION.md` | `docs/vision/` | Philosophical foundation, memory philosophy |
| `DESIGN_PHILOSOPHY.md` | `docs/vision/` | Three Questions Framework, design decisions |
| `CLAUDE.md` | Root `/` | Development philosophy, coding standards |
| `ProjectDescription.md` | Root `/` | High-level project overview |

### 📦 Archived Documentation

**All other documentation** moved to `archive_legacy_docs/`:

| Original Location | Archived To | Reason |
|-------------------|-------------|--------|
| `docs/design/` | `archive_legacy_docs/design/` | Mix of aspirational and implemented features |
| `docs/demo/` | `archive_legacy_docs/demo/` | Demo-specific docs (still accessible) |
| `docs/implementation/` | `archive_legacy_docs/implementation/` | Historical progress reports |
| `docs/quality/` | `archive_legacy_docs/quality/` | Quality assessment docs |
| `docs/reference/` | `archive_legacy_docs/reference/` | Heuristics, model strategy (will extract useful parts) |
| Root `docs/*.md` | `archive_legacy_docs/` | Miscellaneous docs |

### 📝 New Documentation

**Created from scratch** based on actual codebase:

| File | Purpose | Status |
|------|---------|--------|
| `docs/README.md` | Documentation hub, quick navigation | ✅ Complete |
| `docs/getting-started/QUICKSTART.md` | 5-minute setup guide | ✅ Complete |
| `docs/architecture/OVERVIEW.md` | Complete architecture explanation | ✅ Complete |
| `docs/development/WORKFLOW.md` | Development workflow | 🚧 TBD |
| `docs/api/ENDPOINTS.md` | API documentation | 🚧 TBD |
| `docs/database/SCHEMA.md` | Database schema | 🚧 TBD |
| `docs/testing/GUIDE.md` | Testing guide | 🚧 TBD |

---

## How to Find What You Need

### Looking for...

**"How do I get started?"**
→ `docs/getting-started/QUICKSTART.md`

**"How is the system structured?"**
→ `docs/architecture/OVERVIEW.md`

**"What are the guiding principles?"**
→ `docs/vision/VISION.md` (PROTECTED, unchanged)

**"How do I make design decisions?"**
→ `docs/vision/DESIGN_PHILOSOPHY.md` (PROTECTED, unchanged)

**"What are the coding standards?"**
→ `/CLAUDE.md` (PROTECTED, unchanged)

**"What endpoints exist?"**
→ `docs/api/ENDPOINTS.md` (TBD) or `/README.md` for quick examples

**"What are the database tables?"**
→ `docs/database/SCHEMA.md` (TBD) or `src/infrastructure/database/models.py` (source of truth)

**"How do I test?"**
→ `docs/testing/GUIDE.md` (TBD) or `tests/` directory (examples)

**"Where is the old design doc?"**
→ `archive_legacy_docs/design/DESIGN.md` (1,509 lines - preserved)

**"Where are the phase completion reports?"**
→ `archive_legacy_docs/implementation/` (all progress reports preserved)

---

## Why This Change?

### Problems with Old Documentation

1. **100+ markdown files** - overwhelming, hard to navigate
2. **Duplication** - 5+ completion summaries, multiple roadmaps
3. **Aspirational vs Actual** - docs described Phase 2/3 features not yet implemented
4. **Hard to find** - no clear entry point for new developers
5. **Mixed audiences** - technical, business, architectural all mixed together

### Goals of New Documentation

1. **Reflect reality** - Document what's actually implemented
2. **Audience-focused** - Organized by who's reading (new dev, architect, etc.)
3. **Practical** - Answer "how do I..." questions
4. **Discoverable** - Clear starting point (`docs/README.md`)
5. **Maintainable** - Fewer docs, easier to keep up-to-date

---

## What About...?

### Q: Where is the detailed design documentation?

**A**: The original `docs/design/DESIGN.md` (1,509 lines) is preserved in `archive_legacy_docs/design/DESIGN.md`. It contains comprehensive design specifications but mixes implemented and aspirational features. New documentation focuses on what's actually built.

### Q: Where are the heuristics?

**A**: Configuration parameters are in `src/config/heuristics.py` (source of truth). Original `docs/reference/HEURISTICS_CALIBRATION.md` is in `archive_legacy_docs/reference/`.

### Q: What about the API design doc?

**A**: `archive_legacy_docs/design/API_DESIGN.md` preserved. New `docs/api/ENDPOINTS.md` will document actual endpoints (TBD).

### Q: Where are the phase completion reports?

**A**: All preserved in `archive_legacy_docs/implementation/` - valuable historical context showing how the system evolved.

### Q: What about demo documentation?

**A**: Demo-specific docs in `archive_legacy_docs/demo/`. Demo system still works, docs still accessible.

### Q: Can I still reference old docs?

**A**: Yes! Everything preserved in `archive_legacy_docs/`. Nothing deleted, just reorganized.

---

## Migration Checklist

If you were using the old documentation:

- [ ] Bookmark new docs hub: `docs/README.md`
- [ ] Update any external links to point to new structure
- [ ] Check `archive_legacy_docs/` if you need historical context
- [ ] Verify protected files unchanged: `VISION.md`, `DESIGN_PHILOSOPHY.md`, `CLAUDE.md`, `ProjectDescription.md`
- [ ] Report any missing documentation as issues

---

## What's Next?

**Planned documentation** (TBD):

1. `docs/development/WORKFLOW.md` - Day-to-day development workflow
2. `docs/api/ENDPOINTS.md` - Complete API endpoint documentation
3. `docs/database/SCHEMA.md` - Database schema with ER diagram
4. `docs/testing/GUIDE.md` - How to write and run tests
5. `docs/deployment/GUIDE.md` - Deployment instructions
6. `docs/reference/GLOSSARY.md` - Key terms and concepts

**Extracting from legacy**:

- Useful heuristics → `docs/reference/CONFIGURATION.md`
- Entity resolution algorithm → `docs/architecture/ENTITY_RESOLUTION.md`
- Retrieval design → `docs/architecture/RETRIEVAL.md`

---

## Feedback

Found missing documentation or inaccuracies?

1. Check `archive_legacy_docs/` first
2. Verify against actual code in `src/`
3. Create issue or PR with corrections

---

**Philosophy**: *Documentation should reflect reality, guide action, and preserve history.*
