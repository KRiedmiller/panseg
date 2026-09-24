# 15: Frame-by-frame loop: @timepoint_map + split/restack

**What to build:** Every preprocessing, prediction, and segmentation task runs on a
timelapse frame-by-frame with zero task-body changes and no cross-timepoint information
flow, transparently on both execution paths (GUI and headless), so that a user running any
existing task on a timelapse image gets a restacked timelapse result (spec:
"Frame-by-frame loop architecture").

The loop is a transparent, opt-in `@timepoint_map` decorator in the tasks layer, stacked
directly under `@task_tracker`, applied per task; task bodies are unchanged. Both execution
paths are covered for free: the GUI runs the `task_tracker` wrapper, the headless
`SerialRunner` calls the registered callable — the decorator registers the wrapped
function, so the loop sits under the recording layer on both paths. At call time the
decorator inspects kwargs: any `PanSegImage` input with `is_timelapse` ⇒ map over
timepoints; no T-bearing input ⇒ pass through untouched (non-T calls behave exactly as
today).

Core helpers in the image module (data-model ops):
- `PanSegImage.split_timepoints()` — method, mirrors `split_channels`. Each timepoint is a
  derive: data = the T slice, layout = T dropped (TZYX→ZYX, TYX→YX), name =
  `f"{name}_t{i}"` (mirrors the channel naming convention), `t_spacing`/`t_unit` → `None`
  (a timepoint is not a timelapse); `voxel_size`, `semantic_type`, `source_file_name`
  propagate automatically.
- `restack_timepoints(timepoints, t_spacing, t_unit)` — module-level function.
  `np.stack` along a new outer T axis; validates identical shape / layout / `voxel_size` /
  `semantic_type` across timepoints (the same checks as `merge_with`); the decorator stamps
  the parent's `t_spacing`/`t_unit` onto the result (lost on split). Label outputs restack
  with identical mechanics — no cross-timepoint ID renumbering.

Task classification — every task is explicitly frame-mapped or stack-level, and a
non-decorated task receiving a T-bearing input is an error, not a mystery crash.

Frame-mapped (the task never sees T): gaussian smoothing, image cropping, set voxel size
(property-only), **set t spacing (new, property-only — see below)**, rescale-to-shape,
rescale-to-voxel-size, remove-false-positives-by-foreground-probability (both outputs
restacked), fix-over-under-segmentation-from-nuclei, set-biggest-instance-to-zero,
relabel-segmentation, image-pair-operation, dt-watershed, clustering-segmentation
(gasp/multicut/mutex_ws), lmc-segmentation, aio-watershed, unet-prediction, biio-prediction.

Stack-level (operate on the whole timelapse as one object): `import_image_task` (creates
T), `export_image_task` (writes T as one file), `merge_channels_task` — direct two-stage
`np.stack` → TCZYX/TCYX via the T-aware `merge_with`; validates T length / `voxel_size` /
`semantic_type` across channel inputs; no timepoint loop. `unet_training_task` is not
mappable (its image inputs are napari layers / dataset dirs, not `PanSegImage`);
timelapse training is a non-goal.

Multi-image rules: all T-bearing image inputs of a frame-mapped task must have equal T
length, zipped by index; mismatch ⇒ `ValueError`. Mixed T-bearing + non-T image inputs ⇒
`ValueError` by default; a task-level decorator flag opts in **broadcast** of the static
input to every timepoint. v1 opt-ins: `image_pair_operation_task` (e.g. static background
subtraction) and `remove_false_positives_by_foreground_probability_task` (static
foreground probability map); the over/under, lmc, aio, and clustering tasks keep
`ValueError`. Differing `t_spacing` across T-bearing inputs ⇒ `ValueError`; equal or
both-`None` is fine, and the restacked output takes the shared spacing.

Error semantics (abort): the decorator lets the first failed timepoint's exception
propagate — GUI: the identical `Task_message` flow as any task failure; headless: the job
aborts, exactly as today. No skip/fill/drop (a filled timepoint would silently corrupt
downstream segmentation; a dropped timepoint breaks uniform t_spacing, which the data
model cannot represent). A `Task_message` *returned* (not raised) by an inner call is
treated as a failure and propagated.

Progress and DAG surface: the decorator drives the tracker at timepoint granularity
(total = n_timepoints, tick per completed timepoint) and passes no tracker into
per-timepoint calls: one progress level in v1. The recorded DAG node is identical in shape
to today — timelapse image in, restacked timelapse image out, same parameters;
`timepoint_map` is not a parameter, and timepoints are locals inside the decorator, never
entering `var_space` (headless `clean_var_space` unaffected). GUI: one button press, one
progress bar, one restacked result layer added; per-timepoint images are transient and
never added to the viewer.

New task: `set_t_spacing_task(image, t_spacing: float | None) -> PanSegImage`, mirroring
`set_voxel_size_task` — property-only, frame-mapped, derives a
`f"{image.name}_set_t_spacing"` layer, recorded as a DAG node (the headless yaml
mechanism). The viewer widget for it is ticket 16; the workflow-editor entry is ticket 19.

Label semantics (stated for the docstrings of the decorated tasks): label IDs are
independent per timepoint, no correspondence across timepoints; `relabel_segmentation`
renumbers connected components per timepoint (spatial connectivity only);
`set_biggest_instance_to_zero` zeros the largest component *within each timepoint* —
call this out in the task docstring (docs ticket 20 covers the user-facing copy).

**Blocked by:**
- 11: Data model: T in layouts and image properties
- 12: Fixtures: synthetic timelapses, resliced anchors, OME variants

**Status:** ready-for-agent

- [ ] `split_timepoints`/`restack_timepoints` roundtrip on TZYX and TYX: data identical, timepoint layouts ZYX/YX, names `f"{name}_t{i}"`, `t_spacing`/`t_unit` None on timepoints, parent spacing stamped on the restack
- [ ] A decorated task on a timelapse input records exactly one DAG node (timelapse in, restacked timelapse out, same parameters) on both execution paths (GUI `task_tracker` wrapper and headless `SerialRunner`); per-timepoint images never enter `var_space` or the viewer
- [ ] Non-T calls to a decorated task pass through untouched (existing task behavior and tests unchanged)
- [ ] A failed timepoint aborts the run with the first failure's exception (GUI `Task_message` flow, headless job abort); a `Task_message` returned by an inner call is treated as a failure
- [ ] T-length mismatch across T-bearing inputs ⇒ `ValueError`; differing `t_spacing` (set vs set) ⇒ `ValueError`; equal or both-None spacings merge into the shared spacing on the restack
- [ ] Broadcast opt-in: `image_pair_operation_task` and `remove_false_positives_by_foreground_probability_task` accept a static (non-T) input applied to every timepoint; the other multi-image tasks reject mixed inputs with `ValueError`
- [ ] `set_t_spacing_task` sets `t_spacing` (known value and `None`), derives the named layer, is property-only, and is recorded as a DAG node
- [ ] Label outputs restack with no cross-timepoint ID renumbering; a frame-mapped task's output at timepoint i depends only on its input at timepoint i (assert with per-timepoint-distinguishable synthetic data)
- [ ] All 17 frame-mapped tasks are decorated; import/export/merge-channels are stack-level; a non-decorated task receiving a T-bearing input errors
