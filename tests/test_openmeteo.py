import json

import responses

from glm_met.core import GLM_COLUMNS, finalize
from glm_met.sources.openmeteo import ARCHIVE_URL, OpenMeteoSource


@responses.activate
def test_fetch_schema_and_units(openmeteo_payload):
    responses.get(ARCHIVE_URL, json=openmeteo_payload)
    src = OpenMeteoSource()
    df = src.fetch(46.00881, -89.69953, '2000-07-01', '2000-07-03', tz_offset=-5)

    for col in GLM_COLUMNS + ['Cloud']:
        assert col in df.columns, col

    # tz shift applied: window clipped to local time
    assert df['time'].iloc[0].strftime('%Y-%m-%d %H:%M') == '2000-07-01 00:00'
    assert df['time'].dt.date.max().isoformat() == '2000-07-03'

    # July at Sparkling Lake: plausible physical values
    assert df['AirTemp'].between(-5, 45).all()
    assert df['ShortWave'].max() > 200          # sunny midday hours exist
    assert df['LongWave'].between(150, 500).all()
    assert df['RelHum'].between(0, 100).all()
    assert df['Rain'].max() < 0.5               # m/day, not mm
    assert df['Cloud'].between(0, 1).all()


@responses.activate
def test_finalize_output(openmeteo_payload):
    responses.get(ARCHIVE_URL, json=openmeteo_payload)
    df = OpenMeteoSource().fetch(46.0, -89.7, '2000-07-01', '2000-07-02', tz_offset=-5)
    out = finalize(df, rain_units='mm/day', keep_cloud=True)
    assert list(out.columns) == GLM_COLUMNS + ['Cloud']
    assert not out.drop(columns=['time']).isna().any().any()
    # hourly continuity
    assert (out['time'].diff().dropna().dt.total_seconds() == 3600).all()


@responses.activate
def test_bad_request_exits(openmeteo_payload):
    responses.get(ARCHIVE_URL, status=400,
                  body=json.dumps({'reason': 'Latitude must be in range'}))
    src = OpenMeteoSource()
    try:
        src.fetch(999, 0, '2000-07-01', '2000-07-02', 0)
        raised = False
    except SystemExit as e:
        raised = True
        assert 'Latitude' in str(e)
    assert raised
