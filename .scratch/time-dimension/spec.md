# Spec: Time as a First-Class Dimension in PanSeg

## Provenance and status

This spec is the handoff artifact of the wayfinder effort in
[.scratch/time-dimension/map.md](map.md). Every decision below was already made
and recorded in the effort's tickets; this spec synthesizes them into one
implementation-ready document and cross-checks them against the codebase. It
opens no new decisions. Where a choice is phrased as "mirrors X", the
referenced existing code is the authority on the pattern.

Source tickets (all resolved):

- [01](issues/01-research-file-format-time.md) — research: how file formats handle the time dimension (report: `research/time-dimension/file-format-time.md` on branch `research/time-dimension-research`)
- [02](issues/02-decide-canonical-axis-order.md) — canonical internal axis order
- [03](issues/03-design-time-data-model.md) — data-model extension (prototype branch `prototype/time-dimension-data-model`)
- [04](issues/04-decide-frame-loop-architecture.md) — frame-by-frame loop architecture
- [05](issues/05-specify-time-io.md) — time I/O (import + export)
- [06](issues/06-specify-frame-by-frame-pipeline.md) — per-stage pipeline behavior
- [07](issues/07-specify-viewer-gui-headless-ux.md) — viewer/GUI/headless UX
- [08](issues/08-specify-tests-fixtures-docs.md) — tests, fixtures, docs, definition of done
- [10](issues/10-decide-timelapse-evaluation-plan.md) — evaluation plan (spec stays silent; see Non-goals)

Code references are `file:line` as of 2026-09-24. If a line number has drifted,
the named symbol is the anchor.

Anchor dataset for manual sanity checks: 8 example OME-TIFFs from
`/home/kriedmiller/Downloads/ome_tiff_examples.tar.xz` (read-only extracted
copies at `/tmp/opencode/ome_tiff_examples`), covering single/multi-channel ×
2D/3D/time/4D. `4D-series.ome.tif` is 7t×5z×167y×439x int8;
`multi-channel-4D-series.ome.tif` is 7t×3c×5z×167y×439x. None of the 8 carries
timing metadata (`Pixels.TimeIncrement` or `Plane.DeltaT`), so unknown time
spacing is a first-class, expected state, not an edge case.

## Summary

PanSeg gains time as a first-class dimension. A single fixed internal axis
order, **TCZYX**, governs every internal array: each array is a projection of
T-C-Z-Y-X onto the axes it actually carries. Time is carried by the layout
string alone — no separate time fields on the image. All per-pixel work runs
**frame-by-frame**: a transparent `@timepoint_map` wrapper in the tasks layer
maps each frame-mapped task over the timepoints of a timelapse, reusing the
existing 2D/3D task bodies unchanged. There is no cross-timepoint information
flow anywhere in v1. A 3D lightsheet timelapse (with or without channels) can
be imported, segmented timepoint by timepoint, proofread one timepoint at a
time, and exported with time preserved.

v1 scope in one line: layouts TYX/TCYX/TZYX/TCZYX, OME-TIFF/h5/zarr import and
export with time, `t_spacing` settable after import, frame-by-frame
preprocessing/prediction/segmentation, single-timepoint proofreading, and the
tests and docs that pin all of it down.

## Non-goals

Explicitly out of scope for v1. An implementer who reaches one of these has
found the edge of the spec, not a gap in it:

- **Segment tracking over time** and merge/split event detection — the stated
  motivation for the effort, planned as a follow-up effort built on this
  foundation.
- **Spacetime-aware segmentation algorithms** (4D watershed/multicut/GASP using
  T). Any operation whose output depends on neighbouring timepoints is a
  spacetime operation and out of scope.
- **Training new models on timelapse data.** `unet_training_task` is not
  frame-mapped (its image inputs are napari layers / dataset dirs, not
  `PanSegImage`); existing models are reused per timepoint.
- **Out-of-core / chunked / mmap timelapse data handling.** In-memory numpy is
  retained.
- **Multi-file series import** (one file per frame) and **multi-file
  OME-TIFF** (UUID/FileName chain) — the latter is rejected at import with a
  clear error (see Import).
- **Partial-failure tolerance** (skip or fill a failed timepoint with a
  warning). v1 aborts the run on the first failed timepoint.
- **OME-NGFF (OME-Zarr) read/write interop.** PanSeg reads and writes only its
  own zarr format.
- **Writing `panseg_image_metadata_json` from the app export path**
  (`save_image` → `create_h5`/`create_zarr`). The pre-existing asymmetry where
  app-exported h5/zarr is not re-importable via `PanSegImage.from_h5` stands
  (file-path import works via the new `axis_order` attr). Ruled out of v1 as
  not connected to time.
- **Performance expectations.** No performance section in the spec or docs, no
  benchmarking, no numeric targets: memory and runtime depend heavily on input
  and task, and the time dimension should not influence per-timepoint
  execution for most tasks.
- **Quantitative timelapse evaluation.** No metrics, fixture targets, or
  `evaluation/` harness usage in the spec. Per-timepoint segmentations remain
  evaluable by the existing 3D workflow (the metric layer, `run_evaluation` at
  `evaluation/evaluation_segmentation.py:75`, is shape-agnostic — slice each
  timepoint, call it, collect per-timepoint rows). Cross-timepoint consistency
  metrics (object tracking, identity consistency across timepoints, trajectory
  scores) are out of scope and belong to the planned tracking follow-up;
  nothing in the pipeline has cross-timepoint flow by design, so any such
  metric would measure the absence of the feature rather than quality.

## Vocabulary

The shared glossary lives in [CONTEXT.md](../../CONTEXT.md) and is
authoritative: **dimensionality** is spatial only (2D/3D, never counting C or
T); **layout** names the exact axis set and order; **timelapse** = an image
with a time axis; **timepoint** = one T index (never "frame"); **time
spacing** = interval between consecutive timepoints with unit (seconds),
possibly unknown. Never write "4D"/"5D" — name images by layout.

Two terms are spec-specific, from the loop-architecture decision:

- **Frame-by-frame**: the v1 strategy name, defined as "process each
  timepoint independently, with no cross-timepoint information flow". It is a
  strategy description, not a noun for the loop machinery.
