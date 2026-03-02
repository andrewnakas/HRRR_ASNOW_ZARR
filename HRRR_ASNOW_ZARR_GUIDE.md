# HRRR ASNOW Zarr Archive Creation Guide

## Overview

This guide explains how to create a sister zarr archive to Dynamical.org's HRRR Analysis dataset that includes the **ASNOW (Accumulated Snowfall)** variable missing from their catalog.

**Why This Is Needed:**
- Dynamical.org's HRRR Analysis lacks accumulation variables (ASNOW, WEASD, SNOD)
- NOMADS provides ASNOW as the official HRRR model output in meters
- Our current approach (precipitation × percent_frozen × temperature ratio) is an approximation
- This archive will provide the **actual HRRR model snowfall output**

## Architecture

### Data Sources

1. **NOMADS HRRR GRIB2 Files**
   - URL: `https://nomads.ncep.noaa.gov/pub/data/nccf/com/hrrr/prod/`
   - Variable: `ASNOW` (Total Snowfall [m])
   - Temporal Resolution: Hourly analysis files
   - Spatial Resolution: 3km Lambert Conformal Conic projection
   - Coverage: CONUS (Continental United States)

2. **HRRR Coordinate System**
   - Projection: Lambert Conformal Conic
   - Parameters: `+proj=lcc +lat_0=38.5 +lon_0=-97.5 +lat_1=38.5 +lat_2=38.5 +x_0=0 +y_0=0 +R=6371229 +units=m +no_defs`
   - Grid: 1799 x 1059 points

### Target Zarr Structure

```
hrrr-analysis-snowfall.zarr/
├── time (dimension: unlimited)
├── x (dimension: 1799)
├── y (dimension: 1059)
├── latitude (coordinate: [y, x])
├── longitude (coordinate: [y, x])
├── projection (metadata)
└── accumulated_snowfall (data variable: [time, y, x])
    ├── units: "m"
    ├── long_name: "Total Accumulated Snowfall"
    ├── standard_name: "snowfall_amount"
    └── description: "HRRR model ASNOW output - physical snow depth"
```

## Implementation Plan

### Phase 1: Setup Dependencies

**Required Python Packages:**
```bash
pip install zarr[v3] xarray cfgrib eccodes numpy pyproj dask requests
```

**System Dependencies:**
- `eccodes` (for GRIB2 reading)
- `curl` or `wget` (for downloading NOMADS data)

### Phase 2: Data Download Strategy

**Option A: Direct NOMADS Download**
```python
import requests
from datetime import datetime, timedelta

def download_hrrr_analysis(date):
    """Download HRRR analysis file for specific date/hour"""
    base_url = "https://nomads.ncep.noaa.gov/pub/data/nccf/com/hrrr/prod"
    date_str = date.strftime("%Y%m%d")
    hour_str = date.strftime("%H")

    # HRRR analysis file naming: hrrr.t{HH}z.wrfsfcf00.grib2
    filename = f"hrrr.t{hour_str}z.wrfsfcf00.grib2"
    url = f"{base_url}/hrrr.{date_str}/conus/{filename}"

    response = requests.get(url, stream=True)
    if response.status_code == 200:
        with open(filename, 'wb') as f:
            f.write(response.content)
        return filename
    else:
        raise Exception(f"Failed to download: {response.status_code}")
```

**Option B: NOMADS Grib Filter (Recommended for bandwidth)**
```python
def download_asnow_only(date):
    """Download only ASNOW variable using NOMADS grib filter"""
    base_url = "https://nomads.ncep.noaa.gov/cgi-bin/filter_hrrr_2d.pl"

    date_str = date.strftime("%Y%m%d")
    hour_str = date.strftime("%H")

    params = {
        'file': f'hrrr.t{hour_str}z.wrfsfcf00.grib2',
        'lev_surface': 'on',
        'var_ASNOW': 'on',
        'dir': f'/hrrr.{date_str}/conus'
    }

    response = requests.get(base_url, params=params, stream=True)
    if response.status_code == 200:
        filename = f"hrrr_asnow_{date_str}_{hour_str}.grib2"
        with open(filename, 'wb') as f:
            f.write(response.content)
        return filename
    else:
        raise Exception(f"Failed to download filtered GRIB2")
```

### Phase 3: GRIB2 to Zarr Reformatter

**Following Dynamical.org Reformatters Pattern:**

