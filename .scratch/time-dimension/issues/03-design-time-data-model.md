# Design the time data-model extension

Type: prototype
Status: resolved
Blocked by: 02

## Question

How does T land in the data model — `PanSegImage`, `ImageProperties`, `ImageLayout`, `ImageDimensionality`, `VoxelSize` — so a 3D lightsheet timelapse (with or without channels) is a first-class citizen? Prototype a concrete proposal (draft code + behavior table) to react to, covering:

- New `ImageLayout` members for time-bearing data (per the ticket 02 order) vs an orthogonal `has_time`/`time_axis` concept; how `channel_axis`, `time_axis`, `dimensionality` derive.
- `ImageDimensionality` semantics with T present: spatial-only (2D/3D) + separate time presence, vs new 4D/5D values — and the "4D = CZYX" vocabulary clash resolved (first entry in the new `CONTEXT.md` glossary).
- `t_spacing` + unit in properties (default when the file lacks it — the anchor dataset carries no `TimeIncrement`/`DeltaT`, see ticket 01's answer); the `scale` property / napari axis mapping. Settled in ticket 05: unknown t_spacing is a first-class supported state through all v1 I/O, canonical unit is seconds, and t_spacing must be settable on the image after import, analogous to voxel size (`set_voxel_size_task`).
- Singleton-T (and singleton-C) squeeze rules at import (1-frame file → no T).
- `import_image` channel-splitting interplay (multichannel timelapse → list of single-channel timelapse images) and the `merge_with` reverse path.
- 2D timelapse (TYX): supported in v1 or explicitly rejected (anchor: `time-series.ome.tif` in the dataset).
- Roundtrip of the new properties through h5 metadata and napari layer metadata.

## Answer

Resolved 2026-09-21, prototype (HITL, one round of reaction). Prototype on throwaway branch `prototype/time-dimension-data-model` (local, not pushed), all paths below relative to that branch: `prototype/time-dimension/draft_data_model.py` (draft code), `demo.py` (runnable demo, panseg-fork env), `PROTOTYPE.md` (proposal + decisions), `BEHAVIOR_TABLE.md` (captured output: 8 anchors via real tifffile + 16 edge cases). Shape note: draft code + behavior table rather than the HTML state-machine demo — the object of reaction is the Python API surface.

1. **Layout carries T; nothing about time is stored.** `ImageLayout` gains TYX, TCYX, TZYX, TCZYX (ticket 02). No `has_time`/`time_axis` field: `channel_axis`, `time_axis`, `dimensionality`, `is_timelapse` are all derived from the layout string (projection of canonical T-C-Z-Y-X).
2. **`ImageDimensionality` stays spatial-only (TWO/THREE).** Time presence is the orthogonal `is_timelapse` property (mirrors `is_multichannel`). FOUR/FIVE members rejected: dimensionality routes spatial behavior everywhere (model zoo 2D/3D filter, training, mesh export guard at image.py:911). The "4D = CZYX" clash is settled in the new `CONTEXT.md` glossary: never "4D"/"5D"; name images by layout; "dimensionality" = spatial axes.
3. **`t_spacing: float | None` (seconds) + `t_unit` (normalized to `s`) are fields on `ImageProperties` — deliberately NOT in `VoxelSize`, which stays strictly spatial (z, y, x) µm and is unchanged.** `None` = source carried no timing metadata (true of all 8 anchor files; ticket 01). `ImageProperties.t` returns neutral 1.0 when unknown; napari `scale` puts t on the T axis (outermost slider), 1.0 on C. Consequence accepted: `merge_with` needs an **explicit `t_spacing` match** plus an `is_timelapse` match (VoxelSize equality misses it) — set-vs-set differing ⇒ rejected, set-vs-unknown ⇒ rejected, unknown+unknown ⇒ allowed.
4. **Singleton squeeze = one general rule:** drop every length-1 axis except Y and X; layout = projection onto what remains. Generalizes today's ZYX→YX / CZYX→{YX,ZYX,CYX} casts and gives: 1-frame file → no T, C=1 timelapse → no C, Z=1 timelapse → no Z. (The OME reader already squeezes T/C; the rule covers direct construction, h5 and zarr loads.)
5. **`import_image` / `split_channels`:** C-bearing time layouts split per channel exactly like today (TCZYX → list of TZYX; TCYX → list of TYX); TZYX/TYX import as single images. `merge_with` merged layout is TCYX/TCZYX when time-bearing, CYX/CZYX otherwise.
6. **TYX (2D timelapse) supported in v1** — a required projection (anchor `time-series.ome.tif`), the frame loop (ticket 06) is dimensionality-agnostic, the model zoo has 2D models.
7. **Roundtrip:** h5 (`panseg_image_metadata_json`) and napari layer metadata both carry the `ImageProperties` JSON blob, so `t_spacing`/`t_unit` roundtrip with no format change; old files/layers lack the keys → default `None`/`s`. `element_size_um` stays the spatial 3-float.

Handed downstream (not decided here): prefill/shape-heuristic vs format axis metadata, t_spacing extraction from `TimeIncrement`/`DeltaT`/NGFF scale, and PanSeg zarr attrs gaining t_spacing → "Specify time I/O" (05); T in `m_slicing` and input-tab UX → "Specify viewer/GUI/headless UX for time" (07); per-frame map-over-T that this model enables → "Specify the frame-by-frame pipeline" (06).
