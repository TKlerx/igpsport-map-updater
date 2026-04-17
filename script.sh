#!/bin/bash

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Download and extract osmosis if not present
OSMOSIS_VERSION="0.49.2"
OSMOSIS_DIR="$SCRIPT_DIR/osmosis-$OSMOSIS_VERSION"

if [ ! -d "$OSMOSIS_DIR" ]; then
    echo "Osmosis not found. Downloading osmosis-$OSMOSIS_VERSION..."
    OSMOSIS_URL="https://github.com/openstreetmap/osmosis/releases/download/$OSMOSIS_VERSION/osmosis-$OSMOSIS_VERSION.zip"
    OSMOSIS_ZIP="$SCRIPT_DIR/osmosis-$OSMOSIS_VERSION.zip"
    
    curl -sL -o "$OSMOSIS_ZIP" "$OSMOSIS_URL"
    
    echo "Extracting osmosis..."
    unzip -q "$OSMOSIS_ZIP" -d "$SCRIPT_DIR"
    
    echo "Cleaning up..."
    rm "$OSMOSIS_ZIP"
    
    # Make osmosis executable
    chmod +x "$OSMOSIS_DIR/bin/osmosis"
    
    echo "Osmosis $OSMOSIS_VERSION installed successfully."
    echo ""
fi

# Download and install Mapsforge writer plugin if not present
MAPSFORGE_WRITER_VERSION="0.27.0"
MAPSFORGE_WRITER_JAR="$OSMOSIS_DIR/lib/mapsforge-map-writer-${MAPSFORGE_WRITER_VERSION}-jar-with-dependencies.jar"

if [ ! -f "$MAPSFORGE_WRITER_JAR" ]; then
    echo "Mapsforge writer plugin not found. Downloading version $MAPSFORGE_WRITER_VERSION..."
    MAPSFORGE_URL="https://github.com/mapsforge/mapsforge/releases/download/${MAPSFORGE_WRITER_VERSION}/mapsforge-map-writer-${MAPSFORGE_WRITER_VERSION}-jar-with-dependencies.jar"
    
    curl -sL -o "$MAPSFORGE_WRITER_JAR" "$MAPSFORGE_URL"
    
    echo "Mapsforge writer plugin installed successfully."
    echo ""
fi

# Create wrapper script that includes Mapsforge in classpath
OSMOSIS_WRAPPER="$OSMOSIS_DIR/bin/osmosis-with-mapsforge"
if [ ! -f "$OSMOSIS_WRAPPER" ]; then
    # Modify the osmosis script to include Mapsforge in CLASSPATH
    MAPSFORGE_JAR_NAME="mapsforge-map-writer-${MAPSFORGE_WRITER_VERSION}-jar-with-dependencies.jar"
    cp "$OSMOSIS_DIR/bin/osmosis" "$OSMOSIS_WRAPPER"
    
    # Add Mapsforge JAR to the CLASSPATH line in the wrapper
    sed -i "s|^CLASSPATH=\$APP_HOME|CLASSPATH=\$APP_HOME/lib/$MAPSFORGE_JAR_NAME:\$APP_HOME|" "$OSMOSIS_WRAPPER"
    
    chmod +x "$OSMOSIS_WRAPPER"
fi

TAG_CONF_FILE="$SCRIPT_DIR/tag-igpsport.xml"
TAG_TRANSFORM_FILE="$SCRIPT_DIR/tag-igpsport-transform.xml"
THREADS="${MAP_WRITER_THREADS:-}"
MAP_WRITER_TYPE="${MAP_WRITER_TYPE:-auto}"
TMP_DIR="${JAVA_TMP_DIR:-$SCRIPT_DIR/tmp}"
JAVA_XMS="${JAVA_XMS:-}"
JAVA_XMX="${JAVA_XMX:-}"
export CLASSPATH="$OSMOSIS_DIR/lib/mapsforge-map-writer-${MAPSFORGE_WRITER_VERSION}-jar-with-dependencies.jar:$CLASSPATH"

# Create directories
DOWNLOAD_DIR="$SCRIPT_DIR/download"
OUTPUT_DIR="$SCRIPT_DIR/output"

mkdir -p "$TMP_DIR"
mkdir -p "$DOWNLOAD_DIR"
mkdir -p "$OUTPUT_DIR"

