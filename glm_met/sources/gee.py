import os

import numpy as np
import pandas as pd
from dateutil.relativedelta import relativedelta

from ..utils import deaccumulate_era5, saturation_vapor_pressure_hpa
from .base import MetSource

BANDS = [
    'temperature_2m',
    'dewpoint_temperature_2m',
    'u_component_of_wind_10m',
    'v_component_of_wind_10m',
    'soil_temperature_level_1',
    'surface_solar_radiation_downwards',
    'surface_thermal_radiation_downwards',
    'total_precipitation_hourly',
    'snowfall_hourly',
]


def clear_ee_credentials():
    """Remove stored Earth Engine OAuth credentials (same as 'logging out' locally).

    Deletes ``~/.config/earthengine/credentials``. Next use of ``initialize_ee`` will
    run the browser / notebook auth flow again. Does not revoke the token on
    Google's servers; for that, use your Google Account security settings.

    If you authenticated via Application Default Credentials (``gcloud auth
    application-default login``), sign out there separately — that uses a
    different file under ``~/.config/gcloud/``.
    """
    import ee
    path = ee.oauth.get_credentials_path()
    client_id = path + '-client-id.json'
    for p in (path, client_id):
        try:
            os.remove(p)
        except FileNotFoundError:
            pass


def initialize_ee(project):
    import ee
    try:
        ee.Initialize(project=project)
    except Exception:
        print("\n[INFO] Earth Engine credentials not found or expired.")
        print("[INFO] A browser window will open for authentication.")
        print("[INFO] If you are on a remote server, copy the URL and open it locally.\n")
        try:
            ee.Authenticate(auth_mode='notebook')
        except Exception as e:
            raise SystemExit(
                "\n[ERROR] Earth Engine authentication failed.\n"
                "Please ensure you have:\n"
                "  1. A Google Cloud project with the Earth Engine API enabled\n"
                "     -> https://console.cloud.google.com/apis/library/earthengine.googleapis.com\n"
                "  2. Registered the project for Earth Engine access\n"
                "     -> https://code.earthengine.google.com/register\n"
                "  3. Run: earthengine authenticate --auth_mode=notebook\n"
                f"\nOriginal error: {e}"
            )
        ee.Initialize(project=project)


def _fetch_raw_utc(lat, lon, start_date, end_date):
    """Fetch raw ERA5-Land band values at a point, on UTC timestamps.

    Radiation bands are returned as-is (accumulated J/m2 since 00 UTC of the
    same day); de-accumulation happens later over the full series so chunk
    boundaries do not matter. Missing pixels stay NaN.
    """
    import ee
    point = ee.Geometry.Point([lon, lat])
    collection = (
        ee.ImageCollection('ECMWF/ERA5_LAND/HOURLY')
        .filterBounds(point)
        .filterDate(start_date, end_date)
    )

    def extract_data(image):
        date = image.date().format('YYYY-MM-dd HH:mm')
        data = image.reduceRegion(
            reducer=ee.Reducer.first(),
            geometry=point,
            scale=1000,
            maxPixels=1e6
        )
        data_with_time = data.combine(ee.Dictionary({'time': date}))
        return ee.Feature(None, data_with_time)

    features = collection.map(extract_data).getInfo()['features']

    records = []
    for feat in features:
        props = feat['properties']
        record = {'time': props['time']}
        for band in BANDS:
            value = props.get(band)
            record[band] = np.nan if value is None else value
        records.append(record)
    return pd.DataFrame(records)


def _postprocess_raw(df_raw, tz_offset):
    """Pure-pandas conversion of raw UTC ERA5-Land values to the GLM schema."""
    df_raw = df_raw.copy()
    df_raw['time'] = pd.to_datetime(df_raw['time'])
    df_raw = df_raw.drop_duplicates('time').sort_values('time').reset_index(drop=True)

    temp_c = df_raw['temperature_2m'] - 273.15
    dew_c = df_raw['dewpoint_temperature_2m'] - 273.15
    rh = (saturation_vapor_pressure_hpa(dew_c)
          / saturation_vapor_pressure_hpa(temp_c) * 100).clip(0, 100)
    wind = np.sqrt(df_raw['u_component_of_wind_10m'] ** 2
                   + df_raw['v_component_of_wind_10m'] ** 2)

    precip = df_raw['total_precipitation_hourly'] * 24.0   # m/h -> m/day
    snow = df_raw['snowfall_hourly'] * 24.0                # m/h w.e. -> m/day

    df = pd.DataFrame({
        'time': df_raw['time'] + pd.Timedelta(hours=tz_offset),
        'AirTemp': temp_c,
        'ShortWave': deaccumulate_era5(
            df_raw['surface_solar_radiation_downwards'], df_raw['time']),
        'LongWave': deaccumulate_era5(
            df_raw['surface_thermal_radiation_downwards'], df_raw['time']),
        'RelHum': rh,
        'WindSpeed': wind,
        'Rain': (precip - snow).clip(lower=0),
        'Snow': snow,
        'SoilTemp': df_raw['soil_temperature_level_1'] - 273.15,
    })
    return df


class GEESource(MetSource):
    """ERA5-Land hourly data via Google Earth Engine (needs a registered GCP project)."""

    name = 'gee'
    timestep = 'hourly'

    def __init__(self, project):
        if not project:
            raise SystemExit(
                "[ERROR] The gee source needs --project <GCP_PROJECT_ID> "
                "(a Google Cloud project registered with Earth Engine)."
            )
        self.project = project

    def fetch(self, lat, lon, start, end, tz_offset):
        initialize_ee(self.project)

        start_ts = pd.to_datetime(start)
        end_ts = pd.to_datetime(end)
        chunks = []
        chunk_start = start_ts
        while chunk_start < end_ts:
            chunk_end = min(chunk_start + relativedelta(months=1), end_ts)
            print(f"[INFO] Fetching GEE chunk: {chunk_start.date()} to {chunk_end.date()}")
            chunks.append(_fetch_raw_utc(
                lat, lon,
                chunk_start.strftime('%Y-%m-%d'),
                chunk_end.strftime('%Y-%m-%d'),
            ))
            chunk_start = chunk_end

        raw = pd.concat(chunks, ignore_index=True)
        return _postprocess_raw(raw, tz_offset)
