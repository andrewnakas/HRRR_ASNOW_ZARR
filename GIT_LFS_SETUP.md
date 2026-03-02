# Git LFS Setup Guide

This project uses **Git Large File Storage (LFS)** to store zarr data files directly in GitHub instead of using external cloud storage (S3/GCS/Azure).

## What is Git LFS?

Git LFS is a Git extension that replaces large files with text pointers in your Git repository, while storing the actual file contents on a remote server. This allows you to version large files without bloating your Git repository.

## Important Limitations & Costs

⚠️ **Before you proceed, understand these limitations:**

### Storage Limits
- **Free tier**: 1 GB storage, 1 GB/month bandwidth
- **Full dataset size**: ~20-25 GB compressed
- **Cost**: $5/month per 50 GB storage pack + $5/month per 50 GB bandwidth pack

### Bandwidth Costs
Every time you:
- Clone the repository
- Pull updates
- Checkout branches

...you download LFS files, consuming bandwidth.

**Monthly bandwidth estimate:**
- Daily automated runs: ~2-3 GB/month (GitHub Actions)
- Local development (5 clones/month): ~100-125 GB
- **Total cost**: ~$10-15/month

### Comparison to Cloud Storage

| Aspect | Git LFS | Cloud Storage (S3) |
|--------|---------|-------------------|
| Setup complexity | Simple | Moderate |
| Monthly cost | $10-15 | $0.50-1.00 |
| Storage limit | Unlimited (paid) | Unlimited |
| Bandwidth cost | $5 per 50GB | $0.09/GB (after 100GB free) |
| Repository integration | Seamless | Requires separate access |
| Clone speed | Slower (LFS downloads) | Faster (data separate) |

💡 **Recommendation**: Git LFS is good for small datasets or testing. For the full 20GB+ dataset, cloud storage (S3/GCS/Azure) is more cost-effective.

## Installation

### macOS
```bash
brew install git-lfs
git lfs install
```

### Ubuntu/Debian
```bash
sudo apt-get install git-lfs
git lfs install
```

### Windows
Download from: https://git-lfs.github.com/

## Setup for This Repository

### First Time Setup

1. **Install Git LFS** (see above)

2. **Clone the repository with LFS**:
   ```bash
   git clone https://github.com/andrewnakas/HRRR_ASNOW_ZARR
   cd HRRR_ASNOW_ZARR
   git lfs install
   ```

3. **Pull LFS files**:
   ```bash
   git lfs pull
   ```

### Verify LFS is Working

```bash
# Check LFS status
git lfs status

# See which files are tracked by LFS
git lfs ls-files

# Check LFS storage usage
git lfs fetch --all
```

## How It Works

### Tracked Files

The `.gitattributes` file specifies which files use LFS:

```
# All files in data/ directory
data/**/* filter=lfs diff=lfs merge=lfs -text

# All zarr chunk files
*.zarr/**/* filter=lfs diff=lfs merge=lfs -text

# Specific zarr patterns
**/.zarray filter=lfs diff=lfs merge=lfs -text
**/[0-9]* filter=lfs diff=lfs merge=lfs -text
```

### What Gets Stored Where

**In Git** (normal):
- Source code (.py files)
- Configuration (config.yaml)
- Documentation (.md files)
- Zarr metadata (.zgroup, .zattrs - small text files)
- Progress tracking (progress.json)

**In LFS** (large files):
- Zarr data chunks (in data/hrrr-analysis-snowfall.zarr/)
- Binary data arrays
- Compressed chunks

## GitHub Actions Integration

The workflow automatically:
1. Installs Git LFS
2. Pulls existing LFS data
3. Processes new data
4. Commits new zarr chunks to LFS
5. Pushes LFS objects and Git commits

No additional configuration needed!

## Working with LFS Locally

### Pulling Latest Data
```bash
git pull
git lfs pull
```

### Checking LFS Bandwidth Usage
```bash
# View your LFS quota
git lfs fetch --all --recent
```