```python
import xarray as xr
import zarr
import numpy as np
from pyproj import Transformer

class HRRRSnowfallTemplateConfig:
    """Template configuration for HRRR ASNOW zarr archive"""

    @staticmethod
    def create_template():
        # HRRR grid dimensions
        nx, ny = 1799, 1059

        # Create coordinate arrays
        x = np.arange(nx) * 3000  # 3km resolution in meters
        y = np.arange(ny) * 3000

        # Create lat/lon grids
        hrrr_proj = "+proj=lcc +lat_0=38.5 +lon_0=-97.5 +lat_1=38.5 +lat_2=38.5 +x_0=0 +y_0=0 +R=6371229 +units=m +no_defs"
        transformer = Transformer.from_crs(hrrr_proj, "EPSG:4326", always_xy=True)

        xx, yy = np.meshgrid(x, y)
        lons, lats = transformer.transform(xx, yy)

        # Create dataset template
        ds = xr.Dataset(
            data_vars={
                'accumulated_snowfall': (
                    ['time', 'y', 'x'],
                    np.zeros((0, ny, nx), dtype=np.float32),
                    {
                        'units': 'm',
                        'long_name': 'Total Accumulated Snowfall',
                        'standard_name': 'snowfall_amount',
                        'description': 'HRRR model ASNOW output - physical snow depth',
                        '_FillValue': np.nan,
                    }
                ),
                'latitude': (
                    ['y', 'x'],
                    lats.astype(np.float32),
                    {
                        'units': 'degrees_north',
                        'long_name': 'Latitude',
                        'standard_name': 'latitude'
                    }
                ),
                'longitude': (
                    ['y', 'x'],
                    lons.astype(np.float32),
                    {
                        'units': 'degrees_east',
                        'long_name': 'Longitude',
                        'standard_name': 'longitude'
                    }
                )
            },
            coords={
                'time': (
                    'time',
                    np.array([], dtype='datetime64[ns]'),
                    {
                        'long_name': 'Time',
                        'standard_name': 'time'
                    }
                ),
                'x': (
                    'x',
                    x,
                    {
                        'units': 'm',
                        'long_name': 'x coordinate of projection',
                        'standard_name': 'projection_x_coordinate'
                    }
                ),
                'y': (
                    'y',
                    y,
                    {
                        'units': 'm',
                        'long_name': 'y coordinate of projection',
                        'standard_name': 'projection_y_coordinate'
                    }
                )
            },
            attrs={
                'title': 'HRRR Analysis Accumulated Snowfall',
                'source': 'NOAA NCEP HRRR Model',
                'institution': 'NOAA/NCEP',
                'grid_mapping': 'lambert_conformal_conic',
                'Conventions': 'CF-1.8'
            }
        )

        # Add grid mapping variable
        ds['lambert_conformal_conic'] = xr.DataArray(
            data=0,
            attrs={
                'grid_mapping_name': 'lambert_conformal_conic',
                'latitude_of_projection_origin': 38.5,
                'longitude_of_central_meridian': -97.5,
                'standard_parallel': [38.5, 38.5],
                'earth_radius': 6371229.0
            }
        )

        return ds

class HRRRSnowfallRegionJob:
    """Process individual HRRR analysis files and write to zarr"""

    @staticmethod
    def process_file(grib_file, zarr_store, time_index):
        """
        Read ASNOW from GRIB2 and append to zarr store

        Args:
            grib_file: Path to HRRR GRIB2 file
            zarr_store: Path to zarr archive
            time_index: Time dimension index for this file
        """
        # Read ASNOW from GRIB2 using cfgrib
        ds_grib = xr.open_dataset(
            grib_file,
            engine='cfgrib',
            backend_kwargs={
                'filter_by_keys': {'name': 'Total snowfall', 'typeOfLevel': 'surface'}
            }
        )

        # Extract ASNOW data
        asnow = ds_grib['asnow'].values  # In meters
        time = ds_grib['time'].values

        # Open zarr store in append mode
        zarr_group = zarr.open_group(zarr_store, mode='a')

        # Append time
        current_times = zarr_group['time'][:]
        new_times = np.append(current_times, time)
        zarr_group['time'][:] = new_times

        # Append ASNOW data
        zarr_group['accumulated_snowfall'].append(asnow[np.newaxis, :, :], axis=0)

        print(f"Processed {time}: ASNOW min={asnow.min():.4f}m, max={asnow.max():.4f}m")

class HRRRSnowfallBackfill:
    """Orchestrate backfill of historical HRRR ASNOW data"""

    def __init__(self, zarr_path, start_date, end_date):
        self.zarr_path = zarr_path
        self.start_date = start_date
        self.end_date = end_date

    def initialize_zarr(self):
        """Create empty zarr store from template"""
        template = HRRRSnowfallTemplateConfig.create_template()

        # Encoding for efficient storage
        encoding = {
            'accumulated_snowfall': {
                'compressor': zarr.Blosc(cname='zstd', clevel=5, shuffle=2),
                'chunks': (24, 1059, 1799),  # 24 hours at a time
            }
        }

        template.to_zarr(self.zarr_path, mode='w', encoding=encoding)
        print(f"Initialized zarr store at {self.zarr_path}")

    def backfill(self):
        """Download and process all files in date range"""
        current = self.start_date
        time_idx = 0

        while current <= self.end_date:
            for hour in range(24):
                current_dt = current.replace(hour=hour)

                try:
                    # Download GRIB2 file (ASNOW only)
                    grib_file = download_asnow_only(current_dt)

                    # Process and append to zarr
                    HRRRSnowfallRegionJob.process_file(
                        grib_file,
                        self.zarr_path,
                        time_idx
                    )

                    time_idx += 1

                    # Clean up GRIB file
                    os.remove(grib_file)

                except Exception as e:
                    print(f"Error processing {current_dt}: {e}")
                    continue

            current += timedelta(days=1)

        print(f"Backfill complete: {time_idx} hours processed")
```

