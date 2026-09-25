import time
from pathlib import Path
from uuid import uuid4

import numpy as np
import pytest
from napari.layers import Image

from panseg.core.image import (
    ImageDimensionality,
    ImageLayout,
    ImageProperties,
    ImageType,
    PanSegImage,
    SemanticType,
    import_image,
    stack_sort,
)
from panseg.io.voxelsize import VoxelSize
from tests.conftest import (
    TIMELAPSE_PROPS_KNOWN_T_SPACING,
    TIMELAPSE_PROPS_UNKNOWN_T_SPACING,
)


# Tests for Enum classes
def test_semantic_type_enum():
    assert SemanticType.RAW.value == "raw"
    assert SemanticType.SEGMENTATION.value == "segmentation"
    assert SemanticType.PREDICTION.value == "prediction"


def test_image_type_enum():
    assert ImageType.IMAGE.value == "image"
    assert ImageType.LABEL.value == "labels"
    assert ImageType.to_choices() == ["image", "labels"]


def test_image_dimensionality_enum():
    assert ImageDimensionality.TWO.value == "2D"
    assert ImageDimensionality.THREE.value == "3D"


def test_image_layout_enum():
    assert ImageLayout.YX.value == "YX"
    assert ImageLayout.CYX.value == "CYX"
    assert ImageLayout.ZYX.value == "ZYX"
    assert ImageLayout.CZYX.value == "CZYX"
    assert ImageLayout.ZCYX.value == "ZCYX"
    assert ImageLayout.TYX.value == "TYX"
    assert ImageLayout.TCYX.value == "TCYX"
    assert ImageLayout.TZYX.value == "TZYX"
    assert ImageLayout.TCZYX.value == "TCZYX"
    assert ImageLayout.to_choices() == [
        "YX",
        "CYX",
        "ZYX",
        "CZYX",
        "ZCYX",
        "TYX",
        "TCYX",
        "TZYX",
        "TCZYX",
    ]


# Derived layout properties across all nine layouts: the layout string alone
# carries every axis, nothing about the axes is stored.
LAYOUT_DERIVED_PROPS = [
    pytest.param(ImageLayout.YX, None, None, ImageDimensionality.TWO, False, id="YX"),
    pytest.param(ImageLayout.CYX, 0, None, ImageDimensionality.TWO, False, id="CYX"),
    pytest.param(
        ImageLayout.ZYX, None, None, ImageDimensionality.THREE, False, id="ZYX"
    ),
    pytest.param(
        ImageLayout.CZYX, 0, None, ImageDimensionality.THREE, False, id="CZYX"
    ),
    pytest.param(
        ImageLayout.ZCYX, 1, None, ImageDimensionality.THREE, False, id="ZCYX"
    ),
    pytest.param(ImageLayout.TYX, None, 0, ImageDimensionality.TWO, True, id="TYX"),
    pytest.param(ImageLayout.TCYX, 1, 0, ImageDimensionality.TWO, True, id="TCYX"),
    pytest.param(ImageLayout.TZYX, None, 0, ImageDimensionality.THREE, True, id="TZYX"),
    pytest.param(ImageLayout.TCZYX, 1, 0, ImageDimensionality.THREE, True, id="TCZYX"),
]


@pytest.mark.parametrize(
    ("layout", "channel_axis", "time_axis", "dimensionality", "is_timelapse"),
    LAYOUT_DERIVED_PROPS,
)
def test_image_properties_derived_layout_props(
    layout, channel_axis, time_axis, dimensionality, is_timelapse
):
    voxel_size = VoxelSize(voxels_size=(1.0, 1.0, 1.0), unit="um")
    props = ImageProperties(
        name="image",
        semantic_type=SemanticType.RAW,
        voxel_size=voxel_size,
        image_layout=layout,
        original_voxel_size=voxel_size,
    )
    assert props.channel_axis == channel_axis
    assert props.time_axis == time_axis
    assert props.dimensionality == dimensionality
    assert props.is_timelapse is is_timelapse


# Tests for ImageProperties class
def test_image_properties_initialization():
    voxel_size = VoxelSize(voxels_size=(1.0, 1.0, 1.0), unit="um")
    image_props = ImageProperties(
        name="test_image",
        semantic_type=SemanticType.RAW,
        voxel_size=voxel_size,
        image_layout=ImageLayout.ZYX,
        original_voxel_size=voxel_size,
    )
    assert image_props.name == "test_image"
    assert image_props.semantic_type == SemanticType.RAW
    assert image_props.voxel_size == voxel_size
    assert image_props.image_layout == ImageLayout.ZYX
    assert image_props.original_voxel_size == voxel_size


def test_image_properties_dimensionality():
    voxel_size = VoxelSize(voxels_size=(1.0, 1.0, 1.0), unit="um")

    image_props_2d = ImageProperties(
        name="2D_image",
        semantic_type=SemanticType.RAW,
        voxel_size=voxel_size,
        image_layout=ImageLayout.YX,
        original_voxel_size=voxel_size,
    )
    assert image_props_2d.dimensionality == ImageDimensionality.TWO

    image_props_3d = ImageProperties(
        name="3D_image",
        semantic_type=SemanticType.RAW,
        voxel_size=voxel_size,
        image_layout=ImageLayout.ZYX,
        original_voxel_size=voxel_size,
    )
    assert image_props_3d.dimensionality == ImageDimensionality.THREE


def test_image_properties_image_type():
    voxel_size = VoxelSize(voxels_size=(1.0, 1.0, 1.0), unit="um")

    raw_image_props = ImageProperties(
        name="raw_image",
        semantic_type=SemanticType.RAW,
        voxel_size=voxel_size,
        image_layout=ImageLayout.ZYX,
        original_voxel_size=voxel_size,
    )
    assert raw_image_props.image_type == ImageType.IMAGE

    label_image_props = ImageProperties(
        name="label_image",
        semantic_type=SemanticType.SEGMENTATION,
        voxel_size=voxel_size,
        image_layout=ImageLayout.ZYX,
        original_voxel_size=voxel_size,
    )
    assert label_image_props.image_type == ImageType.LABEL


def test_image_properties_t_spacing_default_unknown():
    voxel_size = VoxelSize(voxels_size=(1.0, 1.0, 1.0), unit="um")
    props = ImageProperties(
        name="image",
        semantic_type=SemanticType.RAW,
        voxel_size=voxel_size,
        image_layout=ImageLayout.TZYX,
        original_voxel_size=voxel_size,
    )
    assert props.t_spacing is None
    assert props.t_unit == "s"
    assert props.t == 1.0


