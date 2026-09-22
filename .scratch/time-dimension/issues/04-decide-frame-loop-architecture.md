# Decide the frame-by-frame loop architecture

Type: grilling
Status: claimed
Blocked by: 03

## Question

Where does the frame-by-frame loop live? The user's direction at charting: a transparent task-level "map over T" wrapper (split T → run the existing 2D/3D task per frame → restack), DAG and GUI unchanged. Nail down the design:

- Wrapper mechanics: how a T-bearing `PanSegImage` is split/restacked; how `derive_new` and properties (t_spacing, name, source file) propagate.
- Which tasks are per-frame vs frame-invariant (e.g. crop ROI applied identically across frames, rescale per frame?) — the list of T-aware vs T-transparent tasks in the v1 spec.
- How label outputs restack (independent per-frame IDs — settled at charting).
- Error / partial-failure semantics (frame k fails: abort vs skip-with-warning?).
- Where the wrapper lives in the code (the `tasks/` layer? a decorator? a helper in core?).
