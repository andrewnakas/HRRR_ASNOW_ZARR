"""
Utility scripts for common operations
"""

import xarray as xr
import json
from datetime import datetime
from pathlib import Path
import argparse


def show_zarr_info(zarr_path):
    """Display information about zarr store"""
    print(f"\n{'='*60}")
    print("Zarr Store Information")
    print(f"{'='*60}")

    try:
        ds = xr.open_zarr(zarr_path)

        print(f"\nPath: {zarr_path}")
        print(f"\nDimensions:")
        for dim, size in ds.dims.items():
            print(f"  {dim}: {size}")

        print(f"\nCoordinates:")
        for coord in ds.coords:
            print(f"  {coord}")

        print(f"\nData variables:")
        for var in ds.data_vars:
            shape = ds[var].shape
            dtype = ds[var].dtype
            print(f"  {var}: {shape} ({dtype})")

        if len(ds.time) > 0:
            print(f"\nTime range:")
            print(f"  Start: {ds.time.values[0]}")
            print(f"  End: {ds.time.values[-1]}")
            print(f"  Total timesteps: {len(ds.time)}")

            # Calculate coverage
            expected_hours = (ds.time.values[-1] - ds.time.values[0]).astype('timedelta64[h]').astype(int) + 1
            coverage_pct = len(ds.time) / expected_hours * 100
            print(f"  Coverage: {coverage_pct:.1f}% ({len(ds.time)}/{expected_hours} hours)")

        print(f"\nAttributes:")
        for attr, value in ds.attrs.items():
            print(f"  {attr}: {value}")

        # Size estimation
        zarr_dir = Path(zarr_path)
        if zarr_dir.exists():
            total_size = sum(f.stat().st_size for f in zarr_dir.rglob('*') if f.is_file())
            size_gb = total_size / (1024**3)
            print(f"\nStorage size: {size_gb:.2f} GB")

    except Exception as e:
        print(f"Error reading zarr store: {e}")
        return 1

    return 0


def show_progress(progress_file="progress.json"):
    """Display backfill progress"""
    print(f"\n{'='*60}")
    print("Backfill Progress")
    print(f"{'='*60}")

    try:
        with open(progress_file) as f:
            progress = json.load(f)

        print(f"\nLast completed date: {progress['last_completed_date']}")
        print(f"Last run: {progress['last_run']}")
        print(f"Status: {progress['status']}")

        if 'notes' in progress:
            print(f"Notes: {progress['notes']}")

        # Calculate progress
        start_date = datetime(2014, 10, 1)
        last_date = datetime.strptime(progress['last_completed_date'], '%Y-%m-%d')
        today = datetime.now()

        total_days = (today - start_date).days
        completed_days = (last_date - start_date).days
        progress_pct = completed_days / total_days * 100

        print(f"\nOverall progress: {progress_pct:.1f}%")
        print(f"  Completed: {completed_days} / {total_days} days")
        print(f"  Remaining: {total_days - completed_days} days")

        if completed_days > 0:
            # Estimate completion (assuming consistent daily progress)
            days_per_day = completed_days / max((datetime.now() - start_date).days, 1)
            days_remaining = total_days - completed_days
            # Don't provide timeline estimates per requirements

    except FileNotFoundError:
        print(f"Progress file not found: {progress_file}")
        return 1
    except Exception as e:
        print(f"Error reading progress file: {e}")
        return 1

    return 0


def extract_point(zarr_path, lat, lon, output_file=None):
    """Extract time series for a specific lat/lon point"""
    print(f"\n{'='*60}")
    print("Point Extraction")
    print(f"{'='*60}")

    try:
        ds = xr.open_zarr(zarr_path)

        # Find nearest grid point
        # This is simplified - in practice you'd need proper coordinate transformation
        from pyproj import Transformer

        # HRRR projection
        hrrr_proj = "+proj=lcc +lat_0=38.5 +lon_0=-97.5 +lat_1=38.5 +lat_2=38.5 +x_0=0 +y_0=0 +R=6371229 +units=m +no_defs"
        transformer = Transformer.from_crs("EPSG:4326", hrrr_proj, always_xy=True)

        x_m, y_m = transformer.transform(lon, lat)

        # Select nearest point
        ds_point = ds.sel(x=x_m, y=y_m, method='nearest')

        print(f"\nRequested: lat={lat}, lon={lon}")
        print(f"Nearest grid point: x={float(ds_point.x):.0f}m, y={float(ds_point.y):.0f}m")

        # Extract accumulated_snowfall
        asnow = ds_point['accumulated_snowfall']

        print(f"\nTime series length: {len(asnow)}")
        print(f"ASNOW range: [{float(asnow.min()):.4f}, {float(asnow.max()):.4f}] m")

        # Save to CSV if requested
        if output_file:
            df = asnow.to_dataframe()
            df.to_csv(output_file)
            print(f"\n✓ Saved to {output_file}")

    except Exception as e:
        print(f"Error extracting point: {e}")
        return 1

    return 0


def main():
    parser = argparse.ArgumentParser(description='HRRR ASNOW utility scripts')
    subparsers = parser.add_subparsers(dest='command', help='Command to run')

    # Info command
    info_parser = subparsers.add_parser('info', help='Show zarr store information')
    info_parser.add_argument('--zarr', default='data/hrrr-analysis-snowfall.zarr')

    # Progress command
    progress_parser = subparsers.add_parser('progress', help='Show backfill progress')
    progress_parser.add_argument('--file', default='progress.json')

    # Extract command
    extract_parser = subparsers.add_parser('extract', help='Extract point time series')
    extract_parser.add_argument('--zarr', default='data/hrrr-analysis-snowfall.zarr')
    extract_parser.add_argument('--lat', type=float, required=True)
    extract_parser.add_argument('--lon', type=float, required=True)
    extract_parser.add_argument('--output', type=str, help='Output CSV file')

    args = parser.parse_args()

    if args.command == 'info':
        return show_zarr_info(args.zarr)
    elif args.command == 'progress':
        return show_progress(args.file)
    elif args.command == 'extract':
        return extract_point(args.zarr, args.lat, args.lon, args.output)
    else:
        parser.print_help()
        return 1


if __name__ == "__main__":
    exit(main())
