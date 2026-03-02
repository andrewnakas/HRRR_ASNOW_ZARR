# Deployment Instructions

Complete guide to get your HRRR ASNOW Zarr archive running in production.

## Current Status

✅ **Complete system built and pushed to GitHub**
- All code implemented
- GitHub Actions workflows configured
- Cloud storage support added
- Documentation complete

📋 **Repository**: https://github.com/andrewnakas/HRRR_ASNOW_ZARR

## Deployment Steps

### 1. Choose Your Cloud Storage Provider

You need cloud storage because the complete dataset will be ~20-25GB.

**Recommended: Amazon S3** (easiest, well-supported, cheap)

**Alternatives**: Google Cloud Storage, Azure Blob Storage, or Local (testing only)

### 2. Set Up Cloud Storage

#### Option A: Amazon S3 (Recommended)

**Create an S3 Bucket:**
```bash
# Using AWS CLI
aws s3 mb s3://hrrr-asnow-zarr --region us-east-1

# Or use the AWS Console:
# https://console.aws.amazon.com/s3/
# Click "Create bucket" → Enter name → Select region → Create
```

**Create IAM User with Permissions:**
```bash
# Create user
aws iam create-user --user-name hrrr-asnow-uploader

# Attach S3 policy
aws iam put-user-policy --user-name hrrr-asnow-uploader --policy-name S3Access --policy-document '{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:GetObject",
        "s3:PutObject",
        "s3:ListBucket"
      ],
      "Resource": [
        "arn:aws:s3:::hrrr-asnow-zarr",
        "arn:aws:s3:::hrrr-asnow-zarr/*"
      ]
    }
  ]
}'

# Create access key
aws iam create-access-key --user-name hrrr-asnow-uploader
```

Save the Access Key ID and Secret Access Key!

#### Option B: Google Cloud Storage

```bash
# Create bucket
gsutil mb -l us-central1 gs://hrrr-asnow-zarr

# Create service account
gcloud iam service-accounts create hrrr-asnow-uploader \
  --display-name="HRRR ASNOW Uploader"

# Grant permissions
gsutil iam ch serviceAccount:hrrr-asnow-uploader@YOUR-PROJECT.iam.gserviceaccount.com:objectAdmin gs://hrrr-asnow-zarr

# Create key
gcloud iam service-accounts keys create key.json \
  --iam-account=hrrr-asnow-uploader@YOUR-PROJECT.iam.gserviceaccount.com
```

#### Option C: Azure Blob Storage

```bash
# Create storage account
az storage account create \
  --name hrrrasnowzarr \
  --resource-group your-resource-group \
  --location eastus

# Create container
az storage container create \
  --name hrrr-asnow \
  --account-name hrrrasnowzarr

# Get connection string
az storage account show-connection-string \
  --name hrrrasnowzarr
```

### 3. Configure GitHub Secrets

Go to your repository: https://github.com/andrewnakas/HRRR_ASNOW_ZARR

1. Click **Settings** → **Secrets and variables** → **Actions**
2. Click **New repository secret**
3. Add the following secrets based on your provider:

**For S3:**
- Name: `AWS_ACCESS_KEY_ID`, Value: (your access key ID)
- Name: `AWS_SECRET_ACCESS_KEY`, Value: (your secret access key)
- Name: `AWS_REGION`, Value: `us-east-1` (or your region)

**For GCS:**
- Name: `GCS_SERVICE_ACCOUNT_KEY`, Value: (paste entire JSON key content)

**For Azure:**
- Name: `AZURE_STORAGE_ACCOUNT_NAME`, Value: (your account name)
- Name: `AZURE_STORAGE_ACCOUNT_KEY`, Value: (your account key)

### 4. Update config.yaml

Edit the config.yaml file in your repo:

```yaml
cloud_storage:
  provider: "s3"  # or "gcs" or "azure"
  bucket: "hrrr-asnow-zarr"  # your bucket name
  zarr_path: "hrrr-analysis-snowfall.zarr"
  region: "us-east-1"  # for S3 only
```

**Commit and push:**
```bash
git add config.yaml
git commit -m "Configure S3 cloud storage"
git push
```

### 5. Trigger the First Backfill Run

#### Via GitHub Web Interface:

1. Go to https://github.com/andrewnakas/HRRR_ASNOW_ZARR/actions
2. Click **HRRR ASNOW Cloud Backfill** workflow
3. Click **Run workflow** dropdown
4. Fill in:
   - **Branch**: `main`
   - **Start date**: `2014-10-01`
   - **End date**: `2014-10-07`
   - **Resume**: ✓ (checked)
5. Click green **Run workflow** button

#### Via GitHub CLI:

```bash
gh workflow run backfill_cloud.yml \
  -f start_date=2014-10-01 \
  -f end_date=2014-10-07 \
  -f resume=true
```

### 6. Monitor the Run

**View logs:**
1. Go to Actions tab
2. Click on the running workflow
3. Click on the "backfill" job
4. Watch the logs in real-time

**Expected output:**
```
Processing date range:
  Start: 2014-10-01
  End: 2014-10-07

Downloading 2014-10-01 00:00:00 (attempt 1/3)
✓ Downloaded hrrr_asnow_20141001_00.grib2 (6.84 MB)
✓ Appended 2014-10-01T00:00:00: ASNOW range [0.0000, 0.0023] m
...
```

**Check for success:**
- Workflow completes without errors
- `progress.json` is updated with last completed date
- Your cloud storage bucket shows the zarr data

### 7. Verify Data in Cloud

#### For S3:
```bash
# List zarr contents
aws s3 ls s3://hrrr-asnow-zarr/hrrr-analysis-snowfall.zarr/ --recursive

# Check size
aws s3 ls s3://hrrr-asnow-zarr/hrrr-analysis-snowfall.zarr/ --recursive --summarize | grep "Total Size"
```