def test_image_properties_t_spacing_seconds():
    voxel_size = VoxelSize(voxels_size=(1.0, 1.0, 1.0), unit="um")
    props = ImageProperties(
        name="image",
        semantic_type=SemanticType.RAW,
        voxel_size=voxel_size,
        image_layout=ImageLayout.TZYX,
        original_voxel_size=voxel_size,
        t_spacing=2.0,
    )
    assert props.t_spacing == 2.0
    assert props.t_unit == "s"
    assert props.t == 2.0


def test_image_properties_t_spacing_unit_normalization():
    voxel_size = VoxelSize(voxels_size=(1.0, 1.0, 1.0), unit="um")
    kwargs = dict(
        name="image",
        semantic_type=SemanticType.RAW,
        voxel_size=voxel_size,
        image_layout=ImageLayout.TYX,
        original_voxel_size=voxel_size,
    )
    ms_props = ImageProperties(t_spacing=500.0, t_unit="ms", **kwargs)
    assert ms_props.t_spacing == 0.5
    assert ms_props.t_unit == "s"

    min_props = ImageProperties(t_spacing=2.0, t_unit="min", **kwargs)
    assert min_props.t_spacing == 120.0
    assert min_props.t_unit == "s"


def test_image_properties_t_spacing_invalid():
    voxel_size = VoxelSize(voxels_size=(1.0, 1.0, 1.0), unit="um")
    kwargs = dict(
        name="image",
        semantic_type=SemanticType.RAW,
        voxel_size=voxel_size,
        image_layout=ImageLayout.TYX,
        original_voxel_size=voxel_size,
    )
    with pytest.raises(ValueError):
        ImageProperties(t_spacing=0.0, **kwargs)
    with pytest.raises(ValueError):
        ImageProperties(t_spacing=5.0, t_unit="h", **kwargs)


def test_image_properties_channel_axis():
    voxel_size = VoxelSize(voxels_size=(1.0, 1.0, 1.0), unit="um")

    cyx_image_props = ImageProperties(
        name="cyx_image",
        semantic_type=SemanticType.RAW,
        voxel_size=voxel_size,
        image_layout=ImageLayout.CYX,
        original_voxel_size=voxel_size,
    )
    assert cyx_image_props.channel_axis == 0

    zcyx_image_props = ImageProperties(
        name="zcyx_image",
        semantic_type=SemanticType.RAW,
        voxel_size=voxel_size,
        image_layout=ImageLayout.ZCYX,
        original_voxel_size=voxel_size,
    )
    assert zcyx_image_props.channel_axis == 1


def test_image_properties_interpolation_order():
    voxel_size = VoxelSize(voxels_size=(1.0, 1.0, 1.0), unit="um")

    label_image_props = ImageProperties(
        name="label_image",
        semantic_type=SemanticType.SEGMENTATION,
        voxel_size=voxel_size,
        image_layout=ImageLayout.ZYX,
        original_voxel_size=voxel_size,
    )
    assert label_image_props.interpolation_order() == 0

    raw_image_props = ImageProperties(
        name="raw_image",
        semantic_type=SemanticType.RAW,
        voxel_size=voxel_size,
        image_layout=ImageLayout.ZYX,
        original_voxel_size=voxel_size,
    )
    assert raw_image_props.interpolation_order() == 1


# Singleton squeeze rule: drop every length-1 axis except Y and X, the
# layout is the projection onto what remains.
SQUEEZE_CASES = [
    pytest.param(
        ImageLayout.TZYX,
        (1, 5, 16, 16),
        ImageLayout.ZYX,
        (5, 16, 16),
        id="T=1 TZYX->ZYX",
    ),
    pytest.param(
        ImageLayout.TCZYX,
        (7, 3, 1, 16, 16),
        ImageLayout.TCYX,
        (7, 3, 16, 16),
        id="Z=1 TCZYX->TCYX",
    ),
    pytest.param(
        ImageLayout.TCZYX,
        (1, 3, 5, 16, 16),
        ImageLayout.CZYX,
        (3, 5, 16, 16),
        id="T=1 TCZYX->CZYX",
    ),
    pytest.param(
        ImageLayout.TCZYX,
        (7, 1, 5, 16, 16),
        ImageLayout.TZYX,
        (7, 5, 16, 16),
        id="C=1 TCZYX->TZYX",
    ),
    pytest.param(
        ImageLayout.ZYX, (1, 16, 16), ImageLayout.YX, (16, 16), id="Z=1 ZYX->YX"
    ),
    pytest.param(
        ImageLayout.CZYX,
        (1, 1, 16, 16),
        ImageLayout.YX,
        (16, 16),
        id="C=1,Z=1 CZYX->YX",
    ),
]


@pytest.mark.parametrize(
    "layout, shape, expected_layout, expected_shape", SQUEEZE_CASES
)
def test_construction_squeeze_rule(layout, shape, expected_layout, expected_shape):
    data = np.random.rand(*shape)
    voxel_size = VoxelSize(voxels_size=(1.0, 1.0, 1.0), unit="um")
    props = ImageProperties(
        name="image",
        semantic_type=SemanticType.RAW,
        voxel_size=voxel_size,
        image_layout=layout,
        original_voxel_size=voxel_size,
    )
    image = PanSegImage(data, props)
    assert image.image_layout == expected_layout
    assert image.shape == expected_shape


def test_construction_squeeze_dropping_t_clears_t_spacing():
    data = np.random.rand(1, 5, 16, 16)
    voxel_size = VoxelSize(voxels_size=(1.0, 1.0, 1.0), unit="um")
    props = ImageProperties(
        name="image",
        semantic_type=SemanticType.RAW,
        voxel_size=voxel_size,
        image_layout=ImageLayout.TZYX,
        original_voxel_size=voxel_size,
        t_spacing=5.0,
    )
    image = PanSegImage(data, props)
    assert image.image_layout == ImageLayout.ZYX
    assert image.is_timelapse is False
    assert image.properties.t_spacing is None


def test_construction_squeeze_data_content():
    data = np.random.rand(1, 5, 16, 16)
    voxel_size = VoxelSize(voxels_size=(1.0, 1.0, 1.0), unit="um")
    props = ImageProperties(
        name="image",
        semantic_type=SemanticType.RAW,
        voxel_size=voxel_size,
        image_layout=ImageLayout.TZYX,
        original_voxel_size=voxel_size,
    )
    image = PanSegImage(data, props)
    np.testing.assert_array_equal(image.get_data(normalize_01=False), data[0])


