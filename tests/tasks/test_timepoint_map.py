"""Frame-by-frame loop: the split/restack helpers and the @timepoint_map decorator.

This file is the entire frame-by-frame test coverage (spec:
"Frame-by-frame loop architecture"). The existing non-T task tests remain
the non-T coverage.
"""

import numpy as np
import pytest

from panseg.core.image import (
    ImageLayout,
    ImageProperties,
    PanSegImage,
    SemanticType,
    restack_timepoints,
)
from panseg.functionals.dataprocessing import relabel_segmentation
from panseg.headless.basic_runner import SerialRunner
from panseg.io.voxelsize import VoxelSize
from panseg.tasks import timepoint_map
from panseg.tasks.dataprocessing_tasks import (
    fix_over_under_segmentation_from_nuclei_task,
    gaussian_smoothing_task,
    image_cropping_task,
    image_pair_operation_task,
    image_rescale_to_shape_task,
    image_rescale_to_voxel_size_task,
    relabel_segmentation_task,
    remove_false_positives_by_foreground_probability_task,
    set_biggest_instance_to_zero_task,
    set_t_spacing_task,
    set_voxel_size_task,
)
from panseg.tasks.io_tasks import export_image_task, merge_channels_task
from panseg.tasks.prediction_tasks import biio_prediction_task, unet_prediction_task
from panseg.tasks.segmentation_tasks import (
    aio_watershed_task,
    clustering_segmentation_task,
    dt_watershed_task,
    lmc_segmentation_task,
)
from panseg.tasks.workflow_handler import (
    Task_message,
    task_tracker,
    workflow_handler,
)

TIMESERIES_T_SPACING = 10.0


def make_image(
    data: np.ndarray,
    layout: str,
    semantic_type: SemanticType = SemanticType.RAW,
    t_spacing: float | None = None,
    name: str = "image",
) -> PanSegImage:
    voxel_size = VoxelSize(voxels_size=(1.0, 1.0, 1.0))
    properties = ImageProperties(
        name=name,
        semantic_type=semantic_type,
        voxel_size=voxel_size,
        image_layout=ImageLayout(layout),
        original_voxel_size=voxel_size,
        t_spacing=t_spacing,
    )
    return PanSegImage(data, properties)


def make_segmentation(data: np.ndarray, layout: str, name: str = "seg") -> PanSegImage:
    return make_image(
        data.astype("uint16"),
        layout,
        semantic_type=SemanticType.SEGMENTATION,
        name=name,
    )


# --- split_timepoints / restack_timepoints (data-model ops) ---


@pytest.mark.parametrize(
    "layout, timepoint_layout",
    [("TZYX", "ZYX"), ("TYX", "YX"), ("TCZYX", "CZYX")],
)
def test_split_timepoints_drops_t(layout, timepoint_layout, request):
    data = request.getfixturevalue("timeseries_" + layout.lower())
    image = make_image(data, layout, t_spacing=TIMESERIES_T_SPACING)

    timepoints = image.split_timepoints()

    assert len(timepoints) == data.shape[0]
    assert [tp.name for tp in timepoints] == [
        f"image_t{i}" for i in range(data.shape[0])
    ]
    assert all(tp.image_layout == ImageLayout(timepoint_layout) for tp in timepoints)
    assert all(not tp.is_timeseries for tp in timepoints)
    assert all(tp.properties.t_spacing is None for tp in timepoints)
    assert all(tp.voxel_size == image.voxel_size for tp in timepoints)
    assert all(tp.semantic_type == image.semantic_type for tp in timepoints)
    assert all(tp.source_file_name == image.source_file_name for tp in timepoints)
    for i, tp in enumerate(timepoints):
        np.testing.assert_array_equal(tp.get_data(), data[i])


def test_split_timepoints_still_image_returns_self():
    image = make_image(np.random.rand(5, 16, 16), "ZYX")

    assert image.split_timepoints() == [image]


@pytest.mark.parametrize("layout", ["TZYX", "TYX", "TCZYX"])
def test_restack_timepoints_roundtrip(layout, request):
    data = request.getfixturevalue("timeseries_" + layout.lower())
    image = make_image(data, layout, t_spacing=TIMESERIES_T_SPACING)
    timepoints = image.split_timepoints()

    restacked = restack_timepoints(
        timepoints, t_spacing=image.properties.t_spacing, name=image.name
    )

    assert restacked.image_layout == image.image_layout
    assert restacked.shape == image.shape
    np.testing.assert_array_equal(restacked.get_data(), data)
    assert restacked.properties.t_spacing == TIMESERIES_T_SPACING
    assert restacked.name == "image"
    assert restacked.semantic_type == image.semantic_type
    assert restacked.voxel_size == image.voxel_size
    assert restacked.source_file_name == image.source_file_name


