$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"

$SCRIPT_DIR = $PSScriptRoot

Add-Type -TypeDefinition @"
using System;
using System.Runtime.InteropServices;

public static class CodexMemoryStatus {
    [StructLayout(LayoutKind.Sequential, CharSet = CharSet.Auto)]
    public struct MEMORYSTATUSEX {
        public uint dwLength;
        public uint dwMemoryLoad;
        public ulong ullTotalPhys;
        public ulong ullAvailPhys;
        public ulong ullTotalPageFile;
        public ulong ullAvailPageFile;
        public ulong ullTotalVirtual;
        public ulong ullAvailVirtual;
        public ulong ullAvailExtendedVirtual;
    }

    [DllImport("kernel32.dll", CharSet = CharSet.Auto, SetLastError = true)]
    public static extern bool GlobalMemoryStatusEx(ref MEMORYSTATUSEX lpBuffer);
}
"@

# Download and extract osmosis if not present
$OSMOSIS_VERSION = "0.49.2"
$OSMOSIS_DIR = Join-Path $SCRIPT_DIR "osmosis-$OSMOSIS_VERSION"

if (-not (Test-Path $OSMOSIS_DIR)) {
    Write-Host "Osmosis not found. Downloading osmosis-$OSMOSIS_VERSION..."
    $OSMOSIS_URL = "https://github.com/openstreetmap/osmosis/releases/download/$OSMOSIS_VERSION/osmosis-$OSMOSIS_VERSION.zip"
    $OSMOSIS_ZIP = Join-Path $SCRIPT_DIR "osmosis-$OSMOSIS_VERSION.zip"
    
    Invoke-WebRequest -Uri $OSMOSIS_URL -OutFile $OSMOSIS_ZIP -UseBasicParsing
    
    Write-Host "Extracting osmosis..."
    Expand-Archive -Path $OSMOSIS_ZIP -DestinationPath $SCRIPT_DIR -Force
    
    Write-Host "Cleaning up..."
    Remove-Item $OSMOSIS_ZIP
    
    Write-Host "Osmosis $OSMOSIS_VERSION installed successfully."
    Write-Host ""
}

# Download and install Mapsforge writer plugin if not present
$MAPSFORGE_WRITER_VERSION = "0.27.0"
$MAPSFORGE_WRITER_JAR = Join-Path $OSMOSIS_DIR "lib\mapsforge-map-writer-$MAPSFORGE_WRITER_VERSION-jar-with-dependencies.jar"

if (-not (Test-Path $MAPSFORGE_WRITER_JAR)) {
    Write-Host "Mapsforge writer plugin not found. Downloading version $MAPSFORGE_WRITER_VERSION..."
    $MAPSFORGE_URL = "https://github.com/mapsforge/mapsforge/releases/download/$MAPSFORGE_WRITER_VERSION/mapsforge-map-writer-$MAPSFORGE_WRITER_VERSION-jar-with-dependencies.jar"
    
    Invoke-WebRequest -Uri $MAPSFORGE_URL -OutFile $MAPSFORGE_WRITER_JAR -UseBasicParsing
    
    Write-Host "Mapsforge writer plugin installed successfully."
    Write-Host ""
}

# Create wrapper script that includes Mapsforge in classpath
$OSMOSIS_WRAPPER = Join-Path $OSMOSIS_DIR "bin\osmosis-with-mapsforge.bat"
$OSMOSIS_SCRIPT = Join-Path $OSMOSIS_DIR "bin\osmosis.bat"

if (-not (Test-Path $OSMOSIS_WRAPPER)) {
    $MAPSFORGE_JAR_NAME = "mapsforge-map-writer-$MAPSFORGE_WRITER_VERSION-jar-with-dependencies.jar"
    $content = Get-Content $OSMOSIS_SCRIPT -Raw
    $content = $content -replace '(set CLASSPATH=%APP_HOME%)', "`$1\lib\$MAPSFORGE_JAR_NAME;%APP_HOME%"
    $content | Set-Content $OSMOSIS_WRAPPER
}

