import pandas as pd
import pytest
import responses

import glm_met.cli as cli
from glm_met.sources.openmeteo import ARCHIVE_URL


@responses.activate
def test_backcompat_no_subcommand(nml_path, openmeteo_payload, tmp_path, monkeypatch):
    """`glm-met glm3.nml` (no subcommand) defaults to fetch + openmeteo."""
    responses.get(ARCHIVE_URL, json=openmeteo_payload)
    out = tmp_path / 'met.csv'
    cli.main([nml_path, '--start', '2000-07-01', '--end', '2000-07-02',
              '--output', str(out)])
    df = pd.read_csv(out)
    assert list(df.columns) == ['time', 'AirTemp', 'ShortWave', 'LongWave',
                                'RelHum', 'WindSpeed', 'Rain', 'Snow', 'SoilTemp']
    assert len(df) == 48
    assert df['time'].iloc[0] == '2000-07-01 00:00'


def test_project_implies_gee(nml_path, monkeypatch, capsys):
    captured = {}

    class FakeSource:
        timestep = 'hourly'

        def fetch(self, lat, lon, start, end, tz_offset):
            raise RuntimeError('stop here')

    def fake_get_source(name, **options):
        captured['name'] = name
        return FakeSource()

    monkeypatch.setattr(cli, 'get_source', fake_get_source)
    with pytest.raises(RuntimeError):
        cli.main([nml_path, '--project', 'my-project'])
    assert captured['name'] == 'gee'


def test_silo_requires_email(nml_path, monkeypatch):
    monkeypatch.delenv('GLM_MET_SILO_EMAIL', raising=False)
    with pytest.raises(SystemExit, match='email'):
        cli.main([nml_path, '--source', 'silo'])
