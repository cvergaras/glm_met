import numpy as np
import pandas as pd
import pytest

from glm_met.sources.gee import _postprocess_raw


def _make_raw(times_utc):
    n = len(times_utc)
    acc = []
    for t in times_utc:
        hours = t.hour if t.hour != 0 else 24
        acc.append(hours * 200.0 * 3600.0)  # constant 200 W/m2 accumulated
    return pd.DataFrame({
        'time': [t.strftime('%Y-%m-%d %H:%M') for t in times_utc],
        'temperature_2m': np.full(n, 293.15),
        'dewpoint_temperature_2m': np.full(n, 283.15),
        'u_component_of_wind_10m': np.full(n, 3.0),
        'v_component_of_wind_10m': np.full(n, 4.0),
        'soil_temperature_level_1': np.full(n, 288.15),
        'surface_solar_radiation_downwards': acc,
        'surface_thermal_radiation_downwards': acc,
        'total_precipitation_hourly': np.full(n, 0.001),   # 1 mm/h
        'snowfall_hourly': np.zeros(n),
    })


def test_postprocess_across_chunk_boundary():
    # Simulate two monthly chunks concatenated: continuous hourly UTC series.
    times = pd.date_range('2020-01-30 01:00', '2020-02-02 00:00', freq='h')
    raw = pd.concat([
        _make_raw(times[:24]), _make_raw(times[24:])
    ], ignore_index=True)
    df = _postprocess_raw(raw, tz_offset=0)

    # No NaN anywhere (the old .diff-per-chunk produced NaN at boundaries)
    assert not df.drop(columns=['time']).isna().any().any()
    # Constant flux recovered everywhere, including daily resets
    assert df['ShortWave'].to_numpy() == pytest.approx(np.full(len(df), 200.0))
    assert df['LongWave'].to_numpy() == pytest.approx(np.full(len(df), 200.0))


def test_postprocess_units_and_values():
    times = pd.date_range('2020-06-01 01:00', periods=24, freq='h')
    df = _postprocess_raw(_make_raw(times), tz_offset=10)

    assert df['AirTemp'].iloc[0] == pytest.approx(20.0)
    assert df['SoilTemp'].iloc[0] == pytest.approx(15.0)
    assert df['WindSpeed'].iloc[0] == pytest.approx(5.0)      # 3-4-5 triangle
    assert 50 < df['RelHum'].iloc[0] < 55                     # dewpoint 10C at 20C
    assert df['Rain'].iloc[0] == pytest.approx(0.024)         # 1 mm/h -> m/day
    # tz shift applied
    assert df['time'].iloc[0] == pd.Timestamp('2020-06-01 11:00')


def test_postprocess_missing_data_stays_nan():
    times = pd.date_range('2020-06-01 01:00', periods=3, freq='h')
    raw = _make_raw(times)
    raw.loc[1, 'temperature_2m'] = np.nan
    df = _postprocess_raw(raw, tz_offset=0)
    assert np.isnan(df['AirTemp'].iloc[1])                    # not silently 0 degC
