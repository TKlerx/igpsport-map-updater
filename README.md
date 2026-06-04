# IGPSPORT Map Updater

A tool to generate custom map files for IGPSPORT cycling computers from OpenStreetMap data. This project downloads OSM PBF files, filters them based on polygon boundaries, transforms unsupported tags, and generates Mapsforge map files with the specific naming convention required by IGPSPORT GPS devices.

## Supported Products

- BiNavi
- iGS800
- iGS630
- iGS630S
- BSC300T
- BSC300

Official support/download page: https://www.igpsport.com/en/support/product

BiNavi support is experimental and intentionally separated from the BSC300/iGS630 workflow. It can replace the main visual `.map` file inside an official BiNavi package, but it preserves official `Router/*.rtd` and contour/overview map files because this project cannot regenerate them yet.

Unofficial generated maps may be shared separately here:
https://drive.google.com/drive/folders/1NY_q-Hvnez6VN00m43LLvkheAtAw5vA2

These shared maps are community-generated artifacts, not official iGPSPORT downloads. See [ATTRIBUTION.md](ATTRIBUTION.md) for OpenStreetMap attribution and sharing notes.
Use [MAP_PACKAGE_README.txt](MAP_PACKAGE_README.txt) as the README file for shared map folders or ZIP packages.

## Requirements

- **Java 17** or higher
- **Python 3.12** or higher (for utilities like `generate_maps_csv.py`)
- **Internet connection** (for downloading OSM data and dependencies)
- **Disk space**: Several GB depending on the size of the regions being processed

### Platform-Specific Requirements

#### Windows
- PowerShell 5.0 or higher (included in Windows 10/11)
- Windows 7 or higher

#### Unix/Linux/macOS
- Bash shell
- `curl` (for downloading files)
- `unzip` (for extracting archives)
- `bc` (for mathematical calculations)

### Python Setup

```bash
uv sync                # installs dev dependencies (pytest)
uv sync --extra pbf    # also installs pyosmium (needed for extract_tags_pbf.py)
```

Use `uv run python ...` for Python utilities when possible. This keeps the repo on the configured Python version and avoids accidentally using a different system Python.

## Important Notes

### Before You Start

⚠️ **Use At Your Own Risk**: Do it at your own risk; I am not responsible for broken devices.

⚠️ **Backup Your Maps**: Before using the new maps, make sure to backup your existing maps from your IGPSPORT cycle computer. Store them in a safe location in case you need to revert.

⚠️ **Free Up Space**: Remove old maps from your cycle computer before transferring new ones. The new maps are significantly larger due to enhanced tags and more detailed information, so you'll need extra storage space.

⚠️ **Processing Time**: The map conversion process takes several hours to complete, depending on the size of the regions and your computer's performance. Plan accordingly and let the script run without interruption.

### Map Size Changes

The generated maps are **larger than original IGPSPORT maps** because they include:
- More detailed road networks
- Additional map features (waterways, natural features)
- Enhanced tagging information for better routing
- Extended geographic data

### Tag Configuration

This project uses two XML configuration files to control which OpenStreetMap tags are included in the generated maps:

#### Supported Tags ([tag-igpsport.xml](tag-igpsport.xml))

The following **21 tags** are directly supported by IGPSPORT devices:

| Category | Tags | Zoom Level |
|----------|------|------------|
| **Major Roads** | primary, primary_link, secondary, secondary_link, trunk, trunk_link, tertiary, tertiary_link | 13 |
| **Minor Roads** | cycleway, living_street, pedestrian, residential, road, service, track, unclassified | 14 |
| **Natural** | coastline, water | 13 |
| **Waterways** | canal, dam, drain, river, stream | 14 |

#### Tag Transformations ([tag-igpsport-transform.xml](tag-igpsport-transform.xml))

The following **12 transformations** convert unsupported OSM tags to device-compatible equivalents:

