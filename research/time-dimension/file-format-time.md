# How file formats and readers handle the time dimension

Research ticket: `.scratch/time-dimension/issues/01-research-file-format-time.md`
Date: 2026-09-17 · Repo: panseg-fork @ `fb40ee19` (main)

Method: primary sources (OME-XML 2016-06 XSD, NGFF spec texts for 0.3/0.4.1/0.6, tifffile 2026.3.3 source, napari API docs, bioimageio.core 0.10.2) plus hands-on inspection of the 8 example OME-TIFFs in `/tmp/opencode/ome_tiff_examples` and of PanSeg's own import code/behavior using `/home/kriedmiller/software/miniforge3/envs/panseg-fork/bin/python`.

> Note: `openmicroscopy.org` (and therefore the OME-TIFF spec page and OME-HDF5 spec) was unreachable from this environment (DNS). OME-TIFF facts below were verified against the OME-XML 2016-06 schema (the model OME-TIFF embeds), the tifffile source, and the local example files; the canonical OME-TIFF spec URL is cited where relevant.

## 1. Key facts (TL;DR)

| Format | Axis order readers return | Time-spacing metadata | Time present in PanSeg examples? |
|---|---|---|---|
| OME-TIFF (via tifffile) | `TCZYX` with singleton axes dropped (e.g. `TYX`, `TZYX`, `TCYX`) | Optional only: `Pixels.TimeIncrement[+Unit]` (global) or per-plane `Plane.DeltaT[+Unit]`; **no `PhysicalSize` element for time exists in the OME-XML schema** | Data yes (SizeT); spacing metadata **no** (0/8 files) |
| OME-NGFF / OME-Zarr | Array is stored & read in file order; spec **requires** time before channel before space (space SHOULD be `zyx`) → de facto `TCZYX` | Required-in-practice: per-dataset `coordinateTransformations` `scale` vector (first entry = time step) + axis object `{"type": "time", "unit": "second|millisecond|..."}` (UDUNITS-2) | n/a locally |
| PanSeg h5 (own format) | File order, no axis metadata stored at all | Only `element_size_um` (3-float: z,y,x) + `panseg_image_metadata_json` | n/a |
| PanSeg zarr (own format) | File order, no axis metadata stored at all | Only `element_size_um` (3-float) or `resolution` attrs | n/a |