def test_restack_timepoints_rejects_incompatible_timepoints(timeseries_tzyx):
    image = make_image(timeseries_tzyx, "TZYX", t_spacing=TIMESERIES_T_SPACING)
    timepoints = image.split_timepoints()

    # shape mismatch
    cropped = timepoints[1].derive_new(timepoints[1].get_data()[:, :8], name="cropped")
    with pytest.raises(ValueError, match="not compatible"):
        restack_timepoints([timepoints[0], cropped], t_spacing=None)

    # layout mismatch
    flattened = timepoints[1].derive_new(
        timepoints[1].get_data()[0], name="flat", image_layout=ImageLayout.YX
    )
    with pytest.raises(ValueError, match="not compatible"):
        restack_timepoints([timepoints[0], flattened], t_spacing=None)

    # voxel size mismatch
    small_voxel = timepoints[1].derive_new(
        timepoints[1].get_data(),
        name="small",
        voxel_size=VoxelSize(voxels_size=(0.5, 0.5, 0.5)),
    )
    with pytest.raises(ValueError, match="not compatible"):
        restack_timepoints([timepoints[0], small_voxel], t_spacing=None)

    # semantic type mismatch
    prediction = timepoints[1].derive_new(
        timepoints[1].get_data(),
        name="pred",
        semantic_type=SemanticType.PREDICTION,
    )
    with pytest.raises(ValueError, match="not compatible"):
        restack_timepoints([timepoints[0], prediction], t_spacing=None)

    # t_spacing mismatch (the same check as merge_with)
    other_spacing = timepoints[1].derive_new(
        timepoints[1].get_data(), name="spaced", t_spacing=1.0
    )
    with pytest.raises(ValueError, match="not compatible"):
        restack_timepoints([timepoints[0], other_spacing], t_spacing=None)

    # a timeseries is not a timepoint
    with pytest.raises(ValueError, match="not a single timepoint"):
        restack_timepoints([timepoints[0], image], t_spacing=None)


def test_restack_timepoints_requires_timepoints():
    with pytest.raises(ValueError, match="at least one timepoint"):
        restack_timepoints([], t_spacing=None)


# --- @timepoint_map decorator mechanics ---
#
# The synthetic tasks below mirror real tasks: a frame-mapped body receives
# single-timepoint images and derives its output from the input name.

CALL_LOG: list = []


def _timepoint_index(image: PanSegImage) -> int:
    return int(image.name.rsplit("_t", 1)[1])


@task_tracker
@timepoint_map
def log_timepoints_task(image: PanSegImage, factor: float = 1.0) -> PanSegImage:
    CALL_LOG.append(image)
    return image.derive_new(image.get_data() * factor, name=f"{image.name}_scaled")


@task_tracker
@timepoint_map
def fail_at_second_timepoint_task(image: PanSegImage) -> PanSegImage:
    CALL_LOG.append(image)
    if _timepoint_index(image) == 1:
        raise ValueError("boom at t1")
    return image.derive_new(image.get_data(), name=f"{image.name}_ok")


@task_tracker
@timepoint_map
def message_at_first_timepoint_task(image: PanSegImage) -> PanSegImage | Task_message:
    if _timepoint_index(image) == 0:
        # a Task_message is built inside an except block, as real tasks do
        try:
            raise ValueError("inner failure at t0")
        except ValueError as e:
            return Task_message(str(e), name="message_task")
    return image.derive_new(image.get_data(), name=f"{image.name}_ok")


@task_tracker
@timepoint_map
def tracker_task(image: PanSegImage, _tracker=None) -> PanSegImage:
    CALL_LOG.append(_tracker)
    return image.derive_new(image.get_data(), name=f"{image.name}_ok")


@pytest.fixture(autouse=True)
def _clean_dag_and_log():
    CALL_LOG.clear()
    workflow_handler.clean_dag()
    yield
    CALL_LOG.clear()
    workflow_handler.clean_dag()


