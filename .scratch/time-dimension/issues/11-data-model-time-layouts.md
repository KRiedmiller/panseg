# 11: Data model: T in layouts and image properties

**What to build:** Time becomes a first-class citizen of the core data model, so that a
time-bearing image can be constructed, inspected, and roundtripped in memory with no I/O
involved (spec: "Canonical axis order and layouts" + "Data model").

TCZYX is the canonical full axis order; every internal array is a projection of T-C-Z-Y-X.
The layout string alone carries the time axis — no `has_time`/`time_axis` field anywhere:
`time_axis`, `is_timelapse`, `channel_axis`, and `dimensionality` all derive from the layout
string by projection and are never stored. `ImageLayout` gains exactly four members:
TYX, TCYX, TZYX, TCZYX. `stack_sort` ranks T ahead of C, so the `stack_layout` input
alphabet extends with `t` (the existing `-` inversion syntax unchanged); strings without `t`
behave exactly as today. `ImageDimensionality` stays spatial-only (TWO/THREE) — it routes
spatial behavior everywhere (model zoo filter, training, mesh-export 3D gate); time presence
is the orthogonal `is_timelapse` property on `PanSegImage` mirroring `is_multichannel`.

The singleton squeeze rule generalizes the existing ZYX→YX / CZYX→{YX,ZYX,CYX} casts: drop
every length-1 axis except Y and X; the layout is the projection onto what remains.
Consequences: 1-frame file → no T, C=1 timelapse → no C, Z=1 timelapse → no Z.

`ImageProperties` gains `t_spacing: float | None` (the time spacing in seconds; `None` = the
source carried no timing metadata — a first-class supported state) and `t_unit: str = "s"`
(source units ms/µs/min converted at construction). A `t` property returns `t_spacing` or
neutral 1.0 when unknown. `VoxelSize` stays strictly spatial (z, y, x micrometers) and is
unchanged, including the `element_size_um` on-disk 3-float. `PanSegImage.scale` gains the T
layouts: the T axis takes `properties.t`, the C axis 1.0, spatial axes as today — so in
napari the outermost slider is scaled by the time spacing when known.

`split_channels` and `merge_with` gain T branches: TCZYX → list of TZYX images,
TCYX → list of TYX images (names `f"{name}_{ch}"` as today). Because `VoxelSize` equality
cannot see time spacing, `merge_with` additionally requires an explicit `t_spacing` match
plus an `is_timelapse` match: set-vs-set differing ⇒ rejected, set-vs-unknown ⇒ rejected,
unknown+unknown ⇒ allowed (result `t_spacing` None). Merged layout is TCYX/TCZYX when
time-bearing, CYX/CZYX otherwise.

The `ImageProperties` JSON blob (carried by h5 metadata and napari layer metadata) roundtrips
the new fields with no format change; old JSON lacking the keys defaults to `None`/`"s"`.

Prefactor (do first, it makes the rest one-line additions): replace the duplicated
per-layout member lists scattered across the derived properties, `scale`, and the
import/construction ndim/shape checks with a single layout → axes table. TYX (2D timelapse)
is a supported, required projection — not a rejected case.

**Blocked by:** None (can start immediately)

**Status:** ready-for-agent

- [ ] `ImageLayout` gains exactly TYX, TCYX, TZYX, TCZYX; existing members (incl. the deprecated ZCYX pass-through) and all non-T behavior are untouched (existing suite green)
- [ ] Table-driven test asserts the derived props (`channel_axis`, `time_axis`, `dimensionality`, `is_timelapse`) across all nine layouts; `dimensionality` is spatial-only (TZYX → 3D, TYX → 2D)
- [ ] `stack_sort` / `stack_layout` input accepts `t` and `-t`, ranks T ahead of C, and strings without `t` behave exactly as today
- [ ] Squeeze rule: T=1, C=1, Z=1 time-bearing constructions drop the axis and update the layout (TZYX(1,Z,Y,X) → ZYX; TCZYX(7,C,1,Y,X) → TCYX; TCZYX(1,C,Z,Y,X) → CZYX; TCZYX(T,1,Z,Y,X) → TZYX)
- [ ] `t_spacing` stored in seconds with unit normalization at construction (e.g. 500 ms → 0.5 s); `None` = unknown; the `t` property returns `t_spacing` or 1.0
- [ ] `scale`: T axis = `t_spacing` (1.0 when unknown), C axis 1.0, spatial axes as today
- [ ] `split_channels`: TCZYX → C × TZYX, TCYX → C × TYX, per-channel naming as today; TZYX/TYX are not split
- [ ] `merge_with`: is_timelapse + explicit t_spacing match rules (set/set equal ⇒ merge to TCZYX/TCYX; set/set differing ⇒ rejected; set vs unknown ⇒ rejected; unknown+unknown ⇒ merge, result `t_spacing` None)
- [ ] `ImageProperties` JSON roundtrip carries `t_spacing`/`t_unit`; JSON lacking the keys (old files/layers) loads as `None`/`"s"`