- **Frame-mapped** task: a task the `@timepoint_map` wrapper maps over
  timepoints; the task body never sees T. **Stack-level** task: a task that
  operates on the whole timelapse as one object. Every task is one or the
  other, explicitly (see Frame-by-frame loop architecture).

## Canonical axis order and layouts

**Decision: TCZYX is the canonical full axis order.** Every internal array is
a projection of T, C, Z, Y, X: only the present axes, in that relative order.
Rationale (ticket 02):

- Reader-native on both OME paths: tifffile's OME-TIFF output is TCZYX with
  singleton axes dropped (verified on all 8 anchor files), and the OME-NGFF
  spec mandates time before channel before space. OME-TIFF import is an
  identity mapping — no transpose.
- It extends the existing C-Z-Y-X canonical order by prepending T, so the
  four existing layouts are untouched projections of it.

Accepted consequences:

- In time-bearing data the channel axis sits at index 1, not 0.
- napari layers take memory order as-is (the existing mechanism for all
  layouts), so T is the outermost slider, above Z.
- TIFF export reuses the existing TZCYXS slots of `create_tiff`
  (`panseg/io/tiff.py:167`, slot layout at `:186-261`), T filling the
  currently-singleton T slot with the C/Z swap applied as today.

`ImageLayout` (`panseg/core/image.py:71`) gains exactly four members:
**TYX, TCYX, TZYX, TCZYX**. YX, CYX, ZYX, CZYX and the deprecated ZCYX
pass-through are unchanged; v1 behavior for non-time data is untouched. TCYX
is required, not optional: anchor `multi-channel-time-series.ome.tif` is
(T,C,Y,X) = (7,3,167,439).

`stack_layout` input syntax: the alphabet is extended with `t` — any
permutation of the present letters, the existing `-` inversion syntax
unchanged (e.g. `tzyx`, `tczyx`, `-tzyx`). `stack_sort`
(`panseg/core/image.py:626`) ranks T ahead of C, so its rank order becomes
T, C, Z, Y, X; strings without `t` behave exactly as today.

## Data model

### Layout carries T; nothing about time is stored

No `has_time`/`time_axis` field anywhere. `channel_axis`, `time_axis`,
`dimensionality`, and `is_timelapse` are all **derived from the layout
string** (projection of the canonical T-C-Z-Y-X order). `is_timelapse` is a
property on `PanSegImage` mirroring `is_multichannel`
(`panseg/core/image.py:609`). The existing derived properties
`dimensionality` (`panseg/core/image.py:119`) and `channel_axis`
(`panseg/core/image.py:141`) extend to the new layouts by projection.

`ImageDimensionality` (`panseg/core/image.py:58`) **stays spatial-only**
(TWO/THREE). No FOUR/FIVE members: dimensionality routes spatial behavior
everywhere (model zoo 2D/3D filter, training, the mesh-export 3D gate at
`panseg/core/image.py:911`), and both CZYX and TZYX are four-axis arrays, so
any "4D" member would be ambiguous. Time presence is the orthogonal
`is_timelapse`.

### Time spacing on ImageProperties

`ImageProperties` (`panseg/core/image.py:99`) gains two fields:

- `t_spacing: float | None` — the time spacing in **seconds**. `None` = the
  source carried no timing metadata (true of all 8 anchor files). Unknown is
  a first-class supported state through all v1 I/O.
- `t_unit: str = "s"` — normalized to `s` (source units `ms`/`min`/etc. are
  converted at import).

Deliberately **not** in `VoxelSize` (`panseg/io/voxelsize.py:19`), which stays
strictly spatial (z, y, x) micrometers and is unchanged, including the
`element_size_um` on-disk 3-float in h5/zarr.

`ImageProperties` gains a `t` property returning `t_spacing`, or neutral
**1.0** when unknown. `PanSegImage.scale` (`panseg/core/image.py:533`) gains
the T layouts: the T axis takes `properties.t`, the C axis 1.0 (as today),
spatial axes as today — so in napari the outermost slider is scaled by the
time spacing when known.

### Singleton squeeze rule

One general rule: **drop every length-1 axis except Y and X; the layout is
the projection onto what remains.** This generalizes today's ZYX→YX /
CZYX→{YX,ZYX,CYX} casts and gives: 1-frame file → no T, C=1 timelapse → no
C, Z=1 timelapse → no Z. The OME reader already squeezes T/C at the reader
boundary; the rule is what covers direct construction and h5/zarr loads.

### Channel splitting and merging

`import_image` (`panseg/core/image.py:675`) and `split_channels`
(`panseg/core/image.py:272`) split C-bearing time layouts per channel exactly
like today: TCZYX → list of TZYX images, TCYX → list of TYX images (names
`f"{name}_{ch}"` as today). TZYX/TYX import as single images.
`merge_with` (`panseg/core/image.py:293`) merged layout is TCYX/TCZYX when
time-bearing, CYX/CZYX otherwise. Because `VoxelSize` equality cannot see time
spacing, `merge_with` additionally requires an explicit **t_spacing match**
plus an `is_timelapse` match: set-vs-set differing ⇒ rejected, set-vs-unknown
⇒ rejected, unknown+unknown ⇒ allowed.

### TYX (2D timelapse) is supported

A required projection (anchor `time-series.ome.tif`), not a rejected case.
The frame loop is dimensionality-agnostic and the model zoo has 2D models.

### Roundtrip

h5 (`panseg_image_metadata_json` written at `panseg/core/image.py:380`, read
at `:397`) and napari layer metadata (via `to_napari_layer_tuple`,
`panseg/core/image.py:323`) both carry the `ImageProperties` JSON blob, so
`t_spacing`/`t_unit` roundtrip with no format change. Old files and old JSON
lack the keys → default `None`/`"s"`.

## Frame-by-frame loop architecture

The loop is a **transparent, opt-in decorator in the tasks layer** over a pair
of core split/restack helpers (ticket 04). Both execution paths are covered
for free: the GUI runs the `task_tracker` wrapper, the headless `SerialRunner`
(`panseg/headless/basic_runner.py`) calls the registered callable — and
`task_tracker` (`panseg/tasks/workflow_handler.py:332`) registers the
decorated function, so the loop sits under the recording layer on both paths.

