# Batch processing

PanSeg supports processing a whole stack of images at once through the
use of batch scripts.

To generate such a workflow script, first process one image in the intended way,
and export the result. Then, go to the `Batch` tab in Napari and save the workflow
script to a `yaml` file.

You can review and edit workflow scripts using the build-in workflow editor;
open it either directly from the napari `Batch` tab, or from the command
line using `panseg -e` .

Read more about [batch workflows in this chapter](../workflow_gui/index.md).

!!! note ""
    You find the batch processing section in the output tab in napari!

!!! warning
    Some interactive steps can't be recorded into workflows, especially **cropping** and **proofreading**

## Input paths

The `input_path` of a workflow accepts four shapes, and the import task
interprets each one:

| `input_path` | What runs |
| --- | --- |
| a file | one job, one image |
| a directory of files | one job per file |
| a directory of subdirectories | one job per subdirectory, the files inside each stacked as one time series (alphanumeric filename order) |
| a list of files | one job, the files stacked as one time series |

Files and subdirectories in the same directory: the files win and the
subdirectories are ignored. A subdirectory without importable files stops
the run with an error.

## Stack layout

The workflow's `stack_layout` is one value for all jobs, and it describes
the image a job consumes. A time series workflow records a layout with a
`t` (TYX, TZYX, ...); a workflow recorded from multiple files records the
same layout as one recorded from a single file with a time dimension, and
both behave identically.

A job that consumes one file (a single file, or one file of a directory)
must match the layout exactly: a `t` in the layout requires the file to
carry the time axis, so a directory of time series files runs one series
per file, and a directory of still files errors. A job that stacks files
(a list, or a directory of subdirectories) has the `t` stripped - stacking
supplies the time axis - and the spatial axes apply to every file. A slice
entry on the `t` is rejected for a selection: the time axis exists only
after the files are stacked.

## Widget: Export Batch Workflow

```python exec="1" html="1"
--8<-- "widgets/batch/batch.py"
```
