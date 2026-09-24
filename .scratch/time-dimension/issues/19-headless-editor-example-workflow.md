# 19: Headless: workflow editor entry + example workflow

**What to build:** A user can run a complete timelapse workflow headless from a yaml, and
the `panseg --edit` workflow editor supports the new time-spacing task (spec: "Viewer,
GUI, and headless UX" → "Workflow editor and headless" + "Complete example headless
workflow").

No DAG changes — the loop (ticket 15) is a transparent wrapper, so the recorded node
shape for a timelapse is identical to today. The `panseg --edit` editor (per-task entry
widgets) gains a dedicated entry for `set_t_spacing_task`: one float spin box (seconds),
mirroring the existing `set_voxel_size_task` entry.

The spec's complete example headless workflow — import (TZYX from OME-TIFF) →
`set_t_spacing_task` → `gaussian_smoothing_task` → `unet_prediction_task` →
`dt_watershed_task` → `clustering_segmentation_task` → `set_biggest_instance_to_zero_task`
→ `export_image_task` (tiff) — is valid and runs end-to-end headless against a resliced
anchor (ticket 12), using the existing test model-mocking pattern for prediction (no
network, no new `slow` tests).

**Blocked by:**
- 14: Time-aware export (TIFF, h5/zarr, mesh)
- 15: Frame-by-frame loop: @timepoint_map + split/restack

**Status:** ready-for-agent

- [ ] The `panseg --edit` workflow editor renders a float spin box entry for `set_t_spacing_task` and saves it as a task parameter, mirroring the `set_voxel_size_task` entry
- [ ] The example timelapse workflow yaml (import TZYX → set t_spacing → gaussian → unet prediction → dt watershed → clustering → set-biggest → tiff export) parses and runs headless to completion on a resliced TZYX anchor, with prediction via the existing test mocks
- [ ] The exported tiff re-imports as the same layout with the set t_spacing
- [ ] A widget/CLI test covers the t_spacing headless `--edit` parameter, mirroring the existing edit-parameter test pattern
- [ ] No new `slow` tests; the run is fast by construction (resliced anchor, synthetic/saved model mocks)
