# Research: how file formats handle the time dimension

Type: research
Status: resolved
Blocked by: none

## Question

How do the file formats and reader libraries PanSeg supports represent, order, and metadata the time dimension, so the canonical axis order decision (ticket 02) and the import spec (ticket 05) rest on actual reader behavior rather than assumptions?

Specifically:

- OME-TIFF: the OME-XML model (`SizeT`, `DimensionOrder`, `PhysicalSize T=...` with unit); how `tifffile` (and OME-TIFF readers generally) reshape a multipage series — which axis order comes back, how singletons are handled; how common time-spacing metadata is in real files; single-file vs multi-file series; BigTIFF.
- OME-NGFF (zarr): the explicit axis-string convention (e.g. "TCZYX"), how zarr/napari readers return the array, how time-spacing metadata (axis metadata with unit) is stored.
- HDF5: what PanSeg's own h5 format (`panseg/io/h5.py`) would need for T + t_spacing, and community h5 conventions.
- Ecosystem vocabulary: how the OME world names the dimension ("t", "time", "frame") — input for the glossary (ticket 03).
- Local evidence: inspect the 8 example files in `/tmp/opencode/ome_tiff_examples` (tifffile series shapes, IFD/TiffData ordering, PhysicalSize presence).

Capture findings as a markdown report on the throwaway `research/time-dimension-research` branch, linked from this ticket.

## Answer

Resolved on branch `research/time-dimension-research` (commit `36ea70ab`, local, not pushed): full report at `research/time-dimension/file-format-time.md` (evidence tables, file:line refs, sources).

Key facts:

- **Reader axis order.** tifffile OME-TIFF returns `reversed(DimensionOrder)` — standard files arrive as **TCZYX with singleton axes dropped** (verified on all 8 anchor files). OME-NGFF readers never transpose; the spec mandates time-before-channel-before-space and its canonical 5D example is **TCZYX**. → TCZYX is reader-native on both OME paths.
- **Time spacing.** The 2016-06 OME-XML schema has **no `PhysicalSize` element for time** (corrects the ticket premise) — the mechanisms are `Pixels.TimeIncrement[+Unit]` (default unit s) and per-plane `Plane.DeltaT[+Unit]`; none of the 8 anchor files carry either → t_spacing extraction needs a missing-case default. NGFF: per-dataset `coordinateTransformations.scale` (entry 0 = timestep) + axis unit (UDUNITS-2).
- **PanSeg current path (measured).** OME files return VoxelSize `None` (reader only parses `PhysicalSizeX/Y/Z` attrs); Z-only/T-only shapes are silently mislabeled as channels in the prefill; `shape_to_stack_layout` crashes with `IndexError` (`panseg/io/io.py:120`) on 4D/5D shapes; T is unexpressible (no `T` in `ImageLayout`, `VoxelSize` hard 3-tuple, ndim check at `panseg/core/image.py:702`).
- **Consequence for the order decision (ticket 02).** TCZYX makes both OME import paths identity mappings; it breaks the C-at-axis-0 invariants and makes shape-based guessing worse — either way the import spec must switch from shape heuristics to format axis metadata (`series.axes` / NGFF `axes`).
- **Vocabulary for the glossary (ticket 03).** dimension = **time** (`T`); value = **timepoint** (not "frame"); interval = **time spacing**/**timestep** with unit (default s).
