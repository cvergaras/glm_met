"""Build GLM meteorological forcing files from Open-Meteo, SILO or Google Earth Engine."""

__version__ = '0.2.0'


def fetch_met(lat, lon, start, end, tz_offset=0, source='openmeteo',
              rain_units='m/day', keep_cloud=False, **options):
    """Fetch meteorological data and return a GLM-ready DataFrame.

    Parameters mirror the CLI: source is 'openmeteo' (default), 'silo'
    (needs email=...) or 'gee' (needs project=...); start/end are
    'YYYY-MM-DD' strings; tz_offset is the GLM timezone (hours from UTC).
    """
    from .core import finalize
    from .sources import get_source

    src = get_source(source, **options)
    df = src.fetch(lat, lon, start, end, tz_offset)
    return finalize(df, rain_units=rain_units, keep_cloud=keep_cloud)


__all__ = ['fetch_met', '__version__']