$TAG_CONF_FILE = Join-Path $SCRIPT_DIR "tag-igpsport.xml"
$TAG_TRANSFORM_FILE = Join-Path $SCRIPT_DIR "tag-igpsport-transform.xml"
$THREADS = if ($env:MAP_WRITER_THREADS) { [int]$env:MAP_WRITER_THREADS } else { $null }
$MAP_WRITER_TYPE = if ($env:MAP_WRITER_TYPE) { $env:MAP_WRITER_TYPE } else { "auto" }
$MAP_ALLOW_HD_FALLBACK = if ($env:MAP_ALLOW_HD_FALLBACK) { $env:MAP_ALLOW_HD_FALLBACK } else { "" }
$RESUME_MODE = if ($env:MAP_RESUME) { $env:MAP_RESUME } else { "" }
$TMP_DIR = if ($env:JAVA_TMP_DIR) { $env:JAVA_TMP_DIR } else { (Join-Path $SCRIPT_DIR "tmp") }
$JAVA_XMS = if ($env:JAVA_XMS) { $env:JAVA_XMS } else { $null }
$JAVA_XMX = if ($env:JAVA_XMX) { $env:JAVA_XMX } else { $null }
$env:CLASSPATH = "$MAPSFORGE_WRITER_JAR;$env:CLASSPATH"

# Create directories
$DOWNLOAD_DIR = Join-Path $SCRIPT_DIR "download"
$OUTPUT_DIR = Join-Path $SCRIPT_DIR "output"

New-Item -ItemType Directory -Force -Path $TMP_DIR | Out-Null
New-Item -ItemType Directory -Force -Path $DOWNLOAD_DIR | Out-Null
New-Item -ItemType Directory -Force -Path $OUTPUT_DIR | Out-Null

# Check if maps.csv exists
$CSV_FILE = Join-Path $SCRIPT_DIR "maps.csv"
if (-not (Test-Path $CSV_FILE)) {
    Write-Error "ERROR: maps.csv not found in directory: $SCRIPT_DIR"
    exit 1
}

# Read CSV file and download files
Write-Host "Reading maps.csv..."
$MAP_ENTRIES = @()

$csv = @(Import-Csv $CSV_FILE)
$csv_total = $csv.Count
$csv_index = 0

foreach ($row in $csv) {
    $csv_index++
    $pct = [math]::Floor((($csv_index - 1) / $csv_total) * 100)
    Write-Progress -Activity "Downloading data" -Status "[$csv_index/$csv_total] $($row.'Original filename')" -PercentComplete $pct
    $original_name = $row.'Original filename'
    $pbf_urls = @($row.'OSM BPF URL' -split ';' | ForEach-Object { $_.Trim() } | Where-Object { -not [string]::IsNullOrWhiteSpace($_) })
    $poly_urls = @($row.'Poly URL' -split ';' | ForEach-Object { $_.Trim() } | Where-Object { -not [string]::IsNullOrWhiteSpace($_) })
    
    if ([string]::IsNullOrWhiteSpace($original_name)) {
        continue
    }

    if ($pbf_urls.Count -eq 0 -or $pbf_urls.Count -ne $poly_urls.Count) {
        Write-Warning "Skipping invalid CSV row for $original_name (PBF/poly counts do not match)"
        continue
    }
    
    Write-Host ""
    Write-Host "Processing entry: $original_name"

    $pbf_paths = @()
    $poly_paths = @()
    for ($sourceIndex = 0; $sourceIndex -lt $pbf_urls.Count; $sourceIndex++) {
        $pbf_url = $pbf_urls[$sourceIndex]
        $poly_url = $poly_urls[$sourceIndex]

        $pbf_filename = Split-Path $pbf_url -Leaf
        $pbf_path = Join-Path $DOWNLOAD_DIR $pbf_filename

        if (-not (Test-Path $pbf_path)) {
            Write-Host "  Downloading PBF: $pbf_filename..."
            Invoke-WebRequest -Uri $pbf_url -OutFile $pbf_path -UseBasicParsing
            Write-Host "  PBF downloaded."
        } else {
            Write-Host "  PBF already exists: $pbf_filename"
        }

        $poly_filename = Split-Path $poly_url -Leaf
        $poly_path = Join-Path $DOWNLOAD_DIR $poly_filename

        if (-not (Test-Path $poly_path)) {
            Write-Host "  Downloading Poly: $poly_filename..."
            Invoke-WebRequest -Uri $poly_url -OutFile $poly_path -UseBasicParsing
            Write-Host "  Poly downloaded."
        } else {
            Write-Host "  Poly already exists: $poly_filename"
        }

        $pbf_paths += $pbf_path
        $poly_paths += $poly_path
    }

    $MAP_ENTRIES += [PSCustomObject]@{
        OriginalName = $original_name
        PbfPaths = $pbf_paths
        PolyPaths = $poly_paths
    }
}

Write-Progress -Activity "Downloading data" -Completed

if ($MAP_ENTRIES.Count -eq 0) {
    Write-Error "ERROR: No entries found in maps.csv"
    exit 1
}

