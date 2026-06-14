# my-agent — Commands Reference

> Visual QA regression agent for Claude Code. Captures UI screenshots, detects visual regressions, and produces structured reports.
>
> **Last updated:** 2026-06-14

---

## Quick Start

The most common workflow: run a visual regression check against a live local dev server with a known baseline.

```
/my-agent --target_url http://localhost:3000/dashboard --baseline_file ./baselines/dashboard.png
```

Output lands in `./qa-output/`. Check the console for a run summary, then open `regression_report_<run_id>.md` for the full findings.

---

## Commands

### `/my-agent`

The single entry point for all agent operations. All flags are passed inline as `--key value` pairs.

---

#### Syntax

```
/my-agent [--target_url <url>] [--screenshot_file <path>] [--baseline_file <path>]
          [--viewport <json>] [--selector <css>] [--run_id <id>]
          [--severity_threshold <level>]
```

> **Minimum requirement:** You must supply at least one of `--target_url` or `--screenshot_file`. All other arguments are optional.

---

#### Arguments

| Argument | Type | Required | Default | Description |
|---|---|---|---|---|
| `--target_url` | `string` | Yes *(unless `--screenshot_file` provided)* | — | URL or local dev-server route to capture live. e.g. `http://localhost:3000/dashboard`. When supplied together with `--screenshot_file`, the live capture always takes precedence as the primary analysis subject. |
| `--screenshot_file` | `string` *(file path)* | Yes *(unless `--target_url` provided)* | — | Path to a pre-captured PNG to analyze directly, bypassing `ScreenshotTool`. Used as the primary subject only when no `--target_url` is given. |
| `--baseline_file` | `string` *(file path)* | Optional | — | Path to a known-good baseline PNG for diff comparison. Omit to run in anomaly-detection-only mode (no reference image required). The agent will **never** overwrite or delete this file. |
| `--viewport` | `JSON object` | Optional | `{"width":1280,"height":800,"devicePixelRatio":1}` | Viewport configuration passed to `ScreenshotTool`. Accepts integer `width` (px), integer `height` (px), and number `devicePixelRatio`. |
| `--selector` | `string` *(CSS selector)* | Optional | — | Scopes the screenshot capture to a specific component. e.g. `#nav-header` or `.product-card`. Passed directly to `ScreenshotTool`. |
| `--run_id` | `string` | Optional | Auto-generated UUID | Custom identifier used to namespace all output files (`regression_report_<run_id>.md`, `diff_<run_id>.png`, `analysis_<run_id>.json`). Useful for tying runs to CI job IDs or ticket numbers. |
| `--severity_threshold` | `string` | Optional | `Low` | Minimum severity level included in the Markdown report and annotated diff image. Accepted values: `Low` · `Medium` · `High` · `Critical`. Regressions below the threshold are excluded from the report and diff image but are retained in the JSON output tagged `"filtered": true`. |

---

#### Outputs

| File | Description |
|---|---|
| `./qa-output/regression_report_<run_id>.md` | Structured Markdown report: run metadata, severity summary table, and per-regression entries. |
| `./qa-output/diff_<run_id>.png` | Annotated screenshot with colored bounding boxes (red = Critical, orange = High, yellow = Medium, blue = Low), a legend, and a run ID watermark. |
| `./qa-output/analysis_<run_id>.json` | Full machine-readable output for pipeline integration, including all regressions (filtered and unfiltered) with bounding boxes, confidence scores, and raw `BiniVisionTool` payloads. |
| Console summary | Human-readable run summary printed to the Claude Code terminal on completion or failure. |

---

#### Exit States

| Status | Meaning |
|---|---|
| `SUCCESS` | All three output files written successfully; run complete. |
| `CAPTURE_FAILURE` | `ScreenshotTool` returned an error, empty file, or blank/all-white image. No output files are written. |
| `OUTPUT_FAILURE` | Analysis completed but one or more output files failed to write to `./qa-output/`. |

---

#### Usage Examples

**1. Basic live capture — no baseline (anomaly-detection mode)**

```
/my-agent --target_url http://localhost:3000/login
```

Captures the login page at default viewport (1280×800 @1x) and flags absolute anomalies (blank screens, broken layouts) without a reference image.

---

**2. Live capture with baseline diff**

```
/my-agent --target_url http://localhost:3000/dashboard --baseline_file ./baselines/dashboard.png
```

Captures a fresh screenshot and compares it against the baseline. All regressions at every severity level (`Low` and above) are reported.

---

**3. Analyze a pre-captured screenshot against a baseline**

```
/my-agent --screenshot_file ./screenshots/checkout.png --baseline_file ./baselines/checkout.png
```

Skips live capture. Runs `BiniVisionTool` directly on the provided PNG against the baseline.

---

**4. Scope capture to a single component**

```
/my-agent --target_url http://localhost:3000/home --selector "#nav-header" --baseline_file ./baselines/nav-header.png
```

Captures only the `#nav-header` element and diffs it against its component-level baseline.

---

**5. High-DPI viewport for mobile simulation**

```
/my-agent --target_url http://localhost:3000/product/42 --viewport '{"width":390,"height":844,"devicePixelRatio":3}' --baseline_file ./baselines/product-mobile.png
```

Simulates an iPhone 14 Pro viewport at 3× device pixel ratio.

---

**6. Raise severity threshold to suppress noise in CI**

```
/my-agent --target_url http://localhost:3000/dashboard --baseline_file ./baselines/dashboard.png --severity_threshold High
```

Only `High` and `Critical` regressions appear in the report and diff image. `Low` and `Medium` findings are still recorded in the JSON with `"filtered": true`.

---

**7. Pin a run to a specific CI job ID**

```
/my-agent --target_url http://localhost:3000/dashboard --baseline_file ./baselines/dashboard.png --run_id ci-job-9812
```

Output files are named `regression_report_ci-job-9812.md`, `diff_ci-job-9812.png`, and `analysis_ci-job-9812.json`.

---

**8. Full production-grade invocation**

```
/my-agent \
  --target_url http://localhost:3000/checkout \
  --baseline_file ./baselines/checkout-1440.png \
  --viewport '{"width":1440,"height":900,"devicePixelRatio":2}' \
  --selector "#checkout-form" \
  --run_id release-2.4.1-checkout \
  --severity_threshold Medium
```

Captures the `#checkout-form` component at 1440×900 @2x, diffs against its baseline, reports `Medium` and above regressions, and writes all output files namespaced to `release-2.4.1-checkout`.

---

## Hard Constraints (Quick Reference)

These rules are enforced on every run and cannot be overridden by any argument:

- The agent **never modifies** application source files, assets, or config — output goes only to `./qa-output/`.
- When `--target_url` is provided, a **live screenshot is always captured**, even if `--screenshot_file` is also supplied.
- Regression findings are **never fabricated** — every entry must be backed by `BiniVisionTool` evidence.
- A **confidence score is always required** on every JSON entry; entries below `0.50` are flagged `"low_confidence": true`.
- Baseline files are **never overwritten or deleted** by the agent.
- Screenshots are **never transmitted** outside the local filesystem.
- All timestamps in output artifacts are **UTC in ISO 8601** format (e.g., `2026-06-14T14:32:10Z`).