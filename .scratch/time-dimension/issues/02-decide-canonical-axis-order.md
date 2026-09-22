# Decide the canonical internal axis order

Type: grilling
Status: resolved
Blocked by: 01

## Question

Which single fixed internal axis order does the spec mandate for time-bearing data? The user's tentative lean at charting was TCZYX (T first, then C, then spatial), and the anchor OME-TIFF files read back as (T, C, Z, Y, X) — confirm or adjust with the research findings (ticket 01).

Sub-decisions:

- What "fixed order" guarantees: only time-bearing images (TZYX / TCZYX / TYX, singleton C allowed), with the existing 2D/3D layout behavior (YX, CYX, ZYX, CZYX, import-time squeezing) unchanged in v1? (charting assumption — confirm)
- The import/export conversion cost (transpose) between the fixed order, OME-TIFF physical order, and napari axis order.
- `stack_layout` input syntax for T (e.g. "tzyx", "tczyx"; inversion syntax like the existing "-CZYX").

## Answer

Resolved 2026-09-18, grilling, one round, all three sub-decisions settled.

1. **Canonical full order: TCZYX.** Every internal array is a projection of the order T, C, Z, Y, X: only the present axes, in that relative order. Rationale:
   - Reader-native on both OME paths: tifffile's OME-TIFF output is TCZYX with singleton axes dropped (verified on all 8 anchor files), and the NGFF spec mandates time before channel before space. OME-TIFF and OME-Zarr import are therefore identity mappings, no transpose (evidence: ticket 01).
   - Extends the existing C-Z-Y-X canonical order by prepending T, so the four existing layouts are untouched projections of it.
   - Consequences accepted in the decision: in time-bearing data the channel axis sits at index 1, not 0; napari layers take memory order as-is (current mechanism for all layouts), so T is the outermost slider, above Z; export reuses the existing TZCYXS slots of `create_tiff` (panseg/io/tiff.py:186), T filling the currently unused T slot with the C/Z swap applied as today.
2. **Layout set.** `ImageLayout` (panseg/core/image.py:71) gains exactly four members: TYX, TCYX, TZYX, TCZYX. YX, CYX, ZYX, CZYX and the deprecated ZCYX pass-through are unchanged; v1 behavior for non-time data is untouched. TCYX is required, not optional: anchor file `multi-channel-time-series.ome.tif` is (T,C,Y,X) = (7,3,167,439).
3. **`stack_layout` syntax.** Alphabet extended with `t`: any permutation of the present letters, `-` inversion unchanged (e.g. `tzyx`, `tczyx`, `-tzyx`). `stack_sort` (panseg/core/image.py:626) ranks T ahead of C, so the rank order becomes T, C, Z, Y, X; strings without `t` behave exactly as today.
4. **Not decided here** (owned by the linked tickets):
   - T=1 squeeze rule at import, the `VoxelSize` t_spacing slot and `scale` mapping, and the "4D" glossary ambiguity (both CZYX and TZYX are now 4-axis arrays) all go to "Design the time data-model extension" (03).
   - Prefill source, shape heuristic vs format axis metadata (`series.axes` / NGFF `axes`), goes to "Specify time I/O" (05).
   - T in `m_slicing` and input-tab UX go to "Specify viewer/GUI/headless UX for time" (07).
