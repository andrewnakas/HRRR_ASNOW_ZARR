# Quick Start Guide (Git LFS Storage)

Get your HRRR ASNOW Zarr archive running using Git LFS - **all data stored directly in GitHub!**

## What You Need

- GitHub account (free tier includes 1 GB LFS storage)
- Git with LFS extension installed

⚠️ **Important**: The full dataset (~25 GB) will require purchasing additional LFS storage (~$10-15/month). See [GIT_LFS_SETUP.md](GIT_LFS_SETUP.md) for cost details.

## Option 1: GitHub Actions (Fully Automated)

Let GitHub Actions build your dataset automatically - zero local setup!

### Step 1: Install Git LFS (Local Development Only)

If you want to clone the repository later:

**macOS:**
```bash
brew install git-lfs
git lfs install
```

**Ubuntu/Debian:**
```bash
sudo apt-get install git-lfs
git lfs install
```

**Windows:**
Download from https://git-lfs.github.com/

### Step 2: Enable Git LFS on GitHub

Git LFS is automatically enabled for your repository. No action needed!

### Step 3: Trigger the First Run

Go to your GitHub repository:
1. Click **Actions** tab
2. Select **HRRR ASNOW Backfill** workflow
3. Click **Run workflow**
4. Enter date range:
   - Start date: `2014-10-01`
   - End date: `2014-10-07` (test with 7 days first)
   - Resume: ✓ (checked)
5. Click green **Run workflow** button

### Step 4: Monitor Progress

**View the workflow:**
- Go to Actions tab
- Click on the running workflow
- Watch logs in real-time

**What it does:**
1. Downloads HRRR ASNOW data from NOMADS
2. Processes into zarr format
3. Commits to GitHub using Git LFS
4. Updates progress.json

**First run (7 days)**: ~2-3 hours

### Step 5: Check Results

After the workflow completes:

```bash
# Clone the repository with LFS
git clone https://github.com/andrewnakas/HRRR_ASNOW_ZARR
cd HRRR_ASNOW_ZARR

# Pull LFS data
git lfs pull

# Check the data
python3 scripts/utils.py info
```

### Step 6: Enable Daily Automation

The workflow is already configured to run **daily at 06:00 UTC**. It will:
- Automatically process the next 7 days
- Continue until the full dataset is complete
- No further action needed!

**Timeline**: ~21 months to complete full historical dataset (at 7 days per run)

## Option 2: Local Testing

Want to test locally before running on GitHub?

### Step 1: Clone Repository

```bash
# Install Git LFS first (see Step 1 above)

# Clone with LFS
git clone https://github.com/andrewnakas/HRRR_ASNOW_ZARR
cd HRRR_ASNOW_ZARR
```

### Step 2: Install Dependencies

**System dependencies:**
```bash
# macOS
brew install eccodes

# Ubuntu/Debian
sudo apt-get install libeccodes-dev libeccodes-tools
```

**Python dependencies:**
```bash
pip install -r requirements.txt
```

### Step 3: Test the Pipeline

```bash
./test_pipeline.sh
```

This will:
1. Create a test zarr store
2. Download one recent HRRR file
3. Process and verify the data

### Step 4: Run a Real Backfill

```bash
python src/backfill.py \
  --start 2024-01-01 \
  --end 2024-01-07 \
  --zarr data/hrrr-analysis-snowfall.zarr \
  --resume
```

### Step 5: Commit to GitHub

```bash
# Stage LFS files
git add data/hrrr-analysis-snowfall.zarr/
git add progress.json

# Commit
git commit -m "Add HRRR ASNOW data for 2024-01-01 to 2024-01-07"

# Push (LFS will handle large files automatically)
git push
```

## Understanding Git LFS Costs

### Free Tier
- **Storage**: 1 GB
- **Bandwidth**: 1 GB/month
- **Good for**: Testing with ~7-30 days of data

### Paid Tier (for full dataset)
- **Storage needed**: ~25 GB = 1 pack ($5/month)
- **Bandwidth needed**: ~10-20 GB/month = 1 pack ($5/month)
- **Total**: ~$10/month

