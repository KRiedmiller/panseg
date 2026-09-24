# Decide the timelapse evaluation plan in the spec

Type: grilling
Status: resolved
Blocked by: 08

## Question

Does the handoff spec include a quantitative evaluation plan for timelapse segmentation, and what does it consist of?

The pipeline is settled as per-timepoint with no cross-timepoint information flow (ticket 06), and segment tracking is out of scope — so any in-scope evaluation is per-timepoint. The repo's `evaluation/` harness is 3D-oriented. To decide:

- Include a quantitative evaluation plan at all, or leave evaluation to the existing 3D docs (spec stays silent)?
- If included: per-timepoint reuse of the `evaluation/` harness on the anchor fixtures — which of the 8 example files (or the resliced subset ticket 08 settles), which metrics, reported per timepoint?
- State explicitly that cross-timepoint consistency metrics are out of scope (tracking follow-up), so an implementer doesn't invent them?

## Answer

Resolved 2026-09-24, grilling, two rounds (frontier emptied after round 1). The spec is silent on evaluation, with one non-goals exception.

1. **No quantitative evaluation plan.** The spec contains no metrics, no fixture targets, no reporting format, and no mention of the `evaluation/` harness (the user overrode the recommendation of a short usage section). Per-timepoint segmentations are evaluable by the existing 3D workflow: the metric layer (`run_evaluation` at `evaluation/evaluation_segmentation.py:75`) is shape-agnostic — per-timepoint reuse is "slice each timepoint, call, collect per-timepoint rows" — so the spec does not re-spec it.
2. **One non-goals sentence.** The spec's non-goals list (written by 09) states that cross-timepoint consistency metrics (object tracking, identity consistency across timepoints, trajectory scores) are out of scope and belong to the planned tracking follow-up. Nothing in the repo computes such metrics, and the pipeline has no cross-timepoint flow by design (ticket 06), so any would measure the absence of the feature rather than quality.
3. **Data target moot.** The resliced anchors (ticket 08) are raw images with no ground truth, and no labeled timelapse exists in the repo; with no plan, no data target is settled.

Fact recorded for the implementer's awareness (deliberately **not** in the spec): the harness performs no `ndim` check — feeding it a full TZYX array silently pools all timepoints into one bag of voxels and yields plausible-looking wrong numbers; per-timepoint slicing is a precondition for meaningful metrics.
