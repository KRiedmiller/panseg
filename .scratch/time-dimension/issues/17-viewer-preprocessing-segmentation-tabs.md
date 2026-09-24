# 17: Viewer: preprocessing + segmentation tabs

**What to build:** The preprocessing and segmentation tabs work for every single-channel
layout, including time-bearing ones: a user with a TZYX or TYX layer sees the same task
widgets as with ZYX/YX, can crop/rescale a timelapse with one spatial region, and picks
segmentation modes by spatial dimensionality — TZYX behaves as 3D, TYX as 2D
(spec: "Viewer, GUI, and headless UX" → "Preprocessing tab" + "Segmentation tab"; the
per-stage behavior in "Per-stage pipeline behavior" falls out of the ticket-15 wrapper
with no new algorithm code).

Preprocessing tab: the legacy hide guard ("Preprocessing not supported for 4d images") is
**removed** — import-time channel splitting means multichannel layers essentially never
reach the tab. All frame-mapped task widgets show for every single-channel layout (YX,
ZYX, TYX, TZYX); multichannel layers (reachable only after an explicit merge) hit the
existing task-level rejections. Rescale/crop fields prefill from the spatial axes only (T
never surfaced — this fixes the existing "fix for 4d images" TODO loop). Crop on a
timelapse = one spatial crop (y/x rectangle + z range) applied identically to every
timepoint (the frame-mapped task sees identical parameters); the rectangle is drawn in a
shapes layer matching the image's dimensionality (the hard-coded 3D follows the layer
instead), and the rectangle's position along T is ignored by the crop.

Per-stage behavior that must hold (verified through the ticket-15 wrapper, no new code
expected): filters/normalization run per timepoint (per-timepoint min–max adapts to
illumination drift — this is the intended v1 behavior); crop is identical for every
timepoint (no per-timepoint ROI, no registration); rescale leaves the T axis untouched and
preserves `t_spacing`.

Segmentation tab: the mode branching switches from exact layout match to **spatial
dimensionality**: TZYX behaves as 3D (2D/3D watershed, stacked mode shown), TYX as 2D; no
"Unsupported image layout" log for any T layout (the log remains for genuinely
unsupported layouts, e.g. multichannel). The model zoo's dimensionality filter uses
spatial dimensionality, unchanged: 3D models for TZYX, 2D models for TYX; no T-specific
models in v1.

**Blocked by:**
- 13: OME-TIFF import with time
- 15: Frame-by-frame loop: @timepoint_map + split/restack

**Status:** ready-for-agent

- [ ] The preprocessing tab is visible for TYX/TZYX layers and all frame-mapped task widgets show; the "not supported for 4d images" guard is gone
- [ ] Multichannel layers (CYX/CZYX/TCYX/TCZYX) still hit the existing task-level rejections rather than visible-widget paths
- [ ] The crop shapes layer dimensionality follows the layer (2D for YX/TYX, 3D for ZYX/TZYX); a crop on a timelapse applies one spatial region to every timepoint
- [ ] Rescale/crop fields prefill from spatial axes only for T layouts; rescale output preserves `t_spacing`
- [ ] Segmentation tab: TYX shows 2D modes, TZYX shows 3D modes (incl. stacked); no "Unsupported image layout" log for any T layout
- [ ] The model zoo lists 2D models for TYX and 3D models for TZYX (spatial-dimensionality filter)