| Unsupported Tag | Transformed To | Description |
|-----------------|----------------|-------------|
| `highway=motorway` | `highway=trunk` | Major highways |
| `highway=motorway_link` | `highway=trunk_link` | Highway ramps |
| `highway=footway` | `highway=cycleway` | Pedestrian paths |
| `highway=path` | `highway=cycleway` | Generic paths |
| `highway=bridleway` | `highway=cycleway` | Horse trails |
| `highway=sidewalk` | `highway=cycleway` | Sidewalks |
| `highway=steps` | `highway=pedestrian` | Stairs |
| `highway=byway` | `highway=track` | Rural byways |
| `highway=bus_guideway` | `highway=road` | Guided bus routes |
| `highway=construction` | `highway=road` | Roads under construction |
| `highway=raceway` | `highway=road` | Racing circuits |
| `highway=services` | `highway=service` | Service areas |

This means the maps effectively support **33 highway types** (21 native + 12 transformed).

See the [Mapsforge tag-mapping reference](https://github.com/mapsforge/mapsforge/blob/master/mapsforge-map-writer/src/main/config/tag-mapping.xml) for all available OpenStreetMap tags.

## Quick Start

### 1. Build a country package

The easiest path is the one-command package builder. It downloads the official iGPSPORT map files for the requested region, generates updated OpenStreetMap-based `.map` files, and writes a shareable ZIP to `packages/`.

#### Windows

```powershell
uv run python build_map_package.py switzerland
```

#### Unix/Linux/macOS

```bash
uv run python build_map_package.py switzerland
```

This downloads the official original maps into `tmp/igpsport-official-switzerland/input`, runs the generator with resume mode, and creates `packages/IGPSport300-800-Switzerland.zip`. Use `--dry-run` to print the commands without downloading or generating maps.

For iGS630/iGS630S/iGS800 compatibility builds, use the stricter profile:

#### Windows

```powershell
$env:MAP_TAG_PROFILE = "igs630"
uv run python build_map_package.py switzerland --package-prefix IGPSport-iGS630
```

#### Unix/Linux/macOS

```bash
MAP_TAG_PROFILE=igs630 uv run python build_map_package.py switzerland --package-prefix IGPSport-iGS630
```

The workflow is resumable: existing official input maps in `tmp/igpsport-official-<region>/input` are skipped, and existing generated output maps are skipped by the generator's resume mode when their build metadata matches the current settings.

By default, the work folder is kept so reruns can resume. Use `--clean-work` to delete that country work folder after a successful package build:

```powershell
uv run python build_map_package.py switzerland --clean-work
```

### 2. Copy maps to your device

1. Delete the old maps from your iGPSport device
2. Extract the ZIP in `packages/` and copy the new `.map` files to your device
3. Safely eject and restart the device

Keep a backup of your original device maps somewhere safe before deleting anything from the device.

### Optional: use local original maps

If you already copied official `.map` files from your device, or you want to build from a manually downloaded set, put those files in a folder such as `input/` and run the updater directly.

The `run` script reads the original map filenames to figure out which regions you need, generates `maps.csv`, downloads the latest OpenStreetMap data, and generates updated `.map` files in `output/`.

```powershell
.\run.ps1 input -Resume
```

```bash
chmod +x run.sh
./run.sh input --resume
```

You can also download official map ZIPs into `input/` yourself:

```bash
uv run python download_igpsport_maps.py switzerland --list
uv run python download_igpsport_maps.py switzerland --download -o input
uv run python download_igpsport_maps.py aargau --download -o input
```

If you prefer to run the steps separately or edit `maps.csv` before generating, see [Running Step by Step](#running-step-by-step).

`run.ps1` / `run.sh` are the full local-input workflow. `script.ps1` / `script.sh` are the map-generation-only step and assume `maps.csv` already exists.

### Optional: package existing output

To create a shareable ZIP from maps already generated in `output/`, package them with the original input directory used for generation:

```powershell
uv run python package_maps.py input
```

```bash
uv run python package_maps.py input
```

The package includes matching generated `.map` files, `README.txt` from [MAP_PACKAGE_README.txt](MAP_PACKAGE_README.txt), and `MANIFEST.txt` with the generator commit, included maps, and original input filenames.

Older iGS630 devices may use `map_md5_list.cfg` to validate installed maps. If your device has that file, pass it to the packager so the ZIP includes a refreshed copy with checksums for the generated map filenames:

```powershell
uv run python package_maps.py input --md5-cfg tmp\test-630\map_md5_list.cfg
```

## Running Step by Step

You can also run each step individually, which is useful if you want to review or manually edit `maps.csv` before generating maps.

### Step 1: Generate maps.csv

```bash
uv run python generate_maps_csv.py input/
```

The script reads the iGPSport filenames, figures out which geographic regions they cover, and finds the matching download URLs from [Geofabrik](https://download.geofabrik.de/). Review the output to verify the matched regions are correct.

If one tile spans several Geofabrik subregions, the generator may now emit a small same-country multi-region blend instead of falling back to a whole-country extract.

Alternatively, you can create `maps.csv` manually — see [CSV File Structure](#csv-file-structure).

### Step 2: Generate maps

#### Windows

```powershell
.\script.ps1
```

#### Unix/Linux/macOS

```bash
chmod +x script.sh
./script.sh
```

By default, the generator now uses an adaptive Mapsforge configuration:
- It prefers the in-memory (`ram`) writer to avoid excessive temp-file IO.
- It caps Java heap to about 80% of installed RAM.
- It does not fall back to the disk-backed (`hd`) writer unless explicitly enabled.
- It sizes RAM heuristics from the total source size for that map row, including multi-region blends.
- It uses the capped heap even for small extracts, because OSM density can matter more than PBF file size.

You can still override this manually with `MAP_WRITER_TYPE`, `MAP_WRITER_THREADS`, `JAVA_XMS`, `JAVA_XMX`, `JAVA_TMP_DIR`, and `MAP_TAG_PROFILE`. If you want the old slow-but-stubborn HD retry behavior, set `MAP_ALLOW_HD_FALLBACK=1`.

Tag profiles:
- `MAP_TAG_PROFILE=enhanced` is the default and includes extra waterways.
- `MAP_TAG_PROFILE=igs630` is a stricter compatibility profile for iGS630 devices that crash with enhanced maps. It matches official iGPSPORT maps more closely by keeping `footway`/`path`, excluding `waterway=*`, and copying the original map's Mapsforge `created_by` header value into the generated map.

Windows example:

```powershell
$env:MAP_TAG_PROFILE = "igs630"
uv run python build_map_package.py switzerland --md5-cfg tmp\test-630\map_md5_list.cfg
```

Bash example:

```bash
MAP_TAG_PROFILE=igs630 uv run python build_map_package.py switzerland --md5-cfg tmp/test-630/map_md5_list.cfg
```

If a run was interrupted and some final maps already exist in `output/`, you can resume:

```powershell
.\run.ps1 input -Resume
```

```bash
./run.sh input --resume
```

Resume mode skips entries when the exact expected final output already exists and its sidecar build metadata matches the current settings. This prevents accidentally packaging an older map generated with a different `MAP_TAG_PROFILE`, iGS630 header patch state, tag config, transform file, source mode, or Mapsforge writer version. Existing maps without sidecar metadata are rebuilt once.

## What the Script Does

1. **Downloads Osmosis** (if not present) - OpenStreetMap data processing tool (v0.49.2)
2. **Downloads Mapsforge Writer Plugin** (v0.27.0) - Converts OSM data to Mapsforge format
3. **Reads maps.csv** - Configuration file with region definitions
4. **Downloads OSM PBF files** - Raw OpenStreetMap data from Geofabrik
5. **Downloads Polygon files** - Geographic boundary definitions
6. **Transforms tags** - Converts unsupported OSM tags to device-compatible equivalents
7. **Clips to original tile** - Applies the bounding box encoded in the original iGPSport filename
8. **Chooses writer settings** - Selects adaptive Mapsforge writer mode, threads, and heap size
9. **Generates maps** - Creates Mapsforge `.map` files with proper zoom levels
10. **Stops on RAM failure by default** - HD mode is available only when explicitly requested
11. **Renames output** - Applies the original tile GEOCODE with the updated source date

## CSV File Structure

The `maps.csv` file defines which regions to process. It has three columns:

| Column | Description | Example |
|--------|-------------|---------|
| **Original filename** | The target IGPSPORT map filename format | `BR01002303102B83FO00N00E.map` |
| **OSM BPF URL** | One PBF URL, or several URLs separated by `;` for multi-region blends | `https://download.geofabrik.de/south-america/brazil-latest.osm.pbf` |
| **Poly URL** | Matching polygon URL(s); use same order as PBF column, separated by `;` when needed | `https://download.geofabrik.de/europe/germany/hessen.poly` |

### Example CSV Content

```csv
Original filename,OSM BPF URL,Poly URL
DE07002303103AO23I01L029.map,https://download.geofabrik.de/europe/germany/hessen-latest.osm.pbf,https://download.geofabrik.de/europe/germany/hessen.poly
DE090023031039R20Z03D02W.map,https://download.geofabrik.de/europe/germany/niedersachsen-latest.osm.pbf,https://download.geofabrik.de/europe/germany/niedersachsen.poly
```

Multi-region example:

```csv
Original filename,OSM BPF URL,Poly URL
CZ03002604163DE24P00T00L.map,https://download.geofabrik.de/europe/czech-republic/karlovarsky-latest.osm.pbf;https://download.geofabrik.de/europe/czech-republic/plzensky-latest.osm.pbf;https://download.geofabrik.de/europe/czech-republic/ustecky-latest.osm.pbf,https://download.geofabrik.de/europe/czech-republic/karlovarsky.poly;https://download.geofabrik.de/europe/czech-republic/plzensky.poly;https://download.geofabrik.de/europe/czech-republic/ustecky.poly
```

### Where to Find Resources

- **OSM PBF files**: [Geofabrik Downloads](https://download.geofabrik.de/)
- **Polygon files**: [Geofabrik Downloads](https://download.geofabrik.de/) (`.poly` files alongside the PBF files)

## Directory Structure

```
igpsport-map-updater/
├── igpsport_map_updater/        # Importable Python implementation package
│   ├── build_map_package.py
│   ├── download_igpsport_maps.py
│   ├── generate_maps_csv.py
│   ├── package_maps.py
│   ├── map_md5_cfg.py
│   ├── patch_mapsforge_header.py
│   ├── build_binavi_package.py
│   └── package_binavi.py
├── build_map_package.py         # Compatibility wrapper for the main CLI
├── download_igpsport_maps.py    # Compatibility wrapper for official downloads
├── generate_maps_csv.py         # Compatibility wrapper for maps.csv generation
├── package_maps.py              # Compatibility wrapper for ZIP packaging
├── build_binavi_package.py      # Compatibility wrapper for BiNavi packaging
├── run.sh                       # Full workflow - Unix/Linux/macOS
├── run.ps1                      # Full workflow - Windows
├── script.sh                    # Map generation only - Unix/Linux/macOS
├── script.ps1                   # Map generation only - Windows
├── maps.csv                     # Configuration file with map definitions
├── tag-igpsport*.xml            # Mapsforge tag profiles and transforms
├── tag-igpsport-igs630*.xml     # iGS630 compatibility tag profiles
├── test_*.py                    # Pytest suite
├── specs/                       # Spec Kit feature specifications
├── docs/                        # Project notes and backlog documents
├── download/                    # Downloaded OSM PBF and polygon files
│   ├── *.osm.pbf
│   └── *.poly
├── output/                      # Generated map files (final output)
│   └── *.map
├── input/                       # Optional local original iGPSPORT maps
├── tmp/                         # Temporary files during processing
├── misc/                        # Documentation and diagrams
│   ├── filename-structure.svg
│   ├── tile-grid-concept.svg
│   └── compare-2023-to-2026.jpg
└── osmosis-0.49.2/              # Osmosis tool (auto-downloaded)
    ├── bin/
    ├── lib/
    └── script/
```

### Directory Descriptions

- **igpsport_map_updater/**: Testable Python implementation package. New Python logic should live here.
- **Root Python files**: Thin compatibility wrappers. They keep documented commands such as `uv run python build_map_package.py switzerland` working.
- **download/**: Stores downloaded OSM PBF files and polygon boundary files. Files are cached to avoid re-downloading.
- **output/**: Contains the final generated `.map` files with IGPSPORT-compatible filenames.
- **input/**: Optional location for original iGPSPORT maps when using the local-input workflow.
- **tmp/**: Temporary directory used by Osmosis during processing (can be deleted after completion).
- **misc/**: Contains SVG diagrams explaining the filename structure and tile grid concepts.
- **osmosis-0.49.2/**: Automatically downloaded and extracted Osmosis tool with Mapsforge plugin.

## IGPSPORT Filename Structure

The generated map files follow a specific naming convention required by IGPSPORT devices:

### Format

```
[CC][RRRR][YYMMDD][GEOCODE].map
```

### Components

| Component | Length | Description | Example |
|-----------|--------|-------------|---------|
| **CC** | 2 chars | Country code | `BR`, `PL`, `US` |
| **RRRR** | 4 digits | Region/Product code | `0100`, `0200` |
| **YYMMDD** | 6 digits | Date (Year, Month, Day) | `250317` = March 17, 2025 |
| **GEOCODE** | 12 chars | Geographic boundary encoding | `2B83FO00N00E` |

### GEOCODE Breakdown (12 characters, Base36 encoding)

The GEOCODE consists of 4 parts, each 3 characters in Base36:

1. **MIN_LON** (XXX): Western boundary - minimum longitude as tile X coordinate at zoom 13
2. **MAX_LAT** (YYY): Northern boundary - maximum latitude as tile Y coordinate at zoom 13
3. **LON_SPAN** (WWW): Width in tiles - 1 (horizontal span)
4. **LAT_SPAN** (HHH): Height in tiles - 1 (vertical span)

![Tile Grid Concept](misc/tile-grid-concept.svg)

### Example

**Filename**: `BR01002303102B83FO00N00E.map`

- **BR**: Brazil
- **0100**: Region code 0100
- **230310**: March 10, 2023
- **2B8**: MIN_LON (tile X at zoom 13)
- **3FO**: MAX_LAT (tile Y at zoom 13)
- **00N**: LON_SPAN (width in tiles)
- **00E**: LAT_SPAN (height in tiles)

For a visual representation of the filename structure, see below:

![IGPSPORT Filename Structure](misc/filename-structure.svg)

## Viewing and Comparing Maps

### Cruiser - Map Viewer

[Cruiser](https://wiki.openstreetmap.org/wiki/Cruiser) is a cross-platform map viewer that supports Mapsforge map files, making it ideal for viewing and comparing the generated maps.

#### Features
- View `.map` files generated by this tool
- Compare different map versions
- Test maps before deploying to IGPSPORT devices
- Supports multiple map formats including Mapsforge

#### Download
Visit the [Cruiser Wiki page](https://wiki.openstreetmap.org/wiki/Cruiser) for download links and documentation.

#### Usage
1. Open Cruiser
2. Load your generated `.map` file from the `output/` directory
3. Compare with other map versions or sources

#### Comparison Example

Below is a comparison showing the difference between the original IGPSPORT map (left) and the enhanced map (right) with additional features and details:

![Map Comparison - Original vs Enhanced](misc/compare-2023-to-2026.jpg)

*Left: Original map (2023) | Right: Enhanced map (2026

## Troubleshooting

### Java Not Found
Ensure Java 17 or higher is installed:
```bash
java -version
```

### Out of Memory Errors
The scripts already choose heap size automatically. If you still run into memory problems, try one of these:

- Increase heap manually with `JAVA_XMX`
- Lower the thread count with `MAP_WRITER_THREADS=1`
- Force the disk-backed writer with `MAP_WRITER_TYPE=hd` only when you accept much heavier disk IO

Examples:

```powershell
$env:MAP_WRITER_THREADS = "1"
$env:JAVA_XMX = "24g"
.\script.ps1
```

```bash
MAP_WRITER_THREADS=1 JAVA_XMX=24g ./script.sh
```

To opt back into automatic HD retry:

```powershell
$env:MAP_ALLOW_HD_FALLBACK = "1"
.\script.ps1
```

```bash
MAP_ALLOW_HD_FALLBACK=1 ./script.sh
```

### Download Failures
- Check your internet connection
- Verify the URLs in `maps.csv` are accessible
- Some regions may have updated URLs on Geofabrik

### Permission Denied (Unix/Linux)
Make the script executable:
```bash
chmod +x script.sh
```

## Technical Details

### Processing Pipeline

1. **Read PBF** → Load OpenStreetMap binary data
2. **Apply Polygon** → Filter data to geographic boundary
3. **Tag Filter** → Remove unwanted features, keep roads, waterways, landuse
4. **Used Node** → Keep only referenced nodes
5. **Merge** → Combine filtered data
6. **Mapfile Writer** → Generate Mapsforge `.map` file
7. **Rename** → Calculate GEOCODE and apply IGPSPORT filename

### Map Features Included

The script filters OSM data to include:
- **Roads**: highways, paths, tracks (with tag transformation for unsupported types)
- **Waterways**: rivers, streams, canals, dams, drains
- **Natural features**: water bodies, coastlines

Set `MAP_TAG_PROFILE=igs630` to disable waterways and apply the iGS630 Mapsforge header compatibility patch for older iGS630 devices.

All other features (buildings, POIs, amenities, etc.) are filtered out to reduce file size and focus on navigation.

## Utilities

All utilities use only the Python standard library unless noted otherwise.

### CSV Generator (generate_maps_csv.py)

Automatically generates `maps.csv` from original iGPSport map files. The one-command package builder runs this for you; use this utility directly when you want to review or edit `maps.csv` before generating maps.

iGPSport map filenames encode the country, region, and geographic bounding box in a specific format. This script decodes that information and matches each region against the [Geofabrik region index](https://download.geofabrik.de/) (512 regions worldwide) to find the correct PBF and polygon download URLs. When one tile crosses several same-country Geofabrik subregions, it can emit a small multi-region blend instead of falling back to a whole-country extract.

```bash
# Generate maps.csv from a local input directory
uv run python generate_maps_csv.py input/

# Specify a custom output path
uv run python generate_maps_csv.py input/ -o my_maps.csv
```

### Official Map Downloader (download_igpsport_maps.py)

Lists or downloads official iGPSPORT map ZIPs from the public support API. This is useful when you need the original vendor `.map` files for a country/region before generating `maps.csv`.

```bash
uv run python download_igpsport_maps.py switzerland --list
uv run python download_igpsport_maps.py --countries
uv run python download_igpsport_maps.py --search swiss
uv run python download_igpsport_maps.py switzerland --download -o input
uv run python download_igpsport_maps.py switzerland --download --resume -o input
uv run python download_igpsport_maps.py aargau --download -o input/switzerland
```

You do not need to include the full hierarchy when a region name is unique: `switzerland` downloads all Swiss canton maps. Use `--countries` to list available country-level regions, or `--search <term>` to search region/map names. Use `--resume` to skip official ZIP downloads when a matching extracted `.map` already exists. By default, it targets the current BSC300/BSC300T/iGS630 map version ID used by the official product map page. If iGPSPORT publishes a new support URL later, pass its `mapVersionId` with `--map-version-id`.

### Map Packager (package_maps.py)

Packages generated maps for sharing. It matches generated output maps back to the original input maps by country code, product code, and geocode, so the generated OSM date may differ from the original vendor date.

```bash
uv run python package_maps.py input
uv run python package_maps.py input --label switzerland
uv run python package_maps.py input --package-prefix IGPSport-iGS630
uv run python package_maps.py input --name my-map-pack.zip
uv run python package_maps.py input --md5-cfg map_md5_list.cfg
```

The ZIP contains `README.txt`, `MANIFEST.txt`, and the matching generated `.map` files. For Switzerland, the default package name is `IGPSport300-800-Switzerland.zip`; with `MAP_TAG_PROFILE=igs630`, Greece becomes `IGPSport-iGS630-Greece.zip`. Use `--md5-cfg` for older iGS630 packages when you want to include an updated `map_md5_list.cfg` based on the actual generated map checksums.

### End-to-End Packager (build_map_package.py)

Runs the official map downloader, full map generator, and ZIP packager as one workflow.

```bash
uv run python build_map_package.py switzerland
uv run python build_map_package.py switzerland --dry-run
uv run python build_map_package.py switzerland --clean-work
uv run python build_map_package.py switzerland --package-prefix IGPSport-iGS630
uv run python build_map_package.py switzerland --name IGPSport300-800-Switzerland.zip
uv run python build_map_package.py switzerland --md5-cfg map_md5_list.cfg
```

Downloads are stored under `tmp/igpsport-official-<region>/input`, generated maps are written to `output/`, and the final ZIP is written to `packages/`. Rerunning the same command resumes both the official input download step and the generated map step, but generated maps are only skipped when their build metadata matches the current settings. Use `--clean-work` when you prefer to remove the downloaded official input maps after a successful package build.

If you do not know the exact region name, run `uv run python download_igpsport_maps.py --countries` or `uv run python download_igpsport_maps.py --search <term>` first.

### Experimental BiNavi Packager

BiNavi packages have a different structure from BSC300/iGS630 packages. They contain `Maps/` plus `Router/`, and some map files do not use the standard iGPSPORT tile filename format.

Use an official extracted BiNavi package as the template:

```bash
uv run python build_binavi_package.py tmp/test-binavi/IT00 --dry-run
uv run python build_binavi_package.py tmp/test-binavi/IT00
```

This runs the normal generator only for the one parseable main map in `Maps/`, then creates an experimental ZIP such as `IGPSport-BiNavi-Italy-Experimental.zip`. The package keeps official `Router/*.rtd`, contour maps, and overview maps unchanged, and replaces only the generated main country map.

Contour/elevation and routing files are not regenerated. Building those would require a separate DEM/contour and routing-data pipeline, which is not implemented here.

See [docs/binavi-backlog.md](docs/binavi-backlog.md) for the experimental BiNavi backlog, including DEM/contour maps, router files, and richer BiNavi tag mapping.

### Map Tag Extractor (extract_tags_map.py)

Inspects the generated `.map` files to show which OSM tags they contain. Useful for verifying that the tag configuration and transformations work as expected, or for comparing your generated maps against the originals.

```bash
uv run python extract_tags_map.py output/map.map            # single file
uv run python extract_tags_map.py backup/                    # all files in folder
uv run python extract_tags_map.py backup/ tags_output/       # with output folder
```

### Mapsforge Semantic Comparison (compare_mapsforge_maps.py)

Compares two generated `.map` files for baseline-vs-optimized equivalence. This is intended for checks such as normal generation vs future Osmium preclip generation. It does not require byte-for-byte equality; creation time, file size, `created_by`, and subfile byte offsets may differ, but visible Mapsforge semantics such as bbox, projection, tile size, zoom intervals, and tag dictionaries must match.

```bash
uv run python compare_mapsforge_maps.py output-baseline/CH010026060335Y1F00M0V4.map output-preclip/CH010026060335Y1F00M0V4.map
uv run python compare_mapsforge_maps.py --json output-baseline/map.map output-preclip/map.map
```

### PBF Tag Extractor (extract_tags_pbf.py)

Analyzes the raw OpenStreetMap source data (`.osm.pbf` files) **before** processing. This is a development tool for working on the tag configuration — it shows which OSM tags exist in the source data and how frequently they appear, helping you decide which tags to include or transform.

**Requires pyosmium** — install with `uv sync --extra pbf`.

```bash
uv run python extract_tags_pbf.py download/hessen-latest.osm.pbf              # display in terminal
uv run python extract_tags_pbf.py download/hessen-latest.osm.pbf -o tags.json -f json  # export to JSON
uv run python extract_tags_pbf.py download/ -o output/ -f csv -m 10           # folder, CSV, min 10 occurrences
```

Options: `-o` output path, `-f` format (text/json/csv), `-m` min occurrence count, `-d` max display count.

## License

This project is licensed under the **Apache License 2.0** - see the [LICENSE](LICENSE) file for details.

### Dependencies and Data
- **Osmosis**: LGPL ([GitHub](https://github.com/openstreetmap/osmosis))
- **Mapsforge**: LGPL ([GitHub](https://github.com/mapsforge/mapsforge))
- **OpenStreetMap Data**: ODbL ([License](https://www.openstreetmap.org/copyright))

Generated maps are derived from OpenStreetMap data. If you distribute them, include the attribution and sharing notes described in [ATTRIBUTION.md](ATTRIBUTION.md).

## References

- [Reddit thread](https://www.reddit.com/r/cycling/comments/1khm2ou/newcustom_maps_on_igpsport_bsc300t_630s) shared by [u/povlhp](https://www.reddit.com/user/povlhp/)
- [Original project](https://github.com/tm-cms/MapsforgeMapName) by [tm-cms](https://github.com/tm-cms)
- [OpenStreetMap](https://www.openstreetmap.org/)
- [OpenStreetMap France](https://download.openstreetmap.fr/) - Polygon files
- [Geofabrik Downloads](https://download.geofabrik.de/) - OSM PBF files
- [Osmosis Documentation](https://wiki.openstreetmap.org/wiki/Osmosis)
- [Mapsforge](https://github.com/mapsforge/mapsforge)
- [Cruiser Map Viewer](https://wiki.openstreetmap.org/wiki/Cruiser)
