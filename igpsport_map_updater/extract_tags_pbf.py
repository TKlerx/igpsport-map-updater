#!/usr/bin/env python3
"""
Script to extract tags from OSM .pbf files
"""

import json
import subprocess
import sys
from collections import Counter, defaultdict
from pathlib import Path


class PBFTagExtractor:
    """Extract tags from OSM PBF files using osmium"""
    
    def __init__(self, filepath):
        self.filepath = Path(filepath)
        self.node_tags = Counter()
        self.way_tags = Counter()
        self.relation_tags = Counter()
        
    def check_osmium_installed(self):
        """Check if osmium-tool is installed"""
        try:
            result = subprocess.run(['osmium', '--version'], 
                                  capture_output=True, text=True)
            return result.returncode == 0
        except FileNotFoundError:
            return False
    
    def extract_tags_with_osmium(self, verbose=True):
        """Extract tags using osmium tags-filter"""
        try:
            if not self.check_osmium_installed():
                print("Error: osmium-tool is not installed.")
                print("Install it with:")
                print("  Ubuntu/Debian: sudo apt-get install osmium-tool")
                print("  Fedora: sudo dnf install osmium-tool")
                print("  macOS: brew install osmium-tool")
                return False
            
            if verbose:
                print(f"Extracting tags from: {self.filepath}")
                print("This may take a while depending on file size...\n")
            
            # Use osmium tags-filter to get all tags
            cmd = [
                'osmium', 'tags-filter',
                str(self.filepath),
                '-o', '-',
                '-f', 'opl'
            ]
            
            if verbose:
                print("Running osmium to extract tags...")
            
            # Run osmium and capture output
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=3600)
            
            if result.returncode != 0:
                print(f"Error running osmium: {result.stderr}")
                return False
            
            # Parse output
            if verbose:
                print("Parsing tags from output...")
            
            for line in result.stdout.split('\n'):
                if not line.strip():
                    continue
                
                parts = line.split(' ')
                if len(parts) < 2:
                    continue
                
                elem_type = parts[0][0]  # n=node, w=way, r=relation
                
                # Extract tags (format: Tkey=value)
                for part in parts:
                    if part.startswith('T'):
                        tag = part[1:]  # Remove 'T' prefix
                        if '=' in tag:
                            key, value = tag.split('=', 1)
                            tag_str = f"{key}={value}"
                            
                            if elem_type == 'n':
                                self.node_tags[tag_str] += 1
                            elif elem_type == 'w':
                                self.way_tags[tag_str] += 1
                            elif elem_type == 'r':
                                self.relation_tags[tag_str] += 1
            
            if verbose:
                print(f"\n✓ Tags extracted successfully")
                print(f"  Node tags: {len(self.node_tags)} unique tags")
                print(f"  Way tags: {len(self.way_tags)} unique tags")
                print(f"  Relation tags: {len(self.relation_tags)} unique tags")
            
            return True
            
        except subprocess.TimeoutExpired:
            print("Error: Processing timeout (> 1 hour)")
            return False
        except Exception as e:
            print(f"Error extracting tags: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def extract_tags_with_pyosmium(self, verbose=True):
        """Extract tags using pyosmium library"""
        try:
            import osmium
        except ImportError:
            print("Error: pyosmium is not installed.")
            print("Install it with: pip install osmium")
            return False
        
        class TagHandler(osmium.SimpleHandler):
            def __init__(self):
                osmium.SimpleHandler.__init__(self)
                self.node_tags = Counter()
                self.way_tags = Counter()
                self.relation_tags = Counter()
                self.node_count = 0
                self.way_count = 0
                self.relation_count = 0
            
            def node(self, n):
                self.node_count += 1
                for tag in n.tags:
                    tag_str = f"{tag.k}={tag.v}"
                    self.node_tags[tag_str] += 1
            
            def way(self, w):
                self.way_count += 1
                for tag in w.tags:
                    tag_str = f"{tag.k}={tag.v}"
                    self.way_tags[tag_str] += 1
            
            def relation(self, r):
                self.relation_count += 1
                for tag in r.tags:
                    tag_str = f"{tag.k}={tag.v}"
                    self.relation_tags[tag_str] += 1
        
        if verbose:
            print(f"Extracting tags from: {self.filepath}")
            print("This may take a while depending on file size...\n")
        
        handler = TagHandler()
        handler.apply_file(str(self.filepath), locations=False)
        
        self.node_tags = handler.node_tags
        self.way_tags = handler.way_tags
        self.relation_tags = handler.relation_tags
        
        if verbose:
            print(f"\n✓ Tags extracted successfully")
            print(f"  Processed {handler.node_count:,} nodes")
            print(f"  Processed {handler.way_count:,} ways")
            print(f"  Processed {handler.relation_count:,} relations")
            print(f"\n  Unique node tags: {len(self.node_tags)}")
            print(f"  Unique way tags: {len(self.way_tags)}")
            print(f"  Unique relation tags: {len(self.relation_tags)}")
        
        return True
    
    def extract_tags(self, verbose=True, use_osmium=None):
        """
        Extract tags from PBF file
        
        Args:
            verbose: Print progress information
            use_osmium: Force use of osmium-tool (True) or pyosmium (False). 
                       If None, try pyosmium first, then osmium-tool
        """
        if use_osmium is None:
            # Try pyosmium first (faster and more detailed)
            try:
                return self.extract_tags_with_pyosmium(verbose)
            except Exception as e:
                if verbose:
                    print(f"pyosmium not available, trying osmium-tool...")
                return self.extract_tags_with_osmium(verbose)
        elif use_osmium:
            return self.extract_tags_with_osmium(verbose)
        else:
            return self.extract_tags_with_pyosmium(verbose)
    
    def display_tags(self, max_display=50, min_count=1):
        """Display extracted tags"""
        print("\n" + "=" * 80)
        print(f"=== NODE TAGS ({len(self.node_tags)} unique) ===")
        print("=" * 80)
        
        for i, (tag, count) in enumerate(self.node_tags.most_common(max_display)):
            if count < min_count:
                break
            print(f"{i:4d}. {tag:50s} ({count:,} occurrences)")
        
        if len(self.node_tags) > max_display:
            print(f"\n... and {len(self.node_tags) - max_display} more tags")
        
        print("\n" + "=" * 80)
        print(f"=== WAY TAGS ({len(self.way_tags)} unique) ===")
        print("=" * 80)
        
        for i, (tag, count) in enumerate(self.way_tags.most_common(max_display)):
            if count < min_count:
                break
            print(f"{i:4d}. {tag:50s} ({count:,} occurrences)")
        
        if len(self.way_tags) > max_display:
            print(f"\n... and {len(self.way_tags) - max_display} more tags")
        
        print("\n" + "=" * 80)
        print(f"=== RELATION TAGS ({len(self.relation_tags)} unique) ===")
        print("=" * 80)
        
        for i, (tag, count) in enumerate(self.relation_tags.most_common(max_display)):
            if count < min_count:
                break
            print(f"{i:4d}. {tag:50s} ({count:,} occurrences)")
        
        if len(self.relation_tags) > max_display:
            print(f"\n... and {len(self.relation_tags) - max_display} more tags")
    
    def export_tags_to_file(self, output_file, format='text', min_count=1):
        """
        Export tags to a file
        
        Args:
            output_file: Output file path
            format: Output format ('text', 'json', 'csv')
            min_count: Minimum occurrence count to include
        """
        output_path = Path(output_file)
        
        try:
            if format == 'json':
                self._export_json(output_path, min_count)
            elif format == 'csv':
                self._export_csv(output_path, min_count)
            else:
                self._export_text(output_path, min_count)
            
            print(f"\n✓ Tags exported to: {output_file}")
            return True
        except Exception as e:
            print(f"Error exporting tags: {e}")
            return False
    
    def _export_text(self, output_path, min_count):
        """Export as text file"""
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(f"Tags extracted from: {self.filepath.name}\n")
            f.write(f"Minimum occurrence count: {min_count}\n\n")
            
            f.write(f"=== NODE TAGS ({len(self.node_tags)} unique) ===\n")
            for i, (tag, count) in enumerate(self.node_tags.most_common()):
                if count < min_count:
                    break
                f.write(f"{i:4d}. {tag:50s} ({count:,})\n")
            
            f.write(f"\n=== WAY TAGS ({len(self.way_tags)} unique) ===\n")
            for i, (tag, count) in enumerate(self.way_tags.most_common()):
                if count < min_count:
                    break
                f.write(f"{i:4d}. {tag:50s} ({count:,})\n")
            
            f.write(f"\n=== RELATION TAGS ({len(self.relation_tags)} unique) ===\n")
            for i, (tag, count) in enumerate(self.relation_tags.most_common()):
                if count < min_count:
                    break
                f.write(f"{i:4d}. {tag:50s} ({count:,})\n")
    
    def _export_json(self, output_path, min_count):
        """Export as JSON file"""
        data = {
            'source_file': str(self.filepath.name),
            'min_count': min_count,
            'node_tags': {tag: count for tag, count in self.node_tags.items() if count >= min_count},
            'way_tags': {tag: count for tag, count in self.way_tags.items() if count >= min_count},
            'relation_tags': {tag: count for tag, count in self.relation_tags.items() if count >= min_count},
        }
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    
    def _export_csv(self, output_path, min_count):
        """Export as CSV file"""
        import csv
        
        with open(output_path, 'w', encoding='utf-8', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['Element Type', 'Tag', 'Count'])
            
            for tag, count in self.node_tags.most_common():
                if count < min_count:
                    break
                writer.writerow(['node', tag, count])
            
            for tag, count in self.way_tags.most_common():
                if count < min_count:
                    break
                writer.writerow(['way', tag, count])
            
            for tag, count in self.relation_tags.most_common():
                if count < min_count:
                    break
                writer.writerow(['relation', tag, count])


def process_single_file(pbf_file, output_file=None, format='text', max_display=50, min_count=1):
    """Process a single PBF file"""
    print(f"Processing PBF file: {pbf_file}\n")
    
    extractor = PBFTagExtractor(pbf_file)
    
    if not extractor.extract_tags():
        print("\n✗ Failed to extract tags")
        return False
    
    extractor.display_tags(max_display=max_display, min_count=min_count)
    
    if output_file:
        extractor.export_tags_to_file(output_file, format=format, min_count=min_count)
    
    return True


def process_folder(folder_path, output_folder=None, format='text', max_display=50, min_count=1):
    """Process all .pbf files in a folder"""
    folder = Path(folder_path)
    
    if not folder.exists():
        print(f"Error: Folder '{folder_path}' not found")
        return False
    
    if not folder.is_dir():
        print(f"Error: '{folder_path}' is not a directory")
        return False
    
    # Find all .pbf files
    pbf_files = sorted(folder.glob("*.pbf")) + sorted(folder.glob("*.osm.pbf"))
    
    if not pbf_files:
        print(f"No .pbf files found in '{folder_path}'")
        return False
    
    print(f"Found {len(pbf_files)} .pbf files in '{folder_path}'\n")
    print("=" * 80)
    
    # Prepare output folder if specified
    if output_folder:
        output_path = Path(output_folder)
        output_path.mkdir(parents=True, exist_ok=True)
    
    success_count = 0
    failed_files = []
    all_node_tags = Counter()
    all_way_tags = Counter()
    all_relation_tags = Counter()
    
    for i, pbf_file in enumerate(pbf_files, 1):
        print(f"\n[{i}/{len(pbf_files)}] Processing: {pbf_file.name}")
        print("=" * 80)
        
        extractor = PBFTagExtractor(pbf_file)
        
        try:
            if extractor.extract_tags(verbose=True):
                success_count += 1
                
                # Accumulate all tags
                all_node_tags.update(extractor.node_tags)
                all_way_tags.update(extractor.way_tags)
                all_relation_tags.update(extractor.relation_tags)
                
                # Display tags
                extractor.display_tags(max_display=max_display, min_count=min_count)
                
                # Export to individual file if output folder specified
                if output_folder:
                    output_file = output_path / f"{pbf_file.stem}_tags.{format if format != 'text' else 'txt'}"
                    extractor.export_tags_to_file(output_file, format=format, min_count=min_count)
            else:
                failed_files.append(pbf_file.name)
        except Exception as e:
            print(f"Error processing {pbf_file.name}: {e}")
            import traceback
            traceback.print_exc()
            failed_files.append(pbf_file.name)
        
        print("-" * 80)
    
    # Summary
    print(f"\n{'=' * 80}")
    print(f"SUMMARY:")
    print(f"  Total files: {len(pbf_files)}")
    print(f"  Successful: {success_count}")
    print(f"  Failed: {len(failed_files)}")
    
    if failed_files:
        print(f"\nFailed files:")
        for fname in failed_files:
            print(f"  - {fname}")
    
    # Display consolidated tags
    print(f"\n{'=' * 80}")
    print("CONSOLIDATED TAGS FROM ALL FILES")
    print("=" * 80)
    
    print(f"\n=== Node Tags ({len(all_node_tags)} unique) ===")
    for i, (tag, count) in enumerate(all_node_tags.most_common(max_display)):
        if count < min_count:
            break
        print(f"{i:4d}. {tag:50s} ({count:,})")
    
    print(f"\n=== Way Tags ({len(all_way_tags)} unique) ===")
    for i, (tag, count) in enumerate(all_way_tags.most_common(max_display)):
        if count < min_count:
            break
        print(f"{i:4d}. {tag:50s} ({count:,})")
    
    print(f"\n=== Relation Tags ({len(all_relation_tags)} unique) ===")
    for i, (tag, count) in enumerate(all_relation_tags.most_common(max_display)):
        if count < min_count:
            break
        print(f"{i:4d}. {tag:50s} ({count:,})")
    
    # Export consolidated tags if output folder specified
    if output_folder:
        consolidated_file = output_path / f"all_tags_consolidated.{format if format != 'text' else 'txt'}"
        try:
            # Create temporary extractor for export
            temp_extractor = PBFTagExtractor(folder)
            temp_extractor.node_tags = all_node_tags
            temp_extractor.way_tags = all_way_tags
            temp_extractor.relation_tags = all_relation_tags
            
            temp_extractor.export_tags_to_file(consolidated_file, format=format, min_count=min_count)
        except Exception as e:
            print(f"Error exporting consolidated tags: {e}")
    
    return len(failed_files) == 0


def main():
    if len(sys.argv) < 2:
        print("OSM PBF Tag Extractor")
        print("=" * 80)
        print("\nUsage:")
        print("  python extract_tags_pbf.py <file.pbf> [options]")
        print("  python extract_tags_pbf.py <folder> [options]")
        print("\nOptions:")
        print("  -o, --output <file/folder>  Output file or folder for extracted tags")
        print("  -f, --format <format>       Output format: text (default), json, csv")
        print("  -m, --min-count <n>         Minimum occurrence count to include (default: 1)")
        print("  -d, --display <n>           Maximum tags to display (default: 50)")
        print("\nExamples:")
        print("  # Single file")
        print("  python extract_tags_pbf.py download/brazil-latest.osm.pbf")
        print("  python extract_tags_pbf.py download/sao-paulo.pbf -o tags.txt")
        print("  python extract_tags_pbf.py download/sao-paulo.pbf -o tags.json -f json")
        print("\n  # Process all files in folder")
        print("  python extract_tags_pbf.py download/")
        print("  python extract_tags_pbf.py download/ -o output_tags/")
        print("  python extract_tags_pbf.py download/ -o output/ -f json -m 10")
        print("\nRequirements:")
        print("  - pyosmium: pip install osmium")
        print("  - OR osmium-tool: apt install osmium-tool (Ubuntu/Debian)")
        sys.exit(1)
    
    # Parse arguments
    input_path = sys.argv[1]
    output_path = None
    format_type = 'text'
    min_count = 1
    max_display = 50
    
    i = 2
    while i < len(sys.argv):
        arg = sys.argv[i]
        
        if arg in ['-o', '--output'] and i + 1 < len(sys.argv):
            output_path = sys.argv[i + 1]
            i += 2
        elif arg in ['-f', '--format'] and i + 1 < len(sys.argv):
            format_type = sys.argv[i + 1]
            if format_type not in ['text', 'json', 'csv']:
                print(f"Error: Invalid format '{format_type}'. Use: text, json, or csv")
                sys.exit(1)
            i += 2
        elif arg in ['-m', '--min-count'] and i + 1 < len(sys.argv):
            try:
                min_count = int(sys.argv[i + 1])
            except ValueError:
                print(f"Error: Invalid min-count value '{sys.argv[i + 1]}'")
                sys.exit(1)
            i += 2
        elif arg in ['-d', '--display'] and i + 1 < len(sys.argv):
            try:
                max_display = int(sys.argv[i + 1])
            except ValueError:
                print(f"Error: Invalid display value '{sys.argv[i + 1]}'")
                sys.exit(1)
            i += 2
        else:
            print(f"Error: Unknown argument '{arg}'")
            sys.exit(1)
    
    path = Path(input_path)
    
    if not path.exists():
        print(f"Error: Path '{input_path}' not found")
        sys.exit(1)
    
    # Check if it's a directory or file
    if path.is_dir():
        # Process folder
        success = process_folder(input_path, output_path, format_type, max_display, min_count)
        sys.exit(0 if success else 1)
    else:
        # Process single file
        success = process_single_file(input_path, output_path, format_type, max_display, min_count)
        sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
