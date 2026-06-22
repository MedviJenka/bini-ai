---
type: design
topic: bini-vision-mcp-expansion
created: 2026-06-04
status: proposed
scope: 4 new MCP tools (VisionBatch, VisionDiff, VisionWCAG, VisionBaseline) + testflow integration
phases: 6
estimated_files: 30+
estimated_prs: 4
---

# Bini Vision MCP Expansion: 4 New Tools + Testflow Integration

## Goal

Expand the bini-vision MCP server with 4 new tools and integrate them into the testflow QA pipeline. MCP tools are built first, testflow integration second. All code lives in the bini-ai project.

## Architecture Decisions

### AD-1: Crew-per-tool domain
Each new tool domain gets its own CrewAI crew directory under `backend/ai/agents/`. VisionBatch reuses the existing vision_agent crew. Avoids god-crew anti-pattern where all agents/tasks are loaded for every invocation.

### AD-2: Thin MCP composition root
`main.py` delegates to `backend/mcp/` modules. Each module exports a `register_*_tools(mcp)` function. main.py is ~20 lines.

### AD-3: Result type at crew-to-MCP boundary
`Result[T]` discriminated union (`Ok[T] | Err`) at `backend/ai/types.py`. All crew functions return Result. No throws in business logic.

### AD-4: BaselineStore protocol with filesystem backend
`BaselineStore` protocol in `backend/storage/protocol.py` with `FileSystemBaselineStore`. PNG files + JSON sidecar metadata. Docker volume mounted at `./data/baselines:/app/data/baselines`.

### AD-5: Schemas defined before implementation
All Pydantic input/output schemas per tool defined first. TDD requires schemas for test contracts.

### AD-6: Settings via composition
New fields added to existing `Settings` class with defaults: `BASELINE_DIR`, `MAX_BATCH_SIZE`, `WCAG_TARGET_LEVEL`, `DEFAULT_DIFF_THRESHOLD`.

### AD-7: LLMFactory extended with model parameter
`LLMFactory(model=...)` defaults to `Config.CLAUDE_MODEL`. Per-tool model config possible.

### AD-8: Image format detection from magic bytes
`detect_image_format(data: bytes) -> str` replaces JPEG assumption. PNG preferred for diffs (lossless).

## Phase 0: Foundation

### New Files
- `backend/ai/types.py` — Result[T] type (Ok, Err, is_ok, unwrap, unwrap_or)
- `backend/ai/image_utils.py` — detect_format, resize_image, encode_to_data_uri, decode_data_uri, ensure_png
- `backend/storage/__init__.py`
- `backend/storage/protocol.py` — BaselineStore protocol, BaselineMetadata model
- `backend/storage/filesystem.py` — FileSystemBaselineStore implementation
- `backend/mcp/__init__.py`
- `backend/mcp/vision.py` — Extracted existing Vision tool registration

### Modified Files
- `main.py` — Refactored to thin composition root
- `backend/settings.py` — New fields + LLMFactory model parameter
- `backend/ai/tools/vision_tool.py` — Delegates to shared image_utils

### Tests
- `tests/unit/test_types.py`
- `tests/unit/test_image_utils.py`
- `tests/unit/test_baseline_store.py`

## Phase 1: VisionBatch

### New Files
- `backend/mcp/vision_batch.py` — Tool registration, sequential processing, progress reporting
- `backend/mcp/schemas/batch.py` — VisionBatchInput, VisionBatchOutput, VisionBatchItem, VisionBatchError

### Schemas
```
VisionBatchInput(images: list[str], prompt: str, sample_image: Optional[list[str]])
VisionBatchOutput(results: list[VisionBatchItem], errors: list[VisionBatchError], total: int, succeeded: int, failed: int)
VisionBatchItem(index: int, image_id: str, result: VisionSchema)
VisionBatchError(index: int, image_id: str, error: str)
```

### Tests
- `tests/unit/test_vision_batch.py`

## Phase 2: VisionDiff

