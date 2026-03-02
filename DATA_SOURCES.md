# HRRR ASNOW Data Sources

This document explains where HRRR ASNOW data is available and how to access it.

## Current Implementation Status

✅ **NOMADS Recent Data** - Currently implemented and working
⚠️ **NCEI Historical Data** - Planned for future enhancement
⚠️ **AWS Open Data** - Planned for future enhancement

## Data Availability by Time Period

### Recent Data: Last ~2 Weeks (NOMADS)

**Time Range**: Rolling ~2 weeks (most recent data)
**Source**: NOAA NOMADS
**URL**: https://nomads.ncep.noaa.gov/pub/data/nccf/com/hrrr/prod/
**Status**: ✅ **Currently Working**

**Current Script Support**: ✅ Full support via `src/downloader.py`

This is what the current system uses. NOMADS provides real-time and very recent HRRR data.

**Limitations:**
- Only keeps ~2 weeks of data
- Older data is purged automatically
- Not suitable for historical backfill

### Historical Data: 2014-2021 (NCEI Archive)

**Time Range**: 2014-10-01 to 2021-12-31
**Source**: NOAA NCEI (National Centers for Environmental Information)
**URL**: https://www.ncei.noaa.gov/data/rapid-refresh/access/historical/analysis/
**Status**: ⚠️ **Not Yet Implemented**

**File Structure:**
```
YYYYMM/YYYYMMDD/hrrr_yyyymmdd_HHz_wrfsfcf00.grib2
```

**To Implement:**
1. Create `src/downloader_ncei.py` with NCEI-specific logic
2. Handle different URL structure
3. Add to backfill orchestration
4. Merge with NOMADS data seamlessly

**Example URL:**
```
https://www.ncei.noaa.gov/data/rapid-refresh/access/historical/analysis/201410/20141001/hrrr_20141001_00z_wrfsfcf00.grib2
```

### Recent Historical Data: 2022-Present (AWS Open Data)

**Time Range**: 2022-01-01 to ~2 weeks ago
**Source**: AWS Open Data Program
**URL**: s3://noaa-hrrr-bdp-pds/
**Status**: ⚠️ **Not Yet Implemented**

**Access Method**: AWS S3 (requires boto3)

**File Structure:**
```
s3://noaa-hrrr-bdp-pds/hrrr.YYYYMMDD/conus/hrrr.tHHz.wrfsfcf00.grib2
```

**To Implement:**
1. Use `boto3` or `s3fs` for S3 access
2. No authentication required (public bucket)
3. Add to downloader with S3 support
4. Handle different path structure

**Example Access:**
```python
import s3fs
fs = s3fs.S3FileSystem(anon=True)
files = fs.ls('noaa-hrrr-bdp-pds/hrrr.20220101/conus/')
```

## Current System Behavior

### What Works Now (NOMADS Only)

The current system:
- ✅ Downloads data from last ~2 weeks
- ✅ Processes GRIB2 to zarr
- ✅ Commits to GitHub with Git LFS
- ✅ Runs daily to stay current

### Example Workflow

**Day 1**: Start with 2026-02-20 to 2026-02-26 (7 days)
**Day 2**: Automatic run processes 2026-02-27 to 2026-03-05 (7 days)
**Day 3**: Automatic run processes 2026-03-06 to 2026-03-12 (7 days)
...and so on

**Result**: Continuously growing dataset of recent HRRR ASNOW data

## Future: Complete Historical Dataset

To build a complete 2014-present dataset, we'll need to:

### Phase 1: Current (✅ Done)
- Collect recent data from NOMADS
- Stay current with daily updates
- Build forward-looking dataset

### Phase 2: Historical Backfill (Future)
1. **Add NCEI downloader** for 2014-2021
2. **Add AWS downloader** for 2022-recent
3. **Merge datasets** into single zarr store
4. **Validate continuity** across sources

### Phase 3: Hybrid Operation (Future)
- NOMADS for current data (last 2 weeks)
- NCEI/AWS for backfill on demand
- Smart source selection based on date

## Implementation Roadmap

### Short Term (Now)
- ✅ Use NOMADS for recent data
- ✅ Build dataset going forward
- ✅ Daily automated updates

### Medium Term (Next Enhancement)
- [ ] Add NCEI downloader module
- [ ] Backfill 2014-2021 historical data
- [ ] Add AWS S3 downloader
- [ ] Backfill 2022 to ~2 weeks ago

### Long Term (Complete System)
- [ ] Unified download manager
- [ ] Automatic source selection
- [ ] Gap detection and filling
- [ ] Complete 2014-present coverage

## Manual Historical Data Download

If you need specific historical data right now, you can download manually:

### From NCEI
```bash
# Example: Download October 1, 2014, 00Z
wget https://www.ncei.noaa.gov/data/rapid-refresh/access/historical/analysis/201410/20141001/hrrr_20141001_00z_wrfsfcf00.grib2

# Process it
python src/processor.py data/hrrr-analysis-snowfall.zarr hrrr_20141001_00z_wrfsfcf00.grib2
```

### From AWS Open Data
```bash
# Install AWS CLI
pip install awscli

# Download (no authentication needed)
aws s3 cp s3://noaa-hrrr-bdp-pds/hrrr.20220101/conus/hrrr.t00z.wrfsfcf00.grib2 . --no-sign-request

# Process it
python src/processor.py data/hrrr-analysis-snowfall.zarr hrrr.t00z.wrfsfcf00.grib2
```

## Cost Considerations

### NOMADS (Current)
- ✅ Free
- ✅ No authentication required
- ✅ Rate limited (10 req/min respected)

### NCEI (Future)
- ✅ Free
- ✅ No authentication required
- ⚠️ Slower download speeds
- ⚠️ Large file sizes (full GRIB2 files)

### AWS Open Data (Future)
- ✅ Free (Requester Pays not enabled)
- ✅ No authentication required
- ✅ Fast download speeds
- ⚠️ Bandwidth from AWS (but free for this bucket)

## References

- **NOMADS**: https://nomads.ncep.noaa.gov/
- **NCEI HRRR**: https://www.ncei.noaa.gov/products/weather-climate-models/rapid-refresh-update
- **AWS Open Data**: https://registry.opendata.aws/noaa-hrrr-pds/
- **HRRR Documentation**: https://rapidrefresh.noaa.gov/hrrr/

## Questions?

See the main README.md or open a GitHub issue.

---

*Last Updated: 2026-03-02*
