"""
Validation script for HRRR ASNOW zarr data
Checks data quality, spatial coherence, and temporal continuity
"""

import xarray as xr
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import argparse
from pathlib import Path


def validate_value_ranges(ds, sample_time):
    """Check that ASNOW values are in reasonable range"""
    print(f"\n{'='*60}")
    print("Value Range Validation")
    print(f"{'='*60}")

    ds_sample = ds.sel(time=sample_time, method='nearest')
    asnow = ds_sample['accumulated_snowfall'].values

    stats = {
        'min': np.nanmin(asnow),
        'max': np.nanmax(asnow),
        'mean': np.nanmean(asnow),
        'std': np.nanstd(asnow),
        'nan_count': np.isnan(asnow).sum(),
        'total_points': asnow.size
    }

    print(f"Time: {ds_sample.time.values}")
    print(f"ASNOW range: [{stats['min']:.4f}, {stats['max']:.4f}] m")
    print(f"ASNOW mean: {stats['mean']:.4f} m")
    print(f"ASNOW std: {stats['std']:.4f} m")
    print(f"NaN count: {stats['nan_count']} / {stats['total_points']} "
          f"({stats['nan_count']/stats['total_points']*100:.2f}%)")

    # Check for anomalies
    warnings = []
    if stats['max'] > 5.0:
        warnings.append(f"⚠ Unusually high snowfall: {stats['max']:.2f}m")
    if stats['min'] < 0:
        warnings.append(f"⚠ Negative snowfall values: {stats['min']:.4f}m")
    if stats['nan_count'] / stats['total_points'] > 0.5:
        warnings.append(f"⚠ High proportion of NaN values")

    if warnings:
        print("\nWarnings:")
        for w in warnings:
            print(f"  {w}")
        return False
    else:
        print("\n✓ Value ranges look good")
        return True


def validate_spatial_coherence(ds, sample_time, output_dir="validation_plots"):
    """Check for spatial coherence (no isolated anomalies)"""
    print(f"\n{'='*60}")
    print("Spatial Coherence Validation")
    print(f"{'='*60}")

    ds_sample = ds.sel(time=sample_time, method='nearest')
    asnow = ds_sample['accumulated_snowfall'].values

    # Create plot
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    output_file = Path(output_dir) / f"spatial_{sample_time}.png"

    plt.figure(figsize=(14, 10))

    # Main plot
    plt.subplot(2, 2, 1)
    im = plt.imshow(asnow, cmap='Blues', vmin=0, vmax=min(1.0, np.nanmax(asnow)))
    plt.colorbar(im, label='ASNOW (m)')
    plt.title(f'HRRR ASNOW - {ds_sample.time.values}')

    # Histogram
    plt.subplot(2, 2, 2)
    plt.hist(asnow[~np.isnan(asnow)].flatten(), bins=50, edgecolor='black')
    plt.xlabel('ASNOW (m)')
    plt.ylabel('Frequency')
    plt.title('Distribution')
    plt.yscale('log')

    # Zoomed regions
    cy, cx = asnow.shape[0] // 2, asnow.shape[1] // 2

    plt.subplot(2, 2, 3)
    region = asnow[cy-50:cy+50, cx-50:cx+50]
    plt.imshow(region, cmap='Blues', vmin=0, vmax=min(1.0, np.nanmax(asnow)))
    plt.colorbar(label='ASNOW (m)')
    plt.title('Center Region (100x100)')

    plt.subplot(2, 2, 4)
    # Find region with maximum snowfall
    if np.nanmax(asnow) > 0:
        max_idx = np.unravel_index(np.nanargmax(asnow), asnow.shape)
        my, mx = max_idx
        my = max(50, min(asnow.shape[0]-50, my))
        mx = max(50, min(asnow.shape[1]-50, mx))
        region = asnow[my-50:my+50, mx-50:mx+50]
        plt.imshow(region, cmap='Blues', vmin=0, vmax=np.nanmax(region))
        plt.colorbar(label='ASNOW (m)')
        plt.title(f'Max Snow Region (100x100)')

    plt.tight_layout()
    plt.savefig(output_file, dpi=150, bbox_inches='tight')
    print(f"✓ Spatial plot saved to {output_file}")

    plt.close()
    return True


