import numpy as np
import pandas as pd
import pytest
import responses

from glm_met.sources.openmeteo import ARCHIVE_URL
from glm_met.sources.silo import DATADRILL_URL, SiloSource, _fetch_silo_daily


def test_australia_bounds_guard():
    src = SiloSource(email='someone@example.com')
    with pytest.raises(SystemExit, match='openmeteo'):
        src.fetch(46.0, -89.7, '2020-01-01', '2020-01-05', 0)


@responses.activate
def test_fetch_silo_daily_parsing(silo_body):
    responses.get(DATADRILL_URL, body=silo_body)
    daily = _fetch_silo_daily(-27.5, 151.9, '2020-01-25', '2020-02-10',
                              'someone@example.com')
    assert daily.index[0] == pd.Timestamp('2020-01-25')
    assert len(daily) == 17
    assert daily.loc['2020-02-09', 'rain_m'] == pytest.approx(0.0653)
    # radiation MJ/m2/day -> daily-mean W/m2 stays physical
    assert daily['rad_wm2'].between(0, 500).all()
    assert daily['temp_mean'].between(-10, 50).all()


@responses.activate
def test_silo_error_exits(silo_body):
    responses.get(DATADRILL_URL, body='Sorry, the requested point is invalid')
    with pytest.raises(SystemExit, match='SILO request failed'):
        _fetch_silo_daily(-27.5, 151.9, '2020-01-25', '2020-02-10', 'x@example.com')


@responses.activate
def test_silo_corrected_hourly_matches_daily_aggregates(silo_body, openmeteo_au_body):
    responses.get(DATADRILL_URL, body=silo_body)
    responses.get(ARCHIVE_URL, body=openmeteo_au_body,
                  content_type='application/json')
    src = SiloSource(email='someone@example.com')
    df = src.fetch(-27.5, 151.9, '2020-01-25', '2020-02-10', tz_offset=10)

    silo = _fetch_silo_daily(-27.5, 151.9, '2020-01-25', '2020-02-10',
                             'someone@example.com')
    day = df['time'].dt.normalize()
    common = silo.index.intersection(pd.DatetimeIndex(day.unique()))
    # only score full days (24 hourly rows)
    counts = day.value_counts()
    common = [d for d in common if counts.get(d, 0) == 24]
    assert len(common) >= 10

    for d in common:
        rows = df[day == d]
        # daily mean temperature matches SILO (max+min)/2
        assert rows['AirTemp'].mean() == pytest.approx(
            silo.loc[d, 'temp_mean'], abs=0.01)
        # daily rain total (mean intensity in m/day) matches SILO
        assert rows['Rain'].mean() == pytest.approx(
            silo.loc[d, 'rain_m'], abs=1e-6)
        # daily mean shortwave matches SILO radiation
        if rows['ShortWave'].mean() > 0:
            assert rows['ShortWave'].mean() == pytest.approx(
                silo.loc[d, 'rad_wm2'], rel=0.01)

    # dry SILO days are fully dry, wet days are wet
    d_dry = pd.Timestamp('2020-01-30')
    assert df.loc[day == d_dry, 'Rain'].sum() == 0
    assert df['RelHum'].between(0, 100).all()
    assert not np.isnan(df['LongWave']).any()
