"""
Cloud-aware Backfill Orchestration
Handles both local and cloud storage for zarr data
"""

import yaml
from datetime import datetime, timedelta
from pathlib import Path
import logging
import argparse
import json
import numpy as np

from template import HRRRSnowfallTemplateConfig
from downloader import NomadsDownloader
from processor import HRRRSnowfallProcessor
from cloud_storage import CloudStorageManager

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class CloudAwareBackfill:
    """Backfill orchestrator that works with local or cloud storage"""

    def __init__(self, start_date, end_date, config_path="config.yaml"):
        """
        Initialize cloud-aware backfill

        Args:
            start_date: Start date (datetime or string YYYY-MM-DD)
            end_date: End date (datetime or string YYYY-MM-DD)
            config_path: Path to configuration file
        """
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

        # Initialize cloud storage manager
        self.cloud = CloudStorageManager(config_path)

        # Get zarr path (could be local or cloud)
        self.zarr_path = self.cloud.get_zarr_path()
        self.storage_options = self.cloud.get_storage_options()

        logger.info(f"Using zarr store: {self.zarr_path}")
        logger.info(f"Storage provider: {self.cloud.provider}")

        # Initialize components
        self.downloader = NomadsDownloader(config_path)
        self.processor = None  # Will initialize after zarr exists

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
        exists = self.cloud.zarr_exists()

        if exists:
            logger.info(f"Zarr store already exists")
        else:
            logger.info(f"Creating new zarr store")

            # Create bucket if needed
            self.cloud.create_bucket_if_needed()

            # Create template
            template_config = HRRRSnowfallTemplateConfig(self.config_path)
            template = template_config.create_template()

            # Encoding for efficient storage
            import zarr
            encoding = {
                'accumulated_snowfall': {
                    'compressor': zarr.Blosc(
                        cname=self.config['zarr_encoding']['compressor'],
                        clevel=self.config['zarr_encoding']['compression_level'],
                        shuffle=self.config['zarr_encoding']['shuffle']
                    ),
                    'chunks': (
                        self.config['zarr_encoding']['chunks']['time'],
                        self.config['zarr_encoding']['chunks']['y'],
                        self.config['zarr_encoding']['chunks']['x']
                    ),
                },
                'time': {'chunks': (self.config['zarr_encoding']['chunks']['time'],)},
                'latitude': {'chunks': (self.config['zarr_encoding']['chunks']['y'],
                                       self.config['zarr_encoding']['chunks']['x'])},
                'longitude': {'chunks': (self.config['zarr_encoding']['chunks']['y'],
                                        self.config['zarr_encoding']['chunks']['x'])}
            }

            # Write to zarr (local or cloud)
            if self.cloud.provider == 'local':
                Path(self.zarr_path).parent.mkdir(parents=True, exist_ok=True)
                template.to_zarr(self.zarr_path, mode='w', encoding=encoding, consolidated=True)
            else:
                # For cloud, write with storage options
                template.to_zarr(
                    self.zarr_path,
                    mode='w',
                    encoding=encoding,
                    consolidated=True,
                    storage_options=self.storage_options
                )

            logger.info(f"✓ Initialized zarr store")

        # Initialize processor
        # Note: For cloud storage, we still use local tmp zarr during processing
        # then sync to cloud periodically
        if self.cloud.provider == 'local':
            self.processor = HRRRSnowfallProcessor(self.zarr_path)
        else:
            # Use local tmp zarr for processing, sync to cloud later
            local_zarr = 'tmp/hrrr-analysis-snowfall.zarr'
            Path(local_zarr).parent.mkdir(parents=True, exist_ok=True)

            # Download from cloud if exists, otherwise create new
            if exists:
                logger.info("Syncing zarr from cloud to local tmp...")
                self.cloud.sync_from_cloud(local_zarr)
            else:
                # Already created above, sync to cloud
                logger.info("Syncing new zarr to cloud...")
                # Create local copy first
                template.to_zarr(local_zarr, mode='w', encoding=encoding, consolidated=True)
                self.cloud.sync_to_cloud(local_zarr)

            self.processor = HRRRSnowfallProcessor(local_zarr)

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

    def sync_to_cloud(self):
        """Sync local zarr to cloud storage"""
        if self.cloud.provider == 'local':
            return  # No sync needed

        logger.info("Syncing zarr to cloud storage...")
        local_zarr = 'tmp/hrrr-analysis-snowfall.zarr'
        self.cloud.sync_to_cloud(local_zarr)
        logger.info("✓ Sync complete")

    def run(self, tmp_dir="tmp", resume=False, sync_interval_hours=24):
        """
        Run the backfill process

        Args:
            tmp_dir: Temporary directory for downloads
            resume: If True, skip times already in zarr store
            sync_interval_hours: Sync to cloud every N hours (for cloud storage)

        Returns:
            dict: Statistics about the backfill
        """
        logger.info("=" * 80)
        logger.info("HRRR ASNOW Cloud-Aware Backfill Starting")
        logger.info("=" * 80)
        logger.info(f"Date range: {self.start_date} to {self.end_date}")
        logger.info(f"Storage: {self.cloud.provider}")
        logger.info(f"Zarr path: {self.zarr_path}")

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
                if self.cloud.provider == 'local':
                    ds = xr.open_zarr(self.zarr_path)
                else:
                    ds = xr.open_zarr(
                        self.zarr_path,
                        storage_options=self.storage_options
                    )
                existing_times = set(ds.time.values)
                hours_to_process = [h for h in hours_to_process
                                   if np.datetime64(h) not in existing_times]
                logger.info(f"Resuming: {len(hours_to_process)} hours remaining")
            except Exception as e:
                logger.warning(f"Could not check existing times: {e}")

        # Create tmp directory
        Path(tmp_dir).mkdir(parents=True, exist_ok=True)

        # Process each hour
        hours_since_sync = 0
        for i, date_hour in enumerate(hours_to_process, 1):
            logger.info(f"[{i}/{len(hours_to_process)}] Processing {date_hour}")

            self.process_hour(date_hour, tmp_dir)
            hours_since_sync += 1

            # Sync to cloud periodically
            if self.cloud.provider != 'local' and hours_since_sync >= sync_interval_hours:
                self.sync_to_cloud()
                hours_since_sync = 0

            # Log progress every 24 hours
            if i % 24 == 0:
                self._log_progress()

        # Final sync to cloud
        if self.cloud.provider != 'local':
            self.sync_to_cloud()

        # Final statistics
        self.stats['end_time'] = datetime.now()
        self.stats['duration'] = str(self.stats['end_time'] - self.stats['start_time'])

        logger.info("=" * 80)
        logger.info("Backfill Complete")
        logger.info("=" * 80)
        self._log_progress()

        # Show storage size
        size_gb = self.cloud.get_zarr_size()
        logger.info(f"Zarr size: {size_gb:.2f} GB")

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
        stats_serializable = {
            k: str(v) if isinstance(v, datetime) else v
            for k, v in self.stats.items()
        }

        with open(output_file, 'w') as f:
            json.dump(stats_serializable, f, indent=2)

        logger.info(f"Statistics saved to {output_file}")


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description='Cloud-aware backfill for HRRR ASNOW data'
    )
    parser.add_argument('--start', type=str, required=True, help='Start date (YYYY-MM-DD)')
    parser.add_argument('--end', type=str, required=True, help='End date (YYYY-MM-DD)')
    parser.add_argument('--config', type=str, default='config.yaml', help='Config file')
    parser.add_argument('--tmp', type=str, default='tmp', help='Temp directory')
    parser.add_argument('--resume', action='store_true', help='Resume from existing data')
    parser.add_argument('--sync-interval', type=int, default=24, help='Sync to cloud every N hours')
    parser.add_argument('--save-stats', type=str, default='backfill_stats.json', help='Stats output file')

    args = parser.parse_args()

    # Create backfill orchestrator
    backfill = CloudAwareBackfill(
        start_date=args.start,
        end_date=args.end,
        config_path=args.config
    )

    # Run backfill
    stats = backfill.run(
        tmp_dir=args.tmp,
        resume=args.resume,
        sync_interval_hours=args.sync_interval
    )

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
    main()
