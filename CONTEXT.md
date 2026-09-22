# PanSeg

PanSeg segments microscopy images: import, preprocess, predict, segment, proofread, and export. This glossary is the shared vocabulary for that domain; it holds terms only, no implementation detail.

## Language

**Dimensionality**:
The number of spatial dimensions of an image: 2D or 3D. It never counts channel or time axes.
_Avoid_: "4D", "5D" (ambiguous — both CZYX and TZYX are four-axis arrays), "ndim" for this concept

**Layout**:
The exact set and order of axes of an internal array, a projection of the canonical order T-C-Z-Y-X (e.g. YX, CZYX, TZYX). The unambiguous name for an image's shape.
_Avoid_: "4D image", "5D image", bare "shape" when the axis identity is meant

**Timelapse**:
An image with a time axis: layout TYX, TCYX, TZYX, or TCZYX.
_Avoid_: "frame series", "video", "4D"

**Timepoint**:
One T index of a timelapse — the image at one moment.
_Avoid_: "frame"

**Time spacing**:
The interval between consecutive timepoints, with a unit (seconds). It may be unknown when the source file carries no timing metadata.
_Avoid_: "timestep" without a unit, "fps"
