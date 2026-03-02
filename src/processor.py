"""
GRIB2 to Zarr Processor
Reads ASNOW from HRRR GRIB2 files and appends to zarr store
"""

import xarray as xr
import zarr
import numpy as np
from pathlib import Path
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class HRRRSnowfallProcessor:
    """Process HRRR GRIB2 files and write ASNOW to zarr store"""

    def __init__(self, zarr_path):
        """
        Initialize processor

        Args:
            zarr_path: Path to zarr store
        """
        self.zarr_path = zarr_path

        # Verify zarr store exists
        if not Path(zarr_path).exists():
            raise FileNotFoundError(
                f"Zarr store not found at {zarr_path}. "
                "Run template.py first to initialize."
            )

    def read_asnow_from_grib(self, grib_file):
        """
        Read ASNOW variable from HRRR GRIB2 file

        Args:
            grib_file: Path to GRIB2 file

        Returns:
            tuple: (time, asnow_data) where time is datetime64 and asnow_data is numpy array
        """
        try:
            # Read GRIB2 using cfgrib
            # Filter for ASNOW (Total snowfall at surface)
            ds_grib = xr.open_dataset(
                grib_file,
                engine='cfgrib',
                backend_kwargs={
                    'filter_by_keys': {
                        'shortName': 'asnow',
                        'typeOfLevel': 'surface'
                    }
                }
            )

            # Extract time and data
            time = ds_grib['time'].values
            asnow = ds_grib['asnow'].values  # Already in meters

            # Get valid time (forecast reference time)
            if 'valid_time' in ds_grib.coords:
                time = ds_grib['valid_time'].values

            return time, asnow

        except Exception as e:
            logger.error(f"Error reading GRIB2 file {grib_file}: {e}")
            raise

    def append_to_zarr(self, time, asnow_data):
        """
        Append ASNOW data to zarr store

        Args:
            time: numpy datetime64 timestamp
            asnow_data: 2D numpy array of ASNOW values (meters)

        Returns:
            bool: True if successful
        """
        try:
            # Open zarr store in append mode
            zarr_group = zarr.open_group(self.zarr_path, mode='a')

            # Get current time dimension size
            current_times = zarr_group['time'][:]
            current_size = len(current_times)

            # Check if this time already exists
            if len(current_times) > 0 and time in current_times:
                logger.warning(f"Time {time} already exists in zarr store, skipping")
                return False

            # Resize time dimension
            new_size = current_size + 1
            zarr_group['time'].resize(new_size)
            zarr_group['accumulated_snowfall'].resize(new_size, zarr_group['accumulated_snowfall'].shape[1], zarr_group['accumulated_snowfall'].shape[2])

            # Append time
            zarr_group['time'][current_size] = time

            # Append ASNOW data (ensure correct shape: [1, y, x])
            if asnow_data.ndim == 2:
                asnow_data = asnow_data[np.newaxis, :, :]

            zarr_group['accumulated_snowfall'][current_size:new_size, :, :] = asnow_data

            # Verify the write
            written_data = zarr_group['accumulated_snowfall'][current_size, :, :]

            logger.info(
                f"✓ Appended {time}: "
                f"ASNOW range [{np.nanmin(written_data):.4f}, {np.nanmax(written_data):.4f}] m"
            )

            return True

        except Exception as e:
            logger.error(f"Error appending to zarr: {e}")
            raise

    def process_file(self, grib_file):
        """
        Process a single GRIB2 file and append to zarr

        Args:
            grib_file: Path to GRIB2 file

        Returns:
            bool: True if successful
        """
        logger.info(f"Processing {grib_file}")

        try:
            # Read ASNOW from GRIB2
            time, asnow_data = self.read_asnow_from_grib(grib_file)

            # Append to zarr
            success = self.append_to_zarr(time, asnow_data)

            return success

        except Exception as e:
            logger.error(f"Failed to process {grib_file}: {e}")
            return False

    def process_files(self, grib_files):
        """
        Process multiple GRIB2 files

        Args:
            grib_files: List of paths to GRIB2 files

        Returns:
            dict: Statistics about processing
        """
        stats = {
            'total': len(grib_files),
            'successful': 0,
            'failed': 0,
            'skipped': 0
        }

        for grib_file in grib_files:
            try:
                success = self.process_file(grib_file)

                if success:
                    stats['successful'] += 1
                else:
                    stats['skipped'] += 1

            except Exception as e:
                logger.error(f"Error processing {grib_file}: {e}")
                stats['failed'] += 1
                continue

        logger.info(
            f"Processing complete: "
            f"{stats['successful']} successful, "
            f"{stats['failed']} failed, "
            f"{stats['skipped']} skipped"
        )

        return stats

    def get_zarr_info(self):
        """Get information about the zarr store"""
        try:
            ds = xr.open_zarr(self.zarr_path)

            info = {
                'path': self.zarr_path,
                'time_range': (
                    str(ds.time.values[0]) if len(ds.time) > 0 else 'empty',
                    str(ds.time.values[-1]) if len(ds.time) > 0 else 'empty'
                ),
                'num_timesteps': len(ds.time),
                'grid_shape': (len(ds.y), len(ds.x)),
                'variables': list(ds.data_vars)
            }

            return info

        except Exception as e:
            logger.error(f"Error reading zarr info: {e}")
            return None


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 3:
        print("Usage: python processor.py <zarr_path> <grib_file1> [grib_file2 ...]")
        print("Example: python processor.py data/hrrr.zarr tmp/hrrr_asnow_20240115_12.grib2")
        sys.exit(1)

    zarr_path = sys.argv[1]
    grib_files = sys.argv[2:]

    # Create processor
    processor = HRRRSnowfallProcessor(zarr_path)

    # Show initial info
    info = processor.get_zarr_info()
    if info:
        print(f"Zarr store: {info['path']}")
        print(f"Current time range: {info['time_range']}")
        print(f"Timesteps: {info['num_timesteps']}")

    # Process files
    stats = processor.process_files(grib_files)

    # Show final info
    info = processor.get_zarr_info()
    if info:
        print(f"\nFinal time range: {info['time_range']}")
        print(f"Final timesteps: {info['num_timesteps']}")