def test_decorator_maps_over_timepoints_and_restacks(timeseries_tzyx):
    image = make_image(timeseries_tzyx, "TZYX", t_spacing=TIMESERIES_T_SPACING)

    result = log_timepoints_task(image=image, factor=2.0)

    assert result.is_timeseries
    assert result.image_layout == ImageLayout.TZYX
    assert result.shape == image.shape
    np.testing.assert_array_equal(result.get_data(), timeseries_tzyx * 2.0)
    assert result.properties.t_spacing == TIMESERIES_T_SPACING
    # the restacked layer carries the name the task gives a still image,
    # and the timepoints were transient locals
    assert result.name == "image_scaled"
    assert [tp.name for tp in CALL_LOG] == [f"image_t{i}" for i in range(4)]
    assert all(not tp.is_timeseries for tp in CALL_LOG)


def test_decorator_passes_still_images_through(timeseries_tzyx):
    still = make_image(timeseries_tzyx[0], "ZYX")

    result = log_timepoints_task(image=still, factor=2.0)

    assert result.name == "image_scaled"
    assert not result.is_timeseries
    assert CALL_LOG == [still]


def test_decorator_aborts_on_failed_timepoint(timeseries_tzyx):
    image = make_image(timeseries_tzyx, "TZYX")

    # GUI path: the task_tracker wrapper turns the exception into a
    # Task_message, the identical flow as any task failure
    result = fail_at_second_timepoint_task(image=image)
    assert isinstance(result, Task_message)
    assert "boom at t1" in result.message

    # headless path: the registered callable lets the exception propagate
    registered = workflow_handler.func_registry.get_func(
        "fail_at_second_timepoint_task"
    )
    CALL_LOG.clear()
    with pytest.raises(ValueError, match="boom at t1"):
        registered(image=image)

    # the first failure aborts the run, later timepoints never execute
    assert [_timepoint_index(tp) for tp in CALL_LOG] == [0, 1]


def test_decorator_propagates_task_message_from_inner_call(timeseries_tzyx):
    image = make_image(timeseries_tzyx, "TZYX")

    result = message_at_first_timepoint_task(image=image)

    # a Task_message returned by an inner call is a failure: it propagates
    # instead of being restacked, and no DAG node is recorded
    assert isinstance(result, Task_message)
    assert result.message == "inner failure at t0"
    assert workflow_handler.dag.list_tasks == []


def test_decorator_drives_tracker_at_timepoint_granularity(timeseries_tzyx):
    image = make_image(timeseries_tzyx, "TZYX")

    class FakeTracker:
        total = 0
        progress = 0

    tracker = FakeTracker()
    result = tracker_task(image=image, _tracker=tracker)

    assert tracker.total == 4
    assert tracker.progress == 4
    # per-timepoint calls see no tracker: one progress level in v1
    assert CALL_LOG == [None, None, None, None]
    assert result.name == "image_ok"


# --- task classification: every task is frame-mapped or stack-level ---


@task_tracker
def not_mapped_task(image: PanSegImage) -> PanSegImage:
    return image.derive_new(image.get_data(), name=f"{image.name}_ok")


@task_tracker(stack_level=True)
def stack_level_task(image: PanSegImage) -> PanSegImage:
    return image.derive_new(image.get_data(), name=f"{image.name}_stack")


def test_undecorated_task_rejects_timeseries_input(timeseries_tzyx):
    image = make_image(timeseries_tzyx, "TZYX")

    # GUI path: the task_tracker wrapper rejects before the call
    with pytest.raises(ValueError, match="neither frame-mapped.*nor stack-level"):
        not_mapped_task(image=image)

    # headless path: the registered callable rejects too
    registered = workflow_handler.func_registry.get_func("not_mapped_task")
    with pytest.raises(ValueError, match="neither frame-mapped.*nor stack-level"):
        registered(image=image)

    # still images pass the guard untouched
    still = make_image(timeseries_tzyx[0], "ZYX")
    assert not_mapped_task(image=still).name == "image_ok"


def test_stack_level_task_accepts_timeseries(timeseries_tzyx):
    image = make_image(timeseries_tzyx, "TZYX")

    result = stack_level_task(image=image)

    # the task body saw the whole timeseries, no loop, no restack
    assert result.image_layout == ImageLayout.TZYX
    assert result.name == "image_stack"


# --- the real tasks: DAG surface, both execution paths, multi-image rules ---

FRAME_MAPPED_TASKS = [
    gaussian_smoothing_task,
    image_cropping_task,
    set_voxel_size_task,
    set_t_spacing_task,
    image_rescale_to_shape_task,
    image_rescale_to_voxel_size_task,
    remove_false_positives_by_foreground_probability_task,
    fix_over_under_segmentation_from_nuclei_task,
    set_biggest_instance_to_zero_task,
    relabel_segmentation_task,
    image_pair_operation_task,
    dt_watershed_task,
    clustering_segmentation_task,
    lmc_segmentation_task,
    aio_watershed_task,
    unet_prediction_task,
    biio_prediction_task,
]


