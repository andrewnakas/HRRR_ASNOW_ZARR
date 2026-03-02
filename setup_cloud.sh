#!/bin/bash
# Setup script for cloud storage integration

set -e

echo "======================================"
echo "HRRR ASNOW Cloud Storage Setup"
echo "======================================"
echo ""

# Check if config exists
if [ ! -f "config.yaml" ]; then
    echo "Error: config.yaml not found"
    exit 1
fi

# Ask for provider
echo "Which cloud storage provider do you want to use?"
echo "  1) Amazon S3"
echo "  2) Google Cloud Storage (GCS)"
echo "  3) Microsoft Azure Blob Storage"
echo "  4) Local filesystem (no cloud)"
echo ""
read -p "Enter choice [1-4]: " provider_choice

case $provider_choice in
    1)
        PROVIDER="s3"
        echo ""
        read -p "Enter S3 bucket name: " BUCKET
        read -p "Enter AWS region [us-east-1]: " REGION
        REGION=${REGION:-us-east-1}

        # Configure
        python3 src/cloud_storage.py setup s3 "$BUCKET" "$REGION"

        echo ""
        echo "To use S3, set these environment variables:"
        echo "  export AWS_ACCESS_KEY_ID=your_access_key"
        echo "  export AWS_SECRET_ACCESS_KEY=your_secret_key"
        echo ""
        echo "Or for GitHub Actions, add these secrets:"
        echo "  - AWS_ACCESS_KEY_ID"
        echo "  - AWS_SECRET_ACCESS_KEY"
        echo "  - AWS_REGION (optional, defaults to us-east-1)"
        ;;

    2)
        PROVIDER="gcs"
        echo ""
        read -p "Enter GCS bucket name: " BUCKET

        # Configure
        python3 src/cloud_storage.py setup gcs "$BUCKET"

        echo ""
        echo "To use GCS, set this environment variable:"
        echo "  export GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account-key.json"
        echo ""
        echo "Or for GitHub Actions, add this secret:"
        echo "  - GCS_SERVICE_ACCOUNT_KEY (paste the JSON content)"
        ;;

    3)
        PROVIDER="azure"
        echo ""
        read -p "Enter Azure container name: " BUCKET

        # Configure
        python3 src/cloud_storage.py setup azure "$BUCKET"

        echo ""
        echo "To use Azure, set these environment variables:"
        echo "  export AZURE_STORAGE_ACCOUNT_NAME=your_account_name"
        echo "  export AZURE_STORAGE_ACCOUNT_KEY=your_account_key"
        echo ""
        echo "Or for GitHub Actions, add these secrets:"
        echo "  - AZURE_STORAGE_ACCOUNT_NAME"
        echo "  - AZURE_STORAGE_ACCOUNT_KEY"
        ;;

    4)
        PROVIDER="local"
        echo ""
        echo "Using local filesystem storage (no cloud)"
        python3 src/cloud_storage.py setup local
        ;;

    *)
        echo "Invalid choice"
        exit 1
        ;;
esac

echo ""
echo "======================================"
echo "Cloud storage configured!"
echo "======================================"
echo ""
echo "Provider: $PROVIDER"

if [ "$PROVIDER" != "local" ]; then
    echo "Bucket: $BUCKET"
    echo ""
    echo "Next steps:"
    echo "  1. Set up credentials (see above)"
    echo "  2. Test the connection: python3 src/cloud_storage.py test"
    echo "  3. Run backfill: python3 src/backfill_cloud.py --start 2024-01-01 --end 2024-01-07"
else
    echo ""
    echo "Next steps:"
    echo "  1. Run backfill: python3 src/backfill_cloud.py --start 2024-01-01 --end 2024-01-07"
fi

echo ""