# Tests for PanSegImage class
def test_panseg_image_initialization():
    data = np.random.rand(10, 10, 10)
    voxel_size = VoxelSize(voxels_size=(1.0, 1.0, 1.0), unit="um")
    image_props = ImageProperties(
        name="test_image",
        semantic_type=SemanticType.RAW,
        voxel_size=voxel_size,
        image_layout=ImageLayout.ZYX,
        original_voxel_size=voxel_size,
    )
    ps_image = PanSegImage(data, image_props)

    assert ps_image.shape == (10, 10, 10)
    assert ps_image.voxel_size == voxel_size
    assert ps_image.name == "test_image"


def test_panseg_image_derive_new():
    data = np.random.rand(10, 10, 10)
    voxel_size = VoxelSize(voxels_size=(1.0, 1.0, 1.0), unit="um")
    image_props = ImageProperties(
        name="test_image",
        semantic_type=SemanticType.RAW,
        voxel_size=voxel_size,
        image_layout=ImageLayout.ZYX,
        original_voxel_size=voxel_size,
    )
    ps_image = PanSegImage(data, image_props)

    new_data = np.random.rand(10, 10, 10)
    new_image = ps_image.derive_new(new_data, name="new_image")

    assert new_image.name == "new_image"
    assert new_image.shape == (10, 10, 10)
    assert new_image.voxel_size == voxel_size
    assert new_image.original_voxel_size == voxel_size


def test_panseg_image_get_data():
    data = np.random.rand(10, 10, 10)
    voxel_size = VoxelSize(voxels_size=(1.0, 1.0, 1.0), unit="um")
    image_props = ImageProperties(
        name="test_image",
        semantic_type=SemanticType.RAW,
        voxel_size=voxel_size,
        image_layout=ImageLayout.ZYX,
        original_voxel_size=voxel_size,
    )
    ps_image = PanSegImage(data, image_props)

    # Test without normalization
    normalised_data = (data - np.min(data)) / (np.max(data) - np.min(data) + 1e-12)
    retrieved_data = ps_image.get_data(normalize_01=True)
    assert normalised_data.dtype == retrieved_data.dtype
    np.testing.assert_allclose(retrieved_data, normalised_data)

    # Test with normalization
    retrieved_data = ps_image.get_data(normalize_01=False)
    assert normalised_data.dtype == retrieved_data.dtype
    np.testing.assert_allclose(retrieved_data, data)


def test_panseg_image_from_napari_layer():
    data = np.random.rand(10, 10, 10)
    voxel_size = (1.0, 1.0, 1.0)
    metadata = {
        "semantic_type": "raw",
        "voxel_size": {"voxels_size": voxel_size, "unit": "um"},
        "original_voxel_size": {"voxels_size": voxel_size, "unit": "um"},
        "image_layout": "ZYX",
        "id": uuid4(),
    }
    napari_layer = Image(data, metadata=metadata, name="test_image")

    ps_image = PanSegImage.from_napari_layer(napari_layer)
    assert ps_image.name == "test_image"
    assert ps_image.shape == (10, 10, 10)
    assert ps_image.voxel_size.voxels_size == voxel_size
    assert tuple(ps_image.voxel_size) == voxel_size


def test_panseg_image_to_napari_layer_tuple():
    data = np.random.rand(2, 2, 2)
    voxel_size = VoxelSize(voxels_size=(1.0, 1.0, 1.0), unit="um")
    image_props = ImageProperties(
        name="test_image",
        semantic_type=SemanticType.RAW,
        voxel_size=voxel_size,
        image_layout=ImageLayout.ZYX,
        original_voxel_size=voxel_size,
    )
    ps_image = PanSegImage(data, image_props)
    layer_tuple = ps_image.to_napari_layer_tuple()

    assert isinstance(layer_tuple, tuple)
    layer_tuple = tuple(layer_tuple)
    np.testing.assert_allclose(layer_tuple[0], ps_image.get_data(normalize_01=False))
    assert "metadata" in layer_tuple[1]
    assert layer_tuple[2] == ps_image.image_type.value


def test_panseg_image_scale_property():
    data = np.random.rand(10, 10, 10)
    voxel_size = VoxelSize(voxels_size=(0.5, 1.0, 1.0), unit="um")
    image_props = ImageProperties(
        name="scaled_image",
        semantic_type=SemanticType.RAW,
        voxel_size=voxel_size,
        image_layout=ImageLayout.ZYX,
        original_voxel_size=voxel_size,
    )
    ps_image = PanSegImage(data, image_props)
    assert ps_image.scale == (0.5, 1.0, 1.0)


def test_scale_tzyx_known_t_spacing():
    data = np.random.rand(7, 5, 16, 16)
    voxel_size = VoxelSize(voxels_size=(0.5, 1.0, 2.0), unit="um")
    image_props = ImageProperties(
        name="timelapse",
        semantic_type=SemanticType.RAW,
        voxel_size=voxel_size,
        image_layout=ImageLayout.TZYX,
        original_voxel_size=voxel_size,
        t_spacing=0.5,
    )
    ps_image = PanSegImage(data, image_props)
    assert ps_image.scale == (0.5, 0.5, 1.0, 2.0)


def test_scale_tzyx_unknown_t_spacing():
    data = np.random.rand(7, 5, 16, 16)
    voxel_size = VoxelSize(voxels_size=(0.5, 1.0, 2.0), unit="um")
    image_props = ImageProperties(
        name="timelapse",
        semantic_type=SemanticType.RAW,
        voxel_size=voxel_size,
        image_layout=ImageLayout.TZYX,
        original_voxel_size=voxel_size,
    )
    ps_image = PanSegImage(data, image_props)
    assert ps_image.scale == (1.0, 0.5, 1.0, 2.0)


def test_scale_tcyx():
    data = np.random.rand(7, 3, 16, 16)
    voxel_size = VoxelSize(voxels_size=(1.0, 1.0, 2.0), unit="um")
    image_props = ImageProperties(
        name="timelapse",
        semantic_type=SemanticType.RAW,
        voxel_size=voxel_size,
        image_layout=ImageLayout.TCYX,
        original_voxel_size=voxel_size,
        t_spacing=2.0,
    )
    ps_image = PanSegImage(data, image_props)
    assert ps_image.scale == (2.0, 1.0, 1.0, 2.0)


