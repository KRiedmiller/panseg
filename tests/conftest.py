# pylint: disable=missing-docstring,import-outside-toplevel

import itertools
import shutil
from pathlib import Path
from typing import Sequence
from uuid import uuid4
from xml.etree import ElementTree

import numpy as np
import pytest
import skimage.transform as skt
import tifffile
import torch
import yaml
from napari.layers import Image, Labels, Shapes

from panseg.core.image import SemanticType
from panseg.io.io import smart_load

TEST_FILES = Path(__file__).resolve().parent / "resources"
VOXEL_SIZE = (0.235, 0.15, 0.15)
KEY_ZARR = "volumes/new"

IS_CUDA_AVAILABLE = torch.cuda.is_available()


@pytest.fixture
def napari_raw():
    data = np.random.rand(10, 10, 10)
    voxel_size = (1.0, 1.0, 1.0)
    metadata = {
        "semantic_type": SemanticType.RAW,
        "voxel_size": {"voxels_size": voxel_size, "unit": "um"},
        "original_voxel_size": {"voxels_size": voxel_size, "unit": "um"},
        "image_layout": "ZYX",
        "id": uuid4(),
    }
    return Image(data, metadata=metadata, name="test_image_3D")


@pytest.fixture
def napari_raw_2d():
    data = np.random.rand(10, 10)
    voxel_size = None
    metadata = {
        "semantic_type": SemanticType.RAW,
        "voxel_size": {"voxels_size": voxel_size, "unit": "um"},
        "original_voxel_size": {"voxels_size": voxel_size, "unit": "um"},
        "image_layout": "YX",
        "id": uuid4(),
    }
    return Image(data, metadata=metadata, name="test_image_2D")


@pytest.fixture
def napari_raw_4d():
    data = np.random.rand(10, 10, 10, 10)
    voxel_size = None
    metadata = {
        "semantic_type": SemanticType.RAW,
        "voxel_size": {"voxels_size": voxel_size, "unit": "um"},
        "original_voxel_size": {"voxels_size": voxel_size, "unit": "um"},
        "image_layout": "ZCYX",
        "id": uuid4(),
    }
    return Image(data, metadata=metadata, name="test_image_2D")


@pytest.fixture
def napari_timelapse():
    data = np.random.rand(4, 5, 16, 16).astype("float32")
    voxel_size = (1.0, 1.0, 1.0)
    metadata = {
        "semantic_type": SemanticType.RAW,
        "voxel_size": {"voxels_size": voxel_size, "unit": "um"},
        "original_voxel_size": {"voxels_size": voxel_size, "unit": "um"},
        "image_layout": "TZYX",
        "t_spacing": 10.0,
        "t_unit": "s",
        "id": uuid4(),
    }
    return Image(data, metadata=metadata, name="test_timelapse")


@pytest.fixture
def napari_timelapse_unknown_t_spacing():
    data = np.random.rand(4, 5, 16, 16).astype("float32")
    voxel_size = (1.0, 1.0, 1.0)
    metadata = {
        "semantic_type": SemanticType.RAW,
        "voxel_size": {"voxels_size": voxel_size, "unit": "um"},
        "original_voxel_size": {"voxels_size": voxel_size, "unit": "um"},
        "image_layout": "TZYX",
        "t_spacing": None,
        "t_unit": "s",
        "id": uuid4(),
    }
    return Image(data, metadata=metadata, name="test_timelapse_unknown")


@pytest.fixture
def napari_prediction():
    data = np.random.rand(10, 10, 10)
    voxel_size = (1.0, 1.0, 1.0)
    metadata = {
        "semantic_type": SemanticType.PREDICTION,
        "voxel_size": {"voxels_size": voxel_size, "unit": "um"},
        "original_voxel_size": {"voxels_size": voxel_size, "unit": "um"},
        "image_layout": "ZYX",
        "id": uuid4(),
    }
    return Image(data, metadata=metadata, name="test_prediction_3D")


