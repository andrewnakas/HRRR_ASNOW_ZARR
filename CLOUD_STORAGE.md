# Cloud Storage Guide

This guide explains how to configure cloud storage for the HRRR ASNOW Zarr dataset.

## Why Cloud Storage?

The complete HRRR ASNOW dataset will be **~20-25GB compressed**. Storing this in a Git repository is not recommended due to:
- GitHub repository size limits (soft limit ~1GB, hard limit 100GB)
- Slow git operations with large binary files
- Expensive bandwidth for cloning/pulling

Cloud storage provides:
- ✅ Unlimited storage capacity
- ✅ Fast, efficient access via fsspec
- ✅ Direct integration with xarray/zarr
- ✅ Low cost (~$0.50/month for S3)

## Supported Providers

- **Amazon S3** - Most popular, well-supported
- **Google Cloud Storage** - Good integration with GCP services
- **Microsoft Azure Blob Storage** - Good for Azure ecosystem
- **Local Filesystem** - For testing or small datasets

## Quick Setup

### 1. Run the Setup Script

```bash
./setup_cloud.sh
```

This interactive script will:
1. Ask which provider you want to use
2. Configure `config.yaml` with your settings
3. Show you what credentials are needed

### 2. Configure Credentials

#### For Amazon S3

**Local Development:**
```bash
export AWS_ACCESS_KEY_ID=your_access_key_id
export AWS_SECRET_ACCESS_KEY=your_secret_access_key
export AWS_REGION=us-east-1  # optional
```

**GitHub Actions:**
Add these secrets to your repository (Settings → Secrets → Actions):
- `AWS_ACCESS_KEY_ID`
- `AWS_SECRET_ACCESS_KEY`
- `AWS_REGION` (optional, defaults to us-east-1)

**Create S3 Bucket:**
```bash
aws s3 mb s3://your-hrrr-snowfall-bucket --region us-east-1
```

#### For Google Cloud Storage

**Local Development:**
```bash
# Create service account key
gcloud iam service-accounts create hrrr-snowfall-sa
gcloud iam service-accounts keys create key.json --iam-account hrrr-snowfall-sa@your-project.iam.gserviceaccount.com

# Set environment variable
export GOOGLE_APPLICATION_CREDENTIALS=/path/to/key.json
```

**GitHub Actions:**
Add this secret to your repository:
- `GCS_SERVICE_ACCOUNT_KEY` - Paste the entire JSON key content

**Create GCS Bucket:**
```bash
gsutil mb -l us-central1 gs://your-hrrr-snowfall-bucket
```

#### For Azure Blob Storage

**Local Development:**
```bash
export AZURE_STORAGE_ACCOUNT_NAME=yourstorageaccount
export AZURE_STORAGE_ACCOUNT_KEY=your_account_key
```

**GitHub Actions:**
Add these secrets to your repository:
- `AZURE_STORAGE_ACCOUNT_NAME`
- `AZURE_STORAGE_ACCOUNT_KEY`

**Create Azure Container:**
```bash
az storage container create --name hrrr-snowfall --account-name yourstorageaccount
```

### 3. Test the Connection

```bash
python src/cloud_storage.py test
```

This should show:
```
Provider: s3 (or gcs/azure)
Zarr path: s3://your-bucket/hrrr-analysis-snowfall.zarr
Zarr exists: False (initially)
Zarr size: 0.00 GB
```

## Usage

### Running Backfill with Cloud Storage

Once configured, use the cloud-aware backfill script:

```bash
python src/backfill_cloud.py \
  --start 2024-01-01 \
  --end 2024-01-07 \
  --resume
```

**How it works:**
1. Downloads data from NOMADS
2. Processes locally in `tmp/hrrr-analysis-snowfall.zarr`
3. Syncs to cloud storage every 24 hours (configurable)
4. Final sync when complete

### Reading Data from Cloud

```python
import xarray as xr
from src.cloud_storage import CloudStorageManager

# Get zarr path and credentials
cloud = CloudStorageManager()
zarr_path = cloud.get_zarr_path()
storage_options = cloud.get_storage_options()

# Open zarr store from cloud
ds = xr.open_zarr(zarr_path, storage_options=storage_options)

# Use as normal
print(ds)
```

### Syncing Data Manually

**Download from cloud to local:**
```bash
python -c "
from src.cloud_storage import CloudStorageManager
cloud = CloudStorageManager()
cloud.sync_from_cloud('local_data/hrrr.zarr')
"
```