### Mechanism

`@timepoint_map`, stacked directly under `@task_tracker`, applied per task;
task bodies unchanged. At call time it inspects kwargs: any `PanSegImage`
input with `is_timelapse` → map over timepoints; no T-bearing input → pass
through untouched (non-T calls behave exactly as today).

Core helpers in `panseg/core/image.py` (data-model ops):

- `PanSegImage.split_timepoints()` — method, mirrors `split_channels`
  (`panseg/core/image.py:272`).
- `restack_timepoints(timepoints, t_spacing, t_unit)` — module-level function.

Split: each timepoint is a `derive_new` (`panseg/core/image.py:177`) — data =
the T slice, layout = T dropped (TZYX→ZYX, TYX→YX; by the squeeze rule the
timepoint layout is exactly ZYX or YX), name = `f"{name}_t{i}"` (mirrors the
channel naming convention), `t_spacing`/`t_unit` → `None` (a timepoint is not
a timelapse). `voxel_size`, `semantic_type`, `source_file_name` propagate
automatically.

Restack: `np.stack` along a new outer T axis; validates identical shape /
layout / `voxel_size` / `semantic_type` across timepoints (the same checks as
`merge_with`, `panseg/core/image.py:293`); the wrapper stamps the parent's
`t_spacing`/`t_unit` onto the result (lost on split). Label outputs restack
with identical mechanics — **no cross-timepoint ID renumbering** (see Label
semantics below).

### Task classification

Every task is explicitly **frame-mapped** or **stack-level**. Spec rule: a
non-decorated task receiving a T-bearing input is an error, not a mystery
crash.

Frame-mapped (17 — the task never sees T):

| Task | Location |
| --- | --- |
| `gaussian_smoothing_task` | `panseg/tasks/dataprocessing_tasks.py:28` |
| `image_cropping_task` | `panseg/tasks/dataprocessing_tasks.py:92` |
| `set_voxel_size_task` (property-only) | `panseg/tasks/dataprocessing_tasks.py:124` |
| `set_t_spacing_task` (new, property-only, see Viewer UX) | new, alongside `set_voxel_size_task` |
| `image_rescale_to_shape_task` | `panseg/tasks/dataprocessing_tasks.py:145` |
| `image_rescale_to_voxel_size_task` | `panseg/tasks/dataprocessing_tasks.py:207` |
| `remove_false_positives_by_foreground_probability_task` (both outputs restacked) | `panseg/tasks/dataprocessing_tasks.py:248` |
| `fix_over_under_segmentation_from_nuclei_task` | `panseg/tasks/dataprocessing_tasks.py:279` |
| `set_biggest_instance_to_zero_task` | `panseg/tasks/dataprocessing_tasks.py:316` |
| `relabel_segmentation_task` | `panseg/tasks/dataprocessing_tasks.py:344` |
| `image_pair_operation_task` | `panseg/tasks/dataprocessing_tasks.py:366` |
| `dt_watershed_task` | `panseg/tasks/segmentation_tasks.py:19` |
| `clustering_segmentation_task` | `panseg/tasks/segmentation_tasks.py:116` |
| `lmc_segmentation_task` | `panseg/tasks/segmentation_tasks.py:189` |
| `aio_watershed_task` | `panseg/tasks/segmentation_tasks.py:234` |
| `unet_prediction_task` | `panseg/tasks/prediction_tasks.py:11` |
| `biio_prediction_task` | `panseg/tasks/prediction_tasks.py:80` |

Stack-level (3 — operate on the whole timelapse as one object):

- `import_image_task` (`panseg/tasks/io_tasks.py:19`) — creates T.
- `export_image_task` (`panseg/tasks/io_tasks.py:68`) — writes T as one file.
- `merge_channels_task` (`panseg/tasks/io_tasks.py:107`) — direct two-stage
  `np.stack` → TCZYX/TCYX via the T-aware `merge_with`; validates T length /
  `voxel_size` / `semantic_type` across channel inputs; no timepoint loop.

`unet_training_task` (`panseg/tasks/training_tasks.py:15`) is not mappable
(its image inputs are napari layers / dataset dirs, not `PanSegImage`);
timelapse training is a non-goal.

### Multi-image rules

- All T-bearing image inputs of a frame-mapped task must have **equal T
  length**, zipped by index; mismatch → `ValueError`.
- Mixed T-bearing + non-T image inputs → `ValueError` by default; a
  task-level decorator flag opts in **broadcast** of the static input to every
  timepoint. v1 opt-ins: `image_pair_operation_task` (e.g. static background
  subtraction) and `remove_false_positives_by_foreground_probability_task`
  (static foreground probability map). `fix_over_under_segmentation_from_nuclei_task`,
  `lmc_segmentation_task`, `aio_watershed_task`, `clustering_segmentation_task`
  keep `ValueError`.
- Differing `t_spacing` across T-bearing inputs → `ValueError`; equal or
  both-`None` is fine, and the restacked output takes the shared spacing.

### Error semantics: abort

The wrapper lets the first failed timepoint's exception propagate — GUI: the
identical `Task_message` flow as any task failure; headless: the job aborts,
exactly as today. No skip/fill/drop: a filled timepoint would silently
corrupt downstream segmentation (indistinguishable from real background), and
a dropped timepoint breaks uniform `t_spacing`, which the data model cannot
represent. A `Task_message` *returned* (not raised) by an inner call is
treated as a failure and propagated.

### Progress and DAG/GUI surface

The wrapper drives `_tracker` at timepoint granularity (total = n_timepoints,
tick per completed timepoint) and passes `_tracker=None` into per-timepoint
calls (the headless-tolerated behavior): one progress level in v1, no
sub-timepoint progress.

The recorded DAG node is identical in shape to today: timelapse image in,
restacked timelapse image out, same parameters. `timepoint_map` is not a
parameter, and timepoints are locals inside the wrapper, never entering
`var_space` (so headless `clean_var_space` is unaffected). GUI: one button
press, one progress bar, one restacked result layer added; per-timepoint
images are transient and never added to the viewer.

