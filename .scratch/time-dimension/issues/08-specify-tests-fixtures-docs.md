# Specify tests, fixtures, and docs

Type: grilling
Status: open
Blocked by: 05, 06, 07

## Question

What does the spec mandate for verification and documentation?

- Fixtures: a small synthetic CTZYX (and TZYX/TYX per ticket 03) in `conftest.py`, plus a real anchor subset (which of the 8 example files, resliced small for speed — e.g. `multi-channel-4D-series.ome.tif`) as the integration anchor.
- Coverage: data-model roundtrips (h5, napari metadata), import/export roundtrips per format, the frame-by-frame pipeline on a small fixture (preprocessing → prediction → segmentation → proofreading), widget tests (`QT_QPA_PLATFORM=offscreen`), headless DAG run with a timelapse yaml.
- Performance guardrails: which tests get the `slow` marker; performance expectations for realistic timelapse runs (docs vs benchmarks).
- Docs: which chapters/pages change (import chapter, Python API reference regeneration, a new "timelapse" section?), docstring updates (including the stale `2D_time` fossil at `panseg/tasks/io_tasks.py:33`).
- The spec's own definition of done (ticket 09).
