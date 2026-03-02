# HRRR Analysis Snowfall Zarr Archive

A companion dataset to [Dynamical.org's HRRR Analysis](https://dynamical.org/catalog/noaa-hrrr-analysis/) containing the ASNOW (Accumulated Snowfall) variable from NOAA's High-Resolution Rapid Refresh (HRRR) model.

## Overview

This project creates a zarr archive of HRRR accumulated snowfall data (ASNOW) from NOMADS, providing the **actual HRRR model snowfall output** that is missing from the Dynamical.org HRRR Analysis dataset.

### Dataset Specifications

- **Variable**: ASNOW (Total Accumulated Snowfall)
- **Units**: meters
- **Spatial Domain**: Continental United States (CONUS)
- **Spatial Resolution**: 3 km (Lambert Conformal Conic projection)
- **Time Domain**: 2014-10-01 to Present
- **Time Resolution**: Hourly
- **Grid Dimensions**: 1799 × 1059 points
- **Data Source**: NOAA NOMADS HRRR GRIB2 files

## Why This Dataset?

Dynamical.org's HRRR Analysis dataset lacks accumulation variables (ASNOW, WEASD, SNOD). This sister dataset:

- ✅ Provides **actual HRRR model ASNOW output** (not approximated)
- ✅ Uses the same grid and projection as Dynamical.org HRRR Analysis
- ✅ Can be combined with Dynamical.org data for complete weather analysis
- ✅ Stored in efficient zarr format with compression
- ✅ **Stored directly in GitHub using Git LFS** (or optionally cloud storage)

## Storage Options

This project supports two storage approaches:

1. **Git LFS (Default)** - All data stored directly in GitHub
   - ✅ Simple setup - no cloud accounts needed
   - ✅ Integrated with GitHub
   - ⚠️ Cost: ~$10-15/month for full dataset
   - 📖 See [QUICKSTART_GIT_LFS.md](QUICKSTART_GIT_LFS.md)

2. **Cloud Storage (S3/GCS/Azure)** - Data stored in cloud, code in GitHub
   - ✅ Lower cost (~$0.50-1/month)
   - ✅ Scalable to any size
   - ⚠️ Requires cloud account setup
   - 📖 See [CLOUD_STORAGE.md](CLOUD_STORAGE.md)

## Project Structure

```
.
├── src/
│   ├── template.py      # Zarr template creation
│   ├── downloader.py    # NOMADS data downloader with rate limiting
│   ├── processor.py     # GRIB2 to Zarr processor
│   └── backfill.py      # Backfill orchestration
├── .github/
│   └── workflows/
│       ├── backfill.yml # Automated backfill workflow
│       └── test.yml     # Testing workflow
├── config.yaml          # Configuration settings
├── requirements.txt     # Python dependencies
├── progress.json        # Backfill progress tracker
└── data/
    └── hrrr-analysis-snowfall.zarr/  # Zarr dataset (stored with Git LFS)
```

## Quick Start

**Choose your storage approach:**

### Option 1: Git LFS (Recommended for Quick Start)
👉 **See [QUICKSTART_GIT_LFS.md](QUICKSTART_GIT_LFS.md)** for step-by-step instructions

All data stored in GitHub. Simple setup, no cloud accounts needed.

### Option 2: Cloud Storage (Recommended for Production)
👉 **See [CLOUD_STORAGE.md](CLOUD_STORAGE.md)** and [QUICKSTART.md](QUICKSTART.md)

Lower cost for large datasets. Requires S3/GCS/Azure account.

## Setup (Git LFS Approach)

### Prerequisites

- Python 3.11+
- Git with LFS extension
- eccodes library (for GRIB2 reading)

### Installation

1. **Clone the repository**:
   ```bash
   git clone <your-repo-url>
   cd HRRR_ASNOW_ZARR
   ```

2. **Install system dependencies**:

   **Ubuntu/Debian**:
   ```bash
   sudo apt-get install libeccodes-dev libeccodes-tools
   ```

   **macOS**:
   ```bash
   brew install eccodes
   ```

3. **Install Python dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

## Usage

### 1. Initialize Zarr Store

Create an empty zarr store with the proper structure:

```bash
python src/template.py data/hrrr-analysis-snowfall.zarr
```

### 2. Download Data Manually

Download ASNOW data for a specific date/hour:

```bash
python src/downloader.py 2024-01-15 12 tmp/
```

### 3. Process GRIB2 Files

Process downloaded GRIB2 files and append to zarr:

```bash
python src/processor.py data/hrrr-analysis-snowfall.zarr tmp/*.grib2
```

### 4. Run Backfill

Process a date range automatically:

```bash
python src/backfill.py \
  --start 2024-01-01 \
  --end 2024-01-31 \
  --zarr data/hrrr-analysis-snowfall.zarr \
  --resume
```

Options:
- `--start`: Start date (YYYY-MM-DD)
- `--end`: End date (YYYY-MM-DD)
- `--zarr`: Path to zarr store
- `--config`: Configuration file (default: config.yaml)
- `--tmp`: Temporary directory for downloads (default: tmp)
- `--resume`: Skip existing timesteps
- `--save-stats`: Output file for statistics

## GitHub Actions Automated Backfill

The repository includes automated workflows that progressively build the complete dataset.

### Automatic Scheduled Runs

The backfill workflow runs daily at 06:00 UTC, processing 7 days at a time:

- Reads `progress.json` to determine next date range
- Downloads data with rate limiting (10 requests/minute)
- Processes and appends to zarr store
- Commits updated data and progress
- Continues until reaching present day

### Manual Trigger

You can manually trigger a backfill for specific dates:

1. Go to **Actions** → **HRRR ASNOW Backfill**
2. Click **Run workflow**
3. Enter start and end dates
4. Click **Run workflow**

### Progress Tracking

Check `progress.json` to see:
- Last completed date
- Last run timestamp
- Current status

### Storage Considerations

⚠️ **Important**: The complete dataset (~20GB compressed) may exceed GitHub's repository size limits.

**Options**:

1. **Cloud Storage** (Recommended):
   - Modify workflow to upload to S3, Google Cloud Storage, or Azure Blob
   - Store only metadata in Git

2. **Git LFS**:
   - Use Git Large File Storage for zarr chunks
   - Note: LFS has bandwidth limits

3. **External Hosting**:
   - Store zarr on a dedicated server
   - Keep code only in GitHub

## Configuration

Edit `config.yaml` to customize:

```yaml
# Date range
time_range:
  start_date: "2014-10-01"
  end_date: "2026-03-02"

# Rate limiting (be kind to NOMADS)
rate_limiting:
  requests_per_minute: 10
  retry_attempts: 3

# Zarr encoding
zarr_encoding:
  compressor: "zstd"
  compression_level: 5
  chunks:
    time: 24  # Hours per chunk
```

## Data Access

### Reading the Zarr Store

```python
import xarray as xr

# Open zarr store
ds = xr.open_zarr('data/hrrr-analysis-snowfall.zarr')

# Select a time range
ds_subset = ds.sel(time=slice('2024-01-01', '2024-01-31'))

# Get data for a specific point
lat, lon = 40.0, -105.0
# ... convert to x, y coordinates ...
snowfall = ds.sel(x=x, y=y, method='nearest')['accumulated_snowfall']

print(snowfall)
```

### Combining with Dynamical.org HRRR Analysis

```python
import xarray as xr

# Open both datasets
hrrr_analysis = xr.open_zarr('https://data.dynamical.org/noaa/hrrr/analysis/latest.zarr')
hrrr_snowfall = xr.open_zarr('data/hrrr-analysis-snowfall.zarr')

# Extract point data
x, y = ...  # HRRR grid coordinates
time_range = slice('2024-01-01', '2024-01-31')

# Get temperature, wind, etc. from Dynamical.org
temp = hrrr_analysis.sel(time=time_range, x=x, y=y)['temperature_2m']

# Get snowfall from this dataset
snowfall = hrrr_snowfall.sel(time=time_range, x=x, y=y)['accumulated_snowfall']

# Combine for analysis
combined = xr.Dataset({
    'temperature': temp,
    'snowfall': snowfall
})
```

## Storage Requirements

- **Uncompressed**: ~8GB per year
- **Compressed (zstd)**: ~2-3GB per year
- **Full archive (2014-2026)**: ~20-25GB compressed

## Performance

- **Download rate**: ~10 files/minute (NOMADS rate limit)
- **Processing rate**: ~100-200 files/minute (local)
- **Backfill time estimate**:
  - 1 year: ~2-3 days (with rate limiting)
  - Full 12 years: ~30-40 days

## Validation

The repository includes validation scripts to check data quality:

```bash
# Validate a specific date
python scripts/validate.py --date 2024-01-15

# Check temporal continuity
python scripts/validate.py --check-continuity --start 2024-01-01 --end 2024-01-31
```

## Contributing

Contributions welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## References

- [NOAA NOMADS HRRR Data](https://nomads.ncep.noaa.gov/)
- [Dynamical.org HRRR Analysis](https://dynamical.org/catalog/noaa-hrrr-analysis/)
- [HRRR Model Documentation](https://www.nco.ncep.noaa.gov/pmb/products/hrrr/)
- [Zarr Format](https://zarr.dev/)
- [CF Conventions](https://cfconventions.org/)

## License

This project is licensed under the MIT License. The HRRR data itself is public domain (NOAA).

## Acknowledgments

- NOAA/NCEP for providing HRRR data through NOMADS
- Dynamical.org for inspiration and the main HRRR Analysis dataset
- The zarr, xarray, and cfgrib communities

---

**Status**: 🚧 Actively building dataset

Check `progress.json` for current backfill status.