@pytest.fixture
def napari_segmentation():
    data = np.random.rand(10, 10, 10)
    data = np.array(data, dtype=np.int8)
    voxel_size = (1.0, 1.0, 1.0)
    metadata = {
        "semantic_type": SemanticType.SEGMENTATION,
        "voxel_size": {"voxels_size": voxel_size, "unit": "um"},
        "original_voxel_size": {"voxels_size": voxel_size, "unit": "um"},
        "image_layout": "ZYX",
        "id": uuid4(),
    }
    return Labels(data, metadata=metadata, name="test_segmentation_3D")


@pytest.fixture
def napari_no_meta_image():
    data = np.random.rand(10, 10, 10)
    metadata = {}
    return Image(data, metadata=metadata, name="test_image_3D_no_meta")


@pytest.fixture
def napari_no_meta_labels():
    data = np.random.rand(10, 10, 10)
    data = np.array(data, dtype=np.int8)
    metadata = {}
    return Labels(data, metadata=metadata, name="test_label_3D_no_meta")


@pytest.fixture
def napari_shapes():
    return Shapes()


@pytest.fixture
def raw_zcyx_75x2x75x75() -> np.ndarray:
    return smart_load(TEST_FILES / "rgb_3D.tif")


@pytest.fixture
def raw_zcyx_96x2x96x96(raw_zcyx_75x2x75x75):
    return skt.resize(raw_zcyx_75x2x75x75, (96, 2, 96, 96), order=1)


@pytest.fixture
def raw_cell_3d_100x128x128(raw_zcyx_75x2x75x75):
    return skt.resize(raw_zcyx_75x2x75x75[:, 1], (100, 128, 128), order=1)


@pytest.fixture
def raw_cell_2d_96x96(raw_cell_3d_100x128x128):
    return raw_cell_3d_100x128x128[48]


@pytest.fixture
def path_h5(tmpdir) -> Path:
    """Create an HDF5 file using `h5py`'s API with an example dataset for testing purposes."""
    base = Path(tmpdir)
    base.mkdir(exist_ok=True)
    return base / "test.h5"


@pytest.fixture
def path_zarr(tmpdir) -> Path:
    """Create a Zarr file using `zarr`'s API with an example dataset for testing purposes."""
    base = Path(tmpdir)
    base.mkdir(exist_ok=True)
    return base / "test.zarr"


@pytest.fixture
def path_tiff(tmpdir) -> Path:
    """Create a TIFF file using `tifffile`'s API with an example dataset for testing purposes."""
    base = Path(tmpdir)
    base.mkdir(exist_ok=True)
    return base / "test.tiff"


@pytest.fixture
def path_jpg(tmpdir) -> Path:
    """Create a JPG file using `PIL`'s API with an example image for testing purposes."""
    base = Path(tmpdir)
    base.mkdir(exist_ok=True)
    return base / "test.jpg"


@pytest.fixture
def preprocess_config(path_file_hdf5):
    """Create pipeline config with only pre-processing (Gaussian filter) enabled."""
    config_path = TEST_FILES / "test_config.yaml"
    config = yaml.full_load(config_path.read_text())
    # Add the file path to process
    config["path"] = path_file_hdf5
    # Enable Gaussian smoothing for some work
    config["preprocessing"]["state"] = True
    config["preprocessing"]["filter"]["state"] = True
    return config


@pytest.fixture
def prediction_config(tmpdir):
    """Create pipeline config with Unet prediction enabled.

    Prediction will be executed on the `tests/resources/sample_ovules.h5`.
    The `sample_ovules.h5` file is copied to the temporary directory to avoid
    creating unnecessary files in `tests/resources`.
    """
    # Load the test configuration
    config_path = TEST_FILES / "test_config.yaml"
    config = yaml.full_load(config_path.read_text())
    # Enable UNet prediction
    config["cnn_prediction"]["state"] = True
    # Copy `sample_ovule.h5` to the temporary directory
    sample_ovule_path = TEST_FILES / "sample_ovule.h5"
    tmp_path = Path(tmpdir) / "sample_ovule.h5"
    shutil.copy2(sample_ovule_path, tmp_path)
    # Add the temporary path to the config
    config["path"] = str(tmp_path)  # Ensure the path is a string
    return config