# Check if maps.csv exists
CSV_FILE="$SCRIPT_DIR/maps.csv"
if [ ! -f "$CSV_FILE" ]; then
    echo "ERROR: maps.csv not found in directory: $SCRIPT_DIR" >&2
    exit 1
fi

# Read CSV file and download files
echo "Reading maps.csv..."
declare -a PBF_FILES=()
declare -a POLY_FILES=()
declare -a ORIGINAL_NAMES=()

line_num=0
while IFS=',' read -r original_name pbf_url poly_url; do
    line_num=$((line_num + 1))
    
    # Skip header line
    if [ $line_num -eq 1 ]; then
        continue
    fi
    
    # Skip empty lines
    if [ -z "$original_name" ]; then
        continue
    fi
    
    echo ""
    echo "Processing entry: $original_name"
    
    # Download PBF file
    pbf_filename=$(basename "$pbf_url")
    pbf_path="$DOWNLOAD_DIR/$pbf_filename"
    
    if [ ! -f "$pbf_path" ]; then
        echo "  Downloading PBF: $pbf_filename..."
        curl -sL -o "$pbf_path" "$pbf_url"
        echo "  PBF downloaded."
    else
        echo "  PBF already exists: $pbf_filename"
    fi
    
    # Download Poly file
    poly_filename=$(basename "$poly_url")
    poly_path="$DOWNLOAD_DIR/$poly_filename"
    
    if [ ! -f "$poly_path" ]; then
        echo "  Downloading Poly: $poly_filename..."
        curl -sL -o "$poly_path" "$poly_url"
        echo "  Poly downloaded."
    else
        echo "  Poly already exists: $poly_filename"
    fi
    
    PBF_FILES+=("$pbf_path")
    POLY_FILES+=("$poly_path")
    ORIGINAL_NAMES+=("$original_name")
    
done < "$CSV_FILE"

