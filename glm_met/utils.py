import numpy as np
import pandas as pd

STEFAN_BOLTZMANN = 5.670374419e-8  # W m-2 K-4


def saturation_vapor_pressure_hpa(temp_c):
    """Saturation vapour pressure (hPa) via the Magnus formula.

    Accepts scalars or numpy/pandas arrays.
    """
    return 6.112 * 10 ** ((7.5 * temp_c) / (temp_c + 237.3))


def calculate_relative_humidity(temp_k, dewpoint_k):
    temp_c = temp_k - 273.15
    dewpoint_c = dewpoint_k - 273.15

    es = saturation_vapor_pressure_hpa(temp_c)
    e = saturation_vapor_pressure_hpa(dewpoint_c)

    rh = max(0, min((e / es) * 100, 100))
    return rh


def longwave_incoming(air_temp_c, rel_hum_pct, cloud_frac=0.0):
    """Incoming longwave radiation LW_IN (W/m2) estimated from screen-level data.

    Clear-sky emissivity: Brutsaert (1975), eps_cs = 1.24 * (e_a / T_K)^(1/7)
    with e_a the vapour pressure in hPa. Cloud correction: Crawford & Duchon
    (1999), eps = clf + (1 - clf) * eps_cs with clf the cloud fraction (0-1).

    Vectorized over pandas Series / numpy arrays.
    """
    temp_k = np.asarray(air_temp_c, dtype=float) + 273.15
    rh = np.asarray(rel_hum_pct, dtype=float)
    clf = np.clip(np.nan_to_num(np.asarray(cloud_frac, dtype=float)), 0.0, 1.0)

    e_a = (rh / 100.0) * saturation_vapor_pressure_hpa(temp_k - 273.15)
    eps_cs = 1.24 * (e_a / temp_k) ** (1.0 / 7.0)
    eps = clf + (1.0 - clf) * np.clip(eps_cs, 0.0, 1.0)
    return eps * STEFAN_BOLTZMANN * temp_k ** 4


def deaccumulate_era5(values_jm2, times_utc, timestep_s=3600):
    """Convert an ERA5-Land accumulated radiation series (J/m2) to mean flux (W/m2).

    ERA5-Land accumulations run from 00 UTC of the same day: the value stamped
    at hour H is the total since midnight, and the value stamped 00 UTC is the
    full previous day. A plain diff is therefore correct everywhere except the
    row stamped 01 UTC, where the accumulation has just reset and the flux is
    the raw value itself.
    """
    values = pd.Series(np.asarray(values_jm2, dtype=float))
    times = pd.DatetimeIndex(times_utc)

    flux = values.diff() / timestep_s
    reset = (times.hour == 1) & (times.minute == 0)
    flux[reset] = values[reset] / timestep_s
    # First row has no predecessor: spread the accumulation since 00 UTC over
    # the hours it covers (exact for constant flux; exact at 01 UTC).
    if len(flux) > 0 and np.isnan(flux.iloc[0]):
        hours_covered = times[0].hour if times[0].hour != 0 else 24
        flux.iloc[0] = values.iloc[0] / (hours_covered * 3600.0)
    return flux.clip(lower=0).to_numpy()


def rain_to_units(series_m_per_day, units):
    """Convert rainfall from the internal m/day convention to the given units."""
    if units == 'm/day':
        return series_m_per_day
    if units == 'mm/day':
        return series_m_per_day * 1000.0
    if units == 'mm/hour':
        return series_m_per_day * 1000.0 / 24.0
    raise ValueError(f"Unknown rain units: {units!r}")
