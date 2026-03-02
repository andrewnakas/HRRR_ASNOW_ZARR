# Quick Start Guide

Get your HRRR ASNOW Zarr archive up and running in minutes!

## Prerequisites

- Python 3.11+
- Git
- GitHub account (for automated backfill)
- Cloud storage account (recommended: AWS, GCS, or Azure)

## Option 1: GitHub Actions (Recommended)

Let GitHub Actions automatically build your dataset - no local setup required!

### Step 1: Configure Cloud Storage

1. Choose a cloud provider (S3, GCS, or Azure)
2. Create a bucket/container
3. Add credentials to GitHub Secrets:

**For Amazon S3:**
- Go to your repo → Settings → Secrets → Actions
- Add these secrets:
  - `AWS_ACCESS_KEY_ID`: Your AWS access key
  - `AWS_SECRET_ACCESS_KEY`: Your AWS secret key
  - `AWS_REGION`: e.g., `us-east-1` (optional)

**For Google Cloud Storage:**
- Create a service account with Storage Admin permissions
- Download the JSON key
- Add this secret:
  - `GCS_SERVICE_ACCOUNT_KEY`: Paste the entire JSON content

**For Azure:**
- Add these secrets:
  - `AZURE_STORAGE_ACCOUNT_NAME`: Your storage account name
  - `AZURE_STORAGE_ACCOUNT_KEY`: Your account key

### Step 2: Update config.yaml

Edit `config.yaml` and set your cloud storage settings:

```yaml
cloud_storage:
  provider: "s3"  # or "gcs" or "azure"
  bucket: "your-bucket-name"
  zarr_path: "hrrr-analysis-snowfall.zarr"
  region: "us-east-1"  # for S3 only
```

Commit and push:
```bash
git add config.yaml
git commit -m "Configure cloud storage"
git push
```

### Step 3: Trigger the First Run

Go to your GitHub repository:
1. Click **Actions** tab
2. Select **HRRR ASNOW Cloud Backfill**
3. Click **Run workflow**
4. Enter date range:
   - Start date: `2014-10-01`
   - End date: `2014-10-07`
   - Resume: ✓ (checked)
5. Click **Run workflow**

### Step 4: Monitor Progress

- Watch the workflow run in the Actions tab
- Check `progress.json` after each run to see what's been completed
- The workflow will automatically run daily to process more data

### Done!

The system will now automatically:
- Download HRRR ASNOW data from NOMADS
- Process and compress it
- Upload to your cloud storage
- Continue daily until the full dataset is complete (~21 months for full history)

## Option 2: Local Testing

Want to test locally first?

### Step 1: Install System Dependencies

**macOS:**
```bash
brew install eccodes
```

**Ubuntu/Debian:**
```bash
sudo apt-get update
sudo apt-get install libeccodes-dev libeccodes-tools
```

### Step 2: Install Python Dependencies

```bash
pip install -r requirements.txt
```

### Step 3: Run the Test Pipeline

```bash
./test_pipeline.sh
```

This will:
1. Create a test zarr store
2. Download a single recent HRRR file
3. Process it and add to zarr
4. Verify the data

### Step 4: Run a Real Backfill

**Without cloud storage (local only):**
```bash
python src/backfill.py \
  --start 2024-01-01 \
  --end 2024-01-07 \
  --zarr data/hrrr-analysis-snowfall.zarr
```

**With cloud storage:**
```bash
# First, configure cloud storage
./setup_cloud.sh

# Then run backfill
python src/backfill_cloud.py \
  --start 2024-01-01 \
  --end 2024-01-07 \
  --resume
```

## Option 3: Manual One-off Downloads

Just want to grab a specific file?

```bash
# Download a single hour
python src/downloader.py 2024-01-15 12 tmp/

# This will create: tmp/hrrr_asnow_20240115_12.grib2
```

## Accessing the Data

Once data is available in cloud storage:

```python
import xarray as xr
from src.cloud_storage import CloudStorageManager

# Set up cloud credentials first (export AWS_ACCESS_KEY_ID=... etc.)

# Load the zarr store
cloud = CloudStorageManager()
ds = xr.open_zarr(
    cloud.get_zarr_path(),
    storage_options=cloud.get_storage_options()
)

# Use the data
print(ds)
snowfall = ds['accumulated_snowfall']
```

## Monitoring Progress

### Check Progress File
```bash
cat progress.json
```

### Check Zarr Store Info
```bash
python scripts/utils.py info
```

### Check Backfill Progress
```bash
python scripts/utils.py progress
```

## Troubleshooting

### "No module named 'cfgrib'"
Install dependencies: `pip install -r requirements.txt`

### "eccodes not found"
Install system dependency:
- macOS: `brew install eccodes`
- Ubuntu: `sudo apt-get install libeccodes-dev`

### "Access Denied" (Cloud Storage)
Check your credentials are set correctly:
```bash
# For S3
echo $AWS_ACCESS_KEY_ID

# For GCS
echo $GOOGLE_APPLICATION_CREDENTIALS

# For Azure
echo $AZURE_STORAGE_ACCOUNT_NAME
```

### Download fails with 404
The file may not exist yet on NOMADS. Try:
- An older date (NOMADS keeps ~2 weeks of data)
- Different hour (not all hours may be available)

### GitHub Actions fails
Check:
1. Secrets are added correctly
2. config.yaml has correct cloud storage settings
3. View the Actions logs for specific error messages

## Next Steps

1. **Set up monitoring** - Add your email to GitHub Actions notifications
2. **Validate data** - Run validation scripts periodically
3. **Share your dataset** - Consider making your bucket public
4. **Integrate** - Use the data in your applications!

## Questions?

- Check the [README.md](README.md) for detailed information
- Review [CLOUD_STORAGE.md](CLOUD_STORAGE.md) for cloud setup details
- Open an issue on GitHub

## Estimated Timeline

- **Setup**: 15-30 minutes
- **First test run** (7 days): 2-3 hours
- **Full dataset** (2014-2026): ~21 months at 7 days per day
  - Or faster with manual runs/parallel processing

Speed up by:
- Running multiple date ranges manually in parallel
- Increasing `batch_size_days` in config
- Using faster cloud storage regions

Happy data wrangling! ❄️🌨️
