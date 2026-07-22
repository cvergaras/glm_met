import pandas as pd

from .utils import rain_to_units

GLM_COLUMNS = ['time', 'AirTemp', 'ShortWave', 'LongWave', 'RelHum',
               'WindSpeed', 'Rain', 'Snow', 'SoilTemp']


def finalize(df, rain_units='m/day', keep_cloud=False):
    """Shared post-processing applied to every source's normalized DataFrame.

    Orders columns, clips physically impossible values, converts rain units
    from the internal m/day convention, rounds, and warns about duplicate or
    missing timestamps.
    """
    df = df.copy()
    df['time'] = pd.to_datetime(df['time'])

    dupes = df['time'].duplicated()
    if dupes.any():
        print(f"[WARN] Dropping {int(dupes.sum())} duplicate timestamps")
        df = df[~dupes]
    df = df.sort_values('time').reset_index(drop=True)

    if len(df) > 1:
        step = df['time'].diff().dropna().mode().iloc[0]
        expected = pd.date_range(df['time'].iloc[0], df['time'].iloc[-1], freq=step)
        missing = expected.difference(df['time'])
        if len(missing) > 0:
            preview = ', '.join(str(t) for t in missing[:5])
            print(f"[WARN] {len(missing)} missing timesteps (e.g. {preview})")

    n_nan = int(df.drop(columns=['time']).isna().sum().sum())
    if n_nan:
        print(f"[WARN] {n_nan} missing values in the output — check source coverage")

    df['RelHum'] = df['RelHum'].clip(0, 100)
    df['ShortWave'] = df['ShortWave'].clip(lower=0)
    df['LongWave'] = df['LongWave'].clip(lower=0)
    for col in ('Rain', 'Snow'):
        df[col] = rain_to_units(df[col].clip(lower=0), rain_units)

    columns = list(GLM_COLUMNS)
    if keep_cloud and 'Cloud' in df.columns:
        columns.append('Cloud')
    columns = [c for c in columns if c in df.columns]
    df = df[columns]

    round_map = {c: 2 for c in df.columns if c != 'time'}
    round_map.update({'Rain': 6, 'Snow': 6, 'Cloud': 3})
    df = df.round({c: n for c, n in round_map.items() if c in df.columns})
    return df


def write_met_csv(df, path, timestep='hourly'):
    df = df.copy()
    fmt = '%Y-%m-%d %H:%M' if timestep == 'hourly' else '%Y-%m-%d'
    df['time'] = pd.to_datetime(df['time']).dt.strftime(fmt)
    df.to_csv(path, index=False)
