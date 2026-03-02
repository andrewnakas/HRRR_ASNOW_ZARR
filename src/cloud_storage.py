"""
Cloud Storage Management for Zarr Data
Supports S3, Google Cloud Storage, and Azure Blob Storage
"""

import os
import yaml
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class CloudStorageManager:
    """Manage zarr stores in cloud storage"""

    def __init__(self, config_path="config.yaml"):
        """Initialize cloud storage manager"""
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)

        self.cloud_config = self.config.get('cloud_storage', {})
        self.provider = self.cloud_config.get('provider', 's3')
        self.bucket = self.cloud_config.get('bucket')
        self.zarr_path = self.cloud_config.get('zarr_path', 'hrrr-analysis-snowfall.zarr')

        # Initialize provider-specific client
        self._init_client()

    def _init_client(self):
        """Initialize cloud storage client based on provider"""
        if self.provider == 's3':
            self._init_s3()
        elif self.provider == 'gcs':
            self._init_gcs()
        elif self.provider == 'azure':
            self._init_azure()
        elif self.provider == 'local':
            logger.info("Using local filesystem storage")
            self.fs = None
        else:
            raise ValueError(f"Unsupported provider: {self.provider}")

    def _init_s3(self):
        """Initialize S3 client"""
        try:
            import s3fs

            # Get credentials from environment or config
            aws_access_key = os.environ.get('AWS_ACCESS_KEY_ID')
            aws_secret_key = os.environ.get('AWS_SECRET_ACCESS_KEY')
            region = self.cloud_config.get('region', 'us-east-1')

            if aws_access_key and aws_secret_key:
                self.fs = s3fs.S3FileSystem(
                    key=aws_access_key,
                    secret=aws_secret_key,
                    client_kwargs={'region_name': region}
                )
            else:
                # Use default credentials (IAM role, .aws/credentials, etc.)
                self.fs = s3fs.S3FileSystem(
                    client_kwargs={'region_name': region}
                )

            logger.info(f"Initialized S3 storage: s3://{self.bucket}/{self.zarr_path}")

        except ImportError:
            raise ImportError("s3fs not installed. Run: pip install s3fs")

    def _init_gcs(self):
        """Initialize Google Cloud Storage client"""
        try:
            import gcsfs

            # Get credentials from environment
            credentials = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS')

            if credentials:
                self.fs = gcsfs.GCSFileSystem(token=credentials)
            else:
                self.fs = gcsfs.GCSFileSystem()  # Use default credentials

            logger.info(f"Initialized GCS storage: gs://{self.bucket}/{self.zarr_path}")

        except ImportError:
            raise ImportError("gcsfs not installed. Run: pip install gcsfs")

    def _init_azure(self):
        """Initialize Azure Blob Storage client"""
        try:
            import adlfs

            # Get credentials from environment
            account_name = os.environ.get('AZURE_STORAGE_ACCOUNT_NAME')
            account_key = os.environ.get('AZURE_STORAGE_ACCOUNT_KEY')

            if account_name and account_key:
                self.fs = adlfs.AzureBlobFileSystem(
                    account_name=account_name,
                    account_key=account_key
                )
            else:
                # Use default credentials
                self.fs = adlfs.AzureBlobFileSystem(account_name=account_name)

            logger.info(f"Initialized Azure storage: az://{self.bucket}/{self.zarr_path}")

        except ImportError:
            raise ImportError("adlfs not installed. Run: pip install adlfs")

    def get_zarr_path(self):
        """Get full path to zarr store"""
        if self.provider == 'local':
            return f"data/{self.zarr_path}"
        elif self.provider == 's3':
            return f"s3://{self.bucket}/{self.zarr_path}"
        elif self.provider == 'gcs':
            return f"gs://{self.bucket}/{self.zarr_path}"
        elif self.provider == 'azure':
            return f"az://{self.bucket}/{self.zarr_path}"

    def get_storage_options(self):
        """Get storage options for xarray/zarr"""
        if self.provider == 'local':
            return {}
        else:
            return {'fs': self.fs}

    def zarr_exists(self):
        """Check if zarr store exists"""
        zarr_path = self.get_zarr_path()

        if self.provider == 'local':
            return Path(zarr_path).exists()
        else:
            # Check for .zgroup or .zattrs file
            if self.provider == 's3':
                check_path = f"{self.bucket}/{self.zarr_path}/.zgroup"
            elif self.provider == 'gcs':
                check_path = f"{self.bucket}/{self.zarr_path}/.zgroup"
            elif self.provider == 'azure':
                check_path = f"{self.bucket}/{self.zarr_path}/.zgroup"

            try:
                return self.fs.exists(check_path)
            except Exception as e:
                logger.warning(f"Error checking zarr existence: {e}")
                return False

    def create_bucket_if_needed(self):
        """Create bucket if it doesn't exist (S3/GCS only)"""
        if self.provider == 'local':
            Path('data').mkdir(parents=True, exist_ok=True)
            return

        if not self.bucket:
            raise ValueError("Bucket name not configured")

        try:
            if self.provider == 's3':
                if not self.fs.exists(self.bucket):
                    logger.info(f"Creating S3 bucket: {self.bucket}")
                    self.fs.mkdir(self.bucket)
            elif self.provider == 'gcs':
                if not self.fs.exists(self.bucket):
                    logger.info(f"Creating GCS bucket: {self.bucket}")
                    self.fs.mkdir(self.bucket)
            # Azure buckets (containers) are created differently
        except Exception as e:
            logger.warning(f"Could not create bucket: {e}")

    def get_zarr_size(self):
        """Get size of zarr store in GB"""
        zarr_path = self.get_zarr_path()

        if self.provider == 'local':
            zarr_dir = Path(zarr_path)
            if not zarr_dir.exists():
                return 0
            total_size = sum(f.stat().st_size for f in zarr_dir.rglob('*') if f.is_file())
        else:
            if self.provider == 's3':
                base_path = f"{self.bucket}/{self.zarr_path}"
            elif self.provider == 'gcs':
                base_path = f"{self.bucket}/{self.zarr_path}"
            elif self.provider == 'azure':
                base_path = f"{self.bucket}/{self.zarr_path}"

            try:
                files = self.fs.find(base_path)
                total_size = sum(self.fs.size(f) for f in files)
            except Exception as e:
                logger.warning(f"Error getting zarr size: {e}")
                return 0

        return total_size / (1024**3)  # Convert to GB

    def sync_to_cloud(self, local_path, remote_path=None):
        """Sync local zarr to cloud storage"""
        if self.provider == 'local':
            logger.info("Local storage, no sync needed")
            return

        if remote_path is None:
            remote_path = self.zarr_path

        if self.provider == 's3':
            full_remote = f"{self.bucket}/{remote_path}"
        elif self.provider == 'gcs':
            full_remote = f"{self.bucket}/{remote_path}"
        elif self.provider == 'azure':
            full_remote = f"{self.bucket}/{remote_path}"

        logger.info(f"Syncing {local_path} to {full_remote}")

        try:
            self.fs.put(local_path, full_remote, recursive=True)
            logger.info("✓ Sync complete")
        except Exception as e:
            logger.error(f"Error syncing to cloud: {e}")
            raise

    def sync_from_cloud(self, local_path, remote_path=None):
        """Sync cloud zarr to local storage"""
        if self.provider == 'local':
            logger.info("Local storage, no sync needed")
            return

        if remote_path is None:
            remote_path = self.zarr_path

        if self.provider == 's3':
            full_remote = f"{self.bucket}/{remote_path}"
        elif self.provider == 'gcs':
            full_remote = f"{self.bucket}/{remote_path}"
        elif self.provider == 'azure':
            full_remote = f"{self.bucket}/{remote_path}"

        logger.info(f"Syncing {full_remote} to {local_path}")

        try:
            self.fs.get(full_remote, local_path, recursive=True)
            logger.info("✓ Sync complete")
        except Exception as e:
            logger.error(f"Error syncing from cloud: {e}")
            raise