### Alternative: Cloud Storage
If costs are a concern, use cloud storage instead:
- See [CLOUD_STORAGE.md](CLOUD_STORAGE.md)
- Cost: ~$0.50-1/month (S3/GCS/Azure)
- Workflow: [backfill_cloud.yml](.github/workflows/backfill_cloud.yml)

## Accessing the Data

Once data is available in GitHub:

```bash
# Clone with LFS
git clone https://github.com/andrewnakas/HRRR_ASNOW_ZARR
cd HRRR_ASNOW_ZARR
git lfs pull

# Use the data
python3
```

```python
import xarray as xr

# Open the zarr store
ds = xr.open_zarr('data/hrrr-analysis-snowfall.zarr')

# Explore
print(ds)
print(f"Time range: {ds.time.values[0]} to {ds.time.values[-1]}")
print(f"Total hours: {len(ds.time)}")

# Get snowfall data
snowfall = ds['accumulated_snowfall']
print(f"ASNOW range: {snowfall.min().values:.4f} to {snowfall.max().values:.4f} m")
```

## Monitoring Progress

### Check Progress File
```bash
cat progress.json
```

Or view online:
```
https://raw.githubusercontent.com/andrewnakas/HRRR_ASNOW_ZARR/main/progress.json
```

### Check LFS Usage

Go to your repo settings:
```
https://github.com/andrewnakas/HRRR_ASNOW_ZARR/settings
```

Navigate to: **Billing → Git LFS Data**

### View Workflow Runs

```
https://github.com/andrewnakas/HRRR_ASNOW_ZARR/actions
```

## Troubleshooting

### "This repository is over its data quota"

You've exceeded the free 1 GB LFS limit.

**Solutions:**
1. Purchase LFS data pack: https://github.com/settings/billing
2. Switch to cloud storage (see CLOUD_STORAGE.md)

### LFS files not downloading

```bash
git lfs install --force
git lfs pull
```

### Workflow fails to push

Check if you've hit LFS bandwidth limit:
- Go to Settings → Billing → Git LFS Data
- Purchase bandwidth pack if needed

### Slow git operations

Large LFS files make git operations slower.

**Speed up:**
```bash
# Clone without LFS first
GIT_LFS_SKIP_SMUDGE=1 git clone https://github.com/andrewnakas/HRRR_ASNOW_ZARR

# Pull LFS only when needed
cd HRRR_ASNOW_ZARR
git lfs pull
```

## Speed Up Data Collection

### Option 1: Increase Batch Size
Edit `config.yaml`:
```yaml
github_actions:
  batch_size_days: 30  # Process 30 days instead of 7
```

### Option 2: Manual Runs
Trigger multiple workflows for different date ranges:
- 2014-10-01 to 2014-12-31
- 2015-01-01 to 2015-12-31
- etc.

### Option 3: Local Parallel Processing
Run multiple date ranges locally and push separately.

## Next Steps

1. ✅ **Run first test** (7 days)
2. ✅ **Verify data in GitHub**
3. ✅ **Monitor LFS usage**
4. ✅ **Purchase LFS packs if needed** (for full dataset)
5. ✅ **Let automation run** (daily at 06:00 UTC)

## Cost Comparison

| Storage | Setup | Monthly Cost | Notes |
|---------|-------|--------------|-------|
| **Git LFS** | Easy | $10-15 | Simple, integrated with GitHub |
| **S3/Cloud** | Medium | $0.50-1 | Cheaper, more scalable |
| **Local Only** | Easy | $0 | No sharing, no backup |

**Recommendation**:
- Testing: Use Git LFS with free tier
- Production (full dataset): Use cloud storage for lower cost

## Migration Path

Start with Git LFS, migrate to cloud if costs grow:

1. Start with free LFS tier (test data)
2. When you hit limits, decide:
   - Pay for LFS packs (simple, integrated)
   - Migrate to cloud storage (cheaper long-term)

See [GIT_LFS_SETUP.md](GIT_LFS_SETUP.md) for migration instructions.

## Questions?

- **Git LFS Setup**: See [GIT_LFS_SETUP.md](GIT_LFS_SETUP.md)
- **Cloud Storage**: See [CLOUD_STORAGE.md](CLOUD_STORAGE.md)
- **Full Docs**: See [README.md](README.md)
- **Issues**: Open a GitHub issue

---

**Ready to start?** Trigger your first GitHub Actions run! 🚀