#### For GCS:
```bash
gsutil ls -r gs://hrrr-asnow-zarr/hrrr-analysis-snowfall.zarr/
gsutil du -sh gs://hrrr-asnow-zarr/hrrr-analysis-snowfall.zarr/
```

#### For Azure:
```bash
az storage blob list --container-name hrrr-asnow --account-name hrrrasnowzarr
```

### 8. Enable Automated Daily Runs

The workflow is already configured to run daily at 06:00 UTC via cron schedule.

**To check the schedule:**
- View `.github/workflows/backfill_cloud.yml`
- Line: `cron: '0 6 * * *'`

**To change the schedule:**
Edit the cron expression:
- `'0 6 * * *'` = Daily at 06:00 UTC
- `'0 */6 * * *'` = Every 6 hours
- `'0 0 * * 0'` = Weekly on Sundays at midnight

**First automated run will happen:**
- Tomorrow at 06:00 UTC
- It will process the next 7 days after the last completed date in `progress.json`

## Production Monitoring

### Set Up Notifications

**Email notifications for failures:**
1. Go to repo Settings → Notifications
2. Enable "Actions" notifications
3. Or configure GitHub Actions to send emails/Slack messages

**Cost monitoring:**
- Set up billing alerts in AWS/GCP/Azure
- Expected cost: < $1/month
- Set alert threshold at $5/month to catch any issues

### Check Progress Regularly

```bash
# Clone repo and check progress
git pull
cat progress.json

# Or use GitHub API
curl https://raw.githubusercontent.com/andrewnakas/HRRR_ASNOW_ZARR/main/progress.json
```

### Validate Data Quality

After a few runs, validate the data:

```python
import xarray as xr
from src.cloud_storage import CloudStorageManager

cloud = CloudStorageManager()
ds = xr.open_zarr(
    cloud.get_zarr_path(),
    storage_options=cloud.get_storage_options()
)

print(f"Time range: {ds.time.values[0]} to {ds.time.values[-1]}")
print(f"Total timesteps: {len(ds.time)}")
print(f"Expected hours: {(ds.time.values[-1] - ds.time.values[0]).astype('timedelta64[h]').astype(int) + 1}")
print(f"Coverage: {len(ds.time) / ((ds.time.values[-1] - ds.time.values[0]).astype('timedelta64[h]').astype(int) + 1) * 100:.1f}%")
```

## Timeline Estimates

- **Initial setup**: 30-60 minutes
- **First test run** (7 days, ~168 hours): 2-3 hours
- **Full dataset** (2014-10-01 to present):
  - At 7 days per run, once per day: ~21 months
  - Running manually 4x per day: ~5 months
  - Running manually 24x per day: ~26 days

### Speed Up Strategy

**Option 1: Multiple Manual Runs**
Trigger multiple runs with different date ranges:
```bash
# Run 1
gh workflow run backfill_cloud.yml -f start_date=2014-10-01 -f end_date=2014-10-31

# Run 2
gh workflow run backfill_cloud.yml -f start_date=2014-11-01 -f end_date=2014-11-30

# Run 3
gh workflow run backfill_cloud.yml -f start_date=2014-12-01 -f end_date=2014-12-31

# Etc...
```

**Option 2: Increase Batch Size**
Edit `config.yaml`:
```yaml
github_actions:
  batch_size_days: 30  # Process 30 days at a time instead of 7
```

Note: Longer runs increase risk of timeout (6 hour limit)

**Option 3: Run Locally with Parallel Workers**
Use a powerful local machine or EC2 instance to run multiple date ranges in parallel.

## Troubleshooting Deployment

### Workflow Fails with "Access Denied"

**Check:**
1. Secrets are set correctly in GitHub
2. IAM permissions are correct
3. Bucket name matches config.yaml

**Fix:**
```bash
# Test credentials locally
export AWS_ACCESS_KEY_ID=...
export AWS_SECRET_ACCESS_KEY=...
python src/cloud_storage.py test
```

### Workflow Times Out

**Cause:** Processing too many days at once

**Fix:**
- Reduce `batch_size_days` in config.yaml to 3-5 days
- Or split into smaller manual runs

### Data Missing from NOMADS

**Cause:** NOMADS only keeps ~2 weeks of recent data

**Fix:**
- Start from 2 weeks ago and work forward
- Or use NCEI archive for historical data (different process)

### "eccodes not found" in GitHub Actions

**Cause:** System dependency not installed

**Check:** The workflow should install it automatically
```yaml
- name: Install system dependencies
  run: |
    sudo apt-get install -y libeccodes-dev
```

If it's missing, the step failed. Check the logs.

## Success Criteria

After first run, you should see:

✅ Workflow completed successfully
✅ `progress.json` updated with new date
✅ Zarr data visible in cloud storage bucket
✅ No error messages in workflow logs
✅ Can read data with xarray

## Next Steps After Deployment

1. **Let it run** - The daily automation will build the full dataset
2. **Monitor weekly** - Check progress.json and workflow success
3. **Validate monthly** - Run validation scripts on accumulated data
4. **Document usage** - Update README with your specific access patterns
5. **Share** - Consider making the dataset public once complete

## Support

If you encounter issues:
1. Check workflow logs in Actions tab
2. Review CLOUD_STORAGE.md for provider-specific help
3. Test locally with `./test_pipeline.sh`
4. Open an issue on GitHub

## Congratulations! 🎉

Your HRRR ASNOW Zarr archive is now deploying automatically!

The system will progressively build the complete historical dataset over the coming months, providing you with high-quality, model-native snowfall data for the entire CONUS domain.
