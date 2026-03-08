"""
AWS Open Data HRRR Downloader
Downloads HRRR ASNOW data from AWS Open Data bucket (2022-present, minus last ~10 days)
"""

import yaml
from datetime import datetime, timedelta
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class AWSDownloader:
    """Download HRRR ASNOW data from AWS Open Data bucket"""

    def __init__(self, config_path="config.yaml"):
        """Load configuration"""
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)

        # AWS Open Data bucket (public, no auth needed)
        self.bucket = "noaa-hrrr-bdp-pds"
        self.region = "us-east-1"

        self.retry_attempts = self.config['rate_limiting']['retry_attempts']
        self.retry_delay = self.config['rate_limiting']['retry_delay_seconds']

    def _get_s3_client(self):
        """Get boto3 S3 client (anonymous access)"""
        try:
            import boto3
            from botocore import UNSIGNED
            from botocore.client import Config

            s3 = boto3.client(
                's3',
                region_name=self.region,
                config=Config(signature_version=UNSIGNED)
            )
            return s3
        except ImportError:
            raise ImportError(
                "boto3 not installed. Run: pip install boto3\n"
                "Or use s3fs: pip install s3fs"
            )

    def download_asnow(self, date_hour, output_dir="tmp"):
        """
        Download HRRR analysis file from AWS Open Data

        AWS S3 structure:
        s3://noaa-hrrr-bdp-pds/hrrr.YYYYMMDD/conus/hrrr.tHHz.wrfsfcf00.grib2

        Args:
            date_hour: datetime object for specific hour
            output_dir: Directory to save downloaded files

        Returns:
            Path to downloaded GRIB2 file, or None if failed
        """
        date_str = date_hour.strftime("%Y%m%d")
        hour_str = date_hour.strftime("%H")

        # AWS key format
        s3_key = f"hrrr.{date_str}/conus/hrrr.t{hour_str}z.wrfsfcf00.grib2"

        # Create output directory
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        # Output filename
        local_filename = output_path / f"hrrr_asnow_{date_str}_{hour_str}.grib2"

        # Try to download
        for attempt in range(self.retry_attempts):
            try:
                logger.info(f"Downloading {date_hour} from AWS (attempt {attempt + 1}/{self.retry_attempts})")
                logger.debug(f"S3 key: {s3_key}")

                s3 = self._get_s3_client()

                # Download file
                s3.download_file(
                    self.bucket,
                    s3_key,
                    str(local_filename)
                )

                # Verify file size
                file_size_mb = local_filename.stat().st_size / (1024 * 1024)

                if file_size_mb < 100:
                    logger.warning(f"File too small ({file_size_mb:.2f} MB), may be corrupt")
                    local_filename.unlink()
                    if attempt < self.retry_attempts - 1:
                        time.sleep(self.retry_delay)
                        continue
                    return None

                logger.info(f"✓ Downloaded {local_filename.name} ({file_size_mb:.2f} MB)")
                return local_filename

            except s3.exceptions.NoSuchKey:
                logger.warning(f"File not found in S3 for {date_hour}")
                return None

            except Exception as e:
                logger.error(f"Error downloading {date_hour}: {e}")
                if attempt < self.retry_attempts - 1:
                    import time
                    time.sleep(self.retry_delay)
                    continue

        logger.error(f"Failed to download {date_hour} after {self.retry_attempts} attempts")
        return None

    def download_date_range(self, start_date, end_date, output_dir="tmp"):
        """
        Download HRRR data for a date range from AWS

        Args:
            start_date: datetime for start (inclusive)
            end_date: datetime for end (inclusive)
            output_dir: Directory to save files

        Returns:
            List of successfully downloaded file paths
        """
        downloaded_files = []
        current = start_date

        while current <= end_date:
            filepath = self.download_asnow(current, output_dir)

            if filepath:
                downloaded_files.append(filepath)

            # Move to next hour
            current += timedelta(hours=1)

        logger.info(f"Downloaded {len(downloaded_files)} files from AWS")
        return downloaded_files


def download_aws_file(date_str, hour, output_dir="tmp", config_path="config.yaml"):
    """
    Convenience function to download a single AWS file

    Args:
        date_str: Date string in YYYY-MM-DD format
        hour: Hour (0-23)
        output_dir: Output directory
        config_path: Path to config file

    Returns:
        Path to downloaded file or None
    """
    downloader = AWSDownloader(config_path)
    date_hour = datetime.strptime(date_str, "%Y-%m-%d").replace(hour=hour)
    return downloader.download_asnow(date_hour, output_dir)


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 3:
        print("Usage: python downloader_aws.py YYYY-MM-DD HH [output_dir]")
        print("Example: python downloader_aws.py 2023-01-15 12 tmp")
        print("\nNote: AWS archive covers 2022-01-01 to ~10 days ago")
        sys.exit(1)

    date_str = sys.argv[1]
    hour = int(sys.argv[2])
    output_dir = sys.argv[3] if len(sys.argv) > 3 else "tmp"

    filepath = download_aws_file(date_str, hour, output_dir)

    if filepath:
        print(f"Success: {filepath}")
    else:
        print("Download failed")
        sys.exit(1)
