"""
Backfill Orchestration
Coordinates downloading and processing of historical HRRR ASNOW data
"""

import yaml
from datetime import datetime, timedelta
from pathlib import Path
import logging
import argparse
import json

from template import initialize_zarr_store
from downloader import NomadsDownloader
from processor import HRRRSnowfallProcessor

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class HRRRSnowfallBackfill:
    """Orchestrate backfill of historical HRRR ASNOW data"""

    def __init__(self, zarr_path, start_date, end_date, config_path="config.yaml"):
        """
        Initialize backfill orchestrator

        Args:
            zarr_path: Path to zarr store
            start_date: Start date (datetime or string YYYY-MM-DD)
            end_date: End date (datetime or string YYYY-MM-DD)
            config_path: Path to configuration file
        """
        self.zarr_path = zarr_path
        self.config_path = config_path

        # Parse dates
        if isinstance(start_date, str):
            self.start_date = datetime.strptime(start_date, "%Y-%m-%d")
        else:
            self.start_date = start_date

        if isinstance(end_date, str):
            self.end_date = datetime.strptime(end_date, "%Y-%m-%d")
        else:
            self.end_date = end_date

        # Load config
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)

        # Initialize components
        self.downloader = NomadsDownloader(config_path)
        self.processor = None  # Will initialize after zarr store is created

        # Statistics
        self.stats = {
            'start_time': datetime.now(),
            'total_hours': 0,
            'downloaded': 0,
            'processed': 0,
            'failed': 0,
            'skipped': 0
        }

    def initialize_zarr(self):
        """Create zarr store if it doesn't exist"""
        zarr_file = Path(self.zarr_path)

        if zarr_file.exists():
            logger.info(f"Zarr store already exists at {self.zarr_path}")
        else:
            logger.info(f"Creating new zarr store at {self.zarr_path}")
            initialize_zarr_store(self.zarr_path, self.config_path)

        # Initialize processor
        self.processor = HRRRSnowfallProcessor(self.zarr_path)

    def get_date_range(self):
        """Generate list of all hours to process"""
        hours = []
        current = self.start_date

        while current <= self.end_date:
            hours.append(current)
            current += timedelta(hours=1)

        return hours

    def process_hour(self, date_hour, tmp_dir="tmp"):
        """
        Download and process a single hour

        Args:
            date_hour: datetime for the hour to process
            tmp_dir: Temporary directory for downloads

        Returns:
            bool: True if successful
        """
        try:
            # Download GRIB2 file
            grib_file = self.downloader.download_asnow_filtered(date_hour, tmp_dir)

            if not grib_file:
                logger.warning(f"Failed to download {date_hour}")
                self.stats['failed'] += 1
                return False

            self.stats['downloaded'] += 1

            # Process and append to zarr
            success = self.processor.process_file(grib_file)

            if success:
                self.stats['processed'] += 1
            else:
                self.stats['skipped'] += 1

            # Clean up GRIB file
            Path(grib_file).unlink()

            return success

        except Exception as e:
            logger.error(f"Error processing {date_hour}: {e}")
            self.stats['failed'] += 1
            return False

    def run(self, tmp_dir="tmp", resume=False):
        """
        Run the backfill process

        Args:
            tmp_dir: Temporary directory for downloads
            resume: If True, skip times already in zarr store

        Returns:
            dict: Statistics about the backfill
        """
        logger.info("=" * 80)
        logger.info("HRRR ASNOW Backfill Starting")
        logger.info("=" * 80)
        logger.info(f"Date range: {self.start_date} to {self.end_date}")
        logger.info(f"Zarr store: {self.zarr_path}")
        logger.info(f"Temporary directory: {tmp_dir}")

        # Initialize zarr store
        self.initialize_zarr()

        # Get list of hours to process
        hours_to_process = self.get_date_range()
        self.stats['total_hours'] = len(hours_to_process)

        logger.info(f"Total hours to process: {self.stats['total_hours']}")

        # If resuming, check existing times
        if resume:
            try:
                import xarray as xr
                ds = xr.open_zarr(self.zarr_path)
                existing_times = set(ds.time.values)
                hours_to_process = [h for h in hours_to_process
                                   if np.datetime64(h) not in existing_times]
                logger.info(f"Resuming: {len(hours_to_process)} hours remaining")
            except Exception as e:
                logger.warning(f"Could not check existing times: {e}")

        # Create tmp directory
        Path(tmp_dir).mkdir(parents=True, exist_ok=True)

        # Process each hour
        for i, date_hour in enumerate(hours_to_process, 1):
            logger.info(f"[{i}/{len(hours_to_process)}] Processing {date_hour}")

            self.process_hour(date_hour, tmp_dir)

            # Log progress every 24 hours
            if i % 24 == 0:
                self._log_progress()

        # Final statistics
        self.stats['end_time'] = datetime.now()
        self.stats['duration'] = str(self.stats['end_time'] - self.stats['start_time'])

        logger.info("=" * 80)
        logger.info("Backfill Complete")
        logger.info("=" * 80)
        self._log_progress()

        return self.stats

    def _log_progress(self):
        """Log current progress statistics"""
        logger.info(
            f"Progress: "
            f"{self.stats['processed']} processed, "
            f"{self.stats['failed']} failed, "
            f"{self.stats['skipped']} skipped "
            f"({self.stats['processed'] / max(self.stats['total_hours'], 1) * 100:.1f}% complete)"
        )

    def save_stats(self, output_file="backfill_stats.json"):
        """Save statistics to JSON file"""
        # Convert datetime objects to strings
        stats_serializable = {
            k: str(v) if isinstance(v, datetime) else v
            for k, v in self.stats.items()
        }

        with open(output_file, 'w') as f:
            json.dump(stats_serializable, f, indent=2)

        logger.info(f"Statistics saved to {output_file}")


def main():
    """Main entry point for backfill script"""
    parser = argparse.ArgumentParser(
        description='Backfill HRRR ASNOW data to zarr store'
    )
    parser.add_argument(
        '--start',
        type=str,
        required=True,
        help='Start date (YYYY-MM-DD)'
    )
    parser.add_argument(
        '--end',
        type=str,
        required=True,
        help='End date (YYYY-MM-DD)'
    )
    parser.add_argument(
        '--zarr',
        type=str,
        default='data/hrrr-analysis-snowfall.zarr',
        help='Path to zarr store'
    )
    parser.add_argument(
        '--config',
        type=str,
        default='config.yaml',
        help='Path to configuration file'
    )
    parser.add_argument(
        '--tmp',
        type=str,
        default='tmp',
        help='Temporary directory for downloads'
    )
    parser.add_argument(
        '--resume',
        action='store_true',
        help='Resume from existing zarr store'
    )
    parser.add_argument(
        '--save-stats',
        type=str,
        default='backfill_stats.json',
        help='File to save statistics'
    )

    args = parser.parse_args()

    # Create backfill orchestrator
    backfill = HRRRSnowfallBackfill(
        zarr_path=args.zarr,
        start_date=args.start,
        end_date=args.end,
        config_path=args.config
    )

    # Run backfill
    stats = backfill.run(tmp_dir=args.tmp, resume=args.resume)

    # Save statistics
    backfill.save_stats(args.save_stats)

    # Exit with appropriate code
    if stats['failed'] > stats['processed']:
        logger.error("Backfill had more failures than successes")
        exit(1)
    else:
        logger.info("Backfill completed successfully")
        exit(0)


if __name__ == "__main__":
    import numpy as np
    main()