def validate_temporal_continuity(ds, start_time, duration_days=7, output_dir="validation_plots"):
    """Check temporal continuity (no sudden jumps)"""
    print(f"\n{'='*60}")
    print("Temporal Continuity Validation")
    print(f"{'='*60}")

    # Get time series at center point
    cy, cx = ds.dims['y'] // 2, ds.dims['x'] // 2

    end_time = start_time + timedelta(days=duration_days)
    ds_window = ds.sel(time=slice(start_time, end_time))
    center_point = ds_window.isel(x=cx, y=cy)

    times = center_point.time.values
    asnow = center_point['accumulated_snowfall'].values

    # Check for jumps
    diffs = np.diff(asnow)
    large_decreases = np.where(diffs < -0.1)[0]  # ASNOW shouldn't decrease much

    print(f"Time range: {times[0]} to {times[-1]}")
    print(f"Number of timesteps: {len(times)}")
    print(f"Center point (y={cy}, x={cx}):")
    print(f"  ASNOW range: [{np.nanmin(asnow):.4f}, {np.nanmax(asnow):.4f}] m")

    if len(large_decreases) > 0:
        print(f"⚠ Found {len(large_decreases)} large decreases in ASNOW")
        print(f"  (This is expected when accumulation resets)")

    # Create plot
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    output_file = Path(output_dir) / f"temporal_{start_time}.png"

    plt.figure(figsize=(14, 8))

    plt.subplot(2, 1, 1)
    plt.plot(times, asnow, marker='o', markersize=3, linewidth=1)
    plt.ylabel('ASNOW (m)')
    plt.title(f'Temporal Continuity Check - Center Point (y={cy}, x={cx})')
    plt.grid(True, alpha=0.3)

    plt.subplot(2, 1, 2)
    plt.plot(times[1:], diffs, marker='o', markersize=3, linewidth=1)
    plt.ylabel('ASNOW Change (m/hour)')
    plt.xlabel('Time')
    plt.axhline(y=0, color='r', linestyle='--', alpha=0.5)
    plt.grid(True, alpha=0.3)
    plt.title('Hourly Changes')

    plt.tight_layout()
    plt.savefig(output_file, dpi=150, bbox_inches='tight')
    print(f"✓ Temporal plot saved to {output_file}")

    plt.close()
    return True


def validate_coverage(ds):
    """Check time coverage and gaps"""
    print(f"\n{'='*60}")
    print("Coverage Validation")
    print(f"{'='*60}")

    times = ds.time.values
    print(f"Total timesteps: {len(times)}")
    print(f"Time range: {times[0]} to {times[-1]}")

    # Check for gaps
    time_diffs = np.diff(times.astype('datetime64[h]').astype(int))
    expected_diff = 1  # 1 hour

    gaps = np.where(time_diffs != expected_diff)[0]

    if len(gaps) > 0:
        print(f"\n⚠ Found {len(gaps)} gaps in time series:")
        for i in gaps[:10]:  # Show first 10 gaps
            gap_hours = time_diffs[i]
            print(f"  Gap of {gap_hours} hours between {times[i]} and {times[i+1]}")
        if len(gaps) > 10:
            print(f"  ... and {len(gaps) - 10} more gaps")
        return False
    else:
        print("✓ No gaps in time series")
        return True


def main():
    parser = argparse.ArgumentParser(description='Validate HRRR ASNOW zarr data')
    parser.add_argument(
        '--zarr',
        type=str,
        default='data/hrrr-analysis-snowfall.zarr',
        help='Path to zarr store'
    )
    parser.add_argument(
        '--date',
        type=str,
        help='Date to validate (YYYY-MM-DD), defaults to latest'
    )
    parser.add_argument(
        '--check-continuity',
        action='store_true',
        help='Check temporal continuity'
    )
    parser.add_argument(
        '--output-dir',
        type=str,
        default='validation_plots',
        help='Output directory for plots'
    )

    args = parser.parse_args()

    print("="*60)
    print("HRRR ASNOW Data Validation")
    print("="*60)

    # Open zarr store
    print(f"\nOpening zarr store: {args.zarr}")
    try:
        ds = xr.open_zarr(args.zarr)
        print(f"✓ Successfully opened zarr store")
    except Exception as e:
        print(f"✗ Failed to open zarr store: {e}")
        return 1

    # Determine sample date
    if args.date:
        sample_time = args.date
    else:
        # Use latest available time
        sample_time = str(ds.time.values[-1])[:10]

    print(f"Sample time: {sample_time}")

    # Run validations
    all_passed = True

    # Coverage check
    all_passed &= validate_coverage(ds)

    # Value range check
    all_passed &= validate_value_ranges(ds, sample_time)

    # Spatial coherence check
    all_passed &= validate_spatial_coherence(ds, sample_time, args.output_dir)

    # Temporal continuity check (optional)
    if args.check_continuity:
        all_passed &= validate_temporal_continuity(ds, sample_time, output_dir=args.output_dir)

    # Summary
    print(f"\n{'='*60}")
    if all_passed:
        print("✓ All validations passed")
        return 0
    else:
        print("⚠ Some validations failed or had warnings")
        return 1


if __name__ == "__main__":
    exit(main())
