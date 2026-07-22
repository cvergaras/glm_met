import time
from datetime import date, timedelta

import pandas as pd
import requests

from ..utils import longwave_incoming
from .base import MetSource

ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"

HOURLY_VARS = [
    "temperature_2m",
    "relative_humidity_2m",
    "rain",
    "snowfall",
    "wind_speed_10m",
    "shortwave_radiation",
    "cloud_cover",
    "soil_temperature_0_to_7cm",
]

MODELS = ("best_match", "era5_land", "era5")


def _request_chunk(lat, lon, start_date, end_date, model, hourly=HOURLY_VARS,
                   extra_params=None, retries=3):
    params = {
        "latitude": lat,
        "longitude": lon,
        "start_date": start_date,
        "end_date": end_date,
        "hourly": ",".join(hourly),
        "wind_speed_unit": "ms",
        "timezone": "UTC",
        "models": model,
    }
    if extra_params:
        params.update(extra_params)

    for attempt in range(retries):
        try:
            resp = requests.get(ARCHIVE_URL, params=params, timeout=120)
        except requests.ConnectionError as e:
            if attempt == retries - 1:
                raise SystemExit(f"[ERROR] Could not reach Open-Meteo: {e}")
            time.sleep(2 ** attempt)
            continue
        if resp.status_code in (429, 500, 502, 503, 504) and attempt < retries - 1:
            time.sleep(2 ** attempt)
            continue
        if not resp.ok:
            try:
                reason = resp.json().get('reason', resp.text)
            except ValueError:
                reason = resp.text
            raise SystemExit(f"[ERROR] Open-Meteo request failed: {reason}")
        return resp.json()
    raise SystemExit("[ERROR] Open-Meteo request failed after retries")


class OpenMeteoSource(MetSource):
    """ERA5 / ERA5-Land hourly data from the Open-Meteo archive API (no API key)."""

    name = 'openmeteo'
    timestep = 'hourly'

    def __init__(self, model='best_match'):
        if model not in MODELS:
            raise ValueError(f"model must be one of {MODELS}")
        self.model = model

    def fetch(self, lat, lon, start, end, tz_offset):
        # Request UTC with a day of padding on each side so the requested
        # local-time window is fully covered after the timezone shift.
        start_d = pd.to_datetime(start).date() - timedelta(days=1)
        end_d = min(pd.to_datetime(end).date() + timedelta(days=1), date.today())

        frames = []
        chunk_start = start_d
        while chunk_start <= end_d:
            chunk_end = min(chunk_start + timedelta(days=365), end_d)
            print(f"[INFO] Fetching Open-Meteo chunk: {chunk_start} to {chunk_end}")
            payload = _request_chunk(lat, lon, chunk_start.isoformat(),
                                     chunk_end.isoformat(), self.model)
            frames.append(pd.DataFrame(payload['hourly']))
            chunk_start = chunk_end + timedelta(days=1)

        raw = pd.concat(frames, ignore_index=True)
        df = pd.DataFrame({'time': pd.to_datetime(raw['time'])})
        df['AirTemp'] = raw['temperature_2m'].astype(float)
        df['ShortWave'] = raw['shortwave_radiation'].astype(float)
        df['RelHum'] = raw['relative_humidity_2m'].astype(float)
        df['WindSpeed'] = raw['wind_speed_10m'].astype(float)
        df['Rain'] = raw['rain'] * 24.0 / 1000.0            # mm/h -> m/day
        # snowfall is cm/h of fresh snow; ~7:1 snow:water ratio per Open-Meteo docs
        df['Snow'] = raw['snowfall'] * 10.0 / 7.0 * 24.0 / 1000.0  # -> m/day w.e.
        df['SoilTemp'] = raw['soil_temperature_0_to_7cm']
        df['Cloud'] = raw['cloud_cover'] / 100.0
        df['LongWave'] = longwave_incoming(df['AirTemp'], df['RelHum'], df['Cloud'])

        df['time'] = df['time'] + pd.Timedelta(hours=tz_offset)
        window_start = pd.to_datetime(start)
        window_end = pd.to_datetime(end) + pd.Timedelta(hours=23)
        df = df[(df['time'] >= window_start) & (df['time'] <= window_end)]
        return df.reset_index(drop=True)