def test_all_seventeen_frame_mapped_tasks_are_decorated():
    assert len(FRAME_MAPPED_TASKS) == 17
    for task in FRAME_MAPPED_TASKS:
        assert getattr(task, "__timepoint_mapped__", False), (
            f"{task.__name__} must be decorated with @timepoint_map"
        )


def test_frame_mapped_task_records_one_dag_node(timeseries_tzyx):
    image = make_image(timeseries_tzyx, "TZYX", t_spacing=TIMESERIES_T_SPACING)

    result = gaussian_smoothing_task(image=image, sigma=1.0)

    # one node: the timeseries in, the restacked timeseries out, the same
    # parameters as a still-image call - timepoint_map is not a parameter
    nodes = [
        task for task in workflow_handler.dag.list_tasks if "gaussian" in task.func
    ]
    assert len(nodes) == 1
    assert nodes[0].images_inputs == {"image": image.unique_name}
    assert nodes[0].parameters == {"sigma": 1.0}
    assert nodes[0].outputs == [result.unique_name]

    assert result.is_timeseries
    assert result.image_layout == ImageLayout.TZYX
    assert result.shape == image.shape
    assert result.name == "image_smoothed"


def test_frame_mapped_task_on_headless_runner(timeseries_tzyx, tmp_path):
    image = make_image(timeseries_tzyx, "TZYX", t_spacing=TIMESERIES_T_SPACING)
    result = gaussian_smoothing_task(image=image, sigma=1.0)
    task = workflow_handler.dag.list_tasks[-1]

    dag_path = tmp_path / "workflow.yaml"
    dag_path.write_text("infos: {}\ninputs: {}\nlist_tasks: []\n")
    runner = SerialRunner(dag_path)

    var_space = {image.unique_name: image}
    var_space = runner.run_task(task, var_space)

    # the registered callable ran the loop and produced one restacked
    # timeseries; the timepoints stayed locals and never entered var_space
    assert set(var_space) == {image.unique_name, result.unique_name}
    replayed = var_space[result.unique_name]
    assert replayed.is_timeseries
    assert replayed.image_layout == ImageLayout.TZYX
    np.testing.assert_allclose(replayed.get_data(), result.get_data())


def _ramp_timeseries(n_timepoints: int, value: float) -> PanSegImage:
    data = np.zeros((n_timepoints, 4, 8, 8), dtype="float32")
    for t in range(n_timepoints):
        data[t] = t + value
    return make_image(data, "TZYX", name="ramp")


def test_image_pair_operation_broadcasts_still_input():
    timeseries = _ramp_timeseries(3, value=1.0)
    static = make_image(np.full((4, 8, 8), 10.0, dtype="float32"), "ZYX", name="static")

    result = image_pair_operation_task(
        image1=timeseries, image2=static, operation="add"
    )

    assert result.is_timeseries
    assert result.name == "ramp_add_static"
    for t in range(3):
        np.testing.assert_allclose(result.get_data()[t], t + 11.0)


def test_remove_false_positives_broadcasts_static_foreground(timeseries_segmentation):
    segmentation = make_segmentation(timeseries_segmentation, "TZYX", name="seg")
    foreground = make_image(
        np.ones((5, 16, 16), dtype="float32"), "ZYX", name="foreground"
    )

    kept, removed = remove_false_positives_by_foreground_probability_task(
        segmentation=segmentation, foreground=foreground, threshold=0.5
    )

    # both outputs restack, each timepoint against the static foreground map
    assert kept.is_timeseries and removed.is_timeseries
    assert kept.name == "seg_fg_filtered"
    assert removed.name == "seg_false_positives"
    # the static foreground map (all 1.0) keeps every region of every
    # timepoint; the functional relabels sequentially, so compare support
    np.testing.assert_array_equal(kept.get_data() != 0, timeseries_segmentation != 0)
    assert not removed.get_data().any()


