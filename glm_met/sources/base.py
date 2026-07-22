import abc


class MetSource(abc.ABC):
    """A meteorological data source.

    Implementations return a pandas DataFrame with the normalized GLM schema:
    time (naive local time), AirTemp (degC), ShortWave (W/m2), LongWave (W/m2),
    RelHum (%), WindSpeed (m/s), Rain (m/day), Snow (m/day water-equivalent),
    and optionally SoilTemp (degC) and Cloud (fraction 0-1).
    """

    name = None
    timestep = 'hourly'

    @abc.abstractmethod
    def fetch(self, lat, lon, start, end, tz_offset):
        """Fetch data for a point and date range (YYYY-MM-DD strings)."""