Accepted cost: the wrapper holds the parent stack plus per-timepoint outputs
transiently (~2× peak stack memory). No mitigation in v1.

## Per-stage pipeline behavior

Every stage runs per timepoint under `@timepoint_map`; nothing in this section
introduces cross-timepoint information flow.

**Spec invariant:** a frame-mapped task may only read/write within one
timepoint. Any operation whose output depends on neighbouring timepoints is a
spacetime operation and out of scope.

### Preprocessing

- Filters run per timepoint: Gaussian (`image_gaussian_smoothing`,
  `panseg/functionals/dataprocessing/dataprocessing.py:122`, whole-array
  `vigra.gaussianSmoothing`) or a median filter (`image_median`,
  `panseg/functionals/dataprocessing/dataprocessing.py:92`, skimage
  ball/disk) applied to a TZYX stack would smear across T. Median has **no
  task in v1** (functional only, tested in
  `tests/functionals/dataprocessing/test_dataprocessing.py`); if one is ever
  added it must be frame-mapped.
- Crop: one spatial region (XY rectangle + `crop_z`), **identical for every
  timepoint**. No per-timepoint ROI, no registration/drift correction
  (tracking is a non-goal).
- Rescale: the T axis is untouched, `t_spacing` preserved. Under the decorator
  the task body sees ZYX/YX timepoints, so the existing layout chains in the
  rescale tasks work unchanged; voxel size is re-derived per timepoint
  (identical each time).
- Normalization is per timepoint: `normalize_01`
  (`panseg/functionals/dataprocessing/dataprocessing.py:333`) min–maxes over
  whatever array the frame-mapped body sees (one timepoint) — the
  `is_nuclei_image` path in `dt_watershed_task`/`aio_watershed_task` and
  `image_pair_operation_task`'s normalize flags all normalize per timepoint.
  This follows from the wrapper with zero extra machinery, matches the
  no-cross-timepoint strategy, and adapts to illumination drift across a
  lightsheet run.
- `set_voxel_size_task`: property-only, frame-mapped (no data change).

### Prediction

- Per-timepoint 3D/2D inference reusing existing models; a timepoint is
  inferred exactly as a standalone volume is today.
- Patching: `patch`/`patch_halo` are `(Z, Y, X)` spatial tuples; T is never a
  patch dimension. Auto-derivation runs per timepoint
  (`find_feasible_patch_and_halo_shapes`,
  `panseg/functionals/prediction/utils/size_finder.py:236`).
- The model zoo dimensionality filter (`panseg/core/zoo.py:181`) applies to
  the timepoint's spatial dimensionality, unchanged: TYX → 2D models, TZYX →
  3D models.
- OOM/error behavior is inherited single-volume behavior: auto-derive a
  feasible patch with shrink-and-verify; oversized explicit patch →
  `ValueError` (`panseg/functionals/prediction/prediction.py:266-276`);
  nothing fits → `RuntimeError`
  (`panseg/functionals/prediction/utils/size_finder.py:307`). No new T-aware
  memory handling.
- Known cost, accepted for v1 (no caching requirement): `torch.load` +
  `load_state_dict` (`panseg/functionals/prediction/prediction.py:229`) and
  GPU patch probing re-run on every timepoint call — noise on the 7-timepoint
  anchor, minutes of pure reload on long timelapses.

### Segmentation

- All four tasks (`dt_watershed_task`, `clustering_segmentation_task` in
  gasp/multicut/mutex_ws modes, `lmc_segmentation_task`,
  `aio_watershed_task`) run per timepoint with no algorithmic change; the
  `stacked`/`blockwise` options keep working within a timepoint.
- 2D timelapse: TYX → YX timepoints → 2D segmentation per timepoint.
- Multi-image tasks (e.g. lmc: boundary pmap / superpixels / nuclei) zip per
  timepoint under the Multi-image rules above.

### Proofreading: one explicitly selected timepoint per session

Decision (C1, chosen over refusing timelapse proofreading outright): the
destination requires the timelapse to be proofread, and C1's delta is
contained to one widget module, reuses all 2D/3D machinery untouched, and is
the same work a follow-up effort would pay anyway.

- The session binds to one timepoint `k` **explicitly selected by the user**
  (selection UI: see Viewer UX).
- The handler world is the slice: `segmentation` reads `layer.data[k]` (live
  from the layer); `get_bboxes`
  (`panseg/functionals/proofreading/utils.py:78`, ndim 2/3 dispatch that
  raises on 4D) runs on the ZYX/YX slice — the 4D breakage of the bbox
  machinery on TZYX arrays is sidestepped by construction — and
  `split_merge_from_seeds` + watershed are reused untouched.
- Helper layers (`Scribbles`, `Correct Labels`) are created as 2D/3D slices
  named `Scribbles (t={k})` / `Correct Labels (t={k})` so ownership is
  unambiguous; the "not intended to be proofread" checks
  (`panseg/viewer_napari/widgets/proofreading.py:636`) match by prefix. One
  single layer of each, **persisting across timepoint changes** — no
  clearing, no reset, no re-initialization. The `(t={k})` name tracks the
  session's current timepoint.
- Write-back: `layer.data[k, *region_slice] = new_seg`; all other timepoints
  untouched.
- Session-scoped state: `max_label`, corrected-cells set, corrected mask,
  undo/redo history live on the slice and recompute on re-bind to a new
  timepoint (undo snapshots are one ZYX/YX slice, not TZYX-stack copies). The
  scribbles/corrected canvas content is the exception — it persists across
  timepoint changes.
- Save/load state (`panseg/viewer_napari/widgets/proofreading.py:282`,
  `:314`): the full TZYX label array (only timepoint `k` edited) + a
  `timepoint` attr + the corrected cells of `k`; load re-initializes the
  session on `k`.
- Extract corrected labels: a single-timepoint layer of the proofread
  timepoint's corrected cells, named with the `_t{NNN}` convention — not a
  full-length timelapse with mostly empty timepoints.
