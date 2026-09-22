# Specify viewer/GUI/headless UX for time

Type: grilling
Status: open
Blocked by: 03, 04

## Question

What does the user see and click for a timelapse?

- napari: T axis display (slider) + scale including t_spacing; how the channel split/merge tabs behave on T-bearing images.
- Input tab: `stack_layout` LineEdit syntax with T (tooltip + guessing), t_spacing entry field, `m_slicing` with T.
- Preprocessing tab: the current "4d not supported" guard (5D now) — what shows / is hidden for T-bearing images; crop z for T.
- Segmentation tab: the layout branching (only YX/ZYX accepted today) for T-bearing layouts.
- Proofreading widget: operate on the current frame; how cross-frame scribbles/labels are handled (or blocked).
- Output tab: export options for T-bearing images — tiff/h5/zarr only (no PIL/jpg); per-frame mesh output for 3D timelapses (one file per timepoint, `{name_pattern}_t{index:03d}.{ext}`, settled in ticket 05).
- Workflow editor + headless: DAG yaml for a timelapse (a complete example yaml in the spec), `stack_layout` values, the t_spacing parameter for import (ticket 05 settled that t_spacing is user-supplied after import, not at import); no DAG changes (settled: transparent wrapper).
