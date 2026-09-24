# 20: Docs: Timelapse page + page updates

**What to build:** The documentation tells a user what v1 time support does, how to use
it, and where its edges are (spec: "Documentation" + "Definition of done"). All doc text
is written using the unslop skill.

New top-level **Timelapse** page (mkdocs nav, after Batch Workflow): what v1 supports
(layouts TYX/TCYX/TZYX/TCZYX, OME-TIFF/h5/zarr import and export with time, t_spacing
settable after import); the frame-by-frame strategy in user terms (no cross-timepoint
information flow; per-timepoint label IDs are independent — which is why proofreading is
one timepoint at a time); setting t_spacing after import; per-timepoint mesh naming;
limitations in plain terms — the Non-goals list, including the call-out that
`set_biggest_instance_to_zero` recomputes "largest" per timepoint and the proofreading
stale-marks hazard.

Existing pages: the import page (T prefill from OME metadata + the "Time spacing [s]"
field), the output page (per-timepoint `_t{NNN}` mesh files), the batch page (the complete
example workflow yaml from ticket 19).

`docs/chapters/python_api/*` needs no regeneration step — mkdocstrings pulls docstrings at
build, so docstring edits *are* the API-doc change. Docstrings: every docstring that names
the layout alphabet gains the T members. Explicit list: the `2D_time` fossil in the
import task's docstring, the `import_image` `stack_layout` doc line (lists "YX, CYX, ZYX,
CZYX or ZCYX"), and the TIFF writer docstrings.

Snippets: at most one (they execute at build time offscreen; a synthesized or resliced
timelapse); prose elsewhere. `CONTEXT.md`: no new terms from this spec (dimensionality,
layout, timelapse, timepoint, time spacing are already settled there).

**Blocked by:**
- 16: Viewer: napari display + input tab
- 17: Viewer: preprocessing + segmentation tabs
- 18: Proofreading: one timepoint per session
- 19: Headless: workflow editor entry + example workflow

**Status:** ready-for-agent

- [ ] New top-level Timelapse page in the mkdocs nav after Batch Workflow: v1 scope (layouts, import/export), frame-by-frame in user terms (no cross-timepoint flow; independent per-timepoint label IDs; proofreading one timepoint at a time), t_spacing after import, per-timepoint mesh naming
- [ ] Limitations in plain terms: the Non-goals list, the `set_biggest_instance_to_zero` per-timepoint "largest" call-out, and the proofreading stale-marks hazard
- [ ] Import page updated (T prefill from OME metadata + "Time spacing [s]" field); output page updated (per-timepoint `_t{NNN}` mesh files); batch page updated (the complete example workflow yaml)
- [ ] Docstrings that name the layout alphabet include the T members: the `2D_time` fossil in the import task, the `import_image` `stack_layout` doc line, and the TIFF writer docstrings
- [ ] At most one executable snippet (synthesized or resliced timelapse); prose elsewhere
- [ ] `mkdocs build` succeeds (offscreen)
- [ ] All doc text passes the unslop skill