- Proofreading another timepoint mid-session = **re-bind, not re-initialize**:
  changing the selection re-binds the session to the new timepoint — no
  `are_you_sure` reset, no clearing of the persistent canvases, no extra
  blocking logic; bboxes/corrected-cells/undo recompute for the new slice.
  **Stale-marks hazard (call out in docs and the widget hint):** marks from a
  processed timepoint remain on the persistent canvases and would be applied
  to the next timepoint if Split/Merge runs before the existing Clean button
  is used.
- Premise: single-channel timepoints. Channels are split at import, so
  multichannel images never reach proofreading — no guard.
- Proofreading stays a GUI-interaction step (a direct in-place mutation of the
  labels layer, `panseg/viewer_napari/widgets/proofreading.py`); it is not a
  DAG task and is absent from headless yamls. The headless frame-by-frame
  pipeline covers preprocessing, prediction, and segmentation only.

### Label semantics (stated explicitly)

- **Independent per-timepoint label IDs, no correspondence across timepoints.**
  Label 5 at t=0 and label 5 at t=1 are different cells.
- `relabel_segmentation`
  (`panseg/functionals/dataprocessing/labelprocessing.py:5`) renumbers
  connected components **per timepoint** (spatial connectivity only);
  overlapping ID ranges across timepoints are expected and never "fixed".
- `set_biggest_instance_to_zero`
  (`panseg/functionals/dataprocessing/labelprocessing.py:93`) zeros the
  largest component *within each timepoint* — "largest" is recomputed per
  timepoint. Call this out for users running it on a timelapse (docs +
  task docstring).
- Restacking never renumbers across timepoints.

## Import

### Axis authority: format metadata, not shape guessing

- The `stack_layout` prefill for **OME-TIFF** comes from tifffile's
  `series.axes` — the authoritative per-file axis string, singleton axes
  already dropped by the reader (e.g. `time-series.ome.tif` → `TYX`). The
  prefill hook is `update_stack_layout`
  (`panseg/viewer_napari/widgets/input.py:296`), which today funnels every
  format through `shape_to_stack_layout`.
- **T import is OME-TIFF only.** The non-OME paths (ImageJ, shaped TIFF, PIL)
  and PanSeg-owned h5/zarr lacking the new `axis_order` attr (below) keep the
  existing shape heuristic and stay T-unaware in v1.
- The `shape_to_stack_layout` `IndexError` on 4D shapes with no dim < 10
  (`panseg/io/io.py:99`, the crashing `d_to_put.pop()` at `:120`) is fixed to
  return `""` (no prefill) instead of crashing.

### t_spacing extraction

Extraction order for OME-TIFF import:

1. `Pixels.TimeIncrement[+Unit]`
2. else `Plane.DeltaT` (first plane per timepoint; present but **non-uniform
   across timepoints → warn, treat as missing**)
3. else (missing — true for all 8 anchor files) → t_spacing **unknown**

Canonical unit in the model: **seconds**; `ms`/`min`/etc. converted at
import. **No prompt at import**: import proceeds with unknown t_spacing, and
unknown is a first-class supported state through all v1 I/O (export writes no
time metadata; roundtrip preserves unknown). The user supplies t_spacing
later via `set_t_spacing_task` (see Viewer UX), analogous to the existing
set-voxel-size widget.

### Boundaries

- **Multi-file OME-TIFF** (UUID/FileName chain): rejected at import with a
  clear error. Detection: more than one distinct `(UUID, FileName)` pair over
  the `TiffData` of the `Image` in use, or any `FileName` not matching the
  opened file.
- Multi-position OME (several `<Image>` elements): unchanged — first
  position.
- Non-uniform frame sizes: impossible in OME-TIFF (a single `SizeX`/`SizeY`/
  `SizeZ` per `Pixels`) — one spec line, no rejection mechanism.

### PanSeg h5/zarr on-disk gains

- New dataset attr **`axis_order`** (e.g. `"TZYX"`) written on **every**
  export — additive, old readers ignore it. The prefill for PanSeg-owned
  files reads it, falling back to the shape heuristic for older files.
- New attrs **`t_spacing`** + **`t_spacing_unit`** when T is present and
  known.
- The app export path does **not** start writing
  `panseg_image_metadata_json` (non-goal, see above).

### `import_image` T branches

`import_image` (`panseg/core/image.py:675`) gains T branches mirroring the
existing per-layout branches (the YX/ZYX branch with `m_slicing` at `:714`,
the CYX/CZYX channel-split branches): TZYX/TYX import as a single image
(`m_slicing` applied as in the YX/ZYX branch via `image_crop`,
`panseg/functionals/dataprocessing/dataprocessing.py:139`); TCZYX/TCYX split
per channel into TZYX/TYX images.

## Export

### TIFF

- A time-bearing image is **always written as OME-TIFF**; the ImageJ branch
  stays time-less. `create_tiff` (`panseg/io/tiff.py:167`) gains the T
  layouts (TYX, TCYX, TZYX, TCZYX), mapped into the existing TZCYXS slot — T
  fills the currently-singleton T slot, C/Z swap as today.
- `TimeIncrement`/`TimeIncrementUnit` written when t_spacing is known;
  unknown → `SizeT` with no time metadata.
- BigTIFF behavior unchanged (>4 GiB or forced).
- Time-bearing images export only to tiff/h5/zarr, not PIL/jpg.

### h5/zarr

Roundtrip via the Import attrs: `axis_order` always; `t_spacing`/
`t_spacing_unit` written when known, attrs absent when unknown; re-import
yields unknown again. `element_size_um` stays the spatial 3-float.

### Mesh

A 3D time-bearing segmentation: `save_image` (`panseg/core/image.py:835`)
loops over timepoints and calls the existing `create_mesh`
(`panseg/io/mesh.py:10`) once per 3D frame slice. One file per timepoint,
named **`{name_pattern}_t{index:03d}.{ext}`** (0-based index, e.g.
`seg_t000.glb`) — necessary for headless workflow compatibility. Empty
timepoints still get their file (an empty scene), preserving the 1:1
timepoint↔file mapping. `close_mesh` applies per frame. The 3D gate is
untouched (`panseg/core/image.py:908-917`): TYX segmentations still get
"Mesh export only supported for 3D".

## Viewer, GUI, and headless UX

### napari display