### New Files
- `backend/ai/agents/diff_agent/` — Full crew structure (crew.py, schemas.py, pixel_diff.py, config/*.yaml)
- `backend/mcp/vision_diff.py` — Tool registration
- `backend/mcp/schemas/diff.py`

### Schemas
```
DiffInput(image_a: str, image_b: str, threshold: float = 0.01, mode: Literal["pixel", "ai", "both"] = "both")
DiffOutput(mode_used: str, diff_image: Optional[str], changed_pixels_pct: float, regions: list[DiffRegion], verdict: Literal["identical", "minor_change", "significant_change"], summary: str, confidence: int)
DiffRegion(x: int, y: int, width: int, height: int, change_intensity: float)
```

### Tests
- `tests/unit/test_pixel_diff.py`
- `tests/unit/test_diff_crew.py`

## Phase 3: VisionBaseline

### New Files
- `backend/ai/agents/baseline_agent/schemas.py`
- `backend/mcp/vision_baseline.py` — Two tools: VisionBaselineSave, VisionBaselineCompare
- `backend/mcp/schemas/baseline.py`

### Schemas
```
BaselineSaveInput(key: str, image: str, source_url: Optional[str], tags: list[str])
BaselineSaveOutput(key: str, stored_path: str, checksum: str)
BaselineCompareInput(key: str, current_image: str, threshold: float, mode: Literal["pixel", "ai", "both"])
BaselineCompareOutput(baseline_metadata: BaselineMetadata, diff: DiffOutput, regression_detected: bool)
```

No separate crew needed — composes BaselineStore + VisionDiff.

### Tests
- `tests/unit/test_vision_baseline.py`

## Phase 4: VisionWCAG

### New Files
- `backend/ai/agents/wcag_agent/` — Full crew structure
- `backend/mcp/vision_wcag.py` — Tool registration
- `backend/mcp/schemas/wcag.py`

### Schemas
```
WCAGInput(image: str, criteria: Optional[list[str]], url: Optional[str])
WCAGOutput(criteria_results: list[CriterionResult], overall_pass: bool, summary: str, confidence: int)
CriterionResult(criterion_id: str, criterion_name: str, level: str, status: Literal["pass", "fail", "cannot_evaluate"], findings: list[WCAGFinding], element_count_evaluated: int)
WCAGFinding(element_description: str, location: str, expected: str, actual: str, severity: Literal["critical", "major", "minor"])
```

### WCAG Scope (Screenshot-Evaluable AA)
- 1.4.3 Contrast (Minimum) — text-to-background ≥4.5:1 / 3:1 large
- 1.4.4 Resize Text — readable at 200%
- 1.4.11 Non-text Contrast — UI components ≥3:1
- 1.4.12 Text Spacing — no content loss with adjusted spacing

### Tests
- `tests/unit/test_wcag_schemas.py`
- `tests/unit/test_wcag_crew.py`

## Phase 5: Testflow Integration

### New Files
- `backend/mcp/schemas/testflow.py` — VisualFinding, VisualAssessmentResult, VisualCheck
- `backend/mcp/schemas/evaluation.py` — VIS-01..05 evaluation criteria
- `.claude/commands/testflow-visual-qa.md` — Visual QA domain skill (VQ-01..04)
- `.claude/commands/testflow-explore-ui-visual.md` — explore-ui visual-ai category
- `.claude/commands/testflow-execution-visual.md` — execution evidence analysis

### Modified Files
- `.claude/agents/qa-image-bini-vision.md` — Updated to reference all 5+ tools
- `compose.yaml` — Baseline volume mount
- `pyproject.toml` — Explicit pillow dependency

### Testflow Integration Map
| Skill | Tool | When | Output |
|-------|------|------|--------|
| explore-ui | VisionDiff/Vision | After screenshot | visual-ai issue |
| execution | Vision | After failure screenshot | Evidence classification |
| visual-qa | All tools | Assessment phase | VQ-01..04 checks |
| evaluation | Reads artifacts | Phase gates | VIS-01..05 checklist |

## PR Strategy

| PR | Phases | Key Risk |
|----|--------|----------|
| PR 1 | 0 (Foundation) | main.py backward compat |
| PR 2 | 1+2 (Batch + Diff) | Pixel diff accuracy, batch partial failure |
| PR 3 | 3+4 (Baseline + WCAG) | Storage reliability, WCAG heuristic limits |
| PR 4 | 5 (Testflow) | Skill-to-tool mapping correctness |

## Risks and Mitigations

| Risk | Severity | Mitigation |
|------|----------|-----------|
| CrewAI malformed output | HIGH | Result type + JSON repair + retry |
| Pixel diff slow on 4K | MEDIUM | Resize to 2048px; byte-identical early-out |
| Baseline storage unbounded | MEDIUM | max_baselines=1000 config |
| WCAG is heuristic estimation | MEDIUM | Limit to 4 criteria; cannot_evaluate status |
| Breaking existing Vision | HIGH | Smoke test after main.py refactor |
| VisionBaseline partial success | MEDIUM | Return pixel results if AI crew fails |

## Design Review Notes

- VisionBatch N+1 (sequential crew calls) is intentional for Phase 1
- VisionBaseline compare should return partial results on AI crew failure
- WCAG evaluation is heuristic — document as estimation, not audit replacement