def test_requires_scaling():
    data = np.random.rand(10, 10, 10)

    voxel_size = VoxelSize(voxels_size=(0.5, 1.0, 1.0), unit="um")
    same_voxel_size = VoxelSize(voxels_size=(0.5, 1.0, 1.0), unit="um")
    original_voxel_size = VoxelSize(voxels_size=(1.0, 1.0, 1.0), unit="um")
    assert same_voxel_size == voxel_size
    assert original_voxel_size != voxel_size

    image_props = ImageProperties(
        name="scaled_image",
        semantic_type=SemanticType.RAW,
        voxel_size=voxel_size,
        image_layout=ImageLayout.ZYX,
        original_voxel_size=original_voxel_size,
    )
    ps_image = PanSegImage(data, image_props)
    assert ps_image.requires_scaling is True

    image_props = ImageProperties(
        name="scaled_image",
        semantic_type=SemanticType.RAW,
        voxel_size=voxel_size,
        image_layout=ImageLayout.ZYX,
        original_voxel_size=same_voxel_size,
    )
    ps_image = PanSegImage(data, image_props)
    assert ps_image.requires_scaling is False

    assert same_voxel_size == voxel_size
    assert original_voxel_size != voxel_size


@pytest.fixture
def test_h5_dir():
    return Path(__file__).parent.parent / "resources" / "training_sources"


def test_import_image_YX(test_h5_dir):
    file = test_h5_dir / "train_2D_2D.h5"
    image = import_image(
        path=file,
        key="raw",
        stack_layout="YX",
    )
    assert isinstance(image, PanSegImage)
    assert image.semantic_type == SemanticType.RAW
    assert image.image_layout == ImageLayout.YX


def test_import_image_CYX(test_h5_dir):
    file = test_h5_dir / "train_2Dc_2D.h5"
    images = import_image(
        path=file,
        key="raw",
        stack_layout="CYX",
    )
    assert isinstance(images, list)
    assert all([isinstance(i, PanSegImage) for i in images])
    assert len(images) == 2
    assert images[0].semantic_type == SemanticType.RAW
    assert images[0].image_layout == ImageLayout.YX


def test_import_image_CYX_warning(mocker, test_h5_dir):
    mocker.patch("panseg.core.image.last_warning", new=0.0)
    mock_loader = mocker.patch("panseg.core.image.smart_load_with_vs")
    mock_loader.return_value = (
        np.random.rand(3, 2, 11),
        VoxelSize(voxels_size=(1.0, 1.0, 1.0)),
    )
    file = test_h5_dir / "train_3Dc_3D.h5"
    with pytest.raises(ValueError):
        import_image(
            path=file,
            key="raw",
            stack_layout="CYX",
        )


def test_import_image_YX_error(test_h5_dir):
    file = test_h5_dir / "train_2D_2D.h5"
    with pytest.raises(ValueError):
        import_image(
            path=file,
            key="raw",
            stack_layout="ZYX",
        )


def test_import_image_ZYX(test_h5_dir):
    file = test_h5_dir / "train_3D_3D.h5"
    image = import_image(
        path=file,
        key="raw",
        stack_layout="ZYX",
    )
    assert image.semantic_type == SemanticType.RAW
    assert image.image_layout == ImageLayout.ZYX


def test_import_image_ZYX_inv(test_h5_dir):
    file = test_h5_dir / "train_3D_3D.h5"
    image = import_image(
        path=file,
        key="raw",
        stack_layout="Z-YX",
    )
    assert image.semantic_type == SemanticType.RAW
    assert image.image_layout == ImageLayout.ZYX


def test_import_image_CZYX(test_h5_dir):
    file = test_h5_dir / "train_3Dc_3D.h5"
    images = import_image(
        path=file,
        key="raw",
        stack_layout="CZYX",
    )
    assert isinstance(images, list)
    assert all([isinstance(i, PanSegImage) for i in images])
    assert len(images) == 2
    assert images[0].semantic_type == SemanticType.RAW
    assert images[0].image_layout == ImageLayout.ZYX


def test_import_image_CZYX_warning(mocker, test_h5_dir):
    mocker.patch("panseg.core.image.last_warning", new=0.0)
    mock_loader = mocker.patch("panseg.core.image.smart_load_with_vs")
    mock_loader.return_value = (
        np.random.rand(3, 2, 10, 11),
        VoxelSize(voxels_size=(1.0, 1.0, 1.0)),
    )
    file = test_h5_dir / "train_3Dc_3D.h5"
    with pytest.raises(ValueError):
        import_image(
            path=file,
            key="raw",
            stack_layout="CZYX",
        )


def test_import_image_ZCYX(mocker, test_h5_dir):
    mocker.patch("panseg.core.image.last_warning", new=time.time())
    file = test_h5_dir / "train_3Dc_3D.h5"
    images = import_image(
        path=file,
        key="raw",
        stack_layout="ZCYX",
    )
    assert isinstance(images, list)
    assert all([isinstance(i, PanSegImage) for i in images])
    assert len(images) == 75
    assert images[0].semantic_type == SemanticType.RAW
    assert images[0].image_layout == ImageLayout.ZYX


def test_import_image_ZCYX_warning(mocker, test_h5_dir):
    mocker.patch("panseg.core.image.last_warning", new=0.0)
    file = test_h5_dir / "train_3Dc_3D.h5"
    with pytest.raises(ValueError):
        import_image(
            path=file,
            key="raw",
            stack_layout="ZCYX",
        )


def test_split_image_CZYX():
    data = np.random.rand(3, 9, 10, 11)
    voxel_size = VoxelSize(voxels_size=(0.5, 1.0, 1.0), unit="um")
    image_props = ImageProperties(
        name="image",
        semantic_type=SemanticType.RAW,
        voxel_size=voxel_size,
        image_layout=ImageLayout.CZYX,
        original_voxel_size=voxel_size,
    )
    ps_image = PanSegImage(data, image_props)
    splits = ps_image.split_channels()

    assert len(splits) == 3
    assert all([s.image_layout == ImageLayout.ZYX for s in splits])
    assert all([s.semantic_type == SemanticType.RAW for s in splits])
    assert all([s.voxel_size == voxel_size for s in splits])
    assert all([s.shape == (9, 10, 11) for s in splits])


def test_split_image_ZCYX():
    data = np.random.rand(9, 4, 10, 11)
    voxel_size = VoxelSize(voxels_size=(0.5, 1.0, 1.0), unit="um")
    image_props = ImageProperties(
        name="image",
        semantic_type=SemanticType.RAW,
        voxel_size=voxel_size,
        image_layout=ImageLayout.ZCYX,
        original_voxel_size=voxel_size,
    )
    ps_image = PanSegImage(data, image_props)
    splits = ps_image.split_channels()

    assert len(splits) == 4
    assert all([s.image_layout == ImageLayout.ZYX for s in splits])
    assert all([s.semantic_type == SemanticType.RAW for s in splits])
    assert all([s.voxel_size == voxel_size for s in splits])
    assert all([s.shape == (9, 10, 11) for s in splits])


