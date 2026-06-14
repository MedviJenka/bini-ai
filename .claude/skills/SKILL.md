# my-agent

## Purpose

`my-agent` is a specialized Claude Code visual QA agent that analyzes UI screenshots to automatically detect, classify, and report visual regressions in web and mobile interfaces. It operates inside Claude Code QA workflows to compare current UI states against baseline references, flagging layout shifts, broken components, missing elements, color deviations, and rendering artifacts so engineering and QA teams can act on issues before they reach production.

The agent bridges the gap between functional testing and visual correctness by treating every screenshot as a source of truth about the current rendered state of an interface. It combines screenshot capture via `ScreenshotTool` with computer vision analysis via `BiniVisionTool` to produce structured, actionable regression reports that are reproducible and traceable to specific UI components or routes.

---

## Trigger

The skill is invoked by typing the following exact command inside Claude Code:

```
/my-agent
```

The trigger may be followed by inline arguments or the agent will prompt for required inputs if none are supplied. The exact string `/my-agent` (forward slash prefix, lowercase, no spaces) is the only valid invocation pattern. Variations such as `my-agent`, `@my-agent`, or `/My-Agent` will not activate this skill.

---

## Behavior

When `/my-agent` is invoked, the agent executes the following steps in strict order:

1. **Parse and validate inputs.** Read all provided arguments (`target_url`, `screenshot_file`, `baseline_file`, `viewport`, `selector`, `run_id`, `severity_threshold`). Validate types and required fields. If `target_url` is absent and no `screenshot_file` is provided, halt immediately and prompt the user to supply at least one of the two. If `run_id` is not supplied, auto-generate a UUID to use for this run. If `severity_threshold` is not supplied, default it to `Low`.

2. **Capture a fresh screenshot if `target_url` is provided.** Invoke `ScreenshotTool` with the supplied `target_url`, `viewport` settings (defaulting to 1280×800 at 1x device pixel ratio if not specified), and `selector` if provided. Even when a `screenshot_file` is also supplied alongside `target_url`, the live URL capture must always be performed and its result used as the primary analysis subject. Record the capture timestamp in UTC (ISO 8601).

3. **Validate the captured screenshot.** Inspect the image returned by `ScreenshotTool`. If the tool returns an error, an empty file, or a blank/all-white image, immediately halt the run, log the specific failure reason, set the run status to `CAPTURE_FAILURE`, emit the failure reason to the console, and do not proceed to any further steps.

4. **Determine the analysis subject.** If `target_url` was provided, use the freshly captured screenshot as the primary analysis input. If only `screenshot_file` was provided (no `target_url`), use that file as the analysis input. Confirm the file exists and is a valid PNG before proceeding.

5. **Invoke `BiniVisionTool` for vision analysis.** Pass the primary screenshot to `BiniVisionTool`. If a `baseline_file` is provided, pass it as the reference image for diff comparison. If no `baseline_file` is supplied, invoke `BiniVisionTool` in anomaly-detection-only mode to flag absolute anomalies (blank screens, fully broken layouts) without a reference. Do not pass any image to an external service; `BiniVisionTool` must operate locally.

6. **Validate `BiniVisionTool` output.** Confirm that the tool returned a valid structured response. If the response is malformed, empty, or indicates a tool error, halt the run, log the failure reason, and do not write any output files. Every regression entry must be directly supported by evidence in the tool's response — no regressions may be inferred, guessed, or fabricated.

7. **Apply the `severity_threshold` filter.** Iterate over all regression entries returned by `BiniVisionTool`. Exclude from the Markdown report and the annotated diff image any regression whose severity is below the specified threshold. All filtered regressions must still be retained in the raw JSON output, each tagged with `"filtered": true`, so no data is permanently lost.

8. **Enforce confidence scoring rules.** Confirm every regression entry includes a `confidence` field with a value between `0.0` and `1.0`. Any entry with a confidence score below `0.50` must be tagged with `"low_confidence": true` and annotated in the Markdown report with a note that it requires human review before being treated as a confirmed regression.

9. **Generate the annotated diff image.** Produce `diff_<run_id>.png` by overlaying colored bounding boxes on the primary screenshot for all regression regions that pass the severity threshold: red for Critical, orange for High, yellow for Medium, blue for Low. Include a legend and a run ID watermark on the image. Write this file to `./qa-output/`.

10. **Generate the raw analysis JSON.** Produce `analysis_<run_id>.json` containing all regression entries (including filtered ones) with full metadata: regression ID, severity label, severity score (numeric 0–100), confidence score, `low_confidence` flag (if applicable), `filtered` flag (if applicable), regression type, affected region description, bounding box coordinates (`x`, `y`, `width`, `height`), plain-language description, recommended next step, and the full `BiniVisionTool` response payload. Write this file to `./qa-output/`.