Write-Host ""
Write-Host "=========================================="
Write-Host "Found $($MAP_ENTRIES.Count) entries to process"
Write-Host "=========================================="
Write-Host ""
Write-Host "Mapsforge configuration:"
Write-Host "  Writer Type:  $MAP_WRITER_TYPE"
Write-Host "  Threads:      $(if ($THREADS) { $THREADS } else { 'auto' })"
Write-Host "  Java Heap:    $(if ($JAVA_XMS -or $JAVA_XMX) { "-Xms$JAVA_XMS -Xmx$JAVA_XMX" } else { 'auto' })"
Write-Host "  Java tmpdir:  $TMP_DIR"
Write-Host "  HD Fallback:  $(if ($MAP_ALLOW_HD_FALLBACK) { 'enabled' } else { 'disabled by default' })"
Write-Host "  Resume:       $(if ($RESUME_MODE) { 'skip existing final maps' } else { 'off' })"
Write-Host ""

if (-not (Test-Path $TAG_CONF_FILE)) {
    Write-Error "ERROR: Tag configuration file not found: $TAG_CONF_FILE"
    exit 1
}

if (-not (Test-Path $TAG_TRANSFORM_FILE)) {
    Write-Error "ERROR: Tag transform file not found: $TAG_TRANSFORM_FILE"
    exit 1
}

$MAGIC_STRING = "mapsforge binary OSM"
$DEFAULT_ZOOM = 13
$ZOOM = [math]::Pow(2, $DEFAULT_ZOOM)
$BASE36_CHARS = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"

# Function to read a varint from byte array
function Read-Varint {
    param([byte[]]$data, [ref]$pos)
    
    $result = [uint64]0
    $shift = 0
    while ($pos.Value -lt $data.Length) {
        $b = $data[$pos.Value]
        $pos.Value++
        $result = $result -bor (([uint64]($b -band 0x7f)) -shl $shift)
        if (($b -band 0x80) -eq 0) {
            break
        }
        $shift += 7
    }
    return $result
}

# Function to extract date from PBF file header
function Get-PbfDate {
    param([string]$pbfFile)
    
    try {
        $stream = [System.IO.File]::OpenRead($pbfFile)
        $reader = New-Object System.IO.BinaryReader($stream)
        
        # Read first blob header length (4 bytes big-endian)
        $headerLenBytes = $reader.ReadBytes(4)
        [Array]::Reverse($headerLenBytes)
        $headerLen = [BitConverter]::ToInt32($headerLenBytes, 0)
        
        # Read blob header
        $blobHeader = $reader.ReadBytes($headerLen)
        
        # Parse blob header to get datasize
        $pos = [ref]0
        $datasize = 0
        while ($pos.Value -lt $blobHeader.Length) {
            $tagWire = Read-Varint $blobHeader $pos
            $field = $tagWire -shr 3
            $wireType = $tagWire -band 0x7
            
            if ($wireType -eq 0) {  # varint
                $val = Read-Varint $blobHeader $pos
                if ($field -eq 3) {  # datasize
                    $datasize = $val
                }
            }
            elseif ($wireType -eq 2) {  # length-delimited
                $length = Read-Varint $blobHeader $pos
                $pos.Value += $length
            }
        }
        
        # Read blob data
        $blobData = $reader.ReadBytes($datasize)
        
        # Parse blob to find zlib_data
        $pos.Value = 0
        $zlibData = $null
        $rawData = $null
        while ($pos.Value -lt $blobData.Length) {
            $tagWire = Read-Varint $blobData $pos
            $field = $tagWire -shr 3
            $wireType = $tagWire -band 0x7
            
            if ($wireType -eq 0) {
                $val = Read-Varint $blobData $pos
            }
            elseif ($wireType -eq 2) {
                $length = Read-Varint $blobData $pos
                if ($field -eq 1) {  # raw
                    $rawData = New-Object byte[] $length
                    [Array]::Copy($blobData, $pos.Value, $rawData, 0, $length)
                }
                elseif ($field -eq 3) {  # zlib_data
                    $zlibData = New-Object byte[] $length
                    [Array]::Copy($blobData, $pos.Value, $zlibData, 0, $length)
                }
                $pos.Value += $length
            }
        }
        
        # Decompress if needed
        $headerBlock = $null
        if ($zlibData) {
            # Skip first 2 bytes (zlib header) and decompress
            $compressedStream = New-Object System.IO.MemoryStream(,$zlibData)
            $compressedStream.Position = 2  # Skip zlib header
            $deflateStream = New-Object System.IO.Compression.DeflateStream($compressedStream, [System.IO.Compression.CompressionMode]::Decompress)
            $outputStream = New-Object System.IO.MemoryStream
            $deflateStream.CopyTo($outputStream)
            $headerBlock = $outputStream.ToArray()
            $deflateStream.Close()
            $outputStream.Close()
            $compressedStream.Close()
        }
        elseif ($rawData) {
            $headerBlock = $rawData
        }
        
        if (-not $headerBlock) {
            $reader.Close()
            $stream.Close()
            return $null
        }
        
        # Parse HeaderBlock for osmosis_replication_timestamp
        $pos.Value = 0
        while ($pos.Value -lt $headerBlock.Length) {
            $tagWire = Read-Varint $headerBlock $pos
            $field = $tagWire -shr 3
            $wireType = $tagWire -band 0x7
            
            if ($wireType -eq 0) {  # varint
                $val = Read-Varint $headerBlock $pos
                if ($field -eq 32) {  # osmosis_replication_timestamp (seconds since epoch)
                    $reader.Close()
                    $stream.Close()
                    $epoch = [DateTime]::new(1970, 1, 1, 0, 0, 0, [DateTimeKind]::Utc)
                    $date = $epoch.AddSeconds($val)
                    return $date.ToString("yyMMdd")
                }
            }
            elseif ($wireType -eq 2) {  # length-delimited
                $length = Read-Varint $headerBlock $pos
                $pos.Value += $length
            }
        }
        
        $reader.Close()
        $stream.Close()
    }
    catch {
        Write-Warning "Error reading PBF header: $_"
    }
    
    # Fallback: use file modification date
    $fileInfo = Get-Item $pbfFile
    return $fileInfo.LastWriteTime.ToString("yyMMdd")
}