if [ ${#PBF_FILES[@]} -eq 0 ]; then
    echo "ERROR: No entries found in maps.csv" >&2
    exit 1
fi

echo ""
echo "=========================================="
echo "Found ${#PBF_FILES[@]} entries to process"
echo "=========================================="
echo ""
echo "Mapsforge configuration:"
echo "  Writer Type:  $MAP_WRITER_TYPE"
echo "  Threads:      ${THREADS:-auto}"
if [ -n "$JAVA_XMS" ] || [ -n "$JAVA_XMX" ]; then
    echo "  Java Heap:    -Xms$JAVA_XMS -Xmx$JAVA_XMX"
else
    echo "  Java Heap:    auto"
fi
echo "  Java tmpdir:  $TMP_DIR"
echo "  Fallback:     auto retries with hd if the ram attempt fails"
echo ""

if [ ! -f "$TAG_CONF_FILE" ]; then
    echo "ERROR: Tag configuration file not found: $TAG_CONF_FILE" >&2
    exit 1
fi

if [ ! -f "$TAG_TRANSFORM_FILE" ]; then
    echo "ERROR: Tag transform file not found: $TAG_TRANSFORM_FILE" >&2
    exit 1
fi

MAGIC_STRING="mapsforge binary OSM"
DEFAULT_ZOOM=13
ZOOM=$((1 << DEFAULT_ZOOM))
BASE36_CHARS="0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"

# Function to extract date from PBF file
# Uses osmium if available, otherwise falls back to file modification date
extract_pbf_date() {
    local pbf_file="$1"
    local date_string=""
    
    # Try using osmium fileinfo first (most accurate)
    if command -v osmium &> /dev/null; then
        local timestamp=$(osmium fileinfo -g header.option.osmosis_replication_timestamp "$pbf_file" 2>/dev/null)
        if [ -n "$timestamp" ]; then
            # Parse ISO 8601 timestamp (e.g., 2024-01-15T20:21:53Z)
            date_string=$(date -d "$timestamp" "+%y%m%d" 2>/dev/null)
        fi
    fi
    
    # Fallback: try to extract timestamp from PBF header using Python
    if [ -z "$date_string" ] && command -v python3 &> /dev/null; then
        date_string=$(python3 -c "
import struct
import gzip
import sys
from datetime import datetime

def read_varint(data, pos):
    result = 0
    shift = 0
    while True:
        if pos >= len(data):
            return None, pos
        b = data[pos]
        pos += 1
        result |= (b & 0x7f) << shift
        if (b & 0x80) == 0:
            break
        shift += 7
    return result, pos

def parse_pbf_header(filename):
    with open(filename, 'rb') as f:
        # Read first blob header length (4 bytes big-endian)
        header_len_bytes = f.read(4)
        if len(header_len_bytes) < 4:
            return None
        header_len = struct.unpack('>I', header_len_bytes)[0]
        
        # Read blob header
        blob_header = f.read(header_len)
        
        # Parse blob header to get datasize
        pos = 0
        datasize = 0
        while pos < len(blob_header):
            tag_wire, pos = read_varint(blob_header, pos)
            if tag_wire is None:
                break
            field = tag_wire >> 3
            wire_type = tag_wire & 0x7
            
            if wire_type == 0:  # varint
                val, pos = read_varint(blob_header, pos)
                if field == 3:  # datasize
                    datasize = val
            elif wire_type == 2:  # length-delimited
                length, pos = read_varint(blob_header, pos)
                pos += length
        
        # Read blob data
        blob_data = f.read(datasize)
        
        # Parse blob to find zlib_data or raw data
        pos = 0
        raw_data = None
        zlib_data = None
        while pos < len(blob_data):
            tag_wire, pos = read_varint(blob_data, pos)
            if tag_wire is None:
                break
            field = tag_wire >> 3
            wire_type = tag_wire & 0x7
            
            if wire_type == 0:
                val, pos = read_varint(blob_data, pos)
            elif wire_type == 2:
                length, pos = read_varint(blob_data, pos)
                if field == 1:  # raw
                    raw_data = blob_data[pos:pos+length]
                elif field == 3:  # zlib_data
                    zlib_data = blob_data[pos:pos+length]
                pos += length
        
        # Decompress if needed
        import zlib
        if zlib_data:
            header_block = zlib.decompress(zlib_data)
        elif raw_data:
            header_block = raw_data
        else:
            return None
        
        # Parse HeaderBlock for osmosis_replication_timestamp
        pos = 0
        while pos < len(header_block):
            tag_wire, pos = read_varint(header_block, pos)
            if tag_wire is None:
                break
            field = tag_wire >> 3
            wire_type = tag_wire & 0x7
            
            if wire_type == 0:
                val, pos = read_varint(header_block, pos)
                if field == 32:  # osmosis_replication_timestamp (seconds since epoch)
                    return datetime.utcfromtimestamp(val).strftime('%y%m%d')
            elif wire_type == 2:
                length, pos = read_varint(header_block, pos)
                pos += length
    
    return None

try:
    result = parse_pbf_header('$pbf_file')
    if result:
        print(result)
except Exception as e:
    pass
" 2>/dev/null)
    fi
    
    # Final fallback: use file modification date
    if [ -z "$date_string" ]; then
        date_string=$(date -r "$pbf_file" "+%y%m%d" 2>/dev/null || stat -c %y "$pbf_file" 2>/dev/null | cut -d' ' -f1 | sed 's/-//g' | cut -c3-8)
    fi
    
    echo "$date_string"
}

convert_to_base36() {
    local value=$1
    local length=$2
    
    if [ $value -lt 0 ]; then
        value=0
    fi
    
    local result=""
    for (( i=0; i<length; i++ )); do
        result="${BASE36_CHARS:$((value % 36)):1}$result"
        value=$((value / 36))
    done
    
    echo "$result"
}

convert_to_tile_x() {
    local lon=$1
    local tiles_per_side=$2
    echo "scale=10; ((($lon + 180.0) / 360.0) * $tiles_per_side)" | bc | awk '{printf("%d\n", $1)}'
}

convert_to_tile_y() {
    local lat=$1
    local tiles_per_side=$2
    echo "scale=10; ((1.0 - (l((1.0 + s($lat * 3.141592653589793 / 180.0)) / (1.0 - s($lat * 3.141592653589793 / 180.0))) / 2.0) / 3.141592653589793) / 2.0) * $tiles_per_side" | bc -l | awk '{printf("%d\n", $1)}'
}

get_geo_name() {
    local min_lng=$1
    local max_lng=$2
    local min_lat=$3
    local max_lat=$4
    
    local x_start=$(convert_to_tile_x "$min_lng" "$ZOOM")
    local y_start=$(convert_to_tile_y "$max_lat" "$ZOOM")
    local x_end=$(convert_to_tile_x "$max_lng" "$ZOOM")
    local y_end=$(convert_to_tile_y "$min_lat" "$ZOOM")
    
    local x_span=$((x_end - x_start + 1))
    local y_span=$((y_end - y_start + 1))
    
    echo "$(convert_to_base36 $x_start 3)$(convert_to_base36 $y_start 3)$(convert_to_base36 $((x_span - 1)) 3)$(convert_to_base36 $((y_span - 1)) 3)"
}

get_total_physical_memory_bytes() {
    if [ -r /proc/meminfo ]; then
        awk '/MemTotal:/ {print $2 * 1024; exit}' /proc/meminfo
        return
    fi

    if command -v sysctl >/dev/null 2>&1; then
        sysctl -n hw.memsize 2>/dev/null
        return
    fi

    echo 0
}

bytes_to_heap_string() {
    local bytes="$1"
    local gigabytes=$((bytes / 1024 / 1024 / 1024))
    if [ "$gigabytes" -lt 1 ]; then
        gigabytes=1
    fi
    echo "${gigabytes}g"
}

heap_string_to_bytes() {
    local value
    value=$(echo "$1" | tr '[:upper:]' '[:lower:]')
    case "$value" in
        *g) echo $(( ${value%g} * 1024 * 1024 * 1024 )) ;;
        *m) echo $(( ${value%m} * 1024 * 1024 )) ;;
        *) echo "$value" ;;
    esac
}