def test_split_image_CYX():
    data = np.random.rand(4, 10, 11)
    voxel_size = VoxelSize(voxels_size=(1.0, 1.0, 1.0), unit="um")
    image_props = ImageProperties(
        name="image",
        semantic_type=SemanticType.RAW,
        voxel_size=voxel_size,
        image_layout=ImageLayout.CYX,
        original_voxel_size=voxel_size,
    )
    ps_image = PanSegImage(data, image_props)
    splits = ps_image.split_channels()

    assert len(splits) == 4
    assert all([s.image_layout == ImageLayout.YX for s in splits])
    assert all([s.semantic_type == SemanticType.RAW for s in splits])
    assert all([s.voxel_size == voxel_size for s in splits])
    assert all([s.shape == (10, 11) for s in splits])


def test_split_image_TCZYX():
    data = np.random.rand(7, 3, 5, 16, 16)
    voxel_size = VoxelSize(voxels_size=(0.5, 1.0, 1.0), unit="um")
    image_props = ImageProperties(
        name="image",
        semantic_type=SemanticType.RAW,
        voxel_size=voxel_size,
        image_layout=ImageLayout.TCZYX,
        original_voxel_size=voxel_size,
        t_spacing=0.5,
    )
    ps_image = PanSegImage(data, image_props)
    splits = ps_image.split_channels()

    assert len(splits) == 3
    assert [s.name for s in splits] == ["image_0", "image_1", "image_2"]
    assert all([s.image_layout == ImageLayout.TZYX for s in splits])
    assert all([s.is_timelapse for s in splits])
    assert all([s.shape == (7, 5, 16, 16) for s in splits])
    assert all([s.properties.t_spacing == 0.5 for s in splits])


def test_split_image_TCYX():
    data = np.random.rand(7, 4, 16, 16)
    voxel_size = VoxelSize(voxels_size=(1.0, 1.0, 1.0), unit="um")
    image_props = ImageProperties(
        name="image",
        semantic_type=SemanticType.RAW,
        voxel_size=voxel_size,
        image_layout=ImageLayout.TCYX,
        original_voxel_size=voxel_size,
        t_spacing=0.5,
    )
    ps_image = PanSegImage(data, image_props)
    splits = ps_image.split_channels()

    assert len(splits) == 4
    assert [s.name for s in splits] == ["image_0", "image_1", "image_2", "image_3"]
    assert all([s.image_layout == ImageLayout.TYX for s in splits])
    assert all([s.is_timelapse for s in splits])
    assert all([s.shape == (7, 16, 16) for s in splits])
    assert all([s.properties.t_spacing == 0.5 for s in splits])


def test_split_image_TZYX_not_split():
    data = np.random.rand(7, 5, 16, 16)
    voxel_size = VoxelSize(voxels_size=(1.0, 1.0, 1.0), unit="um")
    image_props = ImageProperties(
        name="image",
        semantic_type=SemanticType.RAW,
        voxel_size=voxel_size,
        image_layout=ImageLayout.TZYX,
        original_voxel_size=voxel_size,
    )
    ps_image = PanSegImage(data, image_props)
    assert ps_image.split_channels() == [ps_image]

    data = np.random.rand(7, 16, 16)
    image_props = ImageProperties(
        name="image",
        semantic_type=SemanticType.RAW,
        voxel_size=voxel_size,
        image_layout=ImageLayout.TYX,
        original_voxel_size=voxel_size,
    )
    ps_image = PanSegImage(data, image_props)
    assert ps_image.split_channels() == [ps_image]


def test_merge_images_2d():
    data = np.random.rand(10, 11)
    voxel_size = VoxelSize(voxels_size=(1.0, 1.0, 1.0), unit="um")
    image_props = ImageProperties(
        name="image",
        semantic_type=SemanticType.RAW,
        voxel_size=voxel_size,
        image_layout=ImageLayout.YX,
        original_voxel_size=voxel_size,
    )
    ps_image_1 = PanSegImage(data, image_props)
    ps_image_2 = PanSegImage(data, image_props)

    merged = ps_image_1.merge_with(ps_image_2)
    assert merged.dimensionality == ImageDimensionality.TWO
    assert merged.is_multichannel
    assert merged.shape == (2, 10, 11)


def test_merge_images_3d():
    data = np.random.rand(9, 10, 11)
    voxel_size = VoxelSize(voxels_size=(1.0, 1.0, 1.0), unit="um")
    image_props = ImageProperties(
        name="image",
        semantic_type=SemanticType.RAW,
        voxel_size=voxel_size,
        image_layout=ImageLayout.ZYX,
        original_voxel_size=voxel_size,
    )
    ps_image_1 = PanSegImage(data, image_props)
    ps_image_2 = PanSegImage(data, image_props)

    merged = ps_image_1.merge_with(ps_image_2)
    assert merged.dimensionality == ImageDimensionality.THREE
    assert merged.is_multichannel
    assert merged.shape == (2, 9, 10, 11)


def test_merge_images_3dc():
    data = np.random.rand(2, 9, 10, 11)
    voxel_size = VoxelSize(voxels_size=(1.0, 1.0, 1.0), unit="um")
    image_props = ImageProperties(
        name="image",
        semantic_type=SemanticType.RAW,
        voxel_size=voxel_size,
        image_layout=ImageLayout.CZYX,
        original_voxel_size=voxel_size,
    )
    ps_image_1 = PanSegImage(data, image_props)
    data = np.random.rand(2, 9, 10, 11)
    voxel_size = VoxelSize(voxels_size=(1.0, 1.0, 1.0), unit="um")
    image_props = ImageProperties(
        name="image",
        semantic_type=SemanticType.RAW,
        voxel_size=voxel_size,
        image_layout=ImageLayout.CZYX,
        original_voxel_size=voxel_size,
    )
    ps_image_2 = PanSegImage(data, image_props)

    merged = ps_image_1.merge_with(ps_image_2)
    assert merged.dimensionality == ImageDimensionality.THREE
    assert merged.is_multichannel
    assert merged.shape == (4, 9, 10, 11)

    data = np.random.rand(9, 10, 11)
    voxel_size = VoxelSize(voxels_size=(1.0, 1.0, 1.0), unit="um")
    image_props = ImageProperties(
        name="image",
        semantic_type=SemanticType.RAW,
        voxel_size=voxel_size,
        image_layout=ImageLayout.ZYX,
        original_voxel_size=voxel_size,
    )
    ps_image_3 = PanSegImage(data, image_props)
    merged = merged.merge_with(ps_image_3)
    assert merged.dimensionality == ImageDimensionality.THREE
    assert merged.is_multichannel
    assert merged.shape == (5, 9, 10, 11)