def test_multi_image_task_without_broadcast_rejects_mixed_inputs(
    timeseries_segmentation,
):
    cell_seg = make_segmentation(timeseries_segmentation, "TZYX", name="cells")
    nuclei_seg = make_segmentation(timeseries_segmentation[0], "ZYX", name="nuclei")

    # the GUI wrapper translates the exception into a Task_message (covered
    # by the abort test); the registered callable raises, as headless sees it
    with pytest.raises(ValueError, match="does not opt in to broadcasting"):
        workflow_handler.func_registry.get_func(
            "fix_over_under_segmentation_from_nuclei_task"
        )(
            cell_seg=cell_seg,
            nuclei_seg=nuclei_seg,
            threshold_merge=0.5,
            threshold_split=0.5,
            quantile_min=0.1,
            quantile_max=0.9,
        )


def test_timeseries_inputs_with_different_lengths_are_rejected():
    short = _ramp_timeseries(3, value=1.0)
    long = _ramp_timeseries(4, value=1.0)

    with pytest.raises(ValueError, match="different numbers of timepoints"):
        workflow_handler.func_registry.get_func("image_pair_operation_task")(
            image1=short, image2=long, operation="add"
        )


def test_timeseries_inputs_with_different_t_spacing_are_rejected():
    first = make_image(
        np.zeros((2, 4, 8, 8), dtype="float32"),
        "TZYX",
        t_spacing=10.0,
        name="first",
    )
    second = make_image(
        np.zeros((2, 4, 8, 8), dtype="float32"),
        "TZYX",
        t_spacing=20.0,
        name="second",
    )

    with pytest.raises(ValueError, match="different t_spacing"):
        workflow_handler.func_registry.get_func("image_pair_operation_task")(
            image1=first, image2=second, operation="add"
        )


@pytest.mark.parametrize(
    "t_spacing, expected",
    [(10.0, 10.0), (None, None)],
)
def test_equal_t_spacing_becomes_the_shared_spacing(t_spacing, expected):
    first = make_image(
        np.zeros((2, 4, 8, 8), dtype="float32"),
        "TZYX",
        t_spacing=t_spacing,
        name="first",
    )
    second = make_image(
        np.zeros((2, 4, 8, 8), dtype="float32"),
        "TZYX",
        t_spacing=t_spacing,
        name="second",
    )

    result = image_pair_operation_task(image1=first, image2=second, operation="add")

    assert result.properties.t_spacing == expected


def test_set_t_spacing_task_sets_known_value(timeseries_tzyx):
    image = make_image(timeseries_tzyx, "TZYX")

    result = set_t_spacing_task(image=image, t_spacing=30.0)

    assert result.properties.t_spacing == 30.0
    assert result.name == "image_set_t_spacing"
    # property-only: the data is unchanged
    np.testing.assert_array_equal(result.get_data(), timeseries_tzyx)
    # recorded as a DAG node for the headless yaml mechanism
    nodes = [
        task for task in workflow_handler.dag.list_tasks if "set_t_spacing" in task.func
    ]
    assert len(nodes) == 1
    assert nodes[0].parameters == {"t_spacing": 30.0}
    assert nodes[0].outputs == [result.unique_name]


def test_set_t_spacing_task_clears_known_value(timeseries_tzyx):
    image = make_image(timeseries_tzyx, "TZYX", t_spacing=TIMESERIES_T_SPACING)

    result = set_t_spacing_task(image=image, t_spacing=None)

    assert result.properties.t_spacing is None


def test_relabel_segmentation_is_per_timepoint(timeseries_segmentation):
    segmentation = make_segmentation(timeseries_segmentation, "TZYX", name="seg")

    result = relabel_segmentation_task(image=segmentation)

    # the fixture carries disjoint label IDs per timepoint: the output at
    # timepoint t equals a standalone relabel of input timepoint t, with no
    # cross-timepoint ID renumbering or correspondence
    for t, timepoint in enumerate(segmentation.split_timepoints()):
        expected = relabel_segmentation(timepoint.get_data())
        np.testing.assert_array_equal(result.get_data()[t], expected)


def test_set_biggest_instance_to_zero_is_per_timepoint():
    data = np.zeros((2, 8, 16, 16), dtype="uint16")
    data[0, 0:2, :, :] = 1  # largest in t0
    data[0, 6:8, 0:8, 0:8] = 2
    data[1, 6:8, :, :] = 3  # largest in t1
    data[1, 0:2, 0:8, 0:8] = 4
    segmentation = make_segmentation(data, "TZYX", name="seg")

    result = set_biggest_instance_to_zero_task(image=segmentation)
    out = result.get_data()

    assert set(np.unique(out[0])) == {0, 2}
    assert set(np.unique(out[1])) == {0, 4}


def test_label_semantics_are_stated_in_the_docstrings():
    for task in (
        set_biggest_instance_to_zero_task,
        relabel_segmentation_task,
        fix_over_under_segmentation_from_nuclei_task,
    ):
        assert "timepoint" in task.__doc__