get_auto_map_writer_config() {
    local pbf_size_bytes="$1"
    local total_physical_bytes="$2"
    local min_ram_heap_bytes=$((4 * 1024 * 1024 * 1024))
    local max_auto_heap_bytes=$((total_physical_bytes * 2 / 3))
    local max_auto_heap_string
    max_auto_heap_string=$(bytes_to_heap_string "$max_auto_heap_bytes")

    if [ "$pbf_size_bytes" -le $((350 * 1024 * 1024)) ]; then
        preferred="ram|2|2g|6g"
    elif [ "$pbf_size_bytes" -le $((700 * 1024 * 1024)) ]; then
        preferred="ram|2|3g|8g"
    elif [ "$pbf_size_bytes" -le $((1024 * 1024 * 1024)) ]; then
        preferred="ram|1|6g|$max_auto_heap_string"
    else
        preferred="ram|1|8g|$max_auto_heap_string"
    fi

    IFS='|' read -r preferred_writer preferred_threads preferred_java_xms preferred_java_xmx <<< "$preferred"

    requested_heap_bytes=$(heap_string_to_bytes "$preferred_java_xmx")

    if [ "$max_auto_heap_bytes" -lt "$min_ram_heap_bytes" ]; then
        echo "hd|1|2g|8g|fallback_to_hd_due_to_total_ram_cap"
        return
    fi

    if [ "$requested_heap_bytes" -gt "$max_auto_heap_bytes" ]; then
        effective_java_xmx=$(bytes_to_heap_string "$max_auto_heap_bytes")
        if [ "$(heap_string_to_bytes "$preferred_java_xms")" -gt "$max_auto_heap_bytes" ]; then
            effective_java_xms="$effective_java_xmx"
        else
            effective_java_xms="$preferred_java_xms"
        fi
        echo "ram|$preferred_threads|$effective_java_xms|$effective_java_xmx|ram_capped_by_total_ram"
        return
    fi

    echo "${preferred}|preferred_ram"
}

get_hd_config() {
    echo "hd|1|2g|8g"
}

run_osmosis_map_writer() {
    local writer_type="$1"
    local threads="$2"
    local java_xms="$3"
    local java_xmx="$4"

    export JAVA_OPTS="-Xms$java_xms -Xmx$java_xmx -Djava.io.tmpdir=$TMP_DIR"
    rm -f "$OUTPUT_FILE"

    "$OSMOSIS_DIR/bin/osmosis-with-mapsforge" \
        --read-pbf-fast file="$INPUT_FILE" \
        --bounding-polygon file="$POLY_FILE" \
        --tag-transform file="$TAG_TRANSFORM_FILE" \
        --mapfile-writer file="$OUTPUT_FILE" type="$writer_type" zoom-interval-conf=13,13,13,14,14,14 threads="$threads" tag-conf-file="$TAG_CONF_FILE"
}

