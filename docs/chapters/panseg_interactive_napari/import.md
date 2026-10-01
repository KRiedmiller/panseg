# Import Images

## Widget: Open Files

```python exec="1" html="1"
--8<-- "widgets/input_tab/open_file.py"
```

## Multiple files

The file picker accepts several files at once. They import as one time
series: each file is one timepoint, and the time axis appears without you
writing a `t` anywhere. The files are stacked in alphanumeric filename
order, so `a2.tif` comes before `a10.tif`.

Every file in the selection must be a single image. The stack layout
applies to all of them, so it has to be spatial: a `t` in the layout is
rejected because stacking itself adds the time axis. Multi-channel files
stack per channel, and the channel counts must match across files.

The time spacing between independently stored files is not written anywhere
on disk, so it imports as unknown. Set it afterwards in the Details field of
the input tab (see [Time Series](../timeseries/index.md)).

## Stack Layout

When you pick a file, the **Stack layout** field is prefilled. OME-TIFF files
use the axis string from their OME-XML metadata, h5 and zarr files use
the `axis_order` attribute written on export, and everything else falls back
to a guess from the array shape. The layout can be any permutation of the
letters `t`, `c`, `z`, `y`, `x` that match your file, so a 3D time series
gets prefilled as `TZYX`.  
You can invert an axis by prepending it with a minus.
Also you can slice the data by appending, e.g. `tczxy[:10,2]` to only load the
first ten frames of the third channel.  
The slicing functionality can also be used for cropping already during the
import (`CXYZ[1,:50,:50,:10]`).