def test_merge_timelapse_matching_t_spacing():
    data = np.random.rand(7, 5, 16, 16)
    voxel_size = VoxelSize(voxels_size=(1.0, 1.0, 1.0), unit="um")
    image_props = ImageProperties(
        name="image",
        semantic_type=SemanticType.RAW,
        voxel_size=voxel_size,
        image_layout=ImageLayout.TZYX,
        original_voxel_size=voxel_size,
        t_spacing=10.0,
    )
    ps_image_1 = PanSegImage(data, image_props)
    ps_image_2 = PanSegImage(data, image_props)

    merged = ps_image_1.merge_with(ps_image_2)
    assert merged.image_layout == ImageLayout.TCZYX
    assert merged.is_timelapse
    # The channel axis sits at index 1, after T.
    assert merged.shape == (7, 2, 5, 16, 16)
    assert merged.properties.t_spacing == 10.0
    splits = merged.split_channels()
    assert len(splits) == 2
    assert all([s.image_layout == ImageLayout.TZYX for s in splits])
    assert all([s.shape == (7, 5, 16, 16) for s in splits])


def test_merge_timelapse_2d():
    data = np.random.rand(7, 16, 16)
    voxel_size = VoxelSize(voxels_size=(1.0, 1.0, 1.0), unit="um")
    image_props = ImageProperties(
        name="image",
        semantic_type=SemanticType.RAW,
        voxel_size=voxel_size,
        image_layout=ImageLayout.TYX,
        original_voxel_size=voxel_size,
        t_spacing=5.0,
    )
    ps_image_1 = PanSegImage(data, image_props)
    ps_image_2 = PanSegImage(data, image_props)

    merged = ps_image_1.merge_with(ps_image_2)
    assert merged.image_layout == ImageLayout.TCYX
    assert merged.is_timelapse
    assert merged.shape == (7, 2, 16, 16)
    assert merged.properties.t_spacing == 5.0


def test_merge_timelapse_mismatched_t_spacing():
    data = np.random.rand(7, 5, 16, 16)
    voxel_size = VoxelSize(voxels_size=(1.0, 1.0, 1.0), unit="um")
    image_props_1 = ImageProperties(
        name="image",
        semantic_type=SemanticType.RAW,
        voxel_size=voxel_size,
        image_layout=ImageLayout.TZYX,
        original_voxel_size=voxel_size,
        t_spacing=10.0,
    )
    image_props_2 = ImageProperties(
        name="image",
        semantic_type=SemanticType.RAW,
        voxel_size=voxel_size,
        image_layout=ImageLayout.TZYX,
        original_voxel_size=voxel_size,
        t_spacing=20.0,
    )
    ps_image_1 = PanSegImage(data, image_props_1)
    ps_image_2 = PanSegImage(data, image_props_2)

    with pytest.raises(ValueError):
        ps_image_1.merge_with(ps_image_2)


def test_merge_timelapse_set_vs_unknown_t_spacing():
    data = np.random.rand(7, 5, 16, 16)
    voxel_size = VoxelSize(voxels_size=(1.0, 1.0, 1.0), unit="um")
    image_props_known = ImageProperties(
        name="image",
        semantic_type=SemanticType.RAW,
        voxel_size=voxel_size,
        image_layout=ImageLayout.TZYX,
        original_voxel_size=voxel_size,
        t_spacing=10.0,
    )
    image_props_unknown = ImageProperties(
        name="image",
        semantic_type=SemanticType.RAW,
        voxel_size=voxel_size,
        image_layout=ImageLayout.TZYX,
        original_voxel_size=voxel_size,
    )
    ps_image_1 = PanSegImage(data, image_props_known)
    ps_image_2 = PanSegImage(data, image_props_unknown)

    with pytest.raises(ValueError):
        ps_image_1.merge_with(ps_image_2)


def test_merge_timelapse_both_unknown_t_spacing():
    data = np.random.rand(7, 5, 16, 16)
    voxel_size = VoxelSize(voxels_size=(1.0, 1.0, 1.0), unit="um")
    image_props = ImageProperties(
        name="image",
        semantic_type=SemanticType.RAW,
        voxel_size=voxel_size,
        image_layout=ImageLayout.TZYX,
        original_voxel_size=voxel_size,
    )
    ps_image_1 = PanSegImage(data, image_props)
    ps_image_2 = PanSegImage(data, image_props)

    merged = ps_image_1.merge_with(ps_image_2)
    assert merged.image_layout == ImageLayout.TCZYX
    assert merged.shape == (7, 2, 5, 16, 16)
    assert merged.properties.t_spacing is None


def test_merge_timelapse_vs_still():
    data_3d = np.random.rand(7, 5, 16, 16)
    data_still = np.random.rand(5, 16, 16)
    voxel_size = VoxelSize(voxels_size=(1.0, 1.0, 1.0), unit="um")
    timelapse_props = ImageProperties(
        name="image",
        semantic_type=SemanticType.RAW,
        voxel_size=voxel_size,
        image_layout=ImageLayout.TZYX,
        original_voxel_size=voxel_size,
    )
    still_props = ImageProperties(
        name="image",
        semantic_type=SemanticType.RAW,
        voxel_size=voxel_size,
        image_layout=ImageLayout.ZYX,
        original_voxel_size=voxel_size,
    )
    ps_timelapse = PanSegImage(data_3d, timelapse_props)
    ps_still = PanSegImage(data_still, still_props)

    with pytest.raises(ValueError):
        ps_timelapse.merge_with(ps_still)


def test_merge_images_wrong_semantic():
    data = np.random.rand(9, 10, 11)
    voxel_size = VoxelSize(voxels_size=(1.0, 1.0, 1.0), unit="um")
    image_props = ImageProperties(
        name="image",
        semantic_type=SemanticType.RAW,
        voxel_size=voxel_size,
        image_layout=ImageLayout.ZYX,
        original_voxel_size=voxel_size,
    )
    ps_image_1 = PanSegImage(data, image_props)
    image_props = ImageProperties(
        name="image",
        semantic_type=SemanticType.PREDICTION,
        voxel_size=voxel_size,
        image_layout=ImageLayout.ZYX,
        original_voxel_size=voxel_size,
    )
    ps_image_2 = PanSegImage(data, image_props)

    with pytest.raises(ValueError):
        ps_image_1.merge_with(ps_image_2)


