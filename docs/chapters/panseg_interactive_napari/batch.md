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

## Widget: Export Batch Workflow

```python exec="1" html="1"
--8<-- "widgets/batch/batch.py"
```

## Example: timelapse workflow

A complete workflow for a 3D timelapse (TZYX) from an OME-TIFF file: import,
set the time spacing, smooth, predict, over-segment with the
distance-transform watershed, segment with gasp, set the biggest instance to
background, and export the segmentation as OME-TIFF. Run it with
`panseg --config your_workflow_file.yaml`.

```yaml
infos:
  creation_date: '2026-09-24-00:00:00'
  description: Timelapse example workflow (spec)
  inputs_schema:
    export_directory:
      description: Output directory path where the image will be saved
      is_input_file: false
      required: true
      task: export_image_task
    input_path:
      description: Path to a file, or a directory containing files (all files will be imported) or list of paths.
      is_input_file: true
      required: true
      task: import_image_task
    name_pattern:
      description: 'Output file name pattern. Can contain the special {image_name} or {file_name} tokens'
      is_input_file: false
      required: false
      task: export_image_task
  version: 2.0.0
inputs:
  export_directory: /tmp
  input_path: /path/to/4D-series.ome.tif
  name_pattern: '{file_name}_export'
list_tasks:
- func: import_image_task
  id: 00000000-0000-4000-8000-000000000001
  images_inputs:
    input_path: input_path
  node_type: root
  outputs:
  - timelapse
  parameters:
    image_name: timelapse
    key: null
    semantic_type: raw
    stack_layout: TZYX
  skip: false
- func: set_t_spacing_task
  id: 00000000-0000-4000-8000-000000000002
  images_inputs:
    image: timelapse
  node_type: node
  outputs:
  - timelapse_set_t_spacing
  parameters:
    t_spacing: 5.0
  skip: false
- func: gaussian_smoothing_task
  id: 00000000-0000-4000-8000-000000000003
  images_inputs:
    image: timelapse_set_t_spacing
  node_type: node
  outputs:
  - timelapse_gaussian
  parameters:
    sigma: 0.5
  skip: false
- func: unet_prediction_task
  id: 00000000-0000-4000-8000-000000000004
  images_inputs:
    image: timelapse_gaussian
  node_type: node
  outputs:
  - timelapse_prediction
  parameters:
    config_path: null
    device: cuda:0
    disable_tqdm: false
    model_id: null
    model_name: generic_confocal_3D_unet
    model_update: false
    model_weights_path: null
    patch: null
    patch_halo: null
    single_batch_mode: false
    suffix: generic_confocal_3D_unet
  skip: false
- func: dt_watershed_task
  id: 00000000-0000-4000-8000-000000000005
  images_inputs:
    image: timelapse_prediction
  node_type: node
  outputs:
  - timelapse_dt_watershed
  parameters:
    alpha: 1.0
    apply_nonmax_suppression: false
    is_nuclei_image: false
    min_size: 100
    n_threads: null
    pixel_pitch: null
    sigma_seeds: 0.2
    sigma_weights: 2.0
    stacked: false
    threshold: 0.5
  skip: false
- func: clustering_segmentation_task
  id: 00000000-0000-4000-8000-000000000006
  images_inputs:
    image: timelapse_prediction
    over_segmentation: timelapse_dt_watershed
  node_type: node
  outputs:
  - timelapse_segmentation
  parameters:
    beta: 0.6
    mode: gasp
    post_min_size: 100
  skip: false
- func: set_biggest_instance_to_zero_task
  id: 00000000-0000-4000-8000-000000000007
  images_inputs:
    image: timelapse_segmentation
  node_type: node
  outputs:
  - timelapse_segmentation_bg0
  parameters:
    instance_could_be_zero: false
  skip: false
- func: export_image_task
  id: 00000000-0000-4000-8000-000000000008
  images_inputs:
    export_directory: export_directory
    image: timelapse_segmentation_bg0
    name_pattern: name_pattern
  node_type: leaf
  outputs: []
  parameters:
    close_mesh: false
    data_type: uint16
    export_format: tiff
    export_mesh: null
    key: segmentation
    scale_to_origin: true
  skip: false
```