### Phase 4: Usage Example

```python
from datetime import datetime

# Initialize backfill job
backfill = HRRRSnowfallBackfill(
    zarr_path='s3://your-bucket/hrrr-analysis-snowfall.zarr',
    start_date=datetime(2018, 1, 1),  # HRRR ASNOW available from ~2018
    end_date=datetime(2026, 3, 1)
)

# Create zarr store
backfill.initialize_zarr()

# Run backfill (this will take a while!)
backfill.backfill()
```

### Phase 5: Integration with Tree60 Weather

**Update HRRR Analysis Function:**

```python
# functions/hrrr_analysis.py

import xarray as xr

HRRR_DYNAMICAL_URL = "https://data.dynamical.org/noaa/hrrr/analysis/latest.zarr"
HRRR_SNOWFALL_URL = "s3://your-bucket/hrrr-analysis-snowfall.zarr"  # Your sister zarr

def get_hrrr_historical_data(lat, lon, start_date, end_date):
    """Hybrid approach: Dynamical for most vars, custom zarr for ASNOW"""

    # Get all variables except snowfall from Dynamical.org
    ds_dynamical = xr.open_zarr(HRRR_DYNAMICAL_URL, consolidated=True)
    ds_dynamical = ds_dynamical.sel(time=slice(start_date, end_date))

    x, y = latlon_to_hrrr_xy(lat, lon)
    ds_point = ds_dynamical.sel(x=x, y=y, method="nearest")

    # Extract all variables from Dynamical
    temp_2m = ds_point["temperature_2m"].values
    precip = ds_point["precipitation_surface"].values
    # ... all other variables

    # Get ASNOW from your sister zarr
    ds_snowfall = xr.open_zarr(HRRR_SNOWFALL_URL, consolidated=True)
    ds_snowfall = ds_snowfall.sel(time=slice(start_date, end_date))
    ds_snowfall_point = ds_snowfall.sel(x=x, y=y, method="nearest")

    # Extract actual HRRR ASNOW (already in meters, convert to cm)
    asnow = ds_snowfall_point["accumulated_snowfall"].values * 100  # m to cm

    # Calculate hourly snowfall from accumulated
    hourly_snowfall = np.diff(asnow, prepend=0)  # Hourly increments
    hourly_snowfall = np.maximum(hourly_snowfall, 0)  # Remove resets

    # Aggregate to daily
    times = ds_point.time.values
    daily_data = aggregate_to_daily(
        times, temp_2m, precip, wind_speed, rh, pressure,
        cloud_cover, solar_rad,
        hourly_snowfall  # Use actual HRRR ASNOW instead of calculated
    )

    return {
        "success": True,
        "location": {"lat": lat, "lon": lon, "x": float(x), "y": float(y)},
        "source": "HRRR Analysis (Dynamical.org + NOMADS ASNOW)",
        "timeRange": {"start": start_date, "end": end_date},
        "daily": daily_data
    }
```

