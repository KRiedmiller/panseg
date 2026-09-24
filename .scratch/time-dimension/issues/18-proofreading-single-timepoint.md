# 18: Proofreading: one timepoint per session

**What to build:** A user can proofread a timelapse segmentation one explicitly selected
timepoint at a time, reusing all existing 2D/3D proofreading machinery, with edits
confined to the selected timepoint (spec: "Per-stage pipeline behavior" → "Proofreading"
+ "Viewer, GUI, and headless UX" → "Proofreading widget").

The session binds to one timepoint `k` explicitly selected by the user: a new int input
(0..T-1) in the proofreading widget, shown only for timelapse segmentations. The int
input — not the T slider — is the timepoint selector: changing it moves the T slider to
that timepoint (one-way; the input defaults to the slider's position at initialization).

The handler world is the slice: `segmentation` reads the layer data at `k` (live from the
layer); the bbox machinery (the ndim 2/3 dispatch that raises on 4D) runs on the ZYX/YX
slice — the 4D breakage of bboxes on TZYX arrays is sidestepped by construction — and
split/merge-from-seeds + watershed are reused untouched. Write-back: the layer data at
timepoint `k` is replaced in the selected region; all other timepoints untouched.

Helper layers: one single "Scribbles" canvas and one single "Correct Labels" canvas —
persistent slice-sized (z,y,x) workspaces with no T dimension, named
`Scribbles (t={k})` / `Correct Labels (t={k})`, the name tracking the session's current
timepoint; displayed at the selected timepoint (how the 3D canvas aligns with the TZYX
segmentation layer is an implementation detail). The "not intended to be proofread"
checks match by prefix. One single layer of each, **persisting across timepoint
changes** — no clearing, no reset, no re-initialization.

Mid-session timepoint change = **re-bind, not re-initialize**: changing the selection
re-binds the session to the new timepoint — no `are_you_sure` reset, no clearing of the
persistent canvases, no extra blocking logic. Session-scoped derived state (`max_label`,
corrected-cells set, corrected mask, undo/redo history) lives on the slice and recomputes
on re-bind to a new timepoint (undo snapshots are one ZYX/YX slice, not TZYX-stack
copies). The scribbles/corrected canvas content is the exception — it persists across
timepoint changes. **Stale-marks hazard (call out in the widget hint and the docs,
ticket 20):** marks from a processed timepoint remain on the persistent canvases and
would be applied to the next timepoint if Split/Merge runs before the existing Clean
button is used.

When the displayed timepoint (T slider) differs from the session's timepoint (int input),
operations — Split/Merge, double-click mark-corrected — are **refused with a log hint**
(the one-way slider allows the divergence; silent application would mark the cell at
(`k`, z, y), a different cell than the one under the cursor).

Save/load state: the full TZYX label array (only timepoint `k` edited) + a `timepoint`
attr + the corrected cells of `k`; load re-initializes the session on `k`. Extract
corrected labels: a single-timepoint layer of the proofread timepoint's corrected cells,
named with the `_t{NNN}` convention — not a full-length timelapse with mostly empty
timepoints.

Premise: single-channel timepoints — channels are split at import, so multichannel images
never reach proofreading; no guard. Proofreading stays a GUI-interaction step (direct
in-place mutation of the labels layer); it is not a DAG task and is absent from headless
yamls.

**Blocked by:**
- 13: OME-TIFF import with time
- 15: Frame-by-frame loop: @timepoint_map + split/restack

**Status:** ready-for-agent

- [ ] The int input (0..T-1) is shown only for timelapse segmentations, defaults to the T slider's position, and changing it moves the T slider (one-way)
- [ ] Re-binding to a new timepoint does not clear or reset the persistent canvases; bboxes/corrected-cells/undo recompute for the new slice (undo snapshots are slice-sized)
- [ ] Helper layers are named `Scribbles (t={k})` / `Correct Labels (t={k})`, the name tracks the current timepoint, and the "not intended to be proofread" checks match by prefix
- [ ] A Split/Merge or mark-corrected operation writes only timepoint `k`; every other timepoint is byte-identical before/after (the cross-timepoint isolation invariant)
- [ ] Operations are refused with a log hint when the T slider ≠ the session's timepoint (no silent application)
- [ ] Save/load roundtrip: the saved state carries the full TZYX array (only `k` edited) + a timepoint attr + `k`'s corrected cells; loading re-initializes the session on `k`
- [ ] Extract corrected labels emits a single-timepoint layer named with the `_t{NNN}` convention
- [ ] The stale-marks hazard is called out in the widget hint
