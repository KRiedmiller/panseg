# 12: Fixtures: synthetic timelapses, resliced anchors, OME variants

**What to build:** The shared test fixtures every later time ticket builds on, so each
implementation ticket can verify its slice against both synthetic data and real files
(spec: "Tests and fixtures" → "Fixtures").

1. **Synthetic** — in the shared test conftest (the existing home for image fixtures): one
   raw float32 array fixture per T layout on one shape skeleton T=4, C=2, Z=5, Y=X=16 —
   `timelapse_tyx` (4,16,16), `timelapse_tcyx` (4,2,16,16), `timelapse_tzyx` (4,5,16,16),
   `timelapse_tczyx` (4,2,5,16,16) — plus a `timelapse_segmentation` uint16 fixture whose
   label IDs are independent across timepoints by construction (no correspondence between
   timepoints). Tests build `PanSegImage` inline (existing pattern); known-vs-unknown
   t_spacing are two property dicts, not separate fixtures.
2. **Real anchors** — the three T-bearing anchor OME-TIFFs resliced offline to T=4, C=3,
   Z=2, Y=X=32 and committed to `tests/resources/ome_tiff_examples/` under their original
   names: `time-series.ome.tif` (TYX), `4D-series.ome.tif` (TZYX),
   `multi-channel-4D-series.ome.tif` (TCZYX). A license note file sits next to them
   (`CC-BY-4.0 The Open Microscopy Environment`). The one-off reslice script is documented
   (input: `ome_tiff_examples.tar.xz`; output: the three files) and committed as a static
   artifact reference; tests load the committed files and never reslice at runtime.
3. **Synthetic OME-TIFFs** — builders generating files in `tmp_path` at test time (none of
   the committed anchors carries timing metadata): the t_spacing matrix via
   `TimeIncrement` + unit variants (ms/min converted to s), uniform per-plane `DeltaT`,
   non-uniform `DeltaT` (warn + treat as missing), neither (unknown), a T=1 file (squeezes
   to a non-T layout), and a multi-file UUID/FileName chain (two files, the first's
   OME-XML patched to point at the second — the one fiddly fixture).

**Blocked by:** 11: Data model: T in layouts and image properties

**Status:** ready-for-agent

- [ ] Conftest fixtures exist for all four T layouts plus `timelapse_segmentation`, on the documented shape skeleton, constructible as `PanSegImage` with both known and unknown t_spacing
- [ ] The three resliced anchors are committed under `tests/resources/ome_tiff_examples/` with original names, correct OME axes (TYX/TZYX/TCZYX), resliced shape T=4, C=3, Z=2, Y=X=32, plus the CC-BY-4.0 license note file
- [ ] The one-off reslice script is committed and documented (input tarball → three output files); no test reslices at runtime
- [ ] The OME-TIFF builders produce every fixture-matrix variant in `tmp_path`, each carrying the intended timing metadata (or its intended absence)
- [ ] Full existing suite remains green (fixtures are additive only)