## Performance Considerations

### Storage Requirements
- **Uncompressed**: ~8GB per year (1799 × 1059 × 8760 hours × 4 bytes)
- **With Blosc compression**: ~2-3GB per year (3:1 compression ratio typical)
- **For 8 years (2018-2026)**: ~20GB compressed

### Download Strategy
- **Sequential download**: ~30 days per day of processing (rate limited by NOMADS)
- **Parallel download**: Use multiple workers with rate limiting
- **Recommended**: Download to S3 first, then process in bulk

### Cloud Deployment (Kubernetes)
Following Dynamical's approach:

```yaml
# kubernetes/backfill-job.yaml
apiVersion: batch/v1
kind: Job
metadata:
  name: hrrr-asnow-backfill
spec:
  parallelism: 10  # Process 10 days simultaneously
  completions: 2920  # 8 years × 365 days
  template:
    spec:
      containers:
      - name: backfill-worker
        image: your-registry/hrrr-snowfall-reformatter:latest
        env:
        - name: WORKER_INDEX
          valueFrom:
            fieldRef:
              fieldPath: metadata.annotations['batch.kubernetes.io/job-completion-index']
        - name: TOTAL_WORKERS
          value: "10"
        - name: ZARR_STORE
          value: "s3://your-bucket/hrrr-analysis-snowfall.zarr"
```

## Validation

### Data Quality Checks

```python
import matplotlib.pyplot as plt

def validate_snowfall_data(zarr_path, sample_date):
    """Validate ASNOW data quality"""
    ds = xr.open_zarr(zarr_path)
    ds_sample = ds.sel(time=sample_date, method='nearest')

    # Check 1: Value ranges (ASNOW should be 0-5m typically)
    asnow = ds_sample['accumulated_snowfall'].values
    print(f"ASNOW range: {asnow.min():.4f}m to {asnow.max():.4f}m")

    # Check 2: Spatial coherence (no isolated anomalies)
    plt.figure(figsize=(12, 8))
    plt.imshow(asnow, cmap='Blues', vmin=0, vmax=1)
    plt.colorbar(label='Accumulated Snowfall (m)')
    plt.title(f'HRRR ASNOW - {sample_date}')
    plt.savefig('asnow_validation.png')

    # Check 3: Temporal continuity (no sudden jumps)
    ds_week = ds.sel(time=slice(sample_date, sample_date + timedelta(days=7)))
    center_point = ds_week.isel(x=899, y=529)  # Center of CONUS

    plt.figure(figsize=(10, 4))
    plt.plot(center_point.time, center_point['accumulated_snowfall'])
    plt.ylabel('ASNOW (m)')
    plt.title('Temporal Continuity Check')
    plt.savefig('asnow_temporal.png')
```

## Cost Estimate

### AWS S3 Storage
- **Storage**: 20GB × $0.023/GB/month = $0.46/month
- **Requests**: Negligible for historical data

### Data Transfer
- **NOMADS to local**: Free (NOAA data)
- **Local to S3**: Free (upload)
- **S3 to Cloud Functions**: $0.09/GB × ~20GB = $1.80 (one-time per full read)

**Total ongoing cost: ~$0.50/month**

## Timeline Estimate

1. **Setup and testing**: 1 day
2. **Backfill script development**: 2 days
3. **Sequential backfill (8 years)**: 8-10 days
4. **Validation and debugging**: 1-2 days
5. **Integration with Tree60 Weather**: 1 day

**Total: ~2 weeks start to finish**

## Next Steps

1. Set up AWS S3 bucket for zarr storage
2. Create Docker container with dependencies
3. Test download and processing for single day
4. Run backfill for recent 30 days
5. Validate data quality
6. Deploy full backfill job
7. Update Tree60 Weather to use sister zarr
8. Monitor and maintain operational updates

## References

- [NOMADS HRRR Data](https://nomads.ncep.noaa.gov/)
- [Dynamical.org Reformatters](https://github.com/dynamical-org/reformatters)
- [Zarr V3 Specification](https://zarr-specs.readthedocs.io/)
- [HRRR GRIB2 Variables](https://www.nco.ncep.noaa.gov/pmb/products/hrrr/)
- [CF Conventions](https://cfconventions.org/)
