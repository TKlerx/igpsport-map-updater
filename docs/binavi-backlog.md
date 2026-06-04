# BiNavi Experimental Backlog

BiNavi support currently reuses the existing map generation pipeline for the main parseable `Maps/*.map` file, then packages that generated map together with official BiNavi files copied from a vendor package.

## Current Scope

- Generate the main parseable BiNavi country map with the existing `run.ps1` / `run.sh` pipeline.
- Preserve official `Router/*.rtd` files unchanged.
- Preserve non-standard `Maps/*.map` files unchanged, including contour and overview maps.
- Package the result as an experimental BiNavi ZIP with README and manifest.

## Backlog: DEM / Contour Maps

Goal: regenerate contour/elevation map files such as `IT0000C.map` instead of copying them from the official package.

Open questions:
- Which elevation data source should we use: SRTM, Copernicus DEM, OpenTopoData, or another source?
- What contour interval and tag mapping does BiNavi expect?
- Can Mapsforge writer 0.27 produce compatible contour-only maps, or do we need a preprocessing step that converts DEM contours into OSM/PBF ways?
- How should contour filenames be derived for each country/package?
- Are contour maps optional on-device, or required for stable rendering?

Possible implementation path:
1. Add a small DEM download/cache layer per country bounding box.
2. Generate contour line geometries at the expected intervals.
3. Convert contours into an OSM/PBF stream with `ele=*` way tags matching the official BiNavi contour map.
4. Run Mapsforge writer with a BiNavi contour-specific tag mapping and zoom interval configuration.
5. Compare generated contour tags, bbox, zoom intervals, and file behavior against official `*C.map` files.

Risk:
- This may be a separate project-sized feature. DEM processing can be CPU/storage heavy, and incorrect contour maps may render poorly or not at all.

## Backlog: Router Files

Goal: understand and optionally regenerate `Router/*.rtd` files.

Open questions:
- Is `.rtd` a public routing format, a lightly wrapped graph format, or proprietary iGPSPORT data?
- Does the device require matching `.rtd` files for routing, or can it route acceptably with updated visual maps and old router files?
- Do `.rtd` files encode country-wide routing graph data, map tile IDs, timestamps, or checksums that must match the `.map` files?

Possible implementation path:
1. Collect multiple official BiNavi packages and compare `.rtd` sizes/names/checksums.
2. Inspect file headers and look for recognizable magic bytes, compression, SQLite, protobuf, or graph formats.
3. Test device behavior with old router files plus a regenerated main map.
4. Only attempt generation if the format is understood well enough to avoid device-side surprises.

Risk:
- Router files may be proprietary and impractical to regenerate safely.

## Backlog: BiNavi Tag Mapping

Goal: make the generated main map closer to official BiNavi maps.

Known differences from the inspected Italy package:
- Official BiNavi maps include POIs such as restaurants, toilets, hospitals, stations, bicycle shops, cities, towns, and villages.
- Official BiNavi maps include landuse/natural layers, rail, and elevation tags.
- Current default tag mapping is optimized for BSC300/iGS630 and is much smaller.

Possible implementation path:
1. Add separate `tag-binavi.xml` and optional `tag-binavi-transform.xml`.
2. Generate a BiNavi main map with richer POI/way tags.
3. Compare tags and zoom intervals against the official package using `extract_tags_map.py`.
4. Keep this separate from the BSC300/iGS630 configuration.
