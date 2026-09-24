# 14: Time-aware export (TIFF, h5/zarr, mesh)

**What to build:** A time-bearing image a user has imported (or a segmentation produced
from one) can be exported and re-imported with the time dimension and time spacing
preserved, and a 3D timelapse segmentation exports one mesh per timepoint
(spec: "Export").

TIFF: a time-bearing image is always written as OME-TIFF; the ImageJ branch stays
time-less. The TIFF writer gains the T layouts (TYX, TCYX, TZYX, TCZYX), mapped into the
existing TZCYXS slot — T fills the currently-singleton T slot, C/Z swap applied as today.
`TimeIncrement`/`TimeIncrementUnit` are written when t_spacing is known; unknown ⇒
`SizeT` with no time metadata. BigTIFF behavior unchanged (>4 GiB or forced).
Time-bearing images export only to tiff/h5/zarr, not PIL/jpg (the format options already
exclude those).

h5/zarr: roundtrip via the import attrs — `axis_order` written on every export (additive,
old readers ignore it); `t_spacing` + `t_spacing_unit` attrs written when T is present and
known, absent when unknown; re-import yields the same layout and unknown-again when
unknown. `element_size_um` stays the spatial 3-float.

Mesh: a 3D time-bearing segmentation exports by looping over timepoints and calling the
existing mesh writer once per 3D frame slice — one file per timepoint, named
`{name_pattern}_t{index:03d}.{ext}` (0-based index, e.g. `seg_t000.glb`), necessary for
headless workflow compatibility. Empty timepoints still get their file (an empty scene),
preserving the 1:1 timepoint↔file mapping. The 3D gate is untouched: TYX segmentations
still get "Mesh export only supported for 3D".

**Blocked by:**
- 13: OME-TIFF import with time

**Status:** ready-for-agent

- [ ] T layouts (TYX/TCYX/TZYX/TCZYX) export to OME-TIFF with correct `SizeT`; `TimeIncrement`/unit written iff t_spacing known; unknown exports `SizeT` with no time metadata
- [ ] Re-import roundtrip preserves layout + t_spacing (known stays known in seconds; unknown stays unknown)
- [ ] h5 and zarr export write `axis_order` on every export and `t_spacing`/`t_spacing_unit` iff known; re-import preserves layout + t_spacing
- [ ] BigTIFF behavior unchanged; time-bearing images do not export to PIL/jpg
- [ ] 3D timelapse segmentation mesh export writes one file per timepoint named `{name_pattern}_t{index:03d}.{ext}` (0-based), including empty timepoints (empty scene)
- [ ] TYX segmentation mesh export still returns the "Mesh export only supported for 3D" message
