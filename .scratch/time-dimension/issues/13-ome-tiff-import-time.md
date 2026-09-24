# 13: OME-TIFF import with time

**What to build:** A user can open a T-bearing single-file OME-TIFF and get the right
layout pre-filled, with t_spacing extracted when present and unknown otherwise — no
prompting, no crashing (spec: "Import").

Axis authority is the format metadata, not shape guessing. The `stack_layout` prefill for
OME-TIFF comes from the reader's per-file axis string (singleton axes already dropped by
the reader, e.g. `time-series.ome.tif` → `TYX`) — the prefill hook today funnels every
format through the shape heuristic. T import is OME-TIFF only: the non-OME paths (ImageJ,
shaped TIFF, PIL) and PanSeg-owned h5/zarr lacking the new `axis_order` attr keep the
existing shape heuristic and stay T-unaware in v1. The existing `IndexError` crash in the
shape heuristic on 4D shapes with no dimension < 10 is fixed to return an empty prefill
instead of crashing.

t_spacing extraction order for OME-TIFF import: (1) `Pixels.TimeIncrement` (+ unit,
converted to the canonical unit seconds), (2) else `Plane.DeltaT` (first plane per
timepoint; present but non-uniform across timepoints ⇒ warn and treat as missing),
(3) else missing ⇒ t_spacing unknown. No prompt at import: import proceeds with unknown
t_spacing, which is a first-class supported state through all v1 I/O; the user supplies
t_spacing later via the set-t-spacing task (ticket 16/17 territory).

Boundaries: multi-file OME-TIFF (UUID/FileName chain) is rejected at import with a clear
error — detection is more than one distinct `(UUID, FileName)` pair over the TIFF data of
the Image in use, or any `FileName` not matching the opened file. Multi-position OME
(several Images) is unchanged — first position. Non-uniform frame sizes are impossible in
OME-TIFF, no mechanism needed.

`import_image` gains T branches mirroring the existing per-layout branches: TZYX/TYX
import as a single image (the spatial-slicing crop applied as in the existing YX/ZYX
branch); TCZYX/TCYX split per channel into TZYX/TYX images. `m_slicing` (the import
slicing parameter) extends to T layouts: string positions follow the layout with T first
(e.g. `"0:3,:, :50"` on TZYX); a T slice of length 1 squeezes to no-T per the squeeze rule.
It is the only T sub-range mechanism in v1.

PanSeg h5/zarr on-disk gains a new dataset attr `axis_order` (e.g. `"TZYX"`) written on
every export (additive; old readers ignore it) — the read side for this ticket: the
prefill for PanSeg-owned files reads it, falling back to the shape heuristic for older
files. (Writing it is ticket 14.)

**Blocked by:**
- 11: Data model: T in layouts and image properties
- 12: Fixtures: synthetic timelapses, resliced anchors, OME variants

**Status:** ready-for-agent

- [ ] The three committed resliced anchors import to the right layout (TYX/TZYX/TCZYX) with t_spacing unknown, and the layout prefill is driven by the reader's axis string
- [ ] t_spacing extraction: `TimeIncrement` + unit variants (ms/min) import as seconds; uniform per-plane `DeltaT` imports as seconds; non-uniform `DeltaT` warns and imports as unknown; absent metadata imports as unknown
- [ ] A T=1 file imports with a squeezed non-T layout
- [ ] A multi-file OME-TIFF (UUID/FileName chain) is rejected at import with a clear error
- [ ] The former `shape_to_stack_layout` crash shapes (4D, no dim < 10) prefill empty instead of raising
- [ ] `import_image` T branches: TZYX/TYX import as a single image with spatial slicing; TCZYX/TCYX split per channel into TZYX/TYX
- [ ] `m_slicing` accepts T layouts with T first in the string; a length-1 T slice squeezes to no-T
- [ ] PanSeg-owned files with an `axis_order` attr prefill from it; older files fall back to the shape heuristic; non-OME T-bearing files stay T-unaware (no crash)