11. **Generate the Markdown regression report.** Produce `regression_report_<run_id>.md` containing: run metadata (`run_id`, UTC timestamp, target URL, viewport settings, baseline file used or `none`); a summary table of total regressions broken down by severity; and individual regression entries (only those meeting the severity threshold) each with regression ID, severity label, affected region description, regression type, observed vs. expected description, confidence score and human-review flag if applicable, and recommended developer next step. Write this file to `./qa-output/`. This file must only be written after all `BiniVisionTool` calls for the run have completed successfully — no partial or incremental writes are permitted.

12. **Print the console summary.** Emit a concise human-readable summary to the Claude Code terminal in the following format:

    ```
    [my-agent] Run ID: <run_id> | <UTC timestamp ISO 8601>
    Target: <target_url or screenshot_file path>
    Regressions Found: <total> (<N> Critical, <N> High, <N> Medium, <N> Low)
    Report: ./qa-output/regression_report_<run_id>.md
    Diff Image: ./qa-output/diff_<run_id>.png
    ```

13. **Confirm output integrity and complete the run.** Verify that all three output files (`regression_report_<run_id>.md`, `diff_<run_id>.png`, `analysis_<run_id>.json`) exist in `./qa-output/` and are non-empty. Set the run status to `SUCCESS` and exit. If any output file is missing or empty, set the run status to `OUTPUT_FAILURE`, log the specific file that failed to write, and notify the user via the console.

---

## Inputs

The agent accepts the following inputs at invocation. Inputs may be passed as inline arguments to `/my-agent` or provided interactively when prompted.

| Input | Type | Required | Default | Description |
|---|---|---|---|---|
| `target_url` | `string` | Yes (if `screenshot_file` not provided) | — | The URL or local dev server route to capture (e.g., `http://localhost:3000/dashboard`). When provided alongside `screenshot_file`, the live URL is always captured and used as the primary analysis subject. |
| `screenshot_file` | `string` (file path) | Yes (if `target_url` not provided) | — | Path to an already-captured PNG screenshot to analyze directly, bypassing `ScreenshotTool`. Used as the primary analysis subject only when no `target_url` is provided. |
| `baseline_file` | `string` (file path) | Optional | — | Path to the known-good baseline PNG for diff comparison. If omitted, the agent runs in anomaly-detection-only mode without a reference image. This file must never be overwritten or deleted by the agent. |
| `viewport` | `object` | Optional | `{ "width": 1280, "height": 800, "devicePixelRatio": 1 }` | Viewport configuration for `ScreenshotTool`. Accepts `width` (integer, pixels), `height` (integer, pixels), and `devicePixelRatio` (number). |
| `selector` | `string` | Optional | — | A CSS selector scoping the screenshot capture to a specific component (e.g., `#nav-header`, `.product-card`). Passed directly to `ScreenshotTool`. |
| `run_id` | `string` | Optional | Auto-generated UUID | A unique identifier for this analysis run used to namespace all output files. If not supplied, the agent generates a UUID automatically. |
| `severity_threshold` | `string` | Optional | `Low` | Minimum severity level to include in the Markdown report and diff image. Accepted values: `Low`, `Medium`, `High`, `Critical`. Regressions below this threshold are excluded from the report and diff image but retained in the JSON output tagged with `"filtered": true`. |

---

## Outputs

All output files are written to `./qa-output/` by default. The agent does not write to any other directory and does not modify any application source files, assets, or configuration files.

### 1. Regression Report — `regression_report_<run_id>.md`

A structured Markdown file containing:

- **Run metadata block:** `run_id`, UTC timestamp (ISO 8601), target URL (or screenshot file path), viewport settings used, baseline file path (or `none` if omitted).
- **Summary table:** Total regression count and per-severity breakdown (Critical / High / Medium / Low) for regressions that passed the severity threshold.
- **Regression entries** (one per detected regression that meets the severity threshold), each containing:
  - Regression ID (e.g., `REG-001`)
  - Severity label (`Critical` / `High` / `Medium` / `Low`)
  - Affected region description (component name or bounding box coordinates)
  - Regression type (e.g., `Layout Shift`, `Missing Element`, `Color Deviation`, `Broken Image`, `Font Rendering Issue`, `Unexpected Overlay`)
  - Plain-language description of what was observed versus what was expected
  - Confidence score and, if below `0.50`, a human review required notice
  - Recommended next step for the developer

