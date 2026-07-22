import os

import pandas as pd
import pytest
import responses

from glm_met.sources.silo import PATCHEDPOINT_URL, _nearest_stations

FIXTURES = os.path.join(os.path.dirname(__file__), 'fixtures')


@responses.activate
def test_nearest_stations():
    with open(os.path.join(FIXTURES, 'silo_stations_sample.txt')) as f:
        responses.get(PATCHEDPOINT_URL, body=f.read())
    near = _nearest_stations(-13.97769, 136.43762, n=3)
    assert len(near) == 3
    # Groote Eylandt Airport is ~3 km from the test site
    assert near.iloc[0]['name'] == 'GROOTE EYLANDT AIRPORT'
    assert near.iloc[0]['distance_km'] < 5
    assert near['distance_km'].is_monotonic_increasing


def test_plot_silo_comparison(tmp_path):
    pytest.importorskip('matplotlib')
    from glm_met.plots import plot_silo_comparison

    times = pd.date_range('2020-01-01', periods=72, freq='h')
    base = pd.DataFrame({
        'time': times,
        'AirTemp': 25.0,
        'ShortWave': 200.0,
        'Rain': 0.002,
    })
    adjusted = base.copy()
    adjusted['Rain'] = 0.004
    daily = pd.DataFrame(
        {'temp_mean': [26.0, 25.5, 24.8],
         'rain_m': [0.004, 0.004, 0.004],
         'rad_wm2': [210.0, 190.0, 205.0],
         'vp_hpa': [20.0, 21.0, 19.5]},
        index=pd.DatetimeIndex(['2020-01-01', '2020-01-02', '2020-01-03']))

    out = tmp_path / 'cmp.png'
    assert plot_silo_comparison(base, daily, adjusted, str(out)) is True
    assert out.stat().st_size > 10000
