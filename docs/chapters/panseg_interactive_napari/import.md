# Import Images

## Widget: Open Files

```python exec="1" html="1"
--8<-- "widgets/input_tab/open_file.py"
```

## Timelapse

When you pick a file, the **Stack layout** field is prefilled. OME-TIFF files
use the axis string from their OME-XML metadata, PanSeg h5 and zarr files use
the `axis_order` attribute written on export, and everything else falls back
to a guess from the array shape. The layout can be any permutation of the
letters `t`, `c`, `z`, `y`, `x` that match your file, so a 3D timelapse
prefills as `TZYX`.

OME-TIFF import also reads the time spacing from the timing metadata
(`TimeIncrement` or `Plane.DeltaT`) if the file carries it. Most timelapses do
not carry it, so the spacing is usually unknown after import. Select the
timelapse layer in **Details** to set it with the **Time spacing [s]** field,
which only appears for timelapse layers. The [Timelapse
chapter](../timelapse/index.md) explains what the spacing does and how
frame-by-frame processing works.

Multichannel timelapses (TCYX, TCZYX) import as one single-channel timelapse
layer per channel, the same as multichannel stills.

## Truncate on import

The **Stack layout** field also takes a slice after the letters to restrict
what gets imported: `TZYX[:3,:,:,:]` keeps the first three timepoints,
`ZYX[:10,:,:]` the first ten z slices. An integer entry takes a single index
and drops that axis, so `TZYX[0,:,:,:]` imports one timepoint as a plain ZYX
image.

The entries follow the layout as you write it, before PanSeg reorders the
axes to the canonical T-C-Z-Y-X order, so the first entry always belongs to
the first letter. There may be fewer entries than letters, the axes you leave
out stay whole: `TXYZ[:3]` keeps the first three timepoints and leaves x, y
and z untouched.

A workflow yaml does the same through the `stack_layout` parameter of
`import_image_task`, with the slice written inline.

