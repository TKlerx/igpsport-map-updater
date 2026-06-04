#!/usr/bin/env python3
"""
Script to extract tags from Mapsforge .map files
"""

import os
import struct
import sys
from pathlib import Path


class MapFileReader:
    """Reader for Mapsforge .map files"""
    
    MAGIC_BYTE = b"mapsforge binary OSM"
    
    def __init__(self, filepath):
        self.filepath = Path(filepath)
        self.tags = []
        
    def read_variable_byte(self, f):
        """Read a variable-length byte-encoded integer"""
        result = 0
        shift = 0
        while True:
            byte = f.read(1)
            if not byte:
                return None
            b = byte[0]
            result |= (b & 0x7F) << shift
            if (b & 0x80) == 0:
                break
            shift += 7
        return result
    
    def read_utf8_string(self, f):
        """Read a UTF-8 encoded string"""
        length = self.read_variable_byte(f)
        if length is None or length == 0:
            return ""
        string_bytes = f.read(length)
        return string_bytes.decode('utf-8', errors='ignore')
    
    def extract_tags(self, verbose=True):
        """Extract tags from the .map file"""
        try:
            with open(self.filepath, 'rb') as f:
                # Read and verify magic byte
                magic = f.read(len(self.MAGIC_BYTE))
                if magic != self.MAGIC_BYTE:
                    print(f"Error: Not a valid Mapsforge .map file")
                    return False
                
                # Read header size
                header_size = struct.unpack('>I', f.read(4))[0]
                
                # Read file version
                file_version = struct.unpack('>I', f.read(4))[0]
                if verbose:
                    print(f"Map file version: {file_version}")
                
                # Read file size
                file_size = struct.unpack('>Q', f.read(8))[0]
                if verbose:
                    print(f"File size: {file_size} bytes")
                
                # Read creation date
                date_created = struct.unpack('>Q', f.read(8))[0]
                if verbose:
                    print(f"Date created (timestamp): {date_created}")
                
                # Read bounding box
                min_lat = struct.unpack('>i', f.read(4))[0] / 1000000.0
                min_lon = struct.unpack('>i', f.read(4))[0] / 1000000.0
                max_lat = struct.unpack('>i', f.read(4))[0] / 1000000.0
                max_lon = struct.unpack('>i', f.read(4))[0] / 1000000.0
                if verbose:
                    print(f"Bounding box: ({min_lat}, {min_lon}) to ({max_lat}, {max_lon})")
                
                # Read tile size
                tile_size = struct.unpack('>H', f.read(2))[0]
                if verbose:
                    print(f"Tile size: {tile_size}")
                
                # Read projection
                projection = self.read_utf8_string(f)
                if verbose:
                    print(f"Projection: {projection}")
                
                # Read flags
                flags = f.read(1)[0]
                has_debug_info = bool(flags & 0x80)
                has_map_start_position = bool(flags & 0x40)
                has_start_zoom = bool(flags & 0x20)
                has_language_preference = bool(flags & 0x10)
                has_comment = bool(flags & 0x08)
                has_created_by = bool(flags & 0x04)
                
                if verbose:
                    print(f"\nFlags:")
                    print(f"  Debug info: {has_debug_info}")
                    print(f"  Map start position: {has_map_start_position}")
                    print(f"  Start zoom: {has_start_zoom}")
                    print(f"  Language preference: {has_language_preference}")
                    print(f"  Comment: {has_comment}")
                    print(f"  Created by: {has_created_by}")
                
                # Read optional fields
                if has_map_start_position:
                    start_lat = struct.unpack('>i', f.read(4))[0] / 1000000.0
                    start_lon = struct.unpack('>i', f.read(4))[0] / 1000000.0
                    if verbose:
                        print(f"\nStart position: ({start_lat}, {start_lon})")
                
                if has_start_zoom:
                    start_zoom = f.read(1)[0]
                    if verbose:
                        print(f"Start zoom level: {start_zoom}")
                
                if has_language_preference:
                    language = self.read_utf8_string(f)
                    if verbose:
                        print(f"Language preference: {language}")
                
                if has_comment:
                    comment = self.read_utf8_string(f)
                    if verbose:
                        print(f"Comment: {comment}")
                
                if has_created_by:
                    created_by = self.read_utf8_string(f)
                    if verbose:
                        print(f"Created by: {created_by}")
                
                # Read POI tags
                num_poi_tags = struct.unpack('>H', f.read(2))[0]
                if verbose:
                    print(f"\n=== POI Tags ({num_poi_tags}) ===")
                poi_tags = []
                for i in range(num_poi_tags):
                    tag = self.read_utf8_string(f)
                    poi_tags.append(tag)
                    if verbose:
                        print(f"{i}: {tag}")
                
                # Read Way tags
                num_way_tags = struct.unpack('>H', f.read(2))[0]
                if verbose:
                    print(f"\n=== Way Tags ({num_way_tags}) ===")
                way_tags = []
                for i in range(num_way_tags):
                    tag = self.read_utf8_string(f)
                    way_tags.append(tag)
                    if verbose:
                        print(f"{i}: {tag}")
                
                # Read number of subfiles/zoom intervals
                num_zoom_intervals = f.read(1)[0]
                if verbose:
                    print(f"\n=== Zoom Level Information ===")
                    print(f"Number of zoom intervals: {num_zoom_intervals}")
                
                zoom_intervals = []
                for i in range(num_zoom_intervals):
                    base_zoom = f.read(1)[0]
                    min_zoom = f.read(1)[0]
                    max_zoom = f.read(1)[0]
                    subfile_start = struct.unpack('>Q', f.read(8))[0]
                    subfile_size = struct.unpack('>Q', f.read(8))[0]
                    
                    zoom_intervals.append({
                        'base_zoom': base_zoom,
                        'min_zoom': min_zoom,
                        'max_zoom': max_zoom,
                        'subfile_start': subfile_start,
                        'subfile_size': subfile_size
                    })
                    
                    if verbose:
                        print(f"  Interval {i}:")
                        print(f"    Base zoom: {base_zoom}")
                        print(f"    Zoom range: {min_zoom} - {max_zoom}")
                        print(f"    Subfile start: {subfile_start}")
                        print(f"    Subfile size: {subfile_size} bytes")
                
                self.tags = {
                    'poi_tags': poi_tags,
                    'way_tags': way_tags,
                    'zoom_intervals': zoom_intervals
                }
                
                return True
                
        except Exception as e:
            print(f"Error reading map file: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def export_tags_to_file(self, output_file):
        """Export tags to a text file"""
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write("=== POI Tags ===\n")
                for i, tag in enumerate(self.tags.get('poi_tags', [])):
                    f.write(f"{i}: {tag}\n")
                
                f.write("\n=== Way Tags ===\n")
                for i, tag in enumerate(self.tags.get('way_tags', [])):
                    f.write(f"{i}: {tag}\n")
            
            print(f"\nTags exported to: {output_file}")
            return True
        except Exception as e:
            print(f"Error exporting tags: {e}")
            return False


def process_single_file(map_file, output_file=None):
    """Process a single map file"""
    print(f"Reading map file: {map_file}\n")
    reader = MapFileReader(map_file)
    
    if reader.extract_tags():
        print("\n✓ Tags extracted successfully")
        
        if output_file:
            reader.export_tags_to_file(output_file)
        return True
    else:
        print("\n✗ Failed to extract tags")
        return False


def process_folder(folder_path, output_folder=None):
    """Process all .map files in a folder"""
    folder = Path(folder_path)
    
    if not folder.exists():
        print(f"Error: Folder '{folder_path}' not found")
        return False
    
    if not folder.is_dir():
        print(f"Error: '{folder_path}' is not a directory")
        return False
    
    # Find all .map files
    map_files = sorted(folder.glob("*.map"))
    
    if not map_files:
        print(f"No .map files found in '{folder_path}'")
        return False
    
    print(f"Found {len(map_files)} .map files in '{folder_path}'\n")
    print("=" * 80)
    
    # Prepare output folder if specified
    if output_folder:
        output_path = Path(output_folder)
        output_path.mkdir(parents=True, exist_ok=True)
    
    success_count = 0
    failed_files = []
    all_poi_tags = set()
    all_way_tags = set()
    
    for i, map_file in enumerate(map_files, 1):
        print(f"\n[{i}/{len(map_files)}] Processing: {map_file.name}")
        print("=" * 80)
        
        reader = MapFileReader(map_file)
        
        try:
            if reader.extract_tags(verbose=True):
                success_count += 1
                
                # Collect all unique tags
                all_poi_tags.update(reader.tags.get('poi_tags', []))
                all_way_tags.update(reader.tags.get('way_tags', []))
                
                # Export to individual file if output folder specified
                if output_folder:
                    output_file = output_path / f"{map_file.stem}_tags.txt"
                    reader.export_tags_to_file(output_file)
            else:
                failed_files.append(map_file.name)
        except Exception as e:
            print(f"Error processing {map_file.name}: {e}")
            failed_files.append(map_file.name)
        
        print("-" * 80)
    
    # Summary
    print(f"\n{'=' * 80}")
    print(f"SUMMARY:")
    print(f"  Total files: {len(map_files)}")
    print(f"  Successful: {success_count}")
    print(f"  Failed: {len(failed_files)}")
    
    if failed_files:
        print(f"\nFailed files:")
        for fname in failed_files:
            print(f"  - {fname}")
    
    # Display consolidated tags
    print(f"\n{'=' * 80}")
    print("CONSOLIDATED TAGS FROM ALL MAPS")
    print("=" * 80)
    
    sorted_poi_tags = sorted(all_poi_tags)
    sorted_way_tags = sorted(all_way_tags)
    
    print(f"\n=== All Unique POI Tags ({len(sorted_poi_tags)}) ===")
    for i, tag in enumerate(sorted_poi_tags):
        print(f"{i}: {tag}")
    
    print(f"\n=== All Unique Way Tags ({len(sorted_way_tags)}) ===")
    for i, tag in enumerate(sorted_way_tags):
        print(f"{i}: {tag}")
    
    # Export consolidated tags if output folder specified
    if output_folder:
        consolidated_file = output_path / "all_tags_consolidated.txt"
        try:
            with open(consolidated_file, 'w', encoding='utf-8') as f:
                f.write(f"Consolidated tags from {success_count} map files\n")
                f.write(f"Generated from: {folder_path}\n\n")
                
                f.write(f"=== All Unique POI Tags ({len(sorted_poi_tags)}) ===\n")
                for i, tag in enumerate(sorted_poi_tags):
                    f.write(f"{i}: {tag}\n")
                
                f.write(f"\n=== All Unique Way Tags ({len(sorted_way_tags)}) ===\n")
                for i, tag in enumerate(sorted_way_tags):
                    f.write(f"{i}: {tag}\n")
            
            print(f"\nConsolidated tags exported to: {consolidated_file}")
        except Exception as e:
            print(f"Error exporting consolidated tags: {e}")
    
    return len(failed_files) == 0


def main():
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python extract_tags.py <map_file.map> [output_file.txt]")
        print("  python extract_tags.py <folder> [output_folder]")
        print("\nExamples:")
        print("  # Single file")
        print("  python extract_tags.py output/map.map")
        print("  python extract_tags.py output/map.map tags.txt")
        print("\n  # Process all files in folder")
        print("  python extract_tags.py backup/")
        print("  python extract_tags.py backup/ tags_output/")
        sys.exit(1)
    
    input_path = sys.argv[1]
    output_path = sys.argv[2] if len(sys.argv) > 2 else None
    
    path = Path(input_path)
    
    if not path.exists():
        print(f"Error: Path '{input_path}' not found")
        sys.exit(1)
    
    # Check if it's a directory or file
    if path.is_dir():
        # Process folder
        success = process_folder(input_path, output_path)
        sys.exit(0 if success else 1)
    else:
        # Process single file
        success = process_single_file(input_path, output_path)
        sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