**Bottom line:** both major ecosystems normalize 5D microscopy to **TCZYX** (tifffile's OME output *is* TCZYX-minus-singletons; the NGFF spec *mandates* time→channel→space order and its own 5D example is literally TCZYX). PanSeg today cannot import any T-bearing file: layout enum has no `T`, `VoxelSize` is a hard 3-tuple, the OME-XML voxel-size reader ignores all time metadata, and the shape-guessing prefill either mislabels T as C or crashes.

## 2. OME-TIFF / OME-XML

### 2.1 Model (OME-XML, last released schema 2016-06)

Source: `ome/schemas` `OME/2016-06/ome.xsd` (also `ome/ome-model` `specification/src/main/resources/released-schema/2016-06/ome.xsd`); canonical OME-TIFF spec: https://ome-tiff.openmicroscopy.org/ (unreachable here).

`Pixels` attributes relevant to time (XSD, lines ~350–477):
- `SizeT` — **required** positive int.
- `DimensionOrder` — **required**; enum: `XYZCT, XYZTC, XYCTZ, XYCZT, XYTCZ, XYTZC`. XSD: "The order in which the individual planes of data are interleaved." Semantics (verified empirically + in tifffile source): **leftmost char changes fastest** (X within a plane), **rightmost slowest**; the plane enumeration order is the string reversed minus XY.
- `Type`, `BigEndian` — as in the ticket.
- `PhysicalSizeX/Y/Z` + `PhysicalSizeX/Y/ZUnit` — optional; **attributes**, default unit µm. **There is no `PhysicalSize` *element* and no time-sized physical-size in the schema** (0 occurrences of `PhysicalSizeT`/`PhysicalSize` element in the XSD). The ticket's premise "PhysicalSize T=… Unit=…" does not exist in OME-XML.
- **`TimeIncrement` / `TimeIncrementUnit`** (optional, default unit `s`) — "used for time series that have a global timing specification instead of per-timepoint timing info. For example in a video stream." This is the schema's global time-spacing field.
- **`Plane`** child element (optional, unbounded) — per-plane timing: `TheT` (required index), **`DeltaT` / `DeltaTUnit`** (optional, default `s`; "Time since the beginning of the experiment"), `ExposureTime[+Unit]`, stage `PositionX/Y/Z[+Unit]`. This is the schema's per-timepoint timing field.

`TiffData` (XSD, lines ~792–880): attributes `IFD` (0-based, default 0), `FirstZ`, `FirstT`, `FirstC` (0-based plane indices), `PlaneCount` — "Dimension order of IFDs is given by the enclosing Pixels element's DimensionOrder attribute." Child `UUID` (optional, with optional `FileName`) — "must be used when the IFDs are located in another file… permissible for this to be self referential."

### 2.2 Plane ordering convention (empirical)

All 8 example files: `DimensionOrder="XYZCT"`. Their `TiffData` order (verified from `FirstT/FirstC/FirstZ`) is **Z fastest, then C, then T slowest** — i.e. `TiffData` enumeration = DimensionOrder reversed minus XY, exactly as tifffile computes (`idx = ravel_multi_index([FirstT, FirstC, FirstZ], (T, C, Z))`, tifffile.py:6066–6071). Example, `multi-channel-4D-series.ome.tif` (T=7, C=3, Z=5, 105 IFDs): `(T,C,Z)` sequence = (0,0,0),(0,0,1)…(0,0,4),(0,1,0)…(6,2,4). IFDs are contiguous 0..N-1, `PlaneCount=1`, one IFD per plane, non-tiled.

### 2.3 Multi-file series, BigTIFF, multipage/tiled

- Multi-file: expressed via `TiffData/UUID` + `FileName` chaining across files. All 8 examples are **single-file**: each has exactly one distinct `(UUID, FileName)` pair and `FileName` equals the file's own name (self-referential UUID, which the schema permits). **Clean rejection test for our import spec:** collect distinct `(UUID text, FileName)` over all `TiffData` of the `Image` in use; reject (with a clear "multi-file OME-TIFF is not supported" error) if there is more than one pair, or any `FileName` not matching the opened file. (tifffile itself reads multi-file when `multifile` mode is on; we do not want that path.)
- BigTIFF: examples are classic TIFF (`is_bigtiff=False`); PanSeg's `create_tiff` already switches to `bigtiff=True` above 4 GiB (panseg/io/tiff.py:232). BigTIFF changes no axis/metadata semantics.
- Multipage vs tiled: examples are one-IFD-per-plane contiguous stacks; tiled (Slide-style) storage is legal in the format but irrelevant to axis order.

### 2.4 How common is time-spacing metadata in real files?

Effectively **absent** in the files we can measure, and **optional to the point of rarely written** in the model:
- 0/8 example files contain `TimeIncrement`, `TimeIncrementUnit`, `Plane` elements, or any `PhysicalSize*` at all. Full `Pixels` attribute set per file is only: `ID, BigEndian, DimensionOrder, SizeC, SizeT, SizeX, SizeY, SizeZ, Type` (recorded in §3).
- The schema provides no required/default time spacing; a writer must explicitly emit `TimeIncrement` or per-plane `DeltaT`.
- Consequence for the import spec: treat OME-TIFF time spacing as **missing by default**; when present, read `TimeIncrement`/`TimeIncrementUnit` (prefer) and/or `Plane`/`DeltaT` (first plane per timepoint); default unit is seconds.

## 3. Local evidence — 8 example OME-TIFFs

Inspected with tifffile 2026.3.3, numpy 2.4.3, via `TiffFile`, `TiffFile.series`, `asarray`/`imread`, and raw OME-XML parsing. All files: classic TIFF, no ImageJ metadata, one OME `Image`, no `Plane` elements, no `PhysicalSize*`, no `TimeIncrement`, self-referential `TiffData/UUID`, IFDs contiguous 0..N-1 with `PlaneCount=1`, non-tiled, `Type="int8"`, `BigEndian="true"`, `DimensionOrder="XYZCT"`.

| file | OME Sizes (T,C,Z) | `series.axes` | shape from `imread`/`asarray` (= PanSeg `load_tiff`) |
|---|---|---|---|
| single-channel.ome.tif | 1,1,1 | `YX` | (167, 439) |
| multi-channel.ome.tif | 1,3,1 | `CYX` | (3, 167, 439) |
| z-series.ome.tif | 1,1,5 | `ZYX` | (5, 167, 439) |
| time-series.ome.tif | 7,1,1 | `TYX` | (7, 167, 439) |
| multi-channel-z-series.ome.tif | 1,3,5 | `CZYX` | (3, 5, 167, 439) |
| multi-channel-time-series.ome.tif | 7,3,1 | `TCYX` | (7, 3, 167, 439) |
| 4D-series.ome.tif | 7,1,5 | `TZYX` | (7, 5, 167, 439) |
| multi-channel-4D-series.ome.tif | 7,3,5 | `TCZYX` | (7, 3, 5, 167, 439) |

`read_tiff_shape` (panseg/io/tiff.py:133) returns the same shapes (it falls back to `tiff.asarray().shape` because `shaped_metadata` is None for OME files, then drops singleton dims).

## 4. tifffile behavior (verified empirically + from source)

Source: tifffile 2026.3.3 (installed in the panseg-fork env; `tifffile/tifffile.py`), docs at https://tifffile.readthedocs.io.

- **Reshape:** the OME parser sets `axes = ''.join(reversed(DimensionOrder))` (tifffile.py:6051) and `shape = [Size{ax} for ax in axes]`, then maps each `TiffData` to its position with `First{ax}` indices (6066–6071). So a file with `DimensionOrder="XYZCT"` (or the tifffile default `XYCZT`) comes back as numpy axes **TCZYX(S)**. `imwrite(ome=True)` writes `DimensionOrder` as the reverse of the numpy axes order, default `XYCZT` (15450), i.e. canonical writer output also normalizes to the TCZYX family.
- **Singletons:** internally an `S` axis is always present (1 if absent, 6201–6204); on read, `TiffFile.asarray` squeezes by default: "Remove all length-1 dimensions from array, except X and Y… For series… By default, all but 'shaped' series are squeezed" (docstring, 4516–4535). Hence the per-file `series.axes`/shapes in §3: T-first, C second, Z third, singletons dropped. `series.axes` is the authoritative per-file axis string (includes `T` when present).
- **Metadata exposure:** `tf.ome_metadata` (raw OME-XML string), `tf.imagej_metadata`, `tf.shaped_metadata` (None for OME), `series.axes`/`series.shape`. **There is no API surface for time spacing** — `TimeIncrement`/`DeltaT` are only reachable by parsing `ome_metadata` yourself. (Conversely, `imwrite` *accepts* `TimeIncrement`/`TimeIncrementUnit` under `metadata` for Pixels and `DeltaT`/`DeltaTUnit` per plane — 15340–15375, 15526–15527, 15892–15893.)
- Multi-file: supported in `TiffFile` when `multifile` is enabled (6096–6140); with it off, OME series with foreign `UUID`/`FileName` fall back to generic series. We want an explicit rejection instead (see §2.3).

## 5. PanSeg's current import path on these files

Code: `panseg/io/io.py` (`smart_load` 17, `smart_load_with_vs` 57, `shape_to_stack_layout` 99), `panseg/io/tiff.py` (`load_tiff` 155, `read_tiff_voxel_size` 104, `_read_ome_meta` 49, `read_tiff_shape` 133), `panseg/core/image.py` (`ImageLayout` 71, `import_image` 675, `stack_sort` 626), UI prefill `panseg/viewer_napari/widgets/input.py:296–316`.

Measured behavior (panseg-fork env, actual `smart_load_with_vs` + `shape_to_stack_layout` + `import_image` runs):

| file | `smart_load_with_vs` shape | VoxelSize returned | UI prefill (`shape_to_stack_layout`) | `import_image` with prefill / any valid layout |
|---|---|---|---|---|
| single-channel | (167, 439) | `None` (+warn "Error parsing omero tiff meta.") | `YX` | OK |
| multi-channel | (3, 167, 439) | `None` (+warn) | `CYX` | OK → 3 × YX |
| z-series | (5, 167, 439) | `None` (+warn) | **`CYX` (wrong: 5 z-slices read as 5 channels)** | "OK" → **5 × YX images, Z silently destroyed** |
| time-series | (7, 167, 439) | `None` (+warn) | **`CYX` (wrong: 7 timepoints read as 7 channels)** | "OK" → **7 × YX images, T silently destroyed** |
| multi-channel-z-series | (3, 5, 167, 439) | `None` (+warn) | **CRASH `IndexError: pop from empty list`** (io.py:120) | only `CZYX` works; `ZCYX` rejected by heuristic |
| multi-channel-time-series | (7, 3, 167, 439) | `None` (+warn) | **CRASH** | `CZYX` → 7 images (T→C, C kept as CYX… shape (3,167,439) per image); `ZCYX` → **3 images of (7,167,439): T silently treated as Z** |
| 4D-series (TZYX) | (7, 5, 167, 439) | `None` (+warn) | **CRASH** | `CZYX` → 7 ZYX (T→C); `ZCYX` → 5 ZYX (Z→C, **T kept as Z**); no layout can express T |
| multi-channel-4D (TCZYX) | (7, 3, 5, 167, 439) | `None` (+warn) | `""` (len(shape) > 4, io.py:106) | **unimportable** — every layout fails the ndim check (image.py:702) |

Structural gaps the import spec must close:
1. `ImageLayout` has no `T` (panseg/core/image.py:71–96); `import_image` only branches on YX/CYX/ZYX/CZYX/ZCYX (713–791), and `stack_sort` (626) knows only C/Z/Y/X.
2. `VoxelSize` is a fixed `(z, y, x)` 3-tuple with unit restricted to µm (panseg/io/voxelsize.py:19–57) — no time spacing, no seconds.
3. `_read_ome_meta` (panseg/io/tiff.py:49–101) reads only `PhysicalSizeX/Y/Z` **attributes**; there is no code path for `TimeIncrement`, `Plane/DeltaT`, or any time axis — and the warning "Error parsing omero tiff meta." + `VoxelSize()` is what every OME file without X/Y/Z PhysicalSize hits (all 8 examples).
4. `shape_to_stack_layout` (panseg/io/io.py:99–121): guesses the channel as the single axis `< 10`; a small `T` is indistinguishable from a small `C` (both silently become C); two small leading axes → `IndexError` crash (which propagates in the UI prefill, input.py:303/312); 5D → `""`. Shape-based guessing cannot work for T — the import spec must use format-provided axis names (`series.axes`, NGFF `axes`), not shape heuristics.
5. `load_tiff` applies `.squeeze()` (panseg/io/tiff.py:164): a 1-frame time series (T=1) loses its T axis indistinguishably from a ZYX volume — axis *presence* metadata must be read, not inferred.
6. Zarr/h5 readers (`panseg/io/zarr.py:84–139`, `panseg/io/h5.py:62–133`) read raw datasets + `element_size_um`/`resolution` attrs only; neither reads OME-NGFF `axes`/`coordinateTransformations`, and PanSeg's own writers (`create_zarr` zarr.py:142–173, `create_h5` h5.py:136–167, `PanSegImage.to_h5` image.py:351–380) store **no axis names at all** — so PanSeg-produced h5/zarr with T would be unreadable even by a future T-aware PanSeg.
7. `create_tiff` (panseg/io/tiff.py:167–263) reshapes to 6-D TZCYXS internally and supports layouts up to CZYX; its OME branch comment already notes OME-XML mode doesn't take `spacing`/`unit` — a T-capable writer must pass `TimeIncrement` metadata (supported by tifffile, §4).

## 6. OME-NGFF (OME-Zarr)

Sources: `ome/ngff-spec` (spec v0.6, 2026-09-14) `index.md` + `examples/multiscales_strict/multiscales_example.json` + `version_history.md`; historical spec texts `ome/ngff` tag `0.3.0` and `0.4.1` (`0.3/index.bs`, `0.4/index.bs`).

- **0.3 (2021-08):** `multiscales[].axes` = **list of single-letter strings**, values unique, one of `{"t","c","z","y","x"}` (e.g. `["t","c","z","y","x"]`), also mirrored in each scale group's `_ARRAY_DIMENSIONS` (xarray zarr encoding). No per-axis units, no coordinateTransformations → **no time spacing representable** (only what `omero` display metadata carried).
- **0.4 (2022-02):** `axes` = list of objects `{name, type, unit}`: `type` SHOULD be `space|time|channel`; `unit` SHOULD be a UDUNITS-2 string — time units include `second, millisecond, microsecond, minute, ...`. **Ordering constraint (carried through 0.5/0.6): "the time axis must come first (if present), followed by the channel or custom axis (if present) and the axes of type space"; 3 spatial axes SHOULD be ordered `zyx`.** Each `datasets[]` entry **MUST** contain `coordinateTransformations` with exactly one `scale` — "specifies the pixel size in physical units **or time duration**" — and optionally one `translation`; so time spacing = `scale[t_index]` in the unit declared on the time axis.
- **0.5 (2024-11):** same metadata on **Zarr v3** (attrs in `zarr.json`).
- **0.6 (2026-09-14):** adds `coordinateSystems` (named axes arrays) and a transformation graph (`scale`, `translation`, `affine`, `sequence`, …) plus `scene` metadata; the multiscales dataset transform is restricted to `scale`/`identity`/`sequence(scale+translation)`. The spec's complete 5D example is a **TCZYX** multiscales: axes `[{name:"t",type:"time",unit:"millisecond"},{name:"c",type:"channel"},{name:"z",type:"space",unit:"micrometer"},…]` with `scale: [0.1, 1.0, 0.5, 0.5, 0.5]` — i.e. time step 0.1 ms, voxel 0.5 µm. Display metadata `omero.rdefs` even has `defaultT` ("First timepoint to show the user").

**What a T-bearing store would need from PanSeg today:** `panseg/io/zarr.py` (`load_zarr` 84, `read_zarr_voxel_size` 120) treats any zarr array as anonymous N-D and looks only for `element_size_um`/`resolution` attrs (3 values). A conforming OME-Zarr file (what bioformats2raw, napari exporters, ome-zarr-py produce) has **none of those** — voxel size is in `coordinateTransformations[].scale` and axis identity in `multiscales[].axes`/`coordinateSystems`. So: (a) read `axes` (0.4/0.5/0.6 object form *and* 0.2/0.3 letter-string form for legacy files), (b) map `type:"time"` axis index, (c) take `scale` entries for that axis (+ axis `unit`) as time spacing, (d) return data in file order — **zarr readers never transpose**, the array's dimension order *is* the file's axis order, so a conforming file already gives TCZYX. Writing: PanSeg's `create_zarr` must start emitting axis metadata (at minimum an axes string + per-dimension scale with units) or PanSeg's own T-stores will be ambiguous.

## 7. HDF5

- **PanSeg's own format** (panseg/io/h5.py:136–167, panseg/core/image.py:351–403): one h5py `Dataset` per semantic role under keys `raw|prediction|segmentation|labels` (h5.py:12), attrs on the dataset: `element_size_um` (3-float tuple, z,y,x, µm) and `panseg_image_metadata_json` (full `ImageProperties` JSON, which today can only express C/Z/Y/X layouts). For T + t_spacing this needs: a 4-element (or per-axis) size attr with a time unit, `T` in the layout enum, and axis names in the JSON — otherwise a stored T stack is again just an anonymous 4-D array.
- **Community conventions:** there is no active community h5 standard for microscopy time beyond (a) the old **OME-HDF5** spec (2006; superseded by the OME-NGFF project — the OME site presents NGFF/OME-Zarr as the current OME file-format effort; the spec page was unreachable from this environment, so its exact field names are not cited here) and (b) NGFF-style metadata, which the NGFF spec explicitly notes "will also be usable by HDF5 and other sufficiently advanced" containers (ome/ngff 0.3/0.4 `index.bs`, motivation section). Practical recommendation for the import spec: treat PanSeg h5 as PanSeg's own format (extend its attrs) and treat *foreign* h5 (e.g. OME-HDF5) as best-effort out of scope, mirroring the multi-file OME-TIFF decision.

## 8. Ecosystem vocabulary (glossary input)

| World | Term for the dimension | Term for the interval | Source |
|---|---|---|---|
| OME-XML / OME-TIFF | `T` (`SizeT`, `FirstT`, `TheT`, `DeltaT`) | `TimeIncrement` (global), `DeltaT` (per-plane), unit default `s` | OME-XML 2016-06 XSD (§2.1) |
| OME-NGFF / OME-Zarr | axis `type: "time"`, name arbitrary (spec examples use `"t"`); display metadata `defaultT` | `scale` value on the time axis + axis `unit` (UDUNITS-2: `second`, `millisecond`, …) | NGFF 0.4/0.6 spec (§6) |
| napari | none built-in: extra leading axes are user-named via `axis_labels` ("If not provided, axis_labels will be set to (…, '-2', '-1')"); trailing 2 axes are spatial | — (just the layer `scale` tuple) | napari Image API docs, https://napari.org/stable/api/napari.layers.Image.html |
| bioimage.io (bioimageio.core 0.10.2, already a PanSeg dependency) | axis type `"time"`; legacy ids `"t"`/`"time"` normalize to `"time"` (axis.py:13–14) | — (model specs declare sizes, not spacing) | installed `bioimageio/core/axis.py` |

**Recommended vocabulary for the glossary term:** the dimension is **time** (letter **`T`**); a value along it is a **timepoint** (or frame, when C is absent — avoid "frame" as the generic since C and T are both frame-like); the interval between consecutive timepoints is **time spacing** (or **timestep**), always with a unit (default seconds, matching OME-XML `TimeIncrementUnit`). "T" + "time" + "time spacing" is consistent across OME-XML, NGFF, and bioimage.io, which is every ecosystem PanSeg touches.

## 9. Implications for the axis-order decision (ticket 02)

**Strongest argument FOR the TCZYX lean:**
1. It is the **reader-native order of the two ecosystems we read**. tifffile's OME-TIFF output is TCZYX (minus singletons) for the standard `XYZCT`/`XYCZT` DimensionOrder files — no transpose needed between file and memory (empirical, §3; source §4). The NGFF spec *requires* time-before-channel-before-space with spatial SHOULD `zyx` (0.4 through 0.6), and its canonical 5D example is TCZYX — a conforming zarr array is *already* TCZYX on disk. Choosing TCZYX means both import paths are identity mappings; choosing CZYX-style orders means transposing on every OME import.
2. It matches the OME model's own enumeration: `SizeT` is listed first among the non-spatial sizes in tooling order, and OME tooling (Bio-Formats `TCZYX`, OMERO) treats T as the outermost (slowest) axis — the axis that is *iterated*, not the one segmentation operates on.

**Strongest argument AGAINST:**
1. It breaks PanSeg's current invariants: `C` at axis 0 (`channel_axis` 0 in CZYX, image.py:141–149), 3-element `VoxelSize`, and the per-channel split pipeline (`import_image` CZYX branch, `split_channels`). T-first means `C` is no longer axis 0 and every layout enum, the `stack_sort` sort order (626), the scale property (533–551), and the UI layout widget must change at once.
2. **Shape guessing gets worse, not better**: today a small leading axis is already ambiguous C-vs-Z (and silently misread, §5); with T there are three ambiguous non-spatial letters. The fix is the same regardless of the chosen order — import must be driven by format axis metadata (`series.axes` / NGFF `axes`), with explicit user correction — but it means the prefill heuristic (`shape_to_stack_layout`) must be reworked, not extended.
3. Singleton-squeezing by readers means "TCZYX" in practice means **"TCZYX with absent axes dropped"** (TYX, TZYX, TCYX, ZYX, …). The canonical order decision must therefore define the *complete* 5-letter order plus a rule for dropped singletons, or every downstream consumer will re-invent that rule.

## 10. Sources

- OME-XML 2016-06 XSD (last released schema): https://raw.githubusercontent.com/ome/schemas/master/OME/2016-06/ome.xsd (same file in `ome/ome-model` `specification/src/main/resources/released-schema/2016-06/`) — `Pixels` (DimensionOrder enum, SizeT, PhysicalSizeX/Y/Z attrs, TimeIncrement/TimeIncrementUnit), `Plane` (DeltaT/DeltaTUnit, TheT), `TiffData` (IFD/FirstT/FirstC/FirstZ/PlaneCount, UUID/FileName).
- OME-TIFF format spec (canonical; unreachable from this environment): https://ome-tiff.openmicroscopy.org/
- tifffile 2026.3.3 source (env: `/home/kriedmiller/software/miniforge3/envs/panseg-fork/lib/python3.11/site-packages/tifffile/tifffile.py`): OME parse 6040–6300 (DimensionOrder reversal 6051, TiffData mapping 6066–6071, S-axis 6201), `asarray` squeeze docstring 4516–4535, `imwrite` OME metadata keys 15340–15375 & 15515–15560, plane metadata 15875–15905. Docs: https://tifffile.readthedocs.io
- OME-NGFF spec v0.6: https://github.com/ome/ngff-spec (`index.md`, `examples/multiscales_strict/multiscales_example.json`, `version_history.md`); historical 0.3/0.4 texts: https://github.com/ome/ngff tags `0.3.0`/`0.4.1` (`0.3/index.bs`, `0.4/index.bs`).
- napari `Image` API: https://napari.org/stable/api/napari.layers.Image.html (`axis_labels` default `(…, '-2', '-1')`).
- bioimageio.core 0.10.2 `axis.py` (installed in panseg-fork env): axis type `time`, legacy `t` normalization.
- PanSeg code: `panseg/io/io.py`, `panseg/io/tiff.py`, `panseg/io/zarr.py`, `panseg/io/h5.py`, `panseg/io/voxelsize.py`, `panseg/core/image.py`, `panseg/viewer_napari/widgets/input.py` (line refs in §5).
- Local examples: `/tmp/opencode/ome_tiff_examples/*.ome.tif` (not in repo; inspected 2026-09-17).