function Read-BigEndianInt32 {
    param([System.IO.BinaryReader]$reader)
    
    $bytes = $reader.ReadBytes(4)
    if ($bytes.Length -lt 4) {
        throw "EOF while reading int32"
    }
    
    [Array]::Reverse($bytes)
    return [BitConverter]::ToInt32($bytes, 0)
}

function Convert-ToBase36 {
    param([int]$value, [int]$length)
    
    if ($value -lt 0) {
        $value = 0
    }
    
    $result = ""
    for ($i = 0; $i -lt $length; $i++) {
        $result = $BASE36_CHARS[$value % 36] + $result
        $value = [math]::Floor($value / 36)
    }
    
    return $result
}

function Convert-FromBase36 {
    param([string]$value)

    $result = 0
    foreach ($char in $value.ToUpper().ToCharArray()) {
        $digit = $BASE36_CHARS.IndexOf($char)
        if ($digit -lt 0) {
            throw "Invalid base36 digit: $char"
        }
        $result = ($result * 36) + $digit
    }

    return $result
}

function Convert-TileXToLon {
    param([double]$x, [double]$tiles_per_side)

    return ($x / $tiles_per_side) * 360.0 - 180.0
}

function Convert-TileYToLat {
    param([double]$y, [double]$tiles_per_side)

    $n = [math]::PI * (1.0 - 2.0 * $y / $tiles_per_side)
    return [math]::Atan([math]::Sinh($n)) * 180.0 / [math]::PI
}

function Convert-ToTileX {
    param([double]$lon, [double]$tiles_per_side)
    
    return [math]::Floor((($lon + 180.0) / 360.0) * $tiles_per_side)
}

function Convert-ToTileY {
    param([double]$lat, [double]$tiles_per_side)
    
    $lat_rad = $lat * [math]::PI / 180.0
    return [math]::Floor(((1.0 - ([math]::Log([math]::Tan($lat_rad) + (1.0 / [math]::Cos($lat_rad))) / [math]::PI)) / 2.0) * $tiles_per_side)
}

function Get-OriginalTileBbox {
    param([string]$originalName)

    $geocode = [System.IO.Path]::GetFileNameWithoutExtension($originalName).Substring(12, 12)
    $minLonX = Convert-FromBase36 $geocode.Substring(0, 3)
    $maxLatY = Convert-FromBase36 $geocode.Substring(3, 3)
    $lonSpan = (Convert-FromBase36 $geocode.Substring(6, 3)) + 1
    $latSpan = (Convert-FromBase36 $geocode.Substring(9, 3)) + 1

    return @{
        MinLon = Convert-TileXToLon $minLonX $ZOOM
        MinLat = Convert-TileYToLat ($maxLatY + $latSpan) $ZOOM
        MaxLon = Convert-TileXToLon ($minLonX + $lonSpan) $ZOOM
        MaxLat = Convert-TileYToLat $maxLatY $ZOOM
        Geocode = $geocode
    }
}