**Upload from local to cloud:**
```bash
python -c "
from src.cloud_storage import CloudStorageManager
cloud = CloudStorageManager()
cloud.sync_to_cloud('local_data/hrrr.zarr')
"
```

## Configuration Reference

Edit `config.yaml`:

```yaml
cloud_storage:
  provider: "s3"  # Options: s3, gcs, azure, local
  bucket: "your-bucket-name"
  zarr_path: "hrrr-analysis-snowfall.zarr"
  region: "us-east-1"  # For S3 only
```

## GitHub Actions Integration

The `backfill_cloud.yml` workflow automatically:
1. Detects your cloud provider from `config.yaml`
2. Uses GitHub Secrets for credentials
3. Syncs zarr data to/from cloud storage
4. Only commits `progress.json` to git (not the zarr data)

## Cost Estimates

### Amazon S3

**Storage:**
- Standard: $0.023/GB/month
- For 25GB: ~$0.58/month

**Data Transfer:**
- IN (upload): Free
- OUT (download): $0.09/GB for first 10TB
- First 100GB out per month: Free

**Requests:**
- PUT: $0.005 per 1,000 requests
- GET: $0.0004 per 1,000 requests

**Estimated monthly cost: < $1**

### Google Cloud Storage

**Storage:**
- Standard: $0.020/GB/month
- For 25GB: ~$0.50/month

**Data Transfer:**
- IN: Free
- OUT: $0.12/GB

**Operations:**
- Class A (write): $0.05 per 10,000
- Class B (read): $0.004 per 10,000

**Estimated monthly cost: < $1**

### Azure Blob Storage

**Storage:**
- Hot tier: $0.0184/GB/month
- For 25GB: ~$0.46/month

**Data Transfer:**
- IN: Free
- OUT: $0.087/GB

**Operations:**
- Write: $0.065 per 10,000
- Read: $0.0044 per 10,000

**Estimated monthly cost: < $1**

## Troubleshooting

### "Access Denied" or "403 Forbidden"

Check:
1. Credentials are set correctly
2. IAM/Service Account has proper permissions:
   - S3: `s3:GetObject`, `s3:PutObject`, `s3:ListBucket`
   - GCS: `Storage Object Admin` role
   - Azure: `Storage Blob Data Contributor` role

### "Bucket not found"

Create the bucket first:
```bash
# S3
aws s3 mb s3://your-bucket

# GCS
gsutil mb gs://your-bucket

# Azure
az storage container create --name your-container
```

### Slow sync to cloud

The zarr store contains many small files. To speed up:
1. Increase `sync_interval_hours` (fewer syncs)
2. Use a region close to your GitHub Actions runners
3. Consider using zarr consolidated metadata

### GitHub Actions fails with credentials

Check:
1. Secrets are added correctly (Settings → Secrets → Actions)
2. Secret names match workflow (e.g., `AWS_ACCESS_KEY_ID`)
3. For GCS, paste entire JSON key content into secret

## Best Practices

1. **Use dedicated bucket** - Don't mix with other data
2. **Enable versioning** - Protect against accidental deletion
3. **Set lifecycle policies** - Optionally move old data to cheaper storage tiers
4. **Monitor costs** - Set up billing alerts
5. **Regular backups** - Consider replicating to another region/provider
6. **Access logs** - Enable for security auditing

## Public Access (Optional)

To make your dataset publicly accessible:

### S3
```bash
aws s3api put-bucket-policy --bucket your-bucket --policy '{
  "Version": "2012-10-17",
  "Statement": [{
    "Sid": "PublicReadGetObject",
    "Effect": "Allow",
    "Principal": "*",
    "Action": "s3:GetObject",
    "Resource": "arn:aws:s3:::your-bucket/*"
  }]
}'
```

### GCS
```bash
gsutil iam ch allUsers:objectViewer gs://your-bucket
```

Then users can access without credentials:
```python
ds = xr.open_zarr('s3://your-bucket/hrrr-analysis-snowfall.zarr', anon=True)
```

## Advanced: Multi-Region Replication

For high availability, replicate to multiple regions:

### S3 Cross-Region Replication
```bash
aws s3api put-bucket-replication --bucket source-bucket --replication-configuration file://replication.json
```

### GCS Multi-Region Buckets
```bash
gsutil mb -l multi-region gs://your-bucket
```

This ensures data availability even if one region has an outage.