def test_merge_images_2d_3d():
    data = np.random.rand(9, 10, 11)
    voxel_size = VoxelSize(voxels_size=(1.0, 1.0, 1.0), unit="um")
    image_props = ImageProperties(
        name="image",
        semantic_type=SemanticType.RAW,
        voxel_size=voxel_size,
        image_layout=ImageLayout.ZYX,
        original_voxel_size=voxel_size,
    )
    ps_image_1 = PanSegImage(data, image_props)
    data = np.random.rand(10, 11)
    voxel_size = VoxelSize(voxels_size=(1.0, 1.0, 1.0), unit="um")
    image_props = ImageProperties(
        name="image",
        semantic_type=SemanticType.RAW,
        voxel_size=voxel_size,
        image_layout=ImageLayout.YX,
        original_voxel_size=voxel_size,
    )
    ps_image_2 = PanSegImage(data, image_props)

    with pytest.raises(ValueError):
        ps_image_1.merge_with(ps_image_2)


def test_image_properties_json_roundtrip():
    voxel_size = VoxelSize(voxels_size=(1.0, 1.0, 1.0), unit="um")
    props = ImageProperties(
        name="image",
        semantic_type=SemanticType.RAW,
        voxel_size=voxel_size,
        image_layout=ImageLayout.TCZYX,
        original_voxel_size=voxel_size,
        t_spacing=0.5,
    )
    json_str = props.model_dump_json()
    loaded = ImageProperties.model_validate_json(json_str)
    assert loaded.image_layout == ImageLayout.TCZYX
    assert loaded.t_spacing == 0.5
    assert loaded.t_unit == "s"


def test_image_properties_json_old_format():
    old_json = (
        '{"name": "image", "semantic_type": "raw",'
        ' "voxel_size": {"voxels_size": [1.0, 1.0, 1.0], "unit": "um"},'
        ' "image_layout": "ZYX",'
        ' "original_voxel_size": {"voxels_size": [1.0, 1.0, 1.0], "unit": "um"},'
        ' "source_file_name": null}'
    )
    loaded = ImageProperties.model_validate_json(old_json)
    assert loaded.image_layout == ImageLayout.ZYX
    assert loaded.t_spacing is None
    assert loaded.t_unit == "s"


def test_napari_layer_roundtrip_timelapse():
    data = np.random.rand(7, 3, 5, 16, 16)
    voxel_size = VoxelSize(voxels_size=(0.5, 1.0, 2.0), unit="um")
    image_props = ImageProperties(
        name="timelapse",
        semantic_type=SemanticType.RAW,
        voxel_size=voxel_size,
        image_layout=ImageLayout.TCZYX,
        original_voxel_size=voxel_size,
        t_spacing=2.0,
    )
    ps_image = PanSegImage(data, image_props)

    layer_tuple = ps_image.to_napari_layer_tuple()
    layer = Image(layer_tuple[0], **layer_tuple[1])
    loaded = PanSegImage.from_napari_layer(layer)

    assert loaded.image_layout == ImageLayout.TCZYX
    assert loaded.properties.t_spacing == 2.0
    assert loaded.scale == (2.0, 1.0, 0.5, 1.0, 2.0)


def test_stack_sort_noop():
    stack_layout = "CZYX"
    data = np.arange(120).reshape((2, 3, 4, 5))
    voxel_size = VoxelSize(voxels_size=(3, 4, 5))

    n_stack_layout, n_data, n_voxel_size = stack_sort(stack_layout, data, voxel_size)
    assert n_stack_layout == "CZYX"
    assert n_data.shape == (2, 3, 4, 5)
    assert n_voxel_size.voxels_size == (3, 4, 5)
    assert np.all(n_data == data)


def test_stack_sort_3dc():
    stack_layout = "ZCXY"
    data = np.empty((2, 3, 4, 5))
    voxel_size = VoxelSize(voxels_size=(3, 4, 5))

    n_stack_layout, n_data, n_voxel_size = stack_sort(stack_layout, data, voxel_size)
    assert n_stack_layout == "CZYX"
    assert n_data.shape == (3, 2, 5, 4)
    assert n_voxel_size.voxels_size == (3, 5, 4)


def test_stack_sort_3d():
    stack_layout = "ZXY"
    data = np.empty((3, 4, 5))
    voxel_size = VoxelSize(voxels_size=(3, 4, 5))

    n_stack_layout, n_data, n_voxel_size = stack_sort(stack_layout, data, voxel_size)
    assert n_stack_layout == "ZYX"
    assert n_data.shape == (3, 5, 4)
    assert n_voxel_size.voxels_size == (3, 5, 4)


def test_stack_sort_2dc():
    stack_layout = "XYC"
    data = np.empty((3, 4, 5))
    voxel_size = VoxelSize(voxels_size=(3, 4, 5))

    n_stack_layout, n_data, n_voxel_size = stack_sort(stack_layout, data, voxel_size)
    assert n_stack_layout == "CYX"
    assert n_data.shape == (5, 4, 3)
    assert n_voxel_size.voxels_size == (3, 5, 4)


def test_stack_sort_2dc2():
    stack_layout = "YCX"
    data = np.empty((3, 4, 5))
    voxel_size = VoxelSize(voxels_size=(3, 4, 5))

    n_stack_layout, n_data, n_voxel_size = stack_sort(stack_layout, data, voxel_size)
    assert n_stack_layout == "CYX"
    assert n_data.shape == (4, 3, 5)
    assert n_voxel_size.voxels_size == (3, 4, 5)


def test_stack_sort_2d():
    stack_layout = "YX"
    data = np.empty((3, 4))
    voxel_size = VoxelSize(voxels_size=(3, 4, 5))

    n_stack_layout, n_data, n_voxel_size = stack_sort(stack_layout, data, voxel_size)
    assert n_stack_layout == "YX"
    assert n_data.shape == (3, 4)
    assert n_voxel_size.voxels_size == (3, 4, 5)


def test_stack_sort_3dc_invZ():
    stack_layout = "CYX-Z"
    data = np.arange(120).reshape((2, 3, 4, 5))
    voxel_size = VoxelSize(voxels_size=(3, 4, 5))

    n_stack_layout, n_data, n_voxel_size = stack_sort(stack_layout, data, voxel_size)
    assert n_stack_layout == "CZYX"
    assert n_data.shape == (2, 5, 3, 4)
    assert n_voxel_size.voxels_size == (5, 3, 4)
    assert np.all(n_data[:, ::-1, :, :] == np.transpose(data, axes=[0, 3, 1, 2]))


def test_stack_sort_3dc_invC():
    stack_layout = "-CZYX"
    data = np.arange(120).reshape((2, 3, 4, 5))
    voxel_size = VoxelSize(voxels_size=(3, 4, 5))

    n_stack_layout, n_data, n_voxel_size = stack_sort(stack_layout, data, voxel_size)
    assert n_stack_layout == "CZYX"
    assert n_data.shape == (2, 3, 4, 5)
    assert n_voxel_size.voxels_size == (3, 4, 5)
    assert np.all(n_data[::-1, :, :, :] == data)


