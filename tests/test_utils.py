import numpy as np
import pandas as pd
import pytest

from glm_met.utils import (
    calculate_relative_humidity,
    deaccumulate_era5,
    longwave_incoming,
    rain_to_units,
    saturation_vapor_pressure_hpa,
)


def test_saturation_vapor_pressure():
    # ~6.11 hPa at 0 degC, ~23.4 hPa at 20 degC (Magnus)
    assert saturation_vapor_pressure_hpa(0.0) == pytest.approx(6.112, abs=0.01)
    assert saturation_vapor_pressure_hpa(20.0) == pytest.approx(23.4, abs=0.3)


def test_relative_humidity():
    # dewpoint == temperature -> saturated
    assert calculate_relative_humidity(293.15, 293.15) == pytest.approx(100.0)
    rh = calculate_relative_humidity(293.15, 283.15)  # 20 degC, dewpoint 10 degC
    assert 50 < rh < 55


def test_longwave_physical_range():
    lw = longwave_incoming(15.0, 70.0, 0.0)
    assert 250 < lw < 360


def test_longwave_monotonic_in_cloud():
    clear = longwave_incoming(15.0, 70.0, 0.0)
    half = longwave_incoming(15.0, 70.0, 0.5)
    overcast = longwave_incoming(15.0, 70.0, 1.0)
    assert clear < half < overcast


def test_longwave_vectorized():
    temps = pd.Series([0.0, 10.0, 25.0])
    lw = longwave_incoming(temps, pd.Series([80.0] * 3), pd.Series([0.3] * 3))
    assert len(lw) == 3
    assert (np.diff(lw) > 0).all()


def test_deaccumulate_era5():
    # Two synthetic days: constant 100 W/m2 flux, accumulation resets at 00 UTC.
    # Value stamped at hour H holds the total since midnight; the value at
    # 00 UTC holds the full previous day (24h * 100 W/m2 * 3600 s).
    times = pd.date_range('2020-01-01 01:00', periods=48, freq='h')
    acc = []
    for t in times:
        hours_since_midnight = t.hour if t.hour != 0 else 24
        acc.append(hours_since_midnight * 100.0 * 3600.0)
    flux = deaccumulate_era5(acc, times)
    assert not np.isnan(flux).any()
    assert flux == pytest.approx(np.full(48, 100.0))


def test_deaccumulate_era5_no_negative_at_reset():
    # Plain diff would go hugely negative at 01 UTC; the reset rule must not.
    times = pd.date_range('2020-01-01 22:00', periods=6, freq='h')
    acc = [22 * 3.6e5, 23 * 3.6e5, 24 * 3.6e5, 3.6e5, 2 * 3.6e5, 3 * 3.6e5]
    flux = deaccumulate_era5(acc, times)
    assert (flux >= 0).all()
    assert flux == pytest.approx(np.full(6, 100.0))


def test_rain_to_units():
    s = pd.Series([0.024])
    assert rain_to_units(s, 'm/day').iloc[0] == pytest.approx(0.024)
    assert rain_to_units(s, 'mm/day').iloc[0] == pytest.approx(24.0)
    assert rain_to_units(s, 'mm/hour').iloc[0] == pytest.approx(1.0)
    with pytest.raises(ValueError):
        rain_to_units(s, 'inches')
