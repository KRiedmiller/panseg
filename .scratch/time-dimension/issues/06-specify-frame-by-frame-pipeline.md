# Specify the frame-by-frame pipeline

Type: grilling
Status: open
Blocked by: 04

## Question

Per-stage behavior for T-bearing images in the v1 spec (frame-by-frame, no spacetime algorithms — settled at charting):

- Preprocessing (crop, rescale, median filter): per-frame vs once-for-all-frames; which is which.
- Prediction: per-frame 3D inference reusing existing models (settled direction) — patching per frame, model-zoo dimensionality-filter interplay, error behavior when a frame does not fit in memory (error vs warn vs auto-shrink patch).
- Segmentation: per-frame 2D/3D watershed/GASP/multicut; per-frame 2D segmentation for 2D timelapse; which mode defaults the GUI offers (ticket 07).
- Proofreading: operate on the currently displayed frame; no cross-frame operations in v1 (including the bbox machinery interplay).
- Label semantics: independent per-frame IDs (settled at charting) — stated explicitly in the spec; interplay with relabel / largest-instance utilities.
