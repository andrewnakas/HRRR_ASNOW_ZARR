"""
HRRR ASNOW Zarr Template Configuration
Creates the initial zarr store structure with proper coordinates and metadata
"""

import numpy as np
import xarray as xr
from pyproj import Transformer
import yaml
from pathlib import Path


class HRRRSnowfallTemplateConfig:
    """Template configuration for HRRR ASNOW zarr archive"""

    def __init__(self, config_path="config.yaml"):
        """Load configuration from YAML file"""
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)

        self.nx = self.config['grid']['nx']
        self.ny = self.config['grid']['ny']
        self.resolution = self.config['grid']['resolution_m']
        self.projection = self.config['grid']['projection']

    def create_coordinate_arrays(self):
        """Create x, y coordinate arrays for HRRR grid"""
        x = np.arange(self.nx) * self.resolution
        y = np.arange(self.ny) * self.resolution
        return x, y

    def create_latlon_grids(self, x, y):
        """Transform x, y coordinates to lat/lon using pyproj"""
        transformer = Transformer.from_crs(
            self.projection,
            "EPSG:4326",
            always_xy=True
        )

        xx, yy = np.meshgrid(x, y)
        lons, lats = transformer.transform(xx, yy)

        return lons.astype(np.float32), lats.astype(np.float32)

    def create_template(self):
        """
        Create xarray Dataset template for HRRR ASNOW zarr store

        Returns:
            xr.Dataset: Empty template with proper structure and metadata
        """
        # Create coordinate arrays
        x, y = self.create_coordinate_arrays()
        lons, lats = self.create_latlon_grids(x, y)

        # Create dataset template
        ds = xr.Dataset(
            data_vars={
                'accumulated_snowfall': (
                    ['time', 'y', 'x'],
                    np.zeros((0, self.ny, self.nx), dtype=np.float32),
                    {
                        'units': 'm',
                        'long_name': 'Total Accumulated Snowfall',
                        'standard_name': 'snowfall_amount',
                        'description': 'HRRR model ASNOW output - physical snow depth',
                        '_FillValue': np.nan,
                        'grid_mapping': 'lambert_conformal_conic'
                    }
                ),
                'latitude': (
                    ['y', 'x'],
                    lats,
                    {
                        'units': 'degrees_north',
                        'long_name': 'Latitude',
                        'standard_name': 'latitude'
                    }
                ),
                'longitude': (
                    ['y', 'x'],
                    lons,
                    {
                        'units': 'degrees_east',
                        'long_name': 'Longitude',
                        'standard_name': 'longitude'
                    }
                )
            },
            coords={
                'time': (
                    'time',
                    np.array([], dtype='datetime64[ns]'),
                    {
                        'long_name': 'Time',
                        'standard_name': 'time'
                    }
                ),
                'x': (
                    'x',
                    x,
                    {
                        'units': 'm',
                        'long_name': 'x coordinate of projection',
                        'standard_name': 'projection_x_coordinate'
                    }
                ),
                'y': (
                    'y',
                    y,
                    {
                        'units': 'm',
                        'long_name': 'y coordinate of projection',
                        'standard_name': 'projection_y_coordinate'
                    }
                )
            },
            attrs={
                'title': self.config['dataset']['name'],
                'source': 'NOAA NCEP HRRR Model',
                'institution': 'NOAA/NCEP',
                'grid_mapping': 'lambert_conformal_conic',
                'Conventions': 'CF-1.8',
                'history': f'Created from NOMADS HRRR GRIB2 files',
                'references': 'https://nomads.ncep.noaa.gov/',
                'comment': 'Sister dataset to Dynamical.org HRRR Analysis containing ASNOW variable'
            }
        )

        # Add grid mapping variable
        ds['lambert_conformal_conic'] = xr.DataArray(
            data=0,
            attrs={
                'grid_mapping_name': 'lambert_conformal_conic',
                'latitude_of_projection_origin': 38.5,
                'longitude_of_central_meridian': -97.5,
                'standard_parallel': [38.5, 38.5],
                'earth_radius': 6371229.0
            }
        )

        return ds


def initialize_zarr_store(zarr_path, config_path="config.yaml"):
    """
    Initialize an empty zarr store with the HRRR ASNOW template

    Args:
        zarr_path: Path where zarr store should be created
        config_path: Path to configuration YAML file
    """
    import zarr

    # Load config for encoding settings
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)

    # Create template
    template_config = HRRRSnowfallTemplateConfig(config_path)
    template = template_config.create_template()

    # Encoding for efficient storage
    encoding = {
        'accumulated_snowfall': {
            'compressor': zarr.Blosc(
                cname=config['zarr_encoding']['compressor'],
                clevel=config['zarr_encoding']['compression_level'],
                shuffle=config['zarr_encoding']['shuffle']
            ),
            'chunks': (
                config['zarr_encoding']['chunks']['time'],
                config['zarr_encoding']['chunks']['y'],
                config['zarr_encoding']['chunks']['x']
            ),
        },
        'time': {'chunks': (config['zarr_encoding']['chunks']['time'],)},
        'latitude': {'chunks': (config['zarr_encoding']['chunks']['y'],
                               config['zarr_encoding']['chunks']['x'])},
        'longitude': {'chunks': (config['zarr_encoding']['chunks']['y'],
                                config['zarr_encoding']['chunks']['x'])}
    }

    # Create zarr directory if needed
    Path(zarr_path).parent.mkdir(parents=True, exist_ok=True)

    # Write to zarr
    template.to_zarr(zarr_path, mode='w', encoding=encoding, consolidated=True)
    print(f"✓ Initialized zarr store at {zarr_path}")
    print(f"  Grid size: {template_config.nx} x {template_config.ny}")
    print(f"  Resolution: {template_config.resolution}m (3km)")

    return zarr_path


if __name__ == "__main__":
    import sys

    zarr_path = sys.argv[1] if len(sys.argv) > 1 else "data/hrrr-analysis-snowfall.zarr"
    config_path = sys.argv[2] if len(sys.argv) > 2 else "config.yaml"

    initialize_zarr_store(zarr_path, config_path)
