#!/bin/bash
# Quick start script for HRRR ASNOW Zarr project

set -e

echo "======================================"
echo "HRRR ASNOW Zarr Quick Start"
echo "======================================"
echo ""

# Check Python version
echo "Checking Python version..."
python3 --version
echo ""

# Install dependencies
echo "Installing dependencies..."
if command -v pip3 &> /dev/null; then
    pip3 install -r requirements.txt
else
    pip install -r requirements.txt
fi
echo "✓ Dependencies installed"
echo ""

# Create data directory
echo "Creating data directory..."
mkdir -p data
mkdir -p tmp
echo "✓ Directories created"
echo ""

# Initialize zarr store
echo "Initializing zarr store..."
python3 src/template.py data/hrrr-analysis-snowfall.zarr config.yaml
echo "✓ Zarr store initialized"
echo ""

# Test with a single recent file
echo "Testing with a single recent file..."
YESTERDAY=$(date -d "yesterday" +%Y-%m-%d 2>/dev/null || date -v-1d +%Y-%m-%d)
echo "Downloading data for ${YESTERDAY} 12:00 UTC..."

python3 src/downloader.py ${YESTERDAY} 12 tmp/ || {
    echo "⚠ Download failed (data may not be available yet)"
    echo "This is normal for very recent dates"
}

# Process if file was downloaded
if ls tmp/*.grib2 1> /dev/null 2>&1; then
    echo "Processing downloaded file..."
    python3 src/processor.py data/hrrr-analysis-snowfall.zarr tmp/*.grib2
    echo "✓ Test file processed successfully"

    # Show zarr info
    echo ""
    echo "Zarr store information:"
    python3 scripts/utils.py info --zarr data/hrrr-analysis-snowfall.zarr

    # Clean up
    rm -f tmp/*.grib2
else
    echo "No file to process (download failed)"
fi

echo ""
echo "======================================"
echo "Quick start complete!"
echo "======================================"
echo ""
echo "Next steps:"
echo "  1. Run a backfill for a date range:"
echo "     python3 src/backfill.py --start 2024-01-01 --end 2024-01-07"
echo ""
echo "  2. Enable GitHub Actions for automated backfill"
echo ""
echo "  3. Check progress:"
echo "     python3 scripts/utils.py progress"
echo ""
echo "  4. View zarr info:"
echo "     python3 scripts/utils.py info"
echo ""
