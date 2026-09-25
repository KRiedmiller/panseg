import sys
from typing import Any

sys.path.append("docs/snippets")

import numpy as np
from magicgui.widgets import Container
from napari.layers import Image
from napari_widgets_render import render_widget

from panseg.core.image import ImageLayout, ImageProperties, PanSegImage, SemanticType
from panseg.io.voxelsize import VoxelSize
from panseg.viewer_napari.widgets.input import Input_Tab
from panseg.viewer_napari.widgets.utils import div

data = np.random.rand(4, 5, 16, 16).astype("float32")
voxel_size = VoxelSize(voxels_size=(1.0, 0.5, 0.5), unit="um")
properties = ImageProperties(
    name="timelapse",
    semantic_type=SemanticType.RAW,
    voxel_size=voxel_size,
    image_layout=ImageLayout.TZYX,
    original_voxel_size=voxel_size,
)
image = PanSegImage(data=data, properties=properties)
layer_data = image.to_napari_layer_tuple()
layer = Image(layer_data[0], **layer_data[1])

tab = Input_Tab()
layer_select: Any = tab.widget_details_layer_select
layer_select.layer.choices = [layer]
layer_select.layer.value = layer

widget = Container(
    widgets=[
        tab.widget_details_layer_select,
        tab.widget_info,
        div("Set time spacing"),
        tab.widget_set_t_spacing,
    ],
    labels=False,
)
widget._param_options = {}

html = render_widget(widget, skip_name=True, skip_doc=True)
print(html)
