# Visual baseline review

**Scope.** Chromium visual-regression coverage captures the local overview, the intentionally local-only operational fallback, and the reviewed extension catalog at a fixed viewport, locale, timezone, color scheme, and device scale factor.

**Initial review.** The overview baseline preserves the Aurora Relay dark editorial hierarchy: persistent navigation, readable task composition, status blocks, and activity density remain legible. The first operational and extension captures exposed transient loading states rather than their intended stable surfaces; the visual test now waits for the explicit `Packaged local fallback` and `Sandbox Echo` markers before capture. This keeps baselines focused on stable local-only operator states rather than asynchronous loading frames.

**Baseline policy.** Snapshot images under `frontend/e2e/visual-regression.spec.ts-snapshots/` are intentional reviewed test fixtures. Generated failure diffs remain excluded through `frontend/test-results/`. Any baseline update must accompany a deliberate UI review and a normal visual-test run.

**Loaded extension review.** The regenerated catalog baseline shows the reviewed local registry, visible declared permission, disabled-by-default installation control, and the explicit statement that host execution is never a fallback. The loaded surface is therefore suitable as the committed extension-management reference.
