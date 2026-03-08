"""
NCEI HRRR Historical Data Downloader
Downloads HRRR ASNOW data from NCEI archive (2014-2021)
"""

import requests
import time
import yaml
from datetime import datetime, timedelta
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class NCEIDownloader:
    """Download historical HRRR ASNOW data from NCEI archive"""

    def __init__(self, config_path="config.yaml"):
        """Load configuration"""
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)

        # NCEI base URL for HRRR historical analysis
        self.base_url = "https://www.ncei.noaa.gov/data/rapid-refresh/access/historical/analysis"

        self.requests_per_minute = self.config['rate_limiting']['requests_per_minute']
        self.retry_attempts = self.config['rate_limiting']['retry_attempts']
        self.retry_delay = self.config['rate_limiting']['retry_delay_seconds']

        # Calculate delay between requests
        self.request_delay = 60.0 / self.requests_per_minute
        self.last_request_time = 0

    def _rate_limit(self):
        """Enforce rate limiting between requests"""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time

        if time_since_last < self.request_delay:
            sleep_time = self.request_delay - time_since_last
            logger.debug(f"Rate limiting: sleeping {sleep_time:.2f}s")
            time.sleep(sleep_time)

        self.last_request_time = time.time()

    def download_asnow(self, date_hour, output_dir="tmp"):
        """
        Download HRRR analysis file from NCEI archive

        NCEI URL structure:
        https://www.ncei.noaa.gov/data/rapid-refresh/access/historical/analysis/YYYYMM/YYYYMMDD/hrrr_YYYYMMDD_HHz_wrfsfcf00.grib2

        Args:
            date_hour: datetime object for specific hour
            output_dir: Directory to save downloaded files

        Returns:
            Path to downloaded GRIB2 file, or None if failed
        """
        year_month = date_hour.strftime("%Y%m")
        date_str = date_hour.strftime("%Y%m%d")
        hour_str = date_hour.strftime("%H")

        # NCEI filename format: hrrr_YYYYMMDD_HHz_wrfsfcf00.grib2
        filename = f"hrrr_{date_str}_{hour_str}z_wrfsfcf00.grib2"

        # Full URL
        url = f"{self.base_url}/{year_month}/{date_str}/{filename}"

        # Create output directory
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        # Output filename (keep same format for consistency)
        local_filename = output_path / f"hrrr_asnow_{date_str}_{hour_str}.grib2"

        # Try to download with retries
        for attempt in range(self.retry_attempts):
            try:
                # Rate limit
                self._rate_limit()

                logger.info(f"Downloading {date_hour} from NCEI (attempt {attempt + 1}/{self.retry_attempts})")
                logger.debug(f"URL: {url}")

                response = requests.get(url, stream=True, timeout=120)

                if response.status_code == 200:
                    # Write to file
                    total_size = 0
                    with open(local_filename, 'wb') as f:
                        for chunk in response.iter_content(chunk_size=8192):
                            f.write(chunk)
                            total_size += len(chunk)

                    # Verify file size (full HRRR files are ~400-600 MB)
                    file_size_mb = total_size / (1024 * 1024)

                    if file_size_mb < 100:  # Full GRIB2 should be much larger
                        logger.warning(f"File too small ({file_size_mb:.2f} MB), may be corrupt")
                        local_filename.unlink()
                        if attempt < self.retry_attempts - 1:
                            time.sleep(self.retry_delay)
                            continue
                        return None

                    logger.info(f"✓ Downloaded {local_filename.name} ({file_size_mb:.2f} MB)")
                    return local_filename

                elif response.status_code == 404:
                    logger.warning(f"File not found (404) for {date_hour}")
                    return None

                else:
                    logger.warning(f"HTTP {response.status_code} for {date_hour}")
                    if attempt < self.retry_attempts - 1:
                        time.sleep(self.retry_delay)
                        continue

            except requests.exceptions.Timeout:
                logger.warning(f"Timeout downloading {date_hour}")
                if attempt < self.retry_attempts - 1:
                    time.sleep(self.retry_delay)
                    continue

            except Exception as e:
                logger.error(f"Error downloading {date_hour}: {e}")
                if attempt < self.retry_attempts - 1:
                    time.sleep(self.retry_delay)
                    continue

        logger.error(f"Failed to download {date_hour} after {self.retry_attempts} attempts")
        return None

    def download_date_range(self, start_date, end_date, output_dir="tmp"):
        """
        Download HRRR data for a date range from NCEI

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

        logger.info(f"Downloaded {len(downloaded_files)} files from NCEI")
        return downloaded_files


def download_ncei_file(date_str, hour, output_dir="tmp", config_path="config.yaml"):
    """
    Convenience function to download a single NCEI file

    Args:
        date_str: Date string in YYYY-MM-DD format
        hour: Hour (0-23)
        output_dir: Output directory
        config_path: Path to config file

    Returns:
        Path to downloaded file or None
    """
    downloader = NCEIDownloader(config_path)
    date_hour = datetime.strptime(date_str, "%Y-%m-%d").replace(hour=hour)
    return downloader.download_asnow(date_hour, output_dir)


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 3:
        print("Usage: python downloader_ncei.py YYYY-MM-DD HH [output_dir]")
        print("Example: python downloader_ncei.py 2018-01-15 12 tmp")
        print("\nNote: NCEI archive covers 2014-10-01 to 2021-12-31")
        sys.exit(1)

    date_str = sys.argv[1]
    hour = int(sys.argv[2])
    output_dir = sys.argv[3] if len(sys.argv) > 3 else "tmp"

    filepath = download_ncei_file(date_str, hour, output_dir)

    if filepath:
        print(f"Success: {filepath}")
    else:
        print("Download failed")
        sys.exit(1)
