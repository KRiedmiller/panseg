# 16: Viewer: napari display + input tab

**What to build:** A timelapse layer displays correctly in the napari viewer with proper
axis labels and a time-scaled T slider, and the input tab accepts time layouts, prefills
them from OME metadata, and lets the user set the time spacing on a timelapse layer
(spec: "Viewer, GUI, and headless UX" → "napari display" + "Input tab").

napari display: `to_napari_layer_tuple` gains `axis_labels` for **every** layout, derived
from the layout string (t/c/z/y/x) — uniform, not T-only. `scale` per the data-model
decision (ticket 11): the T axis takes the time spacing (1.0 when unknown), the C axis
1.0, spatial axes as today — so the outermost slider is napari's default leading-axis
slider, scaled by the time spacing when known. No custom time widget. Channel operations
on T-bearing images: split at import (multichannel timelapse → list of single-channel
timelapse layers, each its own layer); merge via the existing output-tab n_channels /
additional-channels widget (T-aware `merge_with`, stack-level) and the prediction tab's
additional inputs — no new GUI.

Input tab: the `stack_layout` field accepts the T layouts (TYX/TCYX/TZYX/TCZYX) for
**every** format — the layout is the user's explicit assertion about their own data; only
the prefill is OME-aware (the reader's axis string, ticket 13). Tooltip updated to mention
`t` for time. The Details section gains a "Time spacing [s]" float field + button, shown
only when the selected layer is a timelapse; empty field = unknown (`None`); applying it
records a `set_t_spacing_task` DAG node (ticket 15) mirroring the existing set-voxel-size
pattern; the Details info shows the time spacing when known.

**Blocked by:**
- 13: OME-TIFF import with time
- 15: Frame-by-frame loop: @timepoint_map + split/restack

**Status:** ready-for-agent

- [ ] A T-layout image added to the viewer produces a layer with `axis_labels` derived from the layout string (all layouts, not just T ones) and `scale` with T = t_spacing (1.0 when unknown), C = 1.0
- [ ] The input tab accepts every T layout string for every format; the OME-TIFF prefill comes from the reader's axis string; non-OME T prefills stay shape-heuristic; the tooltip mentions `t`
- [ ] The Details "Time spacing [s]" field + button are visible only when the selected layer is a timelapse; applying records a `set_t_spacing_task` node with the entered value; an empty field sets unknown (`None`)
- [ ] The Details info shows the time spacing when known
- [ ] A multichannel timelapse shows as one single-channel timelapse layer per channel; merging via the existing additional-channels widget yields a TCZYX/TCYX layer