function Get-GeoName {
    param([double]$min_lng, [double]$max_lng, [double]$min_lat, [double]$max_lat)
    
    $x_start = Convert-ToTileX $min_lng $ZOOM
    $y_start = Convert-ToTileY $max_lat $ZOOM
    $x_end = Convert-ToTileX $max_lng $ZOOM
    $y_end = Convert-ToTileY $min_lat $ZOOM
    
    $x_span = $x_end - $x_start + 1
    $y_span = $y_end - $y_start + 1
    
    return "$(Convert-ToBase36 $x_start 3)$(Convert-ToBase36 $y_start 3)$(Convert-ToBase36 ($x_span - 1) 3)$(Convert-ToBase36 ($y_span - 1) 3)"
}

function Get-CombinedPbfDate {
    param([string[]]$pbfFiles)

    $dates = @()
    foreach ($pbfFile in $pbfFiles) {
        $date = Get-PbfDate $pbfFile
        if (-not [string]::IsNullOrWhiteSpace($date)) {
            $dates += $date
        }
    }

    if ($dates.Count -eq 0) {
        return ""
    }

    return ($dates | Sort-Object | Select-Object -Last 1)
}

function Find-ExistingOutputMap {
    param(
        [string]$outputDir,
        [string]$countryCode,
        [string]$productCode,
        [string]$dateString,
        [string]$geocode
    )

    if ([string]::IsNullOrWhiteSpace($dateString) -or [string]::IsNullOrWhiteSpace($geocode) -or -not (Test-Path $outputDir)) {
        return $null
    }

    $expectedPath = Join-Path $outputDir "${countryCode}${productCode}${dateString}${geocode}.map"
    if (Test-Path $expectedPath) {
        return $expectedPath
    }

    return $null
}

function Get-PhysicalMemoryStatus {
    $mem = New-Object CodexMemoryStatus+MEMORYSTATUSEX
    $mem.dwLength = [System.Runtime.InteropServices.Marshal]::SizeOf($mem)

    if (-not [CodexMemoryStatus]::GlobalMemoryStatusEx([ref]$mem)) {
        throw "Unable to query physical memory status."
    }

    return @{
        TotalBytes = [int64]$mem.ullTotalPhys
        AvailableBytes = [int64]$mem.ullAvailPhys
        MemoryLoadPercent = [int]$mem.dwMemoryLoad
    }
}

function Convert-HeapStringToBytes {
    param([string]$heapValue)

    if (-not $heapValue) {
        return 0
    }

    $normalized = $heapValue.Trim().ToLowerInvariant()
    if ($normalized.EndsWith("g")) {
        return [int64]([double]$normalized.TrimEnd('g') * 1GB)
    }
    if ($normalized.EndsWith("m")) {
        return [int64]([double]$normalized.TrimEnd('m') * 1MB)
    }

    return [int64]$normalized
}

function Convert-BytesToHeapString {
    param([int64]$bytes)

    $gigabytes = [math]::Floor($bytes / 1GB)
    if ($gigabytes -lt 1) {
        $gigabytes = 1
    }

    return "${gigabytes}g"
}

function Get-AutoMapWriterConfig {
    param([int64]$pbfSizeBytes, [int64]$totalPhysicalBytes)

    $sizeMb = [math]::Round($pbfSizeBytes / 1MB, 1)
    $totalGb = [math]::Round($totalPhysicalBytes / 1GB, 2)
    $minRamHeapBytes = 4GB
    $maxAutoHeapBytes = [int64][math]::Floor($totalPhysicalBytes * 2 / 3)
    $maxAutoHeapString = Convert-BytesToHeapString $maxAutoHeapBytes

    if ($pbfSizeBytes -le 350MB) {
        $preferred = @{
            WriterType = "ram"
            Threads = 2
            JavaXms = "2g"
            JavaXmx = "6g"
        }
    }
    elseif ($pbfSizeBytes -le 700MB) {
        $preferred = @{
            WriterType = "ram"
            Threads = 1
            JavaXms = "3g"
            JavaXmx = $maxAutoHeapString
        }
    }
    elseif ($pbfSizeBytes -le 1GB) {
        $preferred = @{
            WriterType = "ram"
            Threads = 1
            JavaXms = "6g"
            JavaXmx = $maxAutoHeapString
        }
    }
    else {
        $preferred = @{
            WriterType = "ram"
            Threads = 1
            JavaXms = "8g"
            JavaXmx = $maxAutoHeapString
        }
    }
    $requestedHeapBytes = Convert-HeapStringToBytes $preferred.JavaXmx

    if ($maxAutoHeapBytes -lt $minRamHeapBytes) {
        return @{
            WriterType = "ram"
            Threads = 1
            JavaXms = $maxAutoHeapString
            JavaXmx = $maxAutoHeapString
            SizeMb = $sizeMb
            TotalGb = $totalGb
            Reason = "ram_limited_by_total_ram"
        }
    }

    $effectiveHeapBytes = [math]::Min($requestedHeapBytes, $maxAutoHeapBytes)
    $effectiveJavaXmx = Convert-BytesToHeapString $effectiveHeapBytes
    $effectiveJavaXms = if ((Convert-HeapStringToBytes $preferred.JavaXms) -gt $effectiveHeapBytes) {
        $effectiveJavaXmx
    } else {
        $preferred.JavaXms
    }

    return @{
        WriterType = "ram"
        Threads = $preferred.Threads
        JavaXms = $effectiveJavaXms
        JavaXmx = $effectiveJavaXmx
        SizeMb = $sizeMb
        TotalGb = $totalGb
        Reason = if ($effectiveHeapBytes -lt $requestedHeapBytes) { "ram_capped_by_total_ram" } else { "preferred_ram" }
    }
}

