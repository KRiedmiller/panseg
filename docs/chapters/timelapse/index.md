# Timelapse

PanSeg imports, processes, and exports timelapses. Processing is frame-by-frame:
each timepoint goes through the pipeline on its own with the same parameters,
and no step looks at neighbouring timepoints. There is no tracking, and label
numbers do not follow cells over time.

## Supported layouts and formats

The timelapse layouts are TYX (2D), TZYX (3D), and their multichannel versions
TCYX and TCZYX.

Import supports OME-TIFF, PanSeg h5, and PanSeg zarr. For OME-TIFF, the input
tab prefills the stack layout from the file's OME-XML, and it reads the time
spacing from the timing metadata (`TimeIncrement` or `Plane.DeltaT`) when the
file has any. Files without timing metadata import with an unknown time
spacing. That is a normal state, not an error; you can set the spacing after
import, see below.

Multichannel timelapses split into single-channel timelapses at import, one
layer per channel, the same as multichannel stills.

Export writes the time axis back out. Tiff export of a timelapse is always
OME-TIFF, with `TimeIncrement` when the spacing is known. H5 and zarr export
carry the layout and the spacing with it.

## How a timelapse is processed

Every task in the pipeline (smoothing, cropping, rescaling, prediction,
segmentation) runs once per timepoint, and the results are stacked back into a
timelapse. In practice:

- A crop you draw once applies to every timepoint. There is no per-timepoint
  crop and no drift correction.
- Min-max normalization happens per timepoint, so a brightness drift across
  the run does not flatten the later timepoints.
- A 3D timelapse (TZYX) runs on the 3D models and algorithms, a 2D timelapse
  (TYX) on the 2D ones. Existing models are reused as-is.

The main consequence of frame-by-frame processing is that label IDs are
independent per timepoint. Label 5 at timepoint 0 and label 5 at timepoint 1
are different cells, and nothing in PanSeg relates them. Relabeling renumbers
per timepoint, and [proofreading](../panseg_interactive_napari/proofreading.md)
works one timepoint at a time.

## Setting the time spacing

```python exec="1" html="1"
--8<-- "widgets/input_tab/timelapse_input.py"
```

Select the timelapse layer in **Details** in the input tab. The **Set time
spacing** section appears below the info box. Enter the interval between
consecutive timepoints in seconds into **Time spacing [s]** and click
**Set Time Spacing**. An empty field marks the spacing as unknown again. The
info box shows the current value, or `None` when unknown.

The spacing is used for the t axis scale in napari and for the
`TimeIncrement` metadata written on tiff export.

## Mesh export

A 3D timelapse segmentation exports one mesh file per timepoint, named
`{name}_t000.{ext}`, `{name}_t001.{ext}`, and so on, with a zero-based index.
Empty timepoints get their file too (an empty mesh), so the file count always
matches the timepoint count. 2D timelapses (TYX) do not export meshes; mesh
export is 3D only.

## Limitations

- **No tracking.** Segment tracking over time and merge/split event detection
  are the planned follow-up built on this version.
- **No spacetime algorithms.** No watershed, multicut, or other step uses
  neighbouring timepoints.
- **No training on timelapse data.** Existing models are reused per timepoint.
- **In-memory only.** The full timelapse is held in memory, there is no
  chunked or out-of-core handling. For very long runs, the `m_slicing`
  parameter of `import_image_task` in a workflow yaml restricts the imported
  range (comma-separated ranges along the layout, T first, e.g.
  `0:3, :, :, :` imports the first three timepoints of a TZYX file). The
  input tab does not expose this field.
- **One file per timelapse.** Multi-file OME-TIFF (UUID/FileName chain) is
  rejected at import with an error, and there is no one-file-per-frame import.
- **A failed timepoint aborts the run.** There is no skipping or filling of
  failed timepoints.
- **PanSeg formats only.** OME-NGFF (OME-Zarr) is not read or written.

Two behaviors to know before running a timelapse through the usual
postprocessing:

- "Set biggest instance to background" recomputes the biggest instance per
  timepoint. The instance it zeros can differ from timepoint to timepoint.
- The proofreading canvases persist across timepoint switches. Marks you drew
  for one timepoint are still on the Scribbles layer after you switch, and
  Split/Merge applies them to the new timepoint if you run it before cleaning.
  Use **Clean scribbles** after switching timepoints.