@pytest.fixture
def complex_test_data():
    """
    Generates a complex 3D dataset with both under-segmented and over-segmented cells.

    Returns:
        tuple[np.ndarray, np.ndarray, np.ndarray]: cell segmentation, nuclei segmentation, and boundary probability map.
    """
    # Create a 3D grid of zeros
    cell_seg = np.zeros((10, 10, 10), dtype=np.uint16)
    nuclei_seg = np.zeros_like(cell_seg, dtype=np.uint16)

    # Define cells with under-segmentation (multiple nuclei in one cell)
    # Cell 1: covers (2, 2, 2) to (5, 5, 5), contains two nuclei
    cell_seg[2:6, 2:6, 2:6] = 1
    nuclei_seg[2:4, 2:3, 2:3] = 1
    nuclei_seg[4:6, 5:6, 5:6] = 2

    # Define cells with over-segmentation (one nucleus split into multiple cells)
    # Cell 2 and 3: cover (6, 6, 6) to (8, 8, 8), with one nucleus overlapping both cells
    cell_seg[6:8, 6:10, 6:10] = 2
    cell_seg[8:10, 6:10, 6:10] = 3
    nuclei_seg[7:9, 7:9, 7:9] = 3

    # Define another under-segmented region with a large cell and multiple nuclei
    # Cell 4: covers (1, 1, 6) to (3, 3, 8), contains two nuclei
    cell_seg[1:4, 1:4, 6:9] = 4
    nuclei_seg[1:2, 1:2, 6:7] = 4
    nuclei_seg[3:4, 3:4, 8:9] = 5

    # Generate a boundary probability map with higher values on the edges of the cells
    boundary_pmap = np.ones_like(cell_seg, dtype=np.float32)
    boundary_pmap[2:6, 2:6, 2:6] = 0.2
    boundary_pmap[6:8, 6:8, 6:8] = 0.2
    boundary_pmap[1:4, 1:4, 6:9] = 0.2

    return cell_seg, nuclei_seg, boundary_pmap


@pytest.fixture
def workflow_yaml(tmpdir: Path):
    return Path(shutil.copy2(TEST_FILES / "test_workflow.yaml", tmpdir))


@pytest.fixture
def workflow_complete_yaml(tmpdir: Path):
    return Path(shutil.copy2(TEST_FILES / "test_complete_workflow.yaml", tmpdir))


@pytest.fixture
def workflow_aio_yaml(tmpdir: Path):
    return Path(shutil.copy2(TEST_FILES / "test_workflow_aio.yaml", tmpdir))


@pytest.fixture
def zarr_file_empty():
    return TEST_FILES / "empty.zarr"


@pytest.fixture
def zarr_file_3d():
    return TEST_FILES / "3d.zarr"


@pytest.fixture
def h5_file():
    return TEST_FILES / "sample_ovule.h5"


# --- Timelapse fixtures (time-dimension spec) ---
#
# Synthetic raw timelapses on one shape skeleton: T=4, C=2, Z=5, Y=X=16.
# Tests build PanSegImage inline from these arrays; known-vs-unknown
# t_spacing are the two property dicts below, not separate fixtures.

TIMELAPSE_PROPS_KNOWN_T_SPACING = {"t_spacing": 10.0, "t_unit": "s"}
TIMELAPSE_PROPS_UNKNOWN_T_SPACING = {"t_spacing": None}


