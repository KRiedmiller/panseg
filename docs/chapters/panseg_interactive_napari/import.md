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