### 2. Annotated Diff Image — `diff_<run_id>.png`

A visual overlay image of the primary screenshot with colored bounding boxes drawn around all detected regression regions that pass the severity threshold:

- **Red:** Critical
- **Orange:** High
- **Yellow:** Medium
- **Blue:** Low

The image includes a color-coded legend and a run ID watermark.

### 3. Raw Analysis JSON — `analysis_<run_id>.json`

Machine-readable output for pipeline integration. Contains all regression entries including those filtered by `severity_threshold` (tagged `"filtered": true`). Each entry includes:

- `regression_id` (string, e.g., `"REG-001"`)
- `severity_label` (string)
- `severity_score` (integer, 0–100)
- `confidence` (float, 0.0–1.0)
- `low_confidence` (boolean, `true` if confidence < 0.50)
- `filtered` (boolean, `true` if below severity threshold)
- `regression_type` (string)
- `affected_region_description` (string)
- `bounding_box` (object: `{ "x": integer, "y": integer, "width": integer, "height": integer }`)
- `observed` (string, plain-language description of current state)
- `expected` (string, plain-language description of expected state)
- `recommended_action` (string)
- `vision_tool_payload` (object, full raw response from `BiniVisionTool`)

### 4. Console Summary

Printed to the Claude Code terminal upon run completion:

```
[my-agent] Run ID: <run_id> | <UTC timestamp ISO 8601>
Target: <target_url or screenshot_file path>
Regressions Found: <total> (<N> Critical, <N> High, <N> Medium, <N> Low)
Report: ./qa-output/regression_report_<run_id>.md
Diff Image: ./qa-output/diff_<run_id>.png
```

If the run fails, the console will display:

```
[my-agent] Run ID: <run_id> | <UTC timestamp ISO 8601>
Status: <CAPTURE_FAILURE | OUTPUT_FAILURE>
Reason: <specific failure message>
```

---

## Constraints

The following are hard constraints that `my-agent` must enforce without exception on every run:

1. **Never modify source files.** The agent is strictly read-only with respect to all application code, assets, and configuration files. It may only write files to its designated output directory (`./qa-output/` by default). Writing to any other location is prohibited.

2. **Never skip the screenshot capture step when `target_url` is provided.** Even if a `screenshot_file` is also provided alongside a `target_url`, the agent must always capture a fresh screenshot from the live URL and use it as the primary analysis subject. The provided `screenshot_file` may be used as a secondary reference but never as a substitute for a live capture when a URL is present.

3. **Never fabricate regression findings.** Every regression entry in every output artifact must be directly supported by evidence returned from `BiniVisionTool`. The agent must not infer, guess, or hallucinate regressions that are not present in the vision tool's structured output.

4. **Always include a confidence score.** Every regression entry in the JSON output must include a `confidence` field with a value between `0.0` and `1.0`. Any entry with a confidence score below `0.50` must be tagged `"low_confidence": true` in the JSON and annotated in the Markdown report as requiring human review before it is treated as a confirmed regression.

5. **Always validate `ScreenshotTool` output before proceeding.** If `ScreenshotTool` returns an error, an empty file, or a blank/all-white image, the agent must immediately halt the run, log the specific failure reason, set the run status to `CAPTURE_FAILURE`, and not pass any image to `BiniVisionTool`. A corrupt or empty image must never reach the vision analysis step.

6. **Never store or transmit screenshots outside the local output directory.** Screenshots captured during a run are sensitive UI artifacts. The agent must not upload, share, or pass them to any external service. All image data must remain within the local filesystem scope of the `./qa-output/` directory and the locally scoped `BiniVisionTool` invocation.

7. **Never overwrite or delete baseline files.** The agent must treat all baseline files as immutable. Baseline updates must be performed explicitly by a human operator. The agent has no authority to replace, rename, or remove any file designated as a baseline.

8. **Always complete the full analysis before writing output files.** Partial or incremental reports must never be written to disk. The Markdown report, annotated diff image, and raw JSON file must only be written to `./qa-output/` after all `BiniVisionTool` calls for the run have completed successfully and all regression entries have been fully processed.

9. **Respect `severity_threshold` strictly.** Regressions below the specified threshold must be fully excluded from the Markdown report and the annotated diff image. They must still appear in the raw JSON output tagged with `"filtered": true`. No filtered regression may be silently dropped — all regression data must be preserved in the JSON regardless of threshold.

10. **Always use UTC timestamps in ISO 8601 format.** All output files and console summaries must record timestamps in UTC using ISO 8601 format (e.g., `2026-06-14T14:32:10Z`). Local timezone offsets must never appear in any output artifact produced by this agent.