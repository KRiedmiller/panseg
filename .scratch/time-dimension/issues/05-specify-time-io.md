# Specify time I/O (import + export)

Type: grilling
Status: resolved
Blocked by: 01, 02

## Question

What exactly does v1 import and export for time?

Import:

- OME-TIFF with T (single file, multipage, BigTIFF): axis conversion to the ticket 02 order, t_spacing extraction from `Pixels.TimeIncrement`/`Plane.DeltaT` (both optional in the 2016-06 schema; the anchor dataset carries neither → missing-case default, see ticket 01's answer), singleton-T squeeze, `stack_layout` syntax, and `shape_to_stack_layout` guessing for 4D/5D shapes (ticket 01 recommends switching from shape heuristics to format axis metadata — `series.axes` / NGFF `axes` — decide here).
- panseg h5 + zarr: what the on-disk format gains for T + t_spacing.
- Non-uniform frame sizes within a timelapse: reject at import (assumption — confirm).

Export:

- The TIFF writer (`panseg/io/tiff.py`) already writes a TZCYXS slot with T=1: write real T through it (writer axis order vs internal order).
- h5/zarr roundtrip including t_spacing.
- Mesh export is currently gated to 3D: what does mesh export mean for a timelapse in v1 (first frame, per-frame, disabled)?

Anchor: the 8 example files in `/tmp/opencode/ome_tiff_examples`.

## Answer

Resolved 2026-09-21, grilling, two rounds + confirmation. The v1 time I/O contract:

**Import**

1. **Axis authority (OME-TIFF).** The `stack_layout` prefill for OME-TIFF comes from format metadata, not shape: tifffile's `series.axes` (authoritative per-file axis string, singleton axes already dropped by the reader, e.g. `time-series.ome.tif` → `TYX`). T import is OME-TIFF only; the non-OME paths (ImageJ, shaped TIFF, PIL) and PanSeg-owned h5/zarr lacking the new attr (point 4) keep the existing shape heuristic and stay T-unaware in v1. The `shape_to_stack_layout` `IndexError` on 4D shapes with no dim < 10 (`panseg/io/io.py:120`) is fixed to return `""` (no prefill) instead of crashing.
2. **t_spacing.** Extraction order: `Pixels.TimeIncrement[+Unit]`; else `Plane.DeltaT` (first plane per timepoint; present but non-uniform across timepoints → warn, treat as missing); missing (true for all 8 anchor files) → t_spacing unknown. Canonical unit in the model: seconds; `ms`/`min`/etc. converted at import. **No prompt at import**: import proceeds with unknown t_spacing, and unknown is a first-class supported state through all v1 I/O (export writes no time metadata; roundtrip preserves unknown). The user supplies t_spacing later, analogous to the input tab's set-voxel-size widget (`set_voxel_size_task`, `panseg/viewer_napari/widgets/input.py:329`); the UI field and headless yaml parameter are specified in ticket 07.
3. **Boundaries.** Multi-file OME-TIFF (UUID/FileName chain): rejected at import with a clear error — detection is more than one distinct `(UUID, FileName)` pair over the `TiffData` of the `Image` in use, or any `FileName` not matching the opened file (research report §2.3). Multi-position OME (several `<Image>` elements): unchanged, first position. Non-uniform frame sizes: impossible in OME-TIFF (single `SizeX`/`SizeY`/`SizeZ` per `Pixels`) — one spec line, no rejection mechanism.
4. **PanSeg h5/zarr on-disk gains.** (a) New dataset attr `axis_order` (e.g. `"TZYX"`) written on every export — additive, old readers ignore it; the prefill for PanSeg-owned files reads it, falling back to the shape heuristic for older files. (b) New attrs `t_spacing` + `t_spacing_unit` when T is present and known. (c) `create_h5`/`create_zarr` (the app's export path via `save_image`) start writing `panseg_image_metadata_json` too, fixing the asymmetry where only `PanSegImage.to_h5` wrote it and app-exported h5 was not re-importable via `from_h5`.
5. **OME-NGFF (OME-Zarr) interop**: out of scope for v1 (both reading conforming NGFF stores and writing them); PanSeg's own zarr format only.

**Export**

6. **TIFF.** A time-bearing image is always written as OME-TIFF; the ImageJ branch stays time-less. `create_tiff` gains the T layouts (TYX, TCYX, TZYX, TCZYX), mapped into the existing TZCYXS slot — T fills the currently-singleton T slot, C/Z swap as today. `TimeIncrement`/`TimeIncrementUnit` written when t_spacing is known; unknown → `SizeT` with no time metadata. BigTIFF behavior unchanged (>4 GiB or forced). Time-bearing images export only to tiff/h5/zarr, not PIL/jpg.
7. **h5/zarr roundtrip** via point 4's attrs: t_spacing written when known, attrs absent when unknown; re-import yields unknown again.
8. **Mesh.** A 3D time-bearing segmentation: `save_image` loops over timepoints and calls the existing `create_mesh` once per 3D frame slice; one file per timepoint named `{name_pattern}_t{index:03d}.{ext}` (0-based index, e.g. `seg_t000.glb`) — necessary for headless workflow compatibility. Empty timepoints still get their file (an empty scene), preserving the 1:1 timepoint↔file mapping. `close_mesh` applies per frame. The 3D gate is untouched: TYX segmentations still get "Mesh export only supported for 3D".

**Not decided here** (owned by the linked tickets):

- T=1 singleton squeeze rule at import, the `t_spacing` field in `ImageProperties` (including settable-after-import and unknown-is-valid), and the napari `scale`/axis-label mapping for T → "Design the time data-model extension" (03).
- The input-tab t_spacing field, its headless yaml parameter, and the export UI for per-frame mesh output → "Specify viewer/GUI/headless UX for time" (07).

Evidence: research report `research/time-dimension/file-format-time.md` on branch `research/time-dimension-research` (ticket 01); code facts: `panseg/io/{io,tiff,h5,zarr}.py`, `panseg/core/image.py`, `panseg/io/mesh.py`, `panseg/viewer_napari/widgets/input.py`.