def setup_cloud_storage(provider='s3', bucket=None, region='us-east-1'):
    """
    Interactive setup for cloud storage configuration

    Args:
        provider: 's3', 'gcs', or 'azure'
        bucket: Bucket/container name
        region: AWS region (for S3 only)
    """
    config_file = Path('config.yaml')

    with open(config_file) as f:
        config = yaml.safe_load(f)

    # Add cloud storage configuration
    config['cloud_storage'] = {
        'provider': provider,
        'bucket': bucket,
        'zarr_path': 'hrrr-analysis-snowfall.zarr',
        'region': region if provider == 's3' else None
    }

    # Write updated config
    with open(config_file, 'w') as f:
        yaml.dump(config, f, default_flow_style=False, sort_keys=False)

    logger.info(f"✓ Cloud storage configured: {provider}://{bucket}/hrrr-analysis-snowfall.zarr")
    logger.info(f"✓ Updated {config_file}")

    # Show next steps
    print("\nNext steps:")
    if provider == 's3':
        print("  1. Set environment variables:")
        print("     export AWS_ACCESS_KEY_ID=your_key")
        print("     export AWS_SECRET_ACCESS_KEY=your_secret")
        print("  2. Or configure GitHub Secrets:")
        print("     - AWS_ACCESS_KEY_ID")
        print("     - AWS_SECRET_ACCESS_KEY")
    elif provider == 'gcs':
        print("  1. Set environment variable:")
        print("     export GOOGLE_APPLICATION_CREDENTIALS=/path/to/credentials.json")
        print("  2. Or configure GitHub Secret:")
        print("     - GCS_SERVICE_ACCOUNT_KEY")
    elif provider == 'azure':
        print("  1. Set environment variables:")
        print("     export AZURE_STORAGE_ACCOUNT_NAME=your_account")
        print("     export AZURE_STORAGE_ACCOUNT_KEY=your_key")
        print("  2. Or configure GitHub Secrets:")
        print("     - AZURE_STORAGE_ACCOUNT_NAME")
        print("     - AZURE_STORAGE_ACCOUNT_KEY")


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage:")
        print("  Setup: python cloud_storage.py setup <provider> <bucket> [region]")
        print("  Test:  python cloud_storage.py test")
        print("")
        print("Providers: s3, gcs, azure, local")
        sys.exit(1)

    command = sys.argv[1]

    if command == 'setup':
        provider = sys.argv[2] if len(sys.argv) > 2 else 's3'
        bucket = sys.argv[3] if len(sys.argv) > 3 else None
        region = sys.argv[4] if len(sys.argv) > 4 else 'us-east-1'

        if not bucket and provider != 'local':
            print("Error: Bucket name required")
            sys.exit(1)

        setup_cloud_storage(provider, bucket, region)

    elif command == 'test':
        manager = CloudStorageManager()
        print(f"Provider: {manager.provider}")
        print(f"Zarr path: {manager.get_zarr_path()}")
        print(f"Zarr exists: {manager.zarr_exists()}")
        print(f"Zarr size: {manager.get_zarr_size():.2f} GB")