### Preventing Accidental Large Downloads

If you just want the code without the large data files:
```bash
# Clone without LFS
GIT_LFS_SKIP_SMUDGE=1 git clone https://github.com/andrewnakas/HRRR_ASNOW_ZARR

# Later, if you need the data
cd HRRR_ASNOW_ZARR
git lfs pull
```

## Monitoring Costs

### Check LFS Usage

Go to: https://github.com/andrewnakas/HRRR_ASNOW_ZARR/settings

Navigate to: **Billing → Git LFS Data**

You'll see:
- Storage used
- Bandwidth used this month
- Cost estimate

### Set Up Billing Alerts

1. Go to your GitHub account settings
2. Navigate to Billing
3. Set spending limit or alerts

## Troubleshooting

### "This repository is over its data quota"

**Cause**: Exceeded free 1 GB storage or bandwidth

**Solution**:
1. Purchase a data pack: https://github.com/settings/billing
2. Or migrate to cloud storage (see CLOUD_STORAGE.md)

### LFS files not downloading

```bash
# Re-initialize LFS
git lfs install --force

# Pull all LFS files
git lfs pull
```

### "Encountered X file(s) that should have been pointers"

```bash
# This happens if large files were committed without LFS
# Fix by re-tracking them
git lfs migrate import --include="data/**/*,*.zarr/**/*"
```

### Slow clones

**Cause**: LFS downloading many large files

**Solutions**:
- Use `GIT_LFS_SKIP_SMUDGE=1` to skip LFS on clone
- Use `--depth=1` for shallow clones
- Download only specific LFS files: `git lfs fetch --include="specific/path"`

## Cost Optimization Tips

### 1. Limit Local Clones
- Use one persistent clone for development
- Use `git fetch` instead of repeatedly cloning

### 2. Skip LFS When Not Needed
```bash
# For code-only work
GIT_LFS_SKIP_SMUDGE=1 git clone ...
```

### 3. Use Sparse Checkout
```bash
# Only checkout specific paths
git sparse-checkout init --cone
git sparse-checkout set src/ scripts/
```

### 4. Clean Up Old LFS Files Locally
```bash
# Remove old LFS files from your local cache
git lfs prune
```

## Migration to Cloud Storage

If costs get too high, you can migrate to cloud storage:

1. **Stop the current backfill**
2. **Set up cloud storage** (see CLOUD_STORAGE.md)
3. **Migrate existing data**:
   ```bash
   # Download current LFS data
   git lfs pull

   # Upload to cloud
   python src/cloud_storage.py setup s3 your-bucket
   python -c "
   from src.cloud_storage import CloudStorageManager
   cloud = CloudStorageManager()
   cloud.sync_to_cloud('data/hrrr-analysis-snowfall.zarr')
   "
   ```
4. **Remove LFS data from repo**:
   ```bash
   git rm -r data/
   git commit -m "Migrate to cloud storage"
   ```
5. **Update config.yaml** to use cloud storage
6. **Switch to backfill_cloud.yml workflow**

## FAQ

**Q: How much will this cost for the full 25GB dataset?**
A: ~$10-15/month with Git LFS vs ~$0.50-1/month with S3

**Q: Can I use both LFS and cloud storage?**
A: Yes, but it's redundant. Choose one approach.

**Q: What happens when I hit the LFS quota?**
A: GitHub will prevent further LFS operations until you upgrade.

**Q: Can I get more free LFS bandwidth?**
A: No, 1GB/month is the free limit. You need to purchase data packs.

**Q: Is LFS data backed up?**
A: Yes, GitHub backs up LFS data, but it's tied to your repository.

## Current Setup

This repository is configured to:
- ✅ Use Git LFS for zarr data
- ✅ Commit all data directly to GitHub
- ✅ Run automated backfill via GitHub Actions
- ✅ Track progress in progress.json

**No external cloud storage needed!**

---

*For questions or issues, see the main README.md or open a GitHub issue.*