- `to_napari_layer_tuple` (`panseg/core/image.py:323`) gains `axis_labels`
  for **every** layout, derived from the layout string (t/c/z/y/x) — uniform,
  not T-only. `scale` per the data-model decision (T axis = time spacing,
  1.0 when unknown; C = 1.0). The T slider is napari's default leading-axis
  slider; no custom time widget.
- Channel operations on T-bearing images: split at import (multichannel
  timelapse → list of single-channel timelapse layers, each its own layer);
  merge via the existing output-tab n_channels/additional-channels widget
  (T-aware `merge_with`, stack-level) and the prediction tab's additional
  inputs — no new GUI.

### Input tab

- `stack_layout` (`panseg/viewer_napari/widgets/input.py:138`): T layouts
  (TYX/TCYX/TZYX/TCZYX) accepted for **every** format — the layout is the
  user's explicit assertion about their own data; only the prefill is
  OME-aware (`series.axes`) per the I/O decision. Tooltip updated to mention
  `t` for time.
- `m_slicing` (parameter of `import_image_task`,
  `panseg/tasks/io_tasks.py:25`) extended to T layouts: string positions
  follow the layout, **T first** (e.g. `"0:3,:, :50"` on TZYX); a T slice of
  length 1 squeezes to no-T per the squeeze rule. It is the **only** T
  sub-range mechanism in v1 — with in-memory numpy, the practical knob for
  long timelapses.
- New **`set_t_spacing_task`** mirroring `set_voxel_size_task`
  (`panseg/tasks/dataprocessing_tasks.py:124`): signature
  `set_t_spacing_task(image: PanSegImage, t_spacing: float | None) ->
  PanSegImage`; derives a `f"{image.name}_set_t_spacing"` layer; recorded as
  a DAG node (the headless yaml mechanism). The input tab's Details section
  gains a "Time spacing [s]" float field + button, shown only when the
  selected layer is a timelapse; empty field = unknown (`None`); the Details
  info shows the time spacing when known. Frame-mapped, property-only per the
  loop-architecture classification.

### Preprocessing tab

- The legacy hide guard (`panseg/viewer_napari/widgets/preprocessing.py:580`,
  "Preprocessing not supported for 4d images") is **removed** — import-time
  channel splitting means multichannel layers essentially never reach the
  tab. All frame-mapped task widgets show for every single-channel layout
  (YX, ZYX, TYX, TZYX); multichannel layers (reachable only after an explicit
  merge) hit the existing task-level rejections.
- Rescale/crop fields prefill from the spatial axes only (T never surfaced;
  fixes the `# TODO: fix for 4d images` loop at
  `panseg/viewer_napari/widgets/preprocessing.py:596`).
- Crop on a timelapse = one spatial crop (y/x rectangle + z range) applied
  identically to every timepoint (a frame-mapped task sees identical
  parameters); the rectangle is drawn in a shapes layer matching the image's
  dimensionality (the hard-coded `ndim=3` at
  `panseg/viewer_napari/widgets/preprocessing.py:84` follows the layer
  instead), and the rectangle's position along T is ignored by the crop.

### Segmentation tab

- The branching (`panseg/viewer_napari/widgets/segmentation.py:493-500`)
  switches from exact layout to **spatial dimensionality**: TZYX behaves as
  3D (2D/3D watershed, stacked mode shown), TYX as 2D; no "Unsupported image
  layout" log for any T layout (the log remains for genuinely unsupported
  layouts, e.g. multichannel). The model zoo's dimensionality filter uses
  spatial dimensionality (3D models for TZYX; no T-specific models in v1).

### Proofreading widget

- A timelapse segmentation is proofread **one timepoint at a time**, selected
  by a new **int input (0..T-1)** in the proofreading widget, shown only for
  timelapse segmentations. The int input — not the T slider — is the
  timepoint selector: changing it moves the T slider to that timepoint
  (one-way; the input defaults to the slider's position at initialisation).
  Drawing is 3D within the selected timepoint; one does not draw with the T
  dimension.
- One single "Scribbles" canvas and one single "Correct Labels" canvas:
  persistent 3D (z,y,x) workspaces with no T dimension, named
  `Scribbles (t={k})` / `Correct Labels (t={k})`, the name tracking the
  session's current timepoint; displayed at the selected timepoint (how the
  3D canvas aligns with the TZYX segmentation layer in the viewer is an
  implementation detail).
- Mid-session timepoint change = **re-bind, not re-initialize**: no
  `are_you_sure` reset, no clearing, no extra blocking logic. The canvases
  persist with their marks; derived session state (bboxes, corrected-cells
  set, undo/redo) recomputes for the new slice. The stale-marks hazard (see
  Per-stage pipeline behavior) is called out in the widget.
- When the displayed timepoint (T slider) differs from the session's
  timepoint (int input), operations — Split/Merge, double-click
  mark-corrected — are **refused with a log hint** (the one-way slider
  allows the divergence; silent application would mark the cell at
  (`k`, z, y), a different cell than the one under the cursor).
- Split/Merge corrects only the selected timepoint: handler world is the
  slice, write-back touches only timepoint `k` (see Per-stage pipeline
  behavior). Cost: none at timelapse scale — helper layers and undo
  snapshots are slice-sized, not full-timelapse.

### Output tab

Status quo, now T-aware: export formats are already tiff/h5/zarr only (no
PIL/jpg export option exists); time-bearing tiff export writes OME-TIFF with
`TimeIncrement` when the time spacing is known; per-timepoint mesh output
`{name_pattern}_t{index:03d}.{ext}` for 3D timelapse segmentations — no new
widgets.

### Workflow editor and headless

- No DAG changes (transparent wrapper): the recorded node shape for a
  timelapse is identical to today (timelapse image in, restacked timelapse
  image out, same parameters).
- The `panseg --edit` editor (CLI flag at `panseg/run_panseg.py:47`; per-task
  entry widgets at `panseg/workflow_gui/widgets.py`) gains a dedicated entry
  for `set_t_spacing_task`: one float spin box (seconds), mirroring the
  `set_voxel_size_task` entry (`panseg/workflow_gui/widgets.py:457`).

### Complete example headless workflow