def _timelapse_raw(shape: tuple[int, ...], seed: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    return rng.random(shape).astype("float32")


@pytest.fixture
def timelapse_tyx() -> np.ndarray:
    """Raw TYX float32 timelapse, shape (4, 16, 16)."""
    return _timelapse_raw((4, 16, 16), seed=11)


@pytest.fixture
def timelapse_tcyx() -> np.ndarray:
    """Raw TCYX float32 timelapse, shape (4, 2, 16, 16)."""
    return _timelapse_raw((4, 2, 16, 16), seed=12)


@pytest.fixture
def timelapse_tzyx() -> np.ndarray:
    """Raw TZYX float32 timelapse, shape (4, 5, 16, 16)."""
    return _timelapse_raw((4, 5, 16, 16), seed=13)


@pytest.fixture
def timelapse_tczyx() -> np.ndarray:
    """Raw TCZYX float32 timelapse, shape (4, 2, 5, 16, 16)."""
    return _timelapse_raw((4, 2, 5, 16, 16), seed=14)


def _timelapse_segmentation() -> np.ndarray:
    """uint16 TZYX segmentation, shape (4, 5, 16, 16).

    Label IDs are independent across timepoints by construction: timepoint
    t carries the disjoint ID range 3t+1..3t+3, so no label ID ever appears
    in two timepoints.
    """
    t, z, y, x = 4, 5, 16, 16
    blob = 3
    rng = np.random.default_rng(15)
    seg = np.zeros((t, z, y, x), dtype="uint16")
    for t_index in range(t):
        for j in range(3):
            z0 = int(rng.integers(0, z - blob + 1))
            y0 = int(rng.integers(0, y - blob + 1))
            x0 = int(rng.integers(0, x - blob + 1))
            seg[t_index, z0 : z0 + blob, y0 : y0 + blob, x0 : x0 + blob] = (
                t_index * 3 + j + 1
            )
    return seg


@pytest.fixture
def timelapse_segmentation() -> np.ndarray:
    """uint16 TZYX segmentation timelapse; label IDs are independent across timepoints."""
    return _timelapse_segmentation()


# --- Synthetic OME-TIFF builders (time-dimension spec) ---
#
# The committed anchors under tests/resources/ome_tiff_examples/ carry no
# timing metadata, so every timing variant is synthesized into tmp_path at
# test time.

_OME_XML_NS = "http://www.openmicroscopy.org/Schemas/OME/2016-06"

# The shared shape skeleton (T, C, Z, Y, X); each layout is the projection of
# the canonical order onto its present axes.
TIMELAPSE_SHAPE_SKELETON = (4, 2, 5, 16, 16)

_TIMELAPSE_OME_SHAPES: dict[str, tuple[int, ...]] = {
    axes: tuple(n for ax, n in zip("TCZYX", TIMELAPSE_SHAPE_SKELETON) if ax in axes)
    for axes in ("TYX", "TCYX", "TZYX", "TCZYX")
}


def _write_ome_timelapse(
    path: Path,
    axes: str,
    shape: tuple[int, ...],
    seed: int,
    t_increment: float | None = None,
    t_increment_unit: str = "s",
    plane_delta_t: Sequence[int | float] | None = None,
    plane_delta_t_unit: str = "ms",
) -> Path:
    rng = np.random.default_rng(seed)
    data = (rng.random(shape) * 4096).astype("uint16")
    metadata: dict = {"axes": axes}
    if t_increment is not None:
        metadata["TimeIncrement"] = t_increment
        metadata["TimeIncrementUnit"] = t_increment_unit
    if plane_delta_t is not None:
        metadata["Plane"] = {
            "DeltaT": plane_delta_t,
            "DeltaTUnit": [plane_delta_t_unit] * len(plane_delta_t),
        }
    tifffile.imwrite(path, data, ome=True, photometric="minisblack", metadata=metadata)
    return path


def _plane_delta_t_sequence(
    axes: str, shape: tuple[int, ...], per_timepoint: Sequence[int | float]
) -> list[int | float]:
    """Per-plane DeltaT values in plane raster order (last page axis fastest)."""
    page_shape = shape[:-2]
    t_axis = axes.index("T")
    return [
        per_timepoint[coords[t_axis]]
        for coords in itertools.product(*[range(n) for n in page_shape])
    ]


@pytest.fixture
def make_ome_timelapse(tmp_path):
    """Factory for synthetic OME-TIFF timelapses written into tmp_path.

    Defaults to the TZYX slice of the shared shape skeleton. ``t_increment``
    writes the Pixels TimeIncrement/TimeIncrementUnit attributes;
    ``plane_delta_t`` writes a uniform per-plane DeltaT and
    ``nonuniform_plane_delta_t`` a per-timepoint varying DeltaT (1000 ms,
    2000 ms, ...). With none of them the file carries no timing metadata.
    Returns the written file path.
    """
    counter = 0

    def _make(
        axes: str = "TZYX",
        shape: tuple[int, ...] | None = None,
        t_increment: float | None = None,
        t_increment_unit: str = "s",
        plane_delta_t: float | None = None,
        nonuniform_plane_delta_t: bool = False,
        plane_delta_t_unit: str = "ms",
    ) -> Path:
        nonlocal counter
        counter += 1
        if shape is None:
            shape = _TIMELAPSE_OME_SHAPES[axes]
        assert len(shape) == len(axes)
        if nonuniform_plane_delta_t:
            per_timepoint = [1000 * (i + 1) for i in range(shape[axes.index("T")])]
            sequence = _plane_delta_t_sequence(axes, shape, per_timepoint)
        elif plane_delta_t is not None:
            sequence = [plane_delta_t] * int(np.prod(shape[:-2]))
        else:
            sequence = None
        return _write_ome_timelapse(
            tmp_path / f"synthetic_ome_{counter}.ome.tif",
            axes,
            shape,
            seed=1000 + counter,
            t_increment=t_increment,
            t_increment_unit=t_increment_unit,
            plane_delta_t=sequence,
            plane_delta_t_unit=plane_delta_t_unit,
        )

    return _make


def _ome_root(path: Path) -> ElementTree.Element:
    with tifffile.TiffFile(path) as tiff:
        return ElementTree.fromstring(tiff.ome_metadata)


def _save_ome_description(path: Path, root: ElementTree.Element) -> None:
    ElementTree.register_namespace("", _OME_XML_NS)
    xml = '<?xml version="1.0" encoding="UTF-8"?>' + ElementTree.tostring(
        root, encoding="unicode"
    )
    with tifffile.TiffFile(path, mode="r+") as tiff:
        tiff.pages[0].tags["ImageDescription"].overwrite(xml.encode("ascii"))


def _ome_multifile_chain(tmp_path: Path) -> tuple[Path, Path, np.ndarray]:
    """Two-file OME-TIFF UUID/FileName chain.

    A 4-timepoint TZYX timelapse (T=4, Z=2, Y=X=16) is split 2+2 across two
    files. The first file's OME-XML is patched to describe the full
    timelapse: its TiffData entry gains a UUID child naming the first file,
    and a second TiffData entry (FirstT=2) is appended whose UUID child
    names the second file. The second file stays a plain 2-timepoint
    OME-TIFF.
    """
    t, z, y, x = 4, 2, 16, 16
    axes = "TZYX"
    rng = np.random.default_rng(42)
    data = (rng.random((t, z, y, x)) * 4096).astype("uint16")
    first = tmp_path / "multifile_first.ome.tif"
    second = tmp_path / "multifile_second.ome.tif"
    tifffile.imwrite(
        first,
        data[: t // 2],
        ome=True,
        photometric="minisblack",
        metadata={"axes": axes},
    )
    tifffile.imwrite(
        second,
        data[t // 2 :],
        ome=True,
        photometric="minisblack",
        metadata={"axes": axes},
    )
    uuid_first = _ome_root(first).get("UUID")
    uuid_second = _ome_root(second).get("UUID")

    root_first = _ome_root(first)
    image = next(e for e in root_first if e.tag.endswith("Image"))
    pixels = next(e for e in image if e.tag.endswith("Pixels"))
    pixels.set("SizeT", str(t))
    own_data = next(e for e in pixels if e.tag.endswith("TiffData"))
    own_uuid = ElementTree.SubElement(own_data, f"{{{_OME_XML_NS}}}UUID")
    own_uuid.set("FileName", first.name)
    own_uuid.text = uuid_first
    other_data = ElementTree.Element(f"{{{_OME_XML_NS}}}TiffData")
    other_data.set("FirstT", str(t // 2))
    other_data.set("FirstZ", "0")
    other_data.set("IFD", "0")
    other_data.set("PlaneCount", str(int(np.prod((t // 2, z)))))
    other_uuid = ElementTree.SubElement(other_data, f"{{{_OME_XML_NS}}}UUID")
    other_uuid.set("FileName", second.name)
    other_uuid.text = uuid_second
    pixels.append(other_data)
    _save_ome_description(first, root_first)
    return first, second, data


@pytest.fixture
def ome_timelapse_multifile(tmp_path):
    """Two-file OME-TIFF UUID/FileName chain (see ``_ome_multifile_chain``).

    Returns (first_path, second_path, full_timelapse_data).
    """
    return _ome_multifile_chain(tmp_path)
