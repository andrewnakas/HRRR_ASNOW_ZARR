"""
Unified HRRR Downloader
Automatically selects the right data source based on date:
- NOMADS: Last ~10 days
- AWS: 2022 to ~10 days ago
- NCEI: 2014-2021
"""

from datetime import datetime, timedelta
import logging

from downloader import NomadsDownloader
from downloader_ncei import NCEIDownloader
from downloader_aws import AWSDownloader

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class UnifiedDownloader:
    """Smart downloader that selects data source based on date"""

    # Date boundaries
    NCEI_START = datetime(2014, 10, 1)  # HRRR started 2014-09-30, but reliable from Oct 1
    NCEI_END = datetime(2021, 12, 31, 23)
    AWS_START = datetime(2022, 1, 1)
    NOMADS_LOOKBACK_DAYS = 10  # NOMADS keeps ~10 days

    def __init__(self, config_path="config.yaml"):
        """Initialize all downloaders"""
        self.config_path = config_path
        self.nomads = NomadsDownloader(config_path)
        self.ncei = NCEIDownloader(config_path)
        self.aws = AWSDownloader(config_path)

    def get_source_for_date(self, date_hour):
        """
        Determine which source to use for a given date

        Args:
            date_hour: datetime object

        Returns:
            tuple: (source_name, downloader_instance)
        """
        now = datetime.now()
        nomads_cutoff = now - timedelta(days=self.NOMADS_LOOKBACK_DAYS)

        if date_hour >= nomads_cutoff:
            return ("NOMADS", self.nomads)
        elif date_hour >= self.AWS_START:
            return ("AWS", self.aws)
        elif date_hour >= self.NCEI_START:
            return ("NCEI", self.ncei)
        else:
            raise ValueError(f"Date {date_hour} is before HRRR start date (2014-10-01)")

    def download_asnow(self, date_hour, output_dir="tmp"):
        """
        Download HRRR ASNOW for a specific date/hour
        Automatically selects the right source

        Args:
            date_hour: datetime object
            output_dir: Output directory

        Returns:
            Path to downloaded file or None
        """
        source_name, downloader = self.get_source_for_date(date_hour)
        logger.info(f"Using {source_name} for {date_hour}")

        if source_name == "NOMADS":
            return downloader.download_asnow_filtered(date_hour, output_dir)
        else:
            return downloader.download_asnow(date_hour, output_dir)

    def download_date_range(self, start_date, end_date, output_dir="tmp"):
        """
        Download HRRR data for a date range
        Automatically switches sources as needed

        Args:
            start_date: datetime for start
            end_date: datetime for end
            output_dir: Output directory

        Returns:
            List of downloaded files
        """
        downloaded_files = []
        current = start_date

        # Determine sources needed
        sources_used = set()

        while current <= end_date:
            source_name, _ = self.get_source_for_date(current)
            sources_used.add(source_name)
            current += timedelta(hours=1)

        logger.info(f"Date range will use sources: {', '.join(sorted(sources_used))}")

        # Download files
        current = start_date
        while current <= end_date:
            filepath = self.download_asnow(current, output_dir)
            if filepath:
                downloaded_files.append(filepath)

            current += timedelta(hours=1)

        logger.info(f"Downloaded {len(downloaded_files)} total files")
        return downloaded_files


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 3:
        print("Unified HRRR ASNOW Downloader")
        print("=" * 50)
        print("\nAutomatically selects data source based on date:")
        print("  • NOMADS: Last ~10 days")
        print("  • AWS Open Data: 2022 to ~10 days ago")
        print("  • NCEI Archive: 2014-2021")
        print("\nUsage:")
        print("  Single file: python downloader_unified.py YYYY-MM-DD HH [output_dir]")
        print("  Date range:  python downloader_unified.py YYYY-MM-DD YYYY-MM-DD [output_dir]")
        print("\nExamples:")
        print("  python downloader_unified.py 2018-01-15 12 tmp/")
        print("  python downloader_unified.py 2020-01-01 2020-01-07 tmp/")
        sys.exit(1)

    if len(sys.argv) == 3 or (len(sys.argv) == 4 and sys.argv[3].isdigit()):
        # Single file mode
        date_str = sys.argv[1]
        hour = int(sys.argv[2])
        output_dir = sys.argv[3] if len(sys.argv) > 3 and not sys.argv[3].isdigit() else "tmp"

        downloader = UnifiedDownloader()
        date_hour = datetime.strptime(date_str, "%Y-%m-%d").replace(hour=hour)
        filepath = downloader.download_asnow(date_hour, output_dir)

        if filepath:
            print(f"✓ Success: {filepath}")
        else:
            print("✗ Download failed")
            sys.exit(1)

    else:
        # Date range mode
        start_str = sys.argv[1]
        end_str = sys.argv[2]
        output_dir = sys.argv[3] if len(sys.argv) > 3 else "tmp"

        downloader = UnifiedDownloader()
        start_date = datetime.strptime(start_str, "%Y-%m-%d")
        end_date = datetime.strptime(end_str, "%Y-%m-%d").replace(hour=23)

        files = downloader.download_date_range(start_date, end_date, output_dir)
        print(f"\n✓ Downloaded {len(files)} files")
