#!/bin/bash
# Test the HRRR ASNOW pipeline with a single recent file

set -e

echo "======================================"
echo "HRRR ASNOW Pipeline Test"
echo "======================================"
echo ""

# Check dependencies
echo "Checking dependencies..."
python3 -c "import xarray, zarr, cfgrib, pyproj, yaml, requests" || {
    echo "❌ Missing dependencies. Run: pip install -r requirements.txt"
    exit 1
}
echo "✓ All dependencies installed"
echo ""

# Create directories
mkdir -p test_data
mkdir -p tmp

# Step 1: Initialize zarr template
echo "Step 1: Initializing zarr template..."
python3 src/template.py test_data/test.zarr config.yaml
echo "✓ Zarr template created"
echo ""

# Step 2: Download a test file (yesterday's 12 UTC)
echo "Step 2: Downloading test file..."
YESTERDAY=$(date -d "2 days ago" +%Y-%m-%d 2>/dev/null || date -v-2d +%Y-%m-%d)
echo "Attempting to download: ${YESTERDAY} 12:00 UTC"

python3 src/downloader.py ${YESTERDAY} 12 tmp/ || {
    echo "⚠ Download failed for ${YESTERDAY}"
    echo "Trying an older date..."
    OLDER_DATE=$(date -d "7 days ago" +%Y-%m-%d 2>/dev/null || date -v-7d +%Y-%m-%d)
    python3 src/downloader.py ${OLDER_DATE} 12 tmp/ || {
        echo "❌ Could not download test data"
        echo "This may be normal if recent data is not yet available on NOMADS"
        exit 1
    }
}

# Check if file was downloaded
if [ ! -f tmp/*.grib2 ]; then
    echo "❌ No GRIB2 file downloaded"
    exit 1
fi

GRIB_FILE=$(ls tmp/*.grib2 | head -1)
echo "✓ Downloaded: $(basename $GRIB_FILE)"
echo ""

# Step 3: Process the file
echo "Step 3: Processing GRIB2 file..."
python3 src/processor.py test_data/test.zarr "$GRIB_FILE"
echo "✓ File processed and added to zarr"
echo ""

# Step 4: Verify the data
echo "Step 4: Verifying zarr contents..."
python3 << EOF
import xarray as xr
import numpy as np

ds = xr.open_zarr('test_data/test.zarr')

print(f"Dataset dimensions: {dict(ds.dims)}")
print(f"Time points: {len(ds.time)}")
print(f"Variables: {list(ds.data_vars)}")

if len(ds.time) > 0:
    print(f"\nTime range: {ds.time.values[0]} to {ds.time.values[-1]}")

    asnow = ds['accumulated_snowfall'].values
    print(f"\nASNOW statistics:")
    print(f"  Min: {np.nanmin(asnow):.6f} m")
    print(f"  Max: {np.nanmax(asnow):.6f} m")
    print(f"  Mean: {np.nanmean(asnow):.6f} m")
    print(f"  NaN count: {np.isnan(asnow).sum()} / {asnow.size}")

    if np.nanmax(asnow) > 0:
        print("\n✓ Data looks good! Found non-zero snowfall values")
    else:
        print("\n⚠ No snowfall in this sample (may be normal for this time/location)")
else:
    print("❌ No data in zarr store")
    exit(1)
EOF

echo ""
echo "======================================"
echo "✓ Pipeline test successful!"
echo "======================================"
echo ""
echo "Cleanup..."
rm -rf test_data/
rm -f tmp/*.grib2

echo ""
echo "Next steps:"
echo "  1. Configure cloud storage (optional):"
echo "     ./setup_cloud.sh"
echo ""
echo "  2. Run a real backfill for a date range:"
echo "     python3 src/backfill_cloud.py --start 2024-01-01 --end 2024-01-07"
echo ""
echo "  3. Or trigger GitHub Actions for automated backfill"
echo ""
