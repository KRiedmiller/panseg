# Wayfinder map: time as a first-class dimension

## Destination

A handoff spec at `.scratch/time-dimension/spec.md` for adding **time as a first-class dimension** to PanSeg: one fixed internal axis order for time-bearing data, import/export (OME-TIFF, panseg h5, zarr), a frame-by-frame pipeline (preprocessing, prediction, segmentation, proofreading), napari viewer support, tests and docs — such that a 3D lightsheet timelapse (with or without channels) can be imported, segmented frame-by-frame, proofread, and exported with T preserved. No code changes in this effort; the spec is the artifact.

## Notes

- Domain: microscopy timelapse segmentation. Core data model: `PanSegImage` + `ImageProperties`/`ImageLayout` (`panseg/core/image.py`), `VoxelSize` (`panseg/io/voxelsize.py`). "4D" in this codebase currently means C+ZYX.
- Settled during charting (standing constraints; the decision text lives in the referenced ticket):
  - v1 = frame-by-frame: no spacetime-aware algorithms (ticket 06).
  - NN prediction on timelapse = per-frame 3D inference reusing existing models; training timelapse models is out of scope (ticket 06).
  - In-memory numpy retained; no dask/mmap/chunking in v1.
  - Channels are split at import (`import_image`, `panseg/core/image.py:675`), so single-channel images dominate internally; a channel axis is rarely carried (constraint on ticket 03).
  - `t_spacing` + unit are part of the v1 properties (ticket 03).
  - Per-frame segmentation yields independent label IDs across frames; documented, not corresponded (ticket 06).
  - Frame-by-frame loop = transparent task-level "map over T" wrapper; DAG/GUI unchanged (ticket 04).
  - Import formats v1: single-file OME-TIFF with T, panseg h5, zarr; no multi-file series (ticket 05).
  - Axis order: settled as TCZYX; every internal array is a projection of T, C, Z, Y, X (ticket 02).
- Anchor dataset: 8 example OME-TIFFs, `/home/kriedmiller/Downloads/ome_tiff_examples.tar.xz` (single/multi-channel × 2D/Z/T/4D; `4D-series` = 7t×5z×167y×439x int8, `multi-channel-4D-series` = 7t×3c×5z×167y×439x). OME-XML carries `SizeT` etc.; the 2016-06 schema has **no time-spacing element at all** — spacing (when present) lives in `Pixels.TimeIncrement`/`Plane.DeltaT`, which none of the 8 anchor files carry, so t_spacing extraction must have a missing-case default (see [ticket 01](issues/01-research-file-format-time.md)). Read-only extracted copies: `/tmp/opencode/ome_tiff_examples`.
- Skills: grilling + domain-modeling for HITL tickets; research for the AFK research ticket; prototype for ticket 03.
- `CONTEXT.md` exists (created by ticket 03): the "4D = CZYX" clash is settled there; consult and extend it (terms: dimensionality, layout, timelapse, timepoint, time spacing).
- Conventions: `docs/agents/conventions.md` (conda env `panseg-fork`, worktrees for code changes, tests from repo root, `QT_QPA_PLATFORM=offscreen` for widget tests).

## Decisions so far

<!-- index: one line per closed ticket; the decision text lives in the ticket -->

- [Research: how file formats handle the time dimension](issues/01-research-file-format-time.md): OME readers (tifffile) and OME-NGFF both natively yield / mandate **TCZYX with singleton axes dropped**; time spacing travels via `Pixels.TimeIncrement`/`Plane.DeltaT` (OME) or the NGFF scale vector — absent in all 8 anchor files; PanSeg's current path mislabels or crashes on T-bearing shapes (report: `research/time-dimension/file-format-time.md` on branch `research/time-dimension-research`).
- [Decide the canonical internal axis order](issues/02-decide-canonical-axis-order.md): TCZYX is the canonical full order and every internal array is a projection of it; `ImageLayout` gains TYX/TCYX/TZYX/TCZYX with existing layouts untouched; `stack_layout` extends the alphabet with `t` and ranks T ahead of C.
- [Specify time I/O (import + export)](issues/05-specify-time-io.md): OME-TIFF imports on `series.axes` (T import is OME-only; non-OME stays shape-heuristic and T-unaware); t_spacing from `TimeIncrement`/`DeltaT` else unknown — no prompt at import, user sets it later like voxel size (canonical unit s); multi-file OME rejected; PanSeg h5/zarr gain `axis_order` + `t_spacing` attrs and the app export path starts writing full JSON metadata; time-bearing TIFF always exports as OME-TIFF (`TimeIncrement` when known); mesh export loops per timepoint (`{name}_t{NNN}.ext`); OME-NGFF interop out of scope for v1.
- [Design the time data-model extension](issues/03-design-time-data-model.md): layout carries T and `channel_axis`/`time_axis`/`dimensionality`/`is_timelapse` all derive from the layout string; `ImageDimensionality` stays spatial-only (no 4D/5D members) with orthogonal `is_timelapse`; `t_spacing` (s, None=unknown) + `t_unit` sit on `ImageProperties`, `VoxelSize` stays strictly spatial (merge needs an explicit t_spacing match); squeeze = drop every length-1 non-Y/X axis; TCZYX/TCYX split per channel like today, TYX first-class in v1; h5/napari JSON roundtrip unchanged; "4D" clash settled in the new `CONTEXT.md` glossary (prototype: branch `prototype/time-dimension-data-model`).

## Not yet specified

- Whether the spec should include a quantitative evaluation plan for timelapse segmentation (the repo's `evaluation/` harness is 3D-oriented) — in scope, not yet sharp; revisit once the pipeline spec (ticket 06) is settled.
- Performance expectations for realistic timelapse runs (docs vs benchmarks, `slow` marker policy) — sharpened once the pipeline (ticket 06) and test plan (ticket 08) are settled.

## Out of scope

- Segment tracking over time + merge/split event detection — the stated motivation for this effort; planned as a follow-up effort built on this foundation.
- Spacetime-aware segmentation algorithms (4D watershed/multicut/GASP using T).
- Training new models on timelapse data.
- Out-of-core / chunked / mmap timelapse data handling.
- Multi-file series import (one file per frame).
- Multi-file OME-TIFF (UUID/FileName chain) — rejected at import with a clear error in v1 (settled in [Specify time I/O (import + export)](issues/05-specify-time-io.md)).
- OME-NGFF (OME-Zarr) read/write interop — v1 reads and writes only PanSeg's own zarr format (settled in [Specify time I/O (import + export)](issues/05-specify-time-io.md)).