def test_stack_sort_3dc_invCX():
    stack_layout = "-CZX-Y"
    data = np.arange(120).reshape((2, 3, 4, 5))
    voxel_size = VoxelSize(voxels_size=(3, 4, 5))

    n_stack_layout, n_data, n_voxel_size = stack_sort(stack_layout, data, voxel_size)
    assert n_stack_layout == "CZYX"
    assert n_data.shape == (2, 3, 5, 4)
    assert n_voxel_size.voxels_size == (3, 5, 4)
    assert np.all(n_data[::-1, :, ::-1, :] == np.transpose(data, axes=[0, 1, 3, 2]))


def test_stack_sort_4d_noop():
    stack_layout = "TZYX"
    data = np.arange(120).reshape((2, 3, 4, 5))
    voxel_size = VoxelSize(voxels_size=(3, 4, 5))

    n_stack_layout, n_data, n_voxel_size = stack_sort(stack_layout, data, voxel_size)
    assert n_stack_layout == "TZYX"
    assert n_data.shape == (2, 3, 4, 5)
    assert n_voxel_size.voxels_size == (3, 4, 5)
    assert np.all(n_data == data)


def test_stack_sort_5dc_noop():
    stack_layout = "TCZYX"
    data = np.arange(720).reshape((2, 3, 4, 5, 6))
    voxel_size = VoxelSize(voxels_size=(4, 5, 6))

    n_stack_layout, n_data, n_voxel_size = stack_sort(stack_layout, data, voxel_size)
    assert n_stack_layout == "TCZYX"
    assert n_data.shape == (2, 3, 4, 5, 6)
    assert n_voxel_size.voxels_size == (4, 5, 6)
    assert np.all(n_data == data)


def test_stack_sort_4dc_reorder():
    stack_layout = "ZTCYX"
    data = np.arange(720).reshape((3, 2, 4, 5, 6))
    voxel_size = VoxelSize(voxels_size=(3, 5, 6))

    n_stack_layout, n_data, n_voxel_size = stack_sort(stack_layout, data, voxel_size)
    assert n_stack_layout == "TCZYX"
    assert n_data.shape == (2, 4, 3, 5, 6)
    assert n_voxel_size.voxels_size == (3, 5, 6)
    assert np.all(n_data == np.transpose(data, axes=[1, 2, 0, 3, 4]))


def test_stack_sort_4d_invT():
    stack_layout = "-TZYX"
    data = np.arange(120).reshape((2, 3, 4, 5))
    voxel_size = VoxelSize(voxels_size=(3, 4, 5))

    n_stack_layout, n_data, n_voxel_size = stack_sort(stack_layout, data, voxel_size)
    assert n_stack_layout == "TZYX"
    assert n_data.shape == (2, 3, 4, 5)
    assert n_voxel_size.voxels_size == (3, 4, 5)
    assert np.all(n_data[::-1, :, :, :] == data)


def test_stack_sort_2dc_invX():
    stack_layout = "CY-X"
    data = np.arange(24).reshape((2, 3, 4))
    voxel_size = VoxelSize(voxels_size=(3, 4, 5))

    n_stack_layout, n_data, n_voxel_size = stack_sort(stack_layout, data, voxel_size)
    assert n_stack_layout == "CYX"
    assert n_data.shape == (2, 3, 4)
    assert n_voxel_size.voxels_size == (3, 4, 5)
    assert np.all(n_data[:, :, ::-1] == data)


# Shared timelapse fixtures: one raw float32 array per T layout on the
# documented shape skeleton, plus a uint16 segmentation whose label IDs are
# independent across timepoints by construction.
TIMELAPSE_RAW_FIXTURES = [
    pytest.param("timelapse_tyx", ImageLayout.TYX, (4, 16, 16), id="TYX"),
    pytest.param("timelapse_tcyx", ImageLayout.TCYX, (4, 2, 16, 16), id="TCYX"),
    pytest.param("timelapse_tzyx", ImageLayout.TZYX, (4, 5, 16, 16), id="TZYX"),
    pytest.param("timelapse_tczyx", ImageLayout.TCZYX, (4, 2, 5, 16, 16), id="TCZYX"),
]


@pytest.mark.parametrize("fixture_name, layout, shape", TIMELAPSE_RAW_FIXTURES)
def test_timelapse_raw_fixture(request, fixture_name, layout, shape):
    data = request.getfixturevalue(fixture_name)
    assert data.shape == shape
    assert data.dtype == np.float32
    voxel_size = VoxelSize(voxels_size=(1.0, 1.0, 1.0), unit="um")
    for t_props, expected_t_spacing in (
        (TIMELAPSE_PROPS_KNOWN_T_SPACING, 10.0),
        (TIMELAPSE_PROPS_UNKNOWN_T_SPACING, None),
    ):
        props = ImageProperties(
            name=fixture_name,
            semantic_type=SemanticType.RAW,
            voxel_size=voxel_size,
            image_layout=layout,
            original_voxel_size=voxel_size,
            **t_props,
        )
        image = PanSegImage(data, props)
        assert image.image_layout == layout
        assert image.is_timelapse
        assert image.shape == shape
        assert image.properties.t_spacing == expected_t_spacing


def test_timelapse_segmentation_fixture(timelapse_segmentation):
    seg = timelapse_segmentation
    assert seg.shape == (4, 5, 16, 16)
    assert seg.dtype == np.uint16
    # Label IDs are independent across timepoints: no ID shared by two t.
    label_sets = [set(np.unique(seg[t]).tolist()) - {0} for t in range(seg.shape[0])]
    assert all(label_sets)
    for i in range(len(label_sets)):
        for j in range(i + 1, len(label_sets)):
            assert not label_sets[i] & label_sets[j]
    voxel_size = VoxelSize(voxels_size=(1.0, 1.0, 1.0), unit="um")
    for t_props, expected_t_spacing in (
        (TIMELAPSE_PROPS_KNOWN_T_SPACING, 10.0),
        (TIMELAPSE_PROPS_UNKNOWN_T_SPACING, None),
    ):
        props = ImageProperties(
            name="timelapse_segmentation",
            semantic_type=SemanticType.SEGMENTATION,
            voxel_size=voxel_size,
            image_layout=ImageLayout.TZYX,
            original_voxel_size=voxel_size,
            **t_props,
        )
        image = PanSegImage(seg, props)
        assert image.image_layout == ImageLayout.TZYX
        assert image.image_type == ImageType.LABEL
        assert image.properties.t_spacing == expected_t_spacing