Assembled from the settled decisions: import (TZYX), set time spacing,
frame-mapped tasks with unchanged parameters, export. Ids and output suffixes
are illustrative; `images_inputs` wire by exact output name.

```yaml
infos:
  creation_date: 2026-09-24-00:00:00
  description: Timelapse example workflow (spec)
  inputs_schema:
    export_directory:
      description: Output directory path where the image will be saved
      is_input_file: false
      required: true
      task: export_image_task
    input_path:
      description: Path to a file, or a directory containing files (all files will be imported) or list of paths.
      is_input_file: true
      required: true
      task: import_image_task
    name_pattern:
      description: 'Output file name pattern. Can contain the special {image_name} or {file_name} tokens'
      is_input_file: false
      required: false
      task: export_image_task
  version: 2.0.0
inputs:
  export_directory: /tmp
  input_path: /path/to/4D-series.ome.tif
  name_pattern: '{file_name}_export'
list_tasks:
- func: import_image_task
  id: 00000000-0000-4000-8000-000000000001
  images_inputs:
    input_path: input_path
  node_type: root
  outputs:
  - timelapse
  parameters:
    image_name: timelapse
    key: null
    m_slicing: null
    semantic_type: raw
    stack_layout: TZYX
  skip: false
- func: set_t_spacing_task
  id: 00000000-0000-4000-8000-000000000002
  images_inputs:
    image: timelapse
  node_type: node
  outputs:
  - timelapse_set_t_spacing
  parameters:
    t_spacing: 5.0
  skip: false
- func: gaussian_smoothing_task
  id: 00000000-0000-4000-8000-000000000003
  images_inputs:
    image: timelapse_set_t_spacing
  node_type: node
  outputs:
  - timelapse_gaussian
  parameters:
    sigma: 0.5
  skip: false
- func: unet_prediction_task
  id: 00000000-0000-4000-8000-000000000004
  images_inputs:
    image: timelapse_gaussian
  node_type: node
  outputs:
  - timelapse_prediction
  parameters:
    config_path: null
    device: cuda:0
    disable_tqdm: false
    model_id: null
    model_name: generic_confocal_3D_unet
    model_update: false
    model_weights_path: null
    patch: null
    patch_halo: null
    single_batch_mode: false
    suffix: generic_confocal_3D_unet
  skip: false
- func: dt_watershed_task
  id: 00000000-0000-4000-8000-000000000005
  images_inputs:
    image: timelapse_prediction
  node_type: node
  outputs:
  - timelapse_dt_watershed
  parameters:
    alpha: 1.0
    apply_nonmax_suppression: false
    is_nuclei_image: false
    min_size: 100
    n_threads: null
    pixel_pitch: null
    sigma_seeds: 0.2
    sigma_weights: 2.0
    stacked: false
    threshold: 0.5
  skip: false
- func: clustering_segmentation_task
  id: 00000000-0000-4000-8000-000000000006
  images_inputs:
    image: timelapse_prediction
    over_segmentation: timelapse_dt_watershed
  node_type: node
  outputs:
  - timelapse_segmentation
  parameters:
    beta: 0.6
    mode: gasp
    post_min_size: 100
  skip: false
- func: set_biggest_instance_to_zero_task
  id: 00000000-0000-4000-8000-000000000007
  images_inputs:
    image: timelapse_segmentation
  node_type: node
  outputs:
  - timelapse_segmentation_bg0
  parameters:
    instance_could_be_zero: false
  skip: false
- func: export_image_task
  id: 00000000-0000-4000-8000-000000000008
  images_inputs:
    export_directory: export_directory
    image: timelapse_segmentation_bg0
    name_pattern: name_pattern
  node_type: leaf
  outputs: []
  parameters:
    data_type: uint16
    export_format: tiff
    key: segmentation
    scale_to_origin: true
  skip: false
```

## Tests and fixtures

### Fixtures

1. **Synthetic** — `tests/conftest.py` (existing home): one raw float32 array
   fixture per T layout on one shape skeleton T=4, C=2, Z=5, Y=X=16 —
   `timelapse_tyx` (4,16,16), `timelapse_tcyx` (4,2,16,16),
   `timelapse_tzyx` (4,5,16,16), `timelapse_tczyx` (4,2,5,16,16) — plus a
   `timelapse_segmentation` uint16 fixture whose label IDs are independent
   across timepoints by construction. Tests build `PanSegImage` inline
   (existing pattern); t_spacing known-vs-unknown are two property dicts, not
   separate fixtures.
2. **Real anchors** — the three T-bearing anchors committed to
   `tests/resources/ome_tiff_examples/` under their original names, resliced
   offline to T=4, C=3, Z=2, Y=X=32: `time-series.ome.tif` (TYX),
   `4D-series.ome.tif` (TZYX), `multi-channel-4D-series.ome.tif` (TCZYX). The
   spec documents the one-off reslice script (input:
   `ome_tiff_examples.tar.xz`; output: the three files); committed as static
   files, tests never reslice at runtime. A license note file sits next to
   them: `CC-BY-4.0 The Open Microscopy Environment`.
