from io import StringIO

import numpy as np
import pandas as pd
import requests

from ..utils import longwave_incoming, saturation_vapor_pressure_hpa
from .base import MetSource
from .openmeteo import OpenMeteoSource

DATADRILL_URL = "https://www.longpaddock.qld.gov.au/cgi-bin/silo/DataDrillDataset.php"

# Australia (SILO grid coverage), roughly
LAT_RANGE = (-44.5, -9.0)
LON_RANGE = (111.5, 154.5)


def _fetch_silo_daily(lat, lon, start, end, email):
    """Fetch SILO DataDrill daily data (rain, min/max temp, vapour pressure, radiation)."""
    params = {
        'lat': f"{lat:.4f}",
        'lon': f"{lon:.4f}",
        'start': pd.to_datetime(start).strftime('%Y%m%d'),
        'finish': pd.to_datetime(end).strftime('%Y%m%d'),
        'format': 'csv',
        'comment': 'RXNVJ',  # rain, max_temp, min_temp, vp, radiation
        'username': email,
        'password': 'apirequest',
    }
    print(f"[INFO] Fetching SILO DataDrill daily data: {start} to {end}")
    resp = requests.get(DATADRILL_URL, params=params, timeout=300)
    if not resp.ok or not resp.text.lstrip().startswith('latitude'):
        raise SystemExit(
            "[ERROR] SILO request failed: "
            f"{resp.text.strip().splitlines()[0] if resp.text.strip() else resp.status_code}"
        )

    df = pd.read_csv(StringIO(resp.text), skipinitialspace=True)
    df = df.rename(columns={'YYYY-MM-DD': 'date'})
    df['date'] = pd.to_datetime(df['date'])
    daily = pd.DataFrame({
        'temp_mean': ((df['max_temp'] + df['min_temp']) / 2.0).to_numpy(),  # degC
        'rain_m': (df['daily_rain'] / 1000.0).to_numpy(),          # mm -> m/day
        'rad_wm2': (df['radiation'] * 1e6 / 86400.0).to_numpy(),   # MJ/m2/day -> mean W/m2
        'vp_hpa': df['vp'].to_numpy(),
    }, index=pd.DatetimeIndex(df['date'], name='date'))
    return daily


def _print_adjustment_summary(base, daily):
    """Report how far the SILO daily values moved the Open-Meteo base series."""
    om = base.assign(_day=base['time'].dt.normalize()).groupby('_day').agg(
        om_temp=('AirTemp', 'mean'),
        om_rain=('Rain', 'mean'),      # mean intensity m/day == daily total m
        om_sw=('ShortWave', 'mean'),
    )
    rep = om.join(daily, how='left')
    matched = rep['temp_mean'].notna()
    print(f"[INFO] SILO adjustment: {int(matched.sum())}/{len(rep)} days matched")
    if not matched.any():
        return
    rep = rep[matched]
    temp_offset = rep['temp_mean'] - rep['om_temp']
    sw_factor = (rep['rad_wm2'] / rep['om_sw'].replace(0, np.nan)).dropna()
    print(f"[INFO]   AirTemp daily offset: mean {temp_offset.mean():+.2f} degC, "
          f"mean magnitude {temp_offset.abs().mean():.2f} degC")
    print(f"[INFO]   Rain total: SILO {rep['rain_m'].sum() * 1000:.0f} mm "
          f"vs Open-Meteo {rep['om_rain'].sum() * 1000:.0f} mm")
    print(f"[INFO]   ShortWave daily factor: mean {sw_factor.mean():.2f} "
          f"(range {sw_factor.min():.2f} to {sw_factor.max():.2f})")


def _adjust_hourly_to_daily(base, daily):
    """Scale/shift the hourly Open-Meteo series so daily aggregates match SILO.

    AirTemp: additive daily offset to match SILO's (max+min)/2.
    ShortWave: multiplicative daily factor to match SILO's daily-mean radiation.
    Rain: multiplicative daily factor to match SILO's daily total; SILO rain on
    a dry Open-Meteo day is spread uniformly. RelHum is recomputed from SILO
    vapour pressure against the adjusted temperature, and LongWave re-derived.
    """
    df = base.copy()
    df['_day'] = df['time'].dt.normalize()
    df = df.merge(daily, left_on='_day', right_index=True, how='left')
    have = df['temp_mean'].notna()

    missing_days = df.loc[~have, '_day'].nunique()
    if missing_days:
        print(f"[WARN] {missing_days} days have no SILO data; "
              "Open-Meteo values kept unadjusted there")

    _print_adjustment_summary(base, daily)

    om_temp_mean = df.groupby('_day')['AirTemp'].transform('mean')
    df.loc[have, 'AirTemp'] += (df['temp_mean'] - om_temp_mean)[have]

    om_sw_mean = df.groupby('_day')['ShortWave'].transform('mean')
    sw_factor = df['rad_wm2'] / om_sw_mean.replace(0, np.nan)
    sw_rows = have & sw_factor.notna()
    df.loc[sw_rows, 'ShortWave'] *= sw_factor[sw_rows]

    # Mean hourly intensity (m/day) numerically equals the daily total in m.
    om_rain_mean = df.groupby('_day')['Rain'].transform('mean')
    wet = have & (df['rain_m'] > 0)
    scalable = wet & (om_rain_mean > 0)
    df.loc[scalable, 'Rain'] *= (df['rain_m'] / om_rain_mean)[scalable]
    uniform = wet & (om_rain_mean <= 0)
    df.loc[uniform, 'Rain'] = df.loc[uniform, 'rain_m']
    df.loc[have & (df['rain_m'] <= 0), 'Rain'] = 0.0

    rh = (100.0 * df['vp_hpa'] / saturation_vapor_pressure_hpa(df['AirTemp'])).clip(0, 100)
    df.loc[have, 'RelHum'] = rh[have]
    df.loc[have, 'LongWave'] = longwave_incoming(
        df['AirTemp'], df['RelHum'], df['Cloud'])[have]

    return df.drop(columns=['_day', 'temp_mean', 'rain_m', 'rad_wm2', 'vp_hpa'])


class SiloSource(MetSource):
    """SILO-corrected hourly data for Australia.

    Uses the Open-Meteo hourly series as the base and adjusts it per day so
    temperature, rainfall and solar radiation aggregates match SILO's
    station-interpolated daily values (DataDrill, 0.05 degree grid).
    """

    name = 'silo'
    timestep = 'hourly'

    def __init__(self, email, model='best_match'):
        self.email = email
        self.model = model

    def fetch(self, lat, lon, start, end, tz_offset):
        if not (LAT_RANGE[0] <= lat <= LAT_RANGE[1]
                and LON_RANGE[0] <= lon <= LON_RANGE[1]):
            raise SystemExit(
                f"[ERROR] SILO only covers Australia (lat {LAT_RANGE}, lon {LON_RANGE}); "
                f"got lat={lat}, lon={lon}. Use --source openmeteo instead."
            )
        daily = _fetch_silo_daily(lat, lon, start, end, self.email)
        base = OpenMeteoSource(model=self.model).fetch(lat, lon, start, end, tz_offset)
        return _adjust_hourly_to_daily(base, daily)