function Get-HdConfig {
    return @{
        WriterType = "hd"
        Threads = 1
        JavaXms = "2g"
        JavaXmx = "8g"
    }
}

function Invoke-OsmosisMapWriter {
    param(
        [string]$osmosisWrapper,
        [string[]]$inputFiles,
        [string[]]$polyFiles,
        [string]$tagTransformFile,
        [string]$outputFile,
        [string]$tagConfFile,
        [hashtable]$tileBbox,
        [string]$writerType,
        [int]$threads,
        [string]$javaXms,
        [string]$javaXmx
    )

    $env:JAVA_OPTS = "-Xms$javaXms -Xmx$javaXmx -Djava.io.tmpdir=$TMP_DIR"

    if (Test-Path $outputFile) {
        Remove-Item $outputFile -Force
    }

    $args = @()
    for ($sourceIndex = 0; $sourceIndex -lt $inputFiles.Count; $sourceIndex++) {
        $args += "--read-pbf-fast"
        $args += "file=$($inputFiles[$sourceIndex])"
        $args += "--bounding-polygon"
        $args += "file=$($polyFiles[$sourceIndex])"
        $args += "--tag-transform"
        $args += "file=$tagTransformFile"

        if ($sourceIndex -ge 1) {
            $args += "--merge"
        }
    }

    if ($tileBbox) {
        $args += "--bounding-box"
        $args += "left=$($tileBbox.MinLon)"
        $args += "right=$($tileBbox.MaxLon)"
        $args += "bottom=$($tileBbox.MinLat)"
        $args += "top=$($tileBbox.MaxLat)"
    }

    $args += "--mapfile-writer"
    $args += "file=$outputFile"
    $args += "type=$writerType"
    $args += "zoom-interval-conf=13,13,13,14,14,14"
    $args += "threads=$threads"
    $args += "tag-conf-file=$tagConfFile"

    $previousErrorActionPreference = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    try {
        & $osmosisWrapper @args | ForEach-Object { Write-Host $_ }
        $exitCode = $LASTEXITCODE
    }
    finally {
        $ErrorActionPreference = $previousErrorActionPreference
    }

    return [bool]($exitCode -eq 0 -and (Test-Path $outputFile))
}

$file_index = 0
$total_files = $MAP_ENTRIES.Count
$stopwatch_total = [System.Diagnostics.Stopwatch]::StartNew()