3. **Synthetic OME-TIFFs** — generated in-test into `tmp_path` (none of the
   anchors carries timing metadata): the t_spacing matrix via
   `TimeIncrement` + unit variants (ms/min converted to s), uniform per-plane
   `DeltaT`, non-uniform `DeltaT` (warn + treat as missing), neither
   (unknown), a T=1 file (squeezes to a non-T layout), and a multi-file
   UUID/FileName chain (rejected with a clear error — the one fiddly fixture:
   two files, patch the first's OME-XML).

### Test design rule (anti-overlap)

Each new test asserts exactly one new behavior. A behavior that is a
composition of already-tested behaviors (frame-mapped wrapper + T-unaware
task; format path + property roundtrip) is tested only for its new part —
e.g. I/O tests assert attr presence and layout/t_spacing survival, never
re-asserting full property dicts (those live in the data-model tests); the
existing non-T tests remain the non-T coverage.

### Frame-by-frame coverage = the wrapper only

Models are T-unaware (per-timepoint inference reuses existing models), so the
only new frame-by-frame surface is `@timepoint_map`. No pipeline integration
test, no prediction or model-zoo test on a timelapse: the zoo dimensionality
filter (TYX → 2D models, TZYX → 3D models) is covered compositionally by the
existing 2D/3D zoo tests on standalone images plus the wrapper test.

### Test plan

- `tests/core/test_image.py` (extend): new layout members are projections of
  TCZYX; one table-driven test of the derived props (`channel_axis`,
  `time_axis`, `dimensionality`, `is_timelapse`) across all nine layouts;
  squeeze rule (every length-1 non-Y/X axis dropped: T=1, C=1, Z=1, existing
  ZYX→YX); channel split TCZYX → [TZYX]×C, TCYX → [TYX]×C; `merge_with`
  t_spacing rules (set/set match only, set/unknown rejected, unknown+unknown
  allowed); `ImageProperties` JSON roundtrip (t_spacing/t_unit; old JSON
  lacking keys → `None`/`"s"`); napari T-axis `scale` = t_spacing or 1.0 +
  from/to-napari-layer roundtrip on a T layout.
- `tests/io/test_tiff.py` (extend): the three committed resliced anchors
  import to the right layout with t_spacing unknown and `series.axes`-driven
  prefill; the generated-OME variant matrix from fixtures #3; the former
  `shape_to_stack_layout` crash shapes prefill `""` instead of raising;
  export: T layouts → OME with correct `SizeT`, `TimeIncrement` written iff
  t_spacing known, re-import roundtrip preserves layout + t_spacing, non-T
  export paths untouched.
- `tests/io/test_h5.py`, `tests/io/test_zarr.py` (extend): `axis_order` attr
  written and read back (T and non-T); `t_spacing`/`t_spacing_unit` attrs iff
  known; re-import preserves layout + t_spacing.
- `tests/tasks/test_io_tasks.py` (extend): `import_image_task` accepts T
  layout strings (the `2D_time`-fossil surface at
  `panseg/tasks/io_tasks.py:33`) and rejects invalid ones; `m_slicing` with T
  (T first in the string); mesh export per timepoint — `{name}_t{NNN}.{ext}`
  0-based, one file per timepoint including empty ones, TYX → the existing
  3D-gate message.
- `tests/tasks/test_timepoint_map.py` (**new**; `task_tracker` lives in
  `panseg/tasks/workflow_handler.py`): core `split_timepoints`/
  `restack_timepoints` roundtrip on TZYX and TYX; the decorator — one
  recorded DAG node, timelapse in → restacked timelapse out, both execution
  paths, abort on first timepoint failure, T-length mismatch `ValueError`,
  t_spacing mismatch `ValueError`, static-input broadcast opt-in (pair ops).
  This file is the entire frame-by-frame test coverage.
- `tests/widgets/` (extend; T-specific wiring only, offscreen):
  `test_input.py` — T layouts accepted, OME prefill from `series.axes`,
  non-OME T prefill stays shape-heuristic (one assertion); the
  `set_t_spacing` widget (Details field in seconds, DAG node) mirroring the
  existing set-voxel-size pattern. `test_segmentation.py` — tab branches on
  spatial dimensionality (TYX → 2D modes, TZYX → 3D modes).
  `test_proofreading.py` — the single-timepoint session: int input 0..T-1
  shown only for timelapse segmentations, operations refused + log hint when
  the slider ≠ k, re-bind without clear/reset, helper layers named `(t={k})`,
  write-back touches only timepoint k (other timepoints byte-identical — the
  cross-timepoint isolation invariant). `test_cli.py` — the t_spacing
  headless `--edit` parameter, mirroring the existing edit-parameter pattern.
- **Regression**: no new tests — the full existing suite green under default
  markers *is* the non-T gate (stated in the DoD, not re-asserted).

### Performance

- `slow` marker policy: unchanged. No new `slow` tests — the marker stays a
  second fail-safe and is never set on tests necessary for coverage. New
  tests are fast by construction (resliced anchors, synthetic data, no
  network, no model weights).
- Performance expectations for realistic timelapse runs: **ignored for v1** —
  no performance section in spec or docs, no benchmarking, no numeric targets.
  Rationale: memory requirements and performance depend heavily on input and
  task; the time dimension should not influence per-timepoint execution for
  most tasks.

## Documentation

- New top-level **Timelapse** page (mkdocs nav, after Batch Workflow): what
  v1 supports (layouts, import); the frame-by-frame strategy in user terms
  (no cross-timepoint information flow; per-timepoint label IDs are
  independent — which is why proofreading is one timepoint at a time);
  setting t_spacing after import; per-timepoint mesh naming; limitations in
  plain terms (the Non-goals list, including the call-out that
  `set_biggest_instance_to_zero` recomputes "largest" per timepoint and the
  proofreading stale-marks hazard).
- Existing pages: `docs/chapters/panseg_interactive_napari/import.md` (T
  prefill + t_spacing field), `.../output.md` (`_t{NNN}` mesh files),
  `.../batch.md` (the complete example yaml above).
- `docs/chapters/python_api/*` needs no regeneration step — mkdocstrings
  pulls docstrings at build, so docstring edits *are* the API-doc change.
- Snippets: at most one (they execute at build time offscreen; a synthesized
  or resliced timelapse); prose elsewhere.
- Docstrings: every docstring that names the layout alphabet gains the T
  members. Explicit list: the `2D_time` fossil at
  `panseg/tasks/io_tasks.py:33`, `import_image` at
  `panseg/core/image.py:675` (its `stack_layout` doc line lists "YX, CYX,
  ZYX, CZYX or ZCYX"), and the TIFF writer docstrings
  (`panseg/io/tiff.py`).
- `CONTEXT.md`: no new terms from this spec (dimensionality, layout,
  timelapse, timepoint, time spacing are already settled there).
- **All doc text is written using the unslop skill.**

## Definition of done

**Spec is done when** (satisfied by this document): every decision from
tickets 02–08 is captured with zero open questions; the test list, docs list,
and non-goals are explicit; the cross-check against the codebase passes
(every referenced path/symbol exists, decisions mutually consistent).

**Implementation is done when**:

1. New + existing tests green under default markers (no new `slow` tests).
2. `mkdocs build` succeeds.
3. The three committed anchors import with the correct layout.

No manual smoke step.