file_index=0
for i in "${!PBF_FILES[@]}"; do
    file_index=$((file_index + 1))
    INPUT_FILE="${PBF_FILES[$i]}"
    POLY_FILE="${POLY_FILES[$i]}"
    ORIGINAL_NAME="${ORIGINAL_NAMES[$i]}"
    file_name=$(basename "$INPUT_FILE")
    pbf_size_bytes=$(wc -c < "$INPUT_FILE" | tr -d ' ')
    pbf_size_mb=$((pbf_size_bytes / 1024 / 1024))
    total_physical_bytes=$(get_total_physical_memory_bytes)
    total_physical_gb=$(awk -v total="$total_physical_bytes" 'BEGIN { printf("%.2f", total / 1024 / 1024 / 1024) }')
    IFS='|' read -r auto_writer_type auto_threads auto_java_xms auto_java_xmx auto_reason <<< "$(get_auto_map_writer_config "$pbf_size_bytes" "$total_physical_bytes")"
    requested_writer_type="$MAP_WRITER_TYPE"
    if [ "$requested_writer_type" = "auto" ]; then
        requested_writer_type="$auto_writer_type"
    fi
    if [ "$requested_writer_type" = "hd" ]; then
        IFS='|' read -r base_writer_type base_threads base_java_xms base_java_xmx <<< "$(get_hd_config)"
    else
        base_writer_type="$auto_writer_type"
        base_threads="$auto_threads"
        base_java_xms="$auto_java_xms"
        base_java_xmx="$auto_java_xmx"
    fi
    effective_threads="${THREADS:-$base_threads}"
    effective_java_xms="${JAVA_XMS:-$base_java_xms}"
    effective_java_xmx="${JAVA_XMX:-$base_java_xmx}"
    
    # Extract country code from original filename (first 2 characters)
    COUNTRY_CODE="${ORIGINAL_NAME:0:2}"
    
    # Extract product code from original filename (characters 2-5, 0-indexed)
    PRODUCT_CODE="${ORIGINAL_NAME:2:4}"
    
    # Extract date from PBF file before processing
    echo "Extracting date from PBF file..."
    date_string=$(extract_pbf_date "$INPUT_FILE")
    
    echo "=========================================="
    echo "Processing [$file_index/${#PBF_FILES[@]}]"
    echo "  PBF File:      $file_name"
    echo "  Poly File:     $(basename "$POLY_FILE")"
    echo "  Original Name: $ORIGINAL_NAME"
    echo "  Country Code:  $COUNTRY_CODE"
    echo "  Product Code:  $PRODUCT_CODE"
    echo "  PBF Date:      $date_string"
    echo "  PBF Size:      ${pbf_size_mb} MB"
    echo "  Total RAM:     ${total_physical_gb} GB"
    echo "  Writer Type:   $requested_writer_type"
    echo "  Threads:       $effective_threads"
    echo "  Java Heap:     -Xms$effective_java_xms -Xmx$effective_java_xmx"
    if [ "$MAP_WRITER_TYPE" = "auto" ]; then
        if [ "$auto_reason" = "ram_capped_by_total_ram" ]; then
            echo "  Auto Decision: ram profile capped to 80% of installed RAM, then retry with hd if needed"
        elif [ "$auto_reason" = "fallback_to_hd_due_to_total_ram_cap" ]; then
            echo "  Auto Decision: total RAM too small for a useful ram profile, using hd"
        else
            echo "  Auto Decision: try ram first and retry with hd if needed"
        fi
    fi
    echo "=========================================="
    
    OUTPUT_FILE="$OUTPUT_DIR/out_$file_index.map"
    
    echo "Running osmosis..."
    run_osmosis_map_writer "$requested_writer_type" "$effective_threads" "$effective_java_xms" "$effective_java_xmx"
    run_status=$?
    final_writer_type="$requested_writer_type"
    final_threads="$effective_threads"
    final_java_xms="$effective_java_xms"
    final_java_xmx="$effective_java_xmx"

    if [ $run_status -ne 0 ] && [ "$MAP_WRITER_TYPE" = "auto" ] && [ "$requested_writer_type" = "ram" ]; then
        IFS='|' read -r hd_writer_type hd_threads hd_java_xms hd_java_xmx <<< "$(get_hd_config)"
        fallback_threads="${THREADS:-$hd_threads}"
        fallback_java_xms="${JAVA_XMS:-$hd_java_xms}"
        fallback_java_xmx="${JAVA_XMX:-$hd_java_xmx}"
        echo "WARNING: RAM writer attempt failed for $file_name. Retrying with hd..."
        run_osmosis_map_writer "hd" "$fallback_threads" "$fallback_java_xms" "$fallback_java_xmx"
        run_status=$?

        if [ $run_status -eq 0 ]; then
            final_writer_type="hd"
            final_threads="$fallback_threads"
            final_java_xms="$fallback_java_xms"
            final_java_xmx="$fallback_java_xmx"
        fi
    fi
    
    if [ $run_status -ne 0 ] || [ ! -f "$OUTPUT_FILE" ]; then
        echo "WARNING: Osmosis did not generate file for: $file_name - skipping"
        continue
    fi

    if [ "$final_writer_type" != "$requested_writer_type" ]; then
        echo "Completed with fallback writer: $final_writer_type (threads=$final_threads, heap=-Xms$final_java_xms -Xmx$final_java_xmx)"
    fi
    
    echo "Osmosis completed. Generating name..."
    
    {
        # Read magic string
        magic=$(dd bs=1 count=${#MAGIC_STRING} 2>/dev/null)
        
        if [ "$magic" != "$MAGIC_STRING" ]; then
            echo "WARNING: Invalid .map file for: $file_name - skipping"
            continue
        fi
        
        # Skip 24 bytes to reach bounding box (4 + 4 + 8 for header + 8 for date timestamp)
        dd bs=1 count=24 2>/dev/null >/dev/null
        
        # Read bounding box (4 int32s)
        read_int32() {
            local bytes=""
            for i in {1..4}; do
                byte=$(dd bs=1 count=1 2>/dev/null | od -An -td1 | tr -d ' ')
                if [ -z "$byte" ]; then byte=0; fi
                bytes="$bytes $byte"
            done
            
            local arr=($bytes)
            for i in 0 1 2 3; do
                if [ ${arr[$i]} -lt 0 ]; then
                    arr[$i]=$((${arr[$i]} + 256))
                fi
            done
            
            local u=$(( (${arr[0]} << 24) | (${arr[1]} << 16) | (${arr[2]} << 8) | ${arr[3]} ))
            
            if [ $u -ge 2147483648 ]; then
                echo $(( u - 4294967296 ))
            else
                echo $u
            fi
        }
        
        min_lat_micro=$(read_int32)
        min_lng_micro=$(read_int32)
        max_lat_micro=$(read_int32)
        max_lng_micro=$(read_int32)
        
        min_lat=$(echo "scale=6; $min_lat_micro / 1000000.0" | bc)
        min_lng=$(echo "scale=6; $min_lng_micro / 1000000.0" | bc)
        max_lat=$(echo "scale=6; $max_lat_micro / 1000000.0" | bc)
        max_lng=$(echo "scale=6; $max_lng_micro / 1000000.0" | bc)
        
        geo_name=$(get_geo_name "$min_lng" "$max_lng" "$min_lat" "$max_lat")
        
        new_name="${COUNTRY_CODE}${PRODUCT_CODE}${date_string}${geo_name}"
        new_path="$OUTPUT_DIR/$new_name.map"
        
        echo "Map Details:"
        echo "  Date (from PBF): $date_string"
        echo "  Bounding Box: minLat=$min_lat minLng=$min_lng maxLat=$max_lat maxLng=$max_lng"
        echo "  Geo Code:    $geo_name"
        echo "  Generated:   $new_name.map"
        
        if [ -f "$new_path" ]; then
            rm -f "$new_path"
        fi
        
        mv "$OUTPUT_FILE" "$new_path"
        
        echo ""
    } < "$OUTPUT_FILE"
done

echo "=========================================="
echo "Done! Processed ${#PBF_FILES[@]} files."
echo "=========================================="