for ($i = 0; $i -lt $MAP_ENTRIES.Count; $i++) {
    $file_index++
    $entry = $MAP_ENTRIES[$i]
    $INPUT_FILES = @($entry.PbfPaths)
    $POLY_FILES = @($entry.PolyPaths)
    $ORIGINAL_NAME = $entry.OriginalName
    $file_name = if ($INPUT_FILES.Count -eq 1) { Split-Path $INPUT_FILES[0] -Leaf } else { "$($INPUT_FILES.Count) merged sources" }

    $pct = [math]::Floor(($i / $total_files) * 100)
    Write-Progress -Activity "Generating maps" -Status "[$file_index/$total_files] $file_name" -PercentComplete $pct

    $inputSizeBytes = ($INPUT_FILES | ForEach-Object { (Get-Item $_).Length } | Measure-Object -Sum).Sum
    $memoryStatus = Get-PhysicalMemoryStatus
    $autoConfig = Get-AutoMapWriterConfig $inputSizeBytes $memoryStatus.TotalBytes
    $requestedWriterType = if ($MAP_WRITER_TYPE -eq "auto") { $autoConfig.WriterType } else { $MAP_WRITER_TYPE }
    $baseConfig = if ($requestedWriterType -eq "hd") { Get-HdConfig } else { $autoConfig }
    $effectiveThreads = if ($THREADS) { $THREADS } else { $baseConfig.Threads }
    $effectiveJavaXms = if ($JAVA_XMS) { $JAVA_XMS } else { $baseConfig.JavaXms }
    $effectiveJavaXmx = if ($JAVA_XMX) { $JAVA_XMX } else { $baseConfig.JavaXmx }

    # Extract country code from original filename (first 2 characters)
    $COUNTRY_CODE = $ORIGINAL_NAME.Substring(0, 2)

    # Extract product code from original filename (characters 2-5, 0-indexed)
    $PRODUCT_CODE = $ORIGINAL_NAME.Substring(2, 4)
    $TILE_BBOX = Get-OriginalTileBbox $ORIGINAL_NAME

    # Extract date from PBF file before processing
    Write-Host "Extracting date from PBF file..."
    $date_string = Get-CombinedPbfDate $INPUT_FILES
    $existingOutput = if ($RESUME_MODE) {
        Find-ExistingOutputMap -outputDir $OUTPUT_DIR -countryCode $COUNTRY_CODE -productCode $PRODUCT_CODE -dateString $date_string -geocode $TILE_BBOX.Geocode
    } else {
        $null
    }

    Write-Host "=========================================="
    Write-Host "Processing [$file_index/$total_files]"
    Write-Host "  PBF File:      $file_name"
    Write-Host "  Poly File:     $(if ($POLY_FILES.Count -eq 1) { Split-Path $POLY_FILES[0] -Leaf } else { "$($POLY_FILES.Count) matching polygons" })"
    Write-Host "  Source Mode:   $(if ($INPUT_FILES.Count -eq 1) { 'single-region' } else { "multi-region blend ($($INPUT_FILES.Count) sources)" })"
    Write-Host "  Original Name: $ORIGINAL_NAME"
    Write-Host "  Country Code:  $COUNTRY_CODE"
    Write-Host "  Product Code:  $PRODUCT_CODE"
    Write-Host "  Tile Geocode:  $($TILE_BBOX.Geocode)"
    Write-Host "  Tile BBox:     minLat=$($TILE_BBOX.MinLat) minLng=$($TILE_BBOX.MinLon) maxLat=$($TILE_BBOX.MaxLat) maxLng=$($TILE_BBOX.MaxLon)"
    Write-Host "  PBF Date:      $date_string"
    Write-Host "  PBF Size:      $($autoConfig.SizeMb) MB"
    Write-Host "  Total RAM:     $($autoConfig.TotalGb) GB"
    Write-Host "  Writer Type:   $requestedWriterType"
    Write-Host "  Threads:       $effectiveThreads"
    Write-Host "  Java Heap:     -Xms$effectiveJavaXms -Xmx$effectiveJavaXmx"
    if ($MAP_WRITER_TYPE -eq "auto") {
        if ($autoConfig.Reason -eq "ram_capped_by_total_ram") {
            Write-Host "  Auto Decision: ram profile capped to about 2/3 of installed RAM"
        }
        elseif ($autoConfig.Reason -eq "ram_limited_by_total_ram") {
            Write-Host "  Auto Decision: total RAM below preferred profile, using capped ram"
        }
        else {
            Write-Host "  Auto Decision: ram writer only; set MAP_WRITER_TYPE=hd or MAP_ALLOW_HD_FALLBACK=1 to use hd"
        }
    }
    Write-Host "=========================================="

    if ($existingOutput) {
        Write-Host "Skipping existing output in resume mode: $(Split-Path $existingOutput -Leaf)"
        Write-Host ""
        continue
    }

    $OUTPUT_FILE = Join-Path $OUTPUT_DIR "out_$file_index.map"

    $stopwatch = [System.Diagnostics.Stopwatch]::StartNew()
    Write-Host "Running osmosis..."
    $runSucceeded = Invoke-OsmosisMapWriter `
        -osmosisWrapper $OSMOSIS_WRAPPER `
        -inputFiles $INPUT_FILES `
        -polyFiles $POLY_FILES `
        -tagTransformFile $TAG_TRANSFORM_FILE `
        -outputFile $OUTPUT_FILE `
        -tagConfFile $TAG_CONF_FILE `
        -tileBbox $TILE_BBOX `
        -writerType $requestedWriterType `
        -threads $effectiveThreads `
        -javaXms $effectiveJavaXms `
        -javaXmx $effectiveJavaXmx

    $finalWriterType = $requestedWriterType
    $finalThreads = $effectiveThreads
    $finalJavaXms = $effectiveJavaXms
    $finalJavaXmx = $effectiveJavaXmx

    if (-not $runSucceeded -and $MAP_WRITER_TYPE -eq "auto" -and $requestedWriterType -eq "ram" -and $MAP_ALLOW_HD_FALLBACK) {
        $hdConfig = Get-HdConfig
        $fallbackThreads = if ($THREADS) { $THREADS } else { $hdConfig.Threads }
        $fallbackJavaXms = if ($JAVA_XMS) { $JAVA_XMS } else { $hdConfig.JavaXms }
        $fallbackJavaXmx = if ($JAVA_XMX) { $JAVA_XMX } else { $hdConfig.JavaXmx }
        Write-Warning "RAM writer attempt failed for $file_name. Retrying with hd..."
        $runSucceeded = Invoke-OsmosisMapWriter `
            -osmosisWrapper $OSMOSIS_WRAPPER `
            -inputFiles $INPUT_FILES `
            -polyFiles $POLY_FILES `
            -tagTransformFile $TAG_TRANSFORM_FILE `
            -outputFile $OUTPUT_FILE `
            -tagConfFile $TAG_CONF_FILE `
            -tileBbox $TILE_BBOX `
            -writerType "hd" `
            -threads $fallbackThreads `
            -javaXms $fallbackJavaXms `
            -javaXmx $fallbackJavaXmx

        if ($runSucceeded) {
            $finalWriterType = "hd"
            $finalThreads = $fallbackThreads
            $finalJavaXms = $fallbackJavaXms
            $finalJavaXmx = $fallbackJavaXmx
        }
    }
    $stopwatch.Stop()

    if (-not $runSucceeded) {
        Write-Warning "Osmosis did not generate file for: $file_name - skipping"
        continue
    }

    if ($finalWriterType -ne $requestedWriterType) {
        Write-Host "Completed with fallback writer: $finalWriterType (threads=$finalThreads, heap=-Xms$finalJavaXms -Xmx$finalJavaXmx)"
    }

    Write-Host "Osmosis completed in $([math]::Round($stopwatch.Elapsed.TotalMinutes, 1)) minutes. Generating name..."
    
    try {
        $stream = [System.IO.File]::OpenRead($OUTPUT_FILE)
        $reader = New-Object System.IO.BinaryReader($stream)
        
        # Read magic string
        $magicBytes = $reader.ReadBytes($MAGIC_STRING.Length)
        $magic = [System.Text.Encoding]::ASCII.GetString($magicBytes)
        
        if ($magic -ne $MAGIC_STRING) {
            Write-Warning "Invalid .map file for: $file_name - skipping"
            continue
        }
        
        # Skip 24 bytes to reach bounding box (4 + 4 + 8 for header + 8 for date timestamp)
        $reader.ReadBytes(24) | Out-Null
        
        # Read bounding box (4 int32s)
        $min_lat_micro = Read-BigEndianInt32 $reader
        $min_lng_micro = Read-BigEndianInt32 $reader
        $max_lat_micro = Read-BigEndianInt32 $reader
        $max_lng_micro = Read-BigEndianInt32 $reader
        
        $min_lat = $min_lat_micro / 1000000.0
        $min_lng = $min_lng_micro / 1000000.0
        $max_lat = $max_lat_micro / 1000000.0
        $max_lng = $max_lng_micro / 1000000.0
        
        $actual_geo_name = Get-GeoName $min_lng $max_lng $min_lat $max_lat
        $geo_name = $TILE_BBOX.Geocode
        
        $new_name = "${COUNTRY_CODE}${PRODUCT_CODE}${date_string}${geo_name}"
        $new_path = Join-Path $OUTPUT_DIR "$new_name.map"
        
        Write-Host "Map Details:"
        Write-Host "  Date (from PBF): $date_string"
        Write-Host "  Bounding Box: minLat=$min_lat minLng=$min_lng maxLat=$max_lat maxLng=$max_lng"
        Write-Host "  Geo Code:    $geo_name"
        if ($actual_geo_name -ne $geo_name) {
            Write-Host "  Data Geo:    $actual_geo_name"
        }
        Write-Host "  Generated:   $new_name.map"
        
        $reader.Close()
        $stream.Close()
        
        if (Test-Path $new_path) {
            Remove-Item $new_path -Force
        }
        
        Move-Item $OUTPUT_FILE $new_path
        
        Write-Host ""
    }
    catch {
        Write-Warning "Error processing file: $_"
        if ($reader) { $reader.Close() }
        if ($stream) { $stream.Close() }
    }
}

Write-Progress -Activity "Generating maps" -Completed
$stopwatch_total.Stop()

Write-Host "=========================================="
Write-Host "Done! Processed $total_files files in $([math]::Round($stopwatch_total.Elapsed.TotalMinutes, 1)) minutes."
Write-Host "=========================================="