def test_stack_level_io_tasks_accept_timeseriess(timeseries_tzyx, tmp_path):
    first = make_image(timeseries_tzyx, "TZYX", name="first")
    second = make_image(timeseries_tzyx, "TZYX", name="second")

    # merge_channels_task is stack-level: T-aware two-stage merge, no loop
    merged = merge_channels_task(image_0=first, image_1=second)
    assert merged.image_layout == ImageLayout.TCZYX
    assert merged.shape == (4, 2, 5, 16, 16)

    # export_image_task is stack-level: it writes the whole timeseries as
    # one file
    export_image_task(
        image=first,
        export_directory=tmp_path,
        name_pattern="{image_name}_export",
        export_format="h5",
        key="raw",
        scale_to_origin=False,
    )
    assert (tmp_path / "first_export.h5").exists()


# --- per-stage pipeline behavior on timeseriess ---
# (spec: "Per-stage pipeline behavior"; falls out of the wrapper, no new
# algorithm code)


def test_crop_applies_one_spatial_region_to_every_timepoint(timeseries_tzyx):
    image = make_image(timeseries_tzyx, "TZYX", t_spacing=TIMESERIES_T_SPACING)
    rectangle = np.array([[0, 2, 2], [0, 2, 9], [0, 9, 9], [0, 9, 2]])

    result = image_cropping_task(image=image, rectangle=rectangle, crop_z=(1, 4))

    assert result.is_timeseries
    assert result.image_layout == ImageLayout.TZYX
    assert result.shape == (4, 3, 7, 7)
    # identical spatial crop at every timepoint: each output frame is the
    # crop of the corresponding input frame, no per-timepoint ROI
    for t, timepoint in enumerate(image.split_timepoints()):
        np.testing.assert_array_equal(
            result.get_data()[t], timepoint.get_data()[1:4, 2:9, 2:9]
        )


def test_crop_applies_one_spatial_region_to_every_timepoint_2d():
    data = np.zeros((3, 12, 12), dtype="float32")
    for t in range(3):
        data[t] = np.arange(144, dtype="float32").reshape(12, 12) + t * 100.0
    image = make_image(data, "TYX", t_spacing=TIMESERIES_T_SPACING)
    rectangle = np.array([[2, 2], [2, 9], [9, 9]])

    result = image_cropping_task(image=image, rectangle=rectangle)

    assert result.is_timeseries
    assert result.image_layout == ImageLayout.TYX
    assert result.shape == (3, 7, 7)
    for t in range(3):
        np.testing.assert_array_equal(result.get_data()[t], data[t][2:9, 2:9])


def test_rescale_leaves_t_untouched_and_preserves_t_spacing():
    data = np.zeros((3, 4, 16, 16), dtype="float32")
    for t in range(3):
        data[t] = t + 1  # per-timepoint constant: mixing frames would be visible
    image = make_image(data, "TZYX", t_spacing=TIMESERIES_T_SPACING)

    result = image_rescale_to_voxel_size_task(
        image=image, new_voxels_size=(2.0, 2.0, 2.0), new_unit="um"
    )

    assert result.is_timeseries
    assert result.image_layout == ImageLayout.TZYX
    # T untouched: same number of timepoints, each frame still its own constant
    assert result.shape == (3, 2, 8, 8)
    for t in range(3):
        np.testing.assert_allclose(result.get_data()[t], t + 1)
    assert result.properties.t_spacing == TIMESERIES_T_SPACING


def test_normalization_runs_per_timepoint():
    ramp = np.arange(256, dtype="float32").reshape(4, 8, 8) / 255.0
    data = np.zeros((2, 4, 8, 8), dtype="float32")
    data[0] = ramp
    data[1] = 2.0 * ramp + 5.0  # illumination drift at t1
    image1 = make_image(data, "TZYX", t_spacing=TIMESERIES_T_SPACING, name="drift")
    image2 = make_image(np.zeros((4, 8, 8), dtype="float32"), "ZYX", name="zeros")

    result = image_pair_operation_task(
        image1=image1,
        image2=image2,
        operation="add",
        normalize_input=True,
        normalize_output=False,
    )

    assert result.is_timeseries
    # the min-max normalizes each timepoint against its own range, so the
    # drifted timepoint lands on the same pattern as the first
    for t in range(2):
        np.testing.assert_allclose(result.get_data()[t], ramp, atol=1e-6)
